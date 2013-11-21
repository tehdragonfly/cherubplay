import datetime
import re
import transaction

from pyramid.httpexceptions import (
    HTTPBadRequest,
    HTTPForbidden,
    HTTPFound,
    HTTPNotFound,
)
from pyramid.view import view_config
from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound

from ..models import (
    Session,
    Chat,
    ChatUser,
    Message,
)

colour_validator = re.compile("^[A-Fa-f0-9]{6}$")

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

@view_config(route_name="chat_send", request_method="POST")
def chat_send(request):
    # Messages can only be sent in ongoing chats.
    try:
        chat = Session.query(Chat).filter(and_(
            Chat.url==request.matchdict["url"],
            Chat.status=="ongoing",
        )).one()
    except NoResultFound:
        raise HTTPNotFound
    # We have to be a member of this chat to send a message.
    try:
        own_chat_user = Session.query(ChatUser).filter(
            and_(
                ChatUser.chat_id==chat.id,
                ChatUser.user_id==request.user.id,
            )
        ).one()
    except NoResultFound:
        raise HTTPForbidden
    colour = request.POST["message_colour"]
    if colour.startswith("#"):
        colour = colour[1:]
    if colour_validator.match(colour) is None:
        raise HTTPBadRequest("Invalid text colour. The colour needs to be a 6-digit hex code.")
    if request.POST["message_text"]=="":
        raise HTTPBadRequest("Message text can't be empty.")
    message_type = "ic"
    if (
        request.POST["message_text"].startswith("((")
        or request.POST["message_text"].endswith("))")
        or request.POST["message_text"].startswith("[[")
        or request.POST["message_text"].endswith("]]")
        or request.POST["message_text"].startswith("{{")
        or request.POST["message_text"].endswith("}}")
    ):
        message_type="ooc"
    Session.add(Message(
        chat_id=chat.id,
        user_id=request.user.id,
        type=message_type,
        colour=colour,
        text=request.POST["message_text"],
    ))
    chat.updated = datetime.datetime.now()
    # XXX OWN_CHAT_USER DATE
    transaction.commit()
    raise HTTPFound(request.route_path("chat", url=request.matchdict["url"]))

