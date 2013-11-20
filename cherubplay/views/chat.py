from pyramid.httpexceptions import HTTPNotFound
from pyramid.view import view_config
from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound

from ..models import (
    Session,
    Chat,
    ChatUser,
    Message,
)

@view_config(route_name="chat", renderer="chat.mako")
def chat(request):
    try:
        chat = Session.query(Chat).filter(Chat.url==request.matchdict["url"]).one()
    except NoResultFound:
        raise HTTPNotFound
    own_chat_user = None
    if request.user is not None:
        try:
            own_chat_user = Session.query(ChatUser).filter(
                and_(
                    ChatUser.chat_id==chat.id,
                    ChatUser.user_id==request.user.id,
                )
            ).one()
        except NoResultFound:
            pass
    continuable = (chat.status=="ongoing" and own_chat_user is not None)
    messages = Session.query(Message, ChatUser).filter(
        Message.chat_id==chat.id
    )
    # Hide OOC messages if the chat doesn't belong to us.
    if own_chat_user is None:
        messages = messages.filter(Message.type!="ooc")
    messages = messages.outerjoin(
        ChatUser,
        and_(
            Message.chat_id==ChatUser.chat_id,
            Message.user_id==ChatUser.user_id,
        ),
    ).order_by(Message.id.asc()).all()
    return {
        "own_chat_user": own_chat_user,
        "continuable": continuable,
        "messages": messages,
    }

