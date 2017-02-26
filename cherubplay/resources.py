from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.security import Allow, Everyone
from sqlalchemy import and_, func, or_, Integer
from sqlalchemy.dialects.postgres import ARRAY
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import cast

from cherubplay.models import (
    Session, BlacklistedTag, Chat, ChatUser, Prompt, PromptReport, Request,
    RequestTag, Resource, Tag,
)


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
    def is_continuable(self):
        return self.chat.status == "ongoing" and self.request.has_permission("chat.send")


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
        tag_filters = []

        split_tag_string = request.matchdict["tag_string"].split(",")[:5]
        for pair in split_tag_string:
            try:
                tag_type, name = pair.split(":")
            except ValueError:
                raise HTTPNotFound
            if tag_type not in Tag.type.type.enums:
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

        actual_tag_string = ",".join(":".join((tag.type, tag.url_name)) for tag in self.tags)
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

