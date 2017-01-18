from pyramid.httpexceptions import HTTPNotFound
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound

from cherubplay.models import (
    Session, Chat, ChatUser, Prompt, PromptReport, Request, RequestTag, Resource
)


class ChatContext(object):
    __parent__ = Resource

    def __init__(self, request):
        try:
            if request.user and request.user.status != "banned": # TODO ???
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

    @property
    def is_continuable(self):
        return self.chat.status == "ongoing" and self.chat_user is not None


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

