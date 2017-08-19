import transaction

from collections import OrderedDict
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.security import Allow, Everyone
from sqlalchemy import and_, func, or_, Integer
from sqlalchemy.dialects.postgres import ARRAY
from sqlalchemy.orm import contains_eager, joinedload
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import cast

from cherubplay.models import (
    Session, BlacklistedTag, Chat, ChatUser, Message, Prompt, PromptReport,
    Request, RequestTag, Resource, Tag, User,
)
from cherubplay.models.enums import ChatUserStatus, TagType
from cherubplay.tasks import update_missing_request_tag_ids


class ChatContext(object):
    __parent__ = Resource

    @reify
    def __acl__(self):
        if self.chat_user:
            return [
                # Everyone so banned users can see their own stuff.
                (Allow, Everyone, "chat.read"),
                (Allow, Everyone, "chat.read_ooc"),
                (Allow, "admin",  "chat.full_user_list"),
                (Allow, "active", "chat.send"),
                (Allow, Everyone, "chat.info"),
                (Allow, "active", "chat.change_name"),
            ]
        return [
            (Allow, Everyone, "chat.read"),
            (Allow, "admin",  "chat.read_ooc"),
            (Allow, "admin",  "chat.full_user_list"),
        ]

    def __init__(self, request):
        self.request = request
        try:
            if request.user:
                self.chat, self.chat_user = Session.query(Chat, ChatUser).filter(
                    Chat.url == request.matchdict["url"],
                ).outerjoin(ChatUser, and_(
                    ChatUser.chat_id == Chat.id,
                    ChatUser.user_id == request.user.id,
                    ChatUser.status == ChatUserStatus.active,
                )).one()
            else:
                self.chat = Session.query(Chat).filter(Chat.url == request.matchdict["url"]).one()
                self.chat_user = None
        except NoResultFound:
            raise HTTPNotFound

    def __repr__(self):
        if self.chat_user:
            return "<ChatContext: User #%s in Chat %s>" % (self.chat_user.user_id, self.chat.id)
        return "<ChatContext: guest in Chat %s>" % self.chat.id

    @reify
    def mode(self):
        if self.chat_user and self.chat_user.name is not None:
            return "group"
        elif self.chat_users and next(iter(self.chat_users.values())).name is not None:
            return "group"
        return "1-on-1"

    @reify
    def is_continuable(self):
        return self.chat.status == "ongoing" and self.request.has_permission("chat.send")

    @reify
    def chat_users(self):
        return OrderedDict([
            (chat_user.user_id, chat_user)
            for chat_user in Session.query(ChatUser).join(User).filter(and_(
                ChatUser.chat_id == self.chat.id,
            )).options(contains_eager(ChatUser.user)).order_by(ChatUser.name).all()
        ])

    @reify
    def active_chat_users(self):
        return OrderedDict([(k, v) for k, v in self.chat_users.items() if v.status == ChatUserStatus.active])

    @reify
    def banned_chat_users(self):
        return [
            _ for _ in self.chat_users.values()
            if _.status == ChatUserStatus.active
            and _.user.status == "banned"
        ]

    @reify
    def away_chat_users(self):
        return [
            _ for _ in self.chat_users.values()
            if _.status == ChatUserStatus.active
            and _.user.away_message
        ]

    @reify
    def first_message(self):
        return (
            Session.query(Message)
            .filter(Message.chat_id == self.chat.id)
            .order_by(Message.id).first()
        )


def prompt_factory(request):
    if not request.user:
        raise HTTPNotFound

    try:
        return Session.query(Prompt).filter(and_(
            Prompt.user_id == request.user.id,
            Prompt.id == int(request.matchdict["id"]),
        )).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound


def report_factory(request):
    try:
        return Session.query(PromptReport).filter(
            PromptReport.id == int(request.matchdict["id"])
        ).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound


class TagList(object):
    __parent__ = Resource

    def __init__(self, request):
        if not request.user:
            raise HTTPNotFound

        tag_filters = []

        split_tag_string = request.matchdict["tag_string"].split(",")[:5]
        for pair in split_tag_string:
            try:
                tag_type_string, name = pair.split(":")
            except ValueError:
                raise HTTPNotFound
            try:
                tag_type = TagType(tag_type_string)
            except ValueError:
                raise HTTPNotFound

            tag_filters.append(and_(
                Tag.type == tag_type,
                func.lower(Tag.name) == Tag.name_from_url(name.strip().lower()),
            ))

        self.tags = [
            tag.synonym_of or tag for tag in
            Session.query(Tag).filter(or_(*tag_filters))
            .options(joinedload(Tag.synonym_of))
            .order_by(Tag.type, Tag.name)
        ]

        if len(self.tags) < len(split_tag_string):
            # One or more tags don't exist, so there won't be any results here.
            raise HTTPNotFound

        actual_tag_string = ",".join(tag.tag_string for tag in self.tags)
        if actual_tag_string != request.matchdict["tag_string"]:
            raise HTTPFound(request.current_route_path(tag_string=actual_tag_string))

        self.blacklisted_tags = [
            _.tag for _ in
            Session.query(BlacklistedTag)
            .filter(and_(
                BlacklistedTag.user_id == request.user.id,
                BlacklistedTag.tag_id.in_(tag.id for tag in self.tags),
            )).all()
        ]

        self.tag_array = cast([tag.id for tag in self.tags], ARRAY(Integer))

    def tag_string_plus(self, extra_tag):
        tag_list = list(self.tags)
        tag_list.append(extra_tag)
        tag_list.sort(key=lambda tag: (Tag.type, Tag.name))
        return ",".join(tag.tag_string for tag in tag_list)


class TagPair(object):
    __parent__ = Resource

    def __init__(self, request):
        try:
            request_tag_type = TagType(request.matchdict["type"])
        except ValueError:
            raise HTTPNotFound
        tag_name = Tag.name_from_url(request.matchdict["name"])

        self.tags = [
            Tag.get_or_create(tag_type, tag_name)
            for tag_type in request_tag_type.pair
        ]

    def set_bump_maturity(self, value: bool):
        for tag in self.tags:
            tag.bump_maturity = value

            if value:
                Session.query(RequestTag).filter(and_(
                    RequestTag.request_id.in_(
                        Session.query(RequestTag.request_id)
                        .filter(RequestTag.tag_id == tag.id)
                    ),
                    RequestTag.tag_id.in_(
                        Session.query(Tag.id).filter(and_(
                            Tag.type == TagType.maturity,
                            Tag.name.in_(("Safe for work", "Not safe for work")),
                        ))
                    ),
                )).update({"tag_id": Session.query(Tag.id).filter(and_(
                    Tag.type == TagType.maturity,
                    Tag.name == "NSFW extreme",
                )).as_scalar()}, synchronize_session=False)

                Session.query(Request).filter(and_(
                    Request.id.in_(
                        Session.query(RequestTag.request_id)
                        .filter(RequestTag.tag_id == tag.id)
                    ),
                )).update({"tag_ids": None}, synchronize_session=False)

        # Commit manually to make sure the task happens after.
        transaction.commit()
        update_missing_request_tag_ids.delay()


def request_factory(request):
    if not request.user:
        raise HTTPNotFound

    try:
        return Session.query(Request).filter(and_(
            Request.id == int(request.matchdict["id"]),
            or_(
                request.user.tag_status_filter,
                Request.user_id == request.user.id,
            ),
        )).options(
            joinedload(Request.tags)
        ).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound


def user_factory(request):
    try:
        return Session.query(User).filter(User.username == request.matchdict["username"]).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound

