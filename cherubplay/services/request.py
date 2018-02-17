import datetime

from collections.abc import Sequence
from sqlalchemy import and_, func, Integer
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import joinedload, subqueryload
from sqlalchemy.sql.expression import cast
from sqlalchemy.sql.operators import asc_op, desc_op
from typing import List, Set, Union
from uuid import uuid4
from zope.interface import Interface, implementer

from cherubplay.lib import prompt_hash
from cherubplay.models import Request, Tag, User, Chat, ChatUser, Message, RequestTag, RequestSlot
from cherubplay.models.enums import ChatMode, ChatSource


class RequestList(Sequence):
    def __init__(
        self,
        requests: List[Request],
        answered: Set[int],
        next_page_start: datetime.datetime=None,
    ):
        self._requests = requests
        self.answered  = answered
        self.next_page_start = next_page_start

    def __len__(self):
        return self._requests.__len__()

    def __getitem__(self, key):
        return self._requests[key]

    def __json__(self, request=None):
        return list(self)


sort_choices = {
    "posted":        (Request.posted, desc_op),
    "edited":        (Request.edited, desc_op),
    "posted_oldest": (Request.posted, asc_op),
    "edited_oldest": (Request.edited, asc_op),
}


class IRequestService(Interface):
    def __init__(self, request): # Pyramid request, not Request
        pass

    def search(
        self,
        for_user: User=None,
        with_tags: List[Tag]=None,
        by_user: User=None,
        posted_only: bool=True,
        sort: str="posted",
        start: Union[str, datetime.datetime]=None,
        page_size=25,
    ) -> RequestList:
        pass

    def random(self, for_user: User=None) -> int:
        pass

    def remove_duplicates(self, new_request: Request):
        pass

    def answer(self, request: Request, as_user: User = None) -> Chat:
        pass

    def delete(self, request: Request):
        pass


@implementer(IRequestService)
class RequestService(object):
    def __init__(self, request):
        self._db    = request.find_service(name="db")
        self._redis = request.login_store

    def search(
        self,
        for_user: User=None,
        with_tags: List[Tag]=None,
        by_user: User=None,
        posted_only: bool=True,
        sort: str="posted",
        start: Union[str, datetime.datetime]=None,
        page_size=25,
    ) -> RequestList:

        query = self._db.query(Request)

        # Blacklist filter
        if for_user and for_user.blacklist_filter is not None:
            query = query.filter(for_user.blacklist_filter)

        # Filter by tags
        if with_tags:
            tag_array = cast([tag.id for tag in with_tags], ARRAY(Integer))
            query = query.filter(Request.tag_ids.contains(tag_array))

        # Filter by user
        if by_user:
            query = query.filter(Request.user_id == by_user.id)

        # Posted only
        if posted_only:
            query = query.filter(Request.status == "posted")

        # Sort
        try:
            sort_field, sort_operator = sort_choices[sort]
        except KeyError:
            raise ValueError("Not a valid sort order.")
        # Request.posted may be null on drafts.
        if not posted_only and sort_field == Request.posted:
            query = query.order_by(func.coalesce(Request.posted, Request.created).operate(sort_operator))
        else:
            query = query.order_by(sort_field.operate(sort_operator))

        # Page start
        if start:
            if type(start) != datetime.datetime:
                try:
                    start = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S.%f")
                except ValueError:
                    raise ValueError("Not a valid start.")
            if sort_operator == asc_op:
                query = query.filter(sort_field > start)
            else:
                query = query.filter(sort_field < start)

        # Page size
        query = query.limit(page_size + 1)

        # Join tags and slots
        query = query.options(
            joinedload(Request.tags),
            subqueryload(Request.slots),
        )

        requests = query.all()

        if for_user:
            pipe = self._redis.pipeline()
            for rq in requests:
                pipe.get("answered:%s:%s" % (for_user.id, rq.id))
            answered = set(int(_) for _ in pipe.execute() if _ is not None)
        else:
            answered = set()

        if len(requests) == page_size + 1:
            if not posted_only and sort_field == Request.posted:
                next_page_start = requests[-1].posted or requests[-1].created
            else:
                next_page_start = getattr(requests[-1], sort_field.name)
            requests.pop()
        else:
            next_page_start = None

        return RequestList(requests, answered, next_page_start)

    def random(self, for_user: User=None) -> int:
        query = self._db.query(Request.id).filter(Request.status == "posted")

        if for_user:
            query = query.filter(Request.user_id != for_user.id)
            if for_user.blacklist_filter is not None:
                query = query.filter(for_user.blacklist_filter)

        row = query.order_by(func.random()).first()
        return row[0] if row else None

    def remove_duplicates(self, new_request: Request):
        new_hash = prompt_hash(new_request.ooc_notes + new_request.starter)
        duplicate_ids = {
            old_request.id
            for old_request in self._db.query(Request).filter(and_(
                Request.id != new_request.id,
                Request.user_id == new_request.user_id,
                Request.status == "posted",
            ))
            if new_hash == prompt_hash(old_request.ooc_notes + old_request.starter)
        }
        self._db.query(Request).filter(Request.id.in_(duplicate_ids)).update({
            "status": "draft",
            "duplicate_of_id": new_request.id,
        }, synchronize_session=False)

    def answer(self, request: Request, as_user: User=None) -> Chat:
        if request.slots and as_user is None:
            raise ValueError("as_user must be provided if there are no slots")

        new_chat = Chat(url=str(uuid4()), request_id=request.id, source=ChatSource.directory)

        if request.slots:
            new_chat.mode = ChatMode.group
            new_chat.op_id = request.user_id

        self._db.add(new_chat)
        self._db.flush()

        if request.slots:
            if not request.slots.all_taken:
                raise ValueError("can't answer until all slots are taken")

            used_names = set()
            for slot in request.slots:

                if slot.user_id != request.user_id:
                    self._redis.setex("answered:%s:%s" % (slot.user_id, request.id), 86400, request.id)

                if slot.user_name in used_names:
                    for n in range(2, 6):
                        attempt = slot.user_name + (" (%s)" % n)
                        if attempt not in used_names:
                            slot.user_name = attempt
                            break

                used_names.add(slot.user_name)

                new_chat_user = ChatUser(chat_id=new_chat.id, user_id=slot.user_id, name=slot.user_name)

                if slot.user_id == request.user_id:
                    new_chat_user.last_colour = request.colour
                else:
                    slot.user_id = None
                    slot.user_name = None

                self._db.add(new_chat_user)
        else:
            self._redis.setex("answered:%s:%s" % (as_user.id, request.id), 86400, request.id)
            self._db.add(ChatUser(chat_id=new_chat.id, user_id=request.user_id, symbol=0, last_colour=request.colour))
            self._db.add(ChatUser(chat_id=new_chat.id, user_id=as_user.id, symbol=1))

        if request.ooc_notes:
            self._db.add(Message(
                chat_id=new_chat.id,
                user_id=request.user_id,
                symbol=None if request.slots else 0,
                text=request.ooc_notes,
            ))
        if request.starter:
            self._db.add(Message(
                chat_id=new_chat.id,
                user_id=request.user_id,
                symbol=None if request.slots else 0,
                colour=request.colour,
                text=request.starter,
            ))

        return new_chat

    def delete(self, request: Request):
        self._db.query(Chat).filter(Chat.request_id == request.id).update({"request_id": None})
        self._db.query(Request).filter(Request.duplicate_of_id == request.id).update({"duplicate_of_id": None})
        self._db.query(RequestTag).filter(RequestTag.request_id == request.id).delete()
        self._db.query(RequestSlot).filter(RequestSlot.request_id == request.id).delete()
        self._db.query(Request).filter(Request.id == request.id).delete()


def includeme(config):
    config.register_service_factory(lambda context, request: RequestService(request), iface=IRequestService)
