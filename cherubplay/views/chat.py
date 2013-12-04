import datetime
import json
import transaction

from pyramid.httpexceptions import (
    HTTPBadRequest,
    HTTPForbidden,
    HTTPFound,
    HTTPNoContent,
    HTTPNotFound,
)
from pyramid.view import view_config
from redis.exceptions import ConnectionError
from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound

from ..lib import colour_validator, symbols, preset_colours
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
    messages = Session.query(Message).filter(
        Message.chat_id==chat.id
    )
    # Hide OOC messages if the chat doesn't belong to us.
    if own_chat_user is None:
        messages = messages.filter(Message.type!="ooc")
    messages = messages.order_by(Message.id.asc()).all()
    return {
        "own_chat_user": own_chat_user,
        "continuable": continuable,
        "messages": messages,
        "symbols": symbols,
        "preset_colours": preset_colours,
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
    trimmed_message_text = request.POST["message_text"].strip()
    if trimmed_message_text=="":
        raise HTTPBadRequest("Message text can't be empty.")
    message_type = "ic"
    if (
        trimmed_message_text.startswith("((")
        or trimmed_message_text.endswith("))")
        or trimmed_message_text.startswith("[[")
        or trimmed_message_text.endswith("]]")
        or trimmed_message_text.startswith("{{")
        or trimmed_message_text.endswith("}}")
    ):
        message_type="ooc"
    Session.add(Message(
        chat_id=chat.id,
        user_id=request.user.id,
        type=message_type,
        colour=colour,
        symbol=own_chat_user.symbol,
        text=trimmed_message_text,
    ))
    # Create pubsub message here, but wait until we've committed before sending it.
    chat_id = chat.id
    pubsub_message = {
        "action": "message",
        "message": {
            "type": message_type,
            "colour": colour,
            "symbol": symbols[own_chat_user.symbol],
            "text": trimmed_message_text,
        },
    }
    chat.updated = datetime.datetime.now()
    # XXX OWN_CHAT_USER DATE
    own_chat_user.last_colour = colour
    transaction.commit()
    try:
        request.pubsub.publish("chat:"+str(chat_id), json.dumps(pubsub_message))
    except ConnectionError:
        pass
    if request.is_xhr:
        raise HTTPNoContent
    raise HTTPFound(request.route_path("chat", url=request.matchdict["url"]))


@view_config(route_name="chat_end", request_method="POST")
def chat_end(request):
    try:
        chat = Session.query(Chat).filter(and_(
            Chat.url==request.matchdict["url"],
            Chat.status=="ongoing",
        )).one()
    except NoResultFound:
        raise HTTPNotFound
    try:
        own_chat_user = Session.query(ChatUser).filter(
            and_(
                ChatUser.chat_id==chat.id,
                ChatUser.user_id==request.user.id,
            )
        ).one()
    except NoResultFound:
        raise HTTPForbidden
    Session.add(Message(
        chat_id=chat.id,
        type="system",
        colour="000000",
        symbol=own_chat_user.symbol,
        text=u"%s ended the chat.",
    ))
    # Create pubsub message here, but wait until we've committed before sending it.
    chat_id = chat.id
    pubsub_message = {
        "action": "end",
        "message": {
            "type": "system",
            "colour": "000000",
            "symbol": symbols[own_chat_user.symbol],
            "text": u"%s ended the chat.",
        },
    }
    chat.status = "ended"
    chat.updated = datetime.datetime.now()
    transaction.commit()
    try:
        request.pubsub.publish("chat:"+str(chat_id), json.dumps(pubsub_message))
    except ConnectionError:
        pass
    if request.is_xhr:
        raise HTTPNoContent
    raise HTTPFound(request.route_path("chat", url=request.matchdict["url"]))

