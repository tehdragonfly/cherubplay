import datetime

from collections.abc import Sequence
from sqlalchemy import Integer
from sqlalchemy.dialects.postgres import ARRAY
from sqlalchemy.orm import joinedload, subqueryload
from sqlalchemy.sql.expression import cast
from sqlalchemy.sql.operators import asc_op, desc_op
from typing import Dict, List, Union
from zope.interface import Interface, implementer

from cherubplay.models import Session, Request, Tag, User


class RequestList(Sequence):
    def __init__(
        self,
        requests: List[Request],
        answered: Dict[int, bool],
        next_page_start: datetime.datetime=None,
    ):
        self._requests = requests
        self.answered  = answered
        self.next_page_start = next_page_start

    def __len__(self):
        return self._requests.__len__()

    def __getitem__(self, key):
        return self._requests[key]


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
        with_tags: List[Tag]=None,
        by_user: User=None,
        posted_only: bool=True,
        sort: str="posted",
        start: Union[str, datetime.datetime]=None,
        page_size=25,
    ) -> RequestList:
        pass


@implementer(IRequestService)
class RequestService(object):
    def __init__(self, request):
        self._db    = request.find_service(name="db")
        self._redis = request.login_store # TODO login or pubsub?

    def search(
        self,
        with_tags: List[Tag]=None,
        by_user: User=None,
        posted_only: bool=True,
        sort: str="posted",
        start: Union[str, datetime.datetime]=None,
        page_size=25,
    ) -> RequestList:

        query = self._db.query(Request)

        # TODO blacklisting

        # Filter by tags
        if with_tags:
            tag_array = cast([tag.id for tag in with_tags], ARRAY(Integer))
            query = query.filter(Request.tag_ids.contains(tag_array))

        # Filter by user
        if by_user:
            query = query.filter(Request.user_id == by_user.id)

        # Posted only
        # TODO do something about the Request.posted filter if drafts are shown
        if posted_only:
            query = query.filter(Request.status == "posted")

        # Sort
        try:
            sort_field, sort_operator = sort_choices[sort]
        except KeyError:
            raise ValueError("Not a valid sort order.")
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

        answered = {} # TODO

        if len(requests) == page_size + 1:
            next_page_start = requests[-1]
            requests.pop()
        else:
            next_page_start = None

        return RequestList(requests, answered, next_page_start)

def includeme(config):
    config.register_service_factory(lambda context, request: RequestService(request), iface=IRequestService)
