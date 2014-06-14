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
from pyramid.renderers import render_to_response
from pyramid.view import view_config
from redis.exceptions import ConnectionError
from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound
from webhelpers import paginate

from ..lib import colour_validator, symbols, preset_colours
from ..models import (
    Session,
    Chat,
    ChatUser,
    Message,
    User,
)


@view_config(route_name="chat_list", renderer="chat_list.mako", permission="view")
@view_config(route_name="chat_list_ongoing", renderer="chat_list.mako", permission="view")
@view_config(route_name="chat_list_ended", renderer="chat_list.mako", permission="view")
def chat_list(request):
    current_page = int(request.GET.get("page", 1))
    if request.matched_route.name == "chat_list_ongoing":
        current_status = "ongoing"
    elif request.matched_route.name == "chat_list_ended":
        current_status = "ended"
    else:
        current_status = None
    chats = Session.query(ChatUser, Chat, Message).join(Chat).outerjoin(
        Message,
        Message.id==Session.query(
            func.min(Message.id),
        ).filter(
            Message.chat_id==Chat.id,
        ).correlate(Chat),
    ).filter(
        ChatUser.user_id==request.user.id,
    )
    if current_status is not None:
        chats = chats.filter(Chat.status==current_status)
    chats = chats.order_by(Chat.updated.desc()).limit(25).offset((current_page-1)*25).all()
    # 404 on empty pages.
    if current_page!=1 and len(chats)==0:
        raise HTTPNotFound
    chat_count = Session.query(func.count('*')).select_from(ChatUser).filter(
        ChatUser.user_id==request.user.id,
    )
    if current_status is not None:
        chat_count = chat_count.join(Chat).filter(Chat.status==current_status)
    chat_count = chat_count.scalar()
    paginator = paginate.Page(
        [],
        page=current_page,
        items_per_page=25,
        item_count=chat_count,
        url=paginate.PageURL(
            request.route_path(request.matched_route.name),
            { "page": current_page }
        ),
    )
    return {
        "chats": chats,
        "paginator": paginator,
    }


@view_config(route_name="chat")
def chat(request):

    try:
        chat = Session.query(Chat).filter(Chat.url==request.matchdict["url"]).one()
    except NoResultFound:
        raise HTTPNotFound

    own_chat_user = None
    if request.user is not None and request.user.status!="banned":
        try:
            own_chat_user = Session.query(ChatUser).filter(
                and_(
                    ChatUser.chat_id==chat.id,
                    ChatUser.user_id==request.user.id,
                )
            ).one()
        except NoResultFound:
            pass

    continuable = chat.status=="ongoing" and own_chat_user is not None

    # If we can continue the chat and there isn't a page number, show the
    # full chat window.
    if ("page" not in request.GET and continuable):

        own_chat_user.visited = datetime.datetime.now()

        # Test if we came here from the homepage, for automatically resuming the search.
        from_homepage = (
            "HTTP_REFERER" in request.environ
            and request.environ["HTTP_REFERER"]==request.route_url("home")
        )

        message_count = Session.query(func.count('*')).select_from(Message).filter(
            Message.chat_id==chat.id,
        ).scalar()

        if message_count < 12:

            prompt = None
            messages = Session.query(Message).filter(
                Message.chat_id==chat.id,
            ).order_by(Message.id.asc()).all()

        else:

            prompt = Session.query(Message).filter(
                Message.chat_id==chat.id,
            ).order_by(Message.id.asc())
            prompt = prompt.options(joinedload(Message.user))
            prompt = prompt.first()

            messages = Session.query(Message).filter(
                Message.chat_id==chat.id,
            ).order_by(Message.id.desc()).limit(9)
            messages = messages.options(joinedload(Message.user))
            messages = messages.all()
            messages.reverse()

        # List users if we're an admin.
        # Get this from both message users and chat users, because the latter is
        # removed if they delete the chat.
        # XXX DON'T REALLY DELETE CHAT USER WHEN DELETING CHATS.
        symbol_users = None
        if request.user is not None and request.user.status=="admin":
            symbol_users = {
                _.symbol: _.user
                for _ in messages
                if _.user is not None
            }
            for chat_user in Session.query(ChatUser).filter(
                ChatUser.chat_id==chat.id
            ).options(joinedload(ChatUser.user)):
                symbol_users[chat_user.symbol] = chat_user.user

        return render_to_response("chat.mako", {
            "symbols": symbols,
            "preset_colours": preset_colours,
            "own_chat_user": own_chat_user,
            "from_homepage": from_homepage,
            "message_count": message_count,
            "prompt": prompt,
            "messages": messages,
            "symbol_users": symbol_users,
        }, request=request)

    # Otherwise show the archive view.

    # Update the visited time in archive view if the chat is ended.
    # We need to do this because otherwise it's impossible to mark an ended
    # chat as read.
    if chat.status=="ended" and own_chat_user is not None:
        own_chat_user.visited = datetime.datetime.now()

    try:
        current_page = int(request.GET["page"])
    except:
        current_page = 1

    messages = Session.query(Message).filter(
        Message.chat_id==chat.id,
    )
    message_count = Session.query(func.count('*')).select_from(Message).filter(
        Message.chat_id==chat.id,
    )

    # Hide OOC messages if the chat doesn't belong to us.
    # Also don't hide OOC messages for admins.
    if own_chat_user is None and (request.user is None or request.user.status!="admin"):
        messages = messages.filter(Message.type!="ooc")
        message_count = message_count.filter(Message.type!="ooc")

    # Join users if we're an admin.
    if request.user is not None and request.user.status=="admin":
        messages = messages.options(joinedload(Message.user))

    messages = messages.order_by(Message.id.asc()).limit(10).offset((current_page-1)*10).all()
    message_count = message_count.scalar()

    paginator = paginate.Page(
        [],
        page=current_page,
        items_per_page=10,
        item_count=message_count,
        url=paginate.PageURL(
            request.route_path("chat", url=request.matchdict["url"]),
            { "page": current_page }
        ),
    )

    # List users if we're an admin.
    # Get this from both message users and chat users, because the latter is
    # removed if they delete the chat.
    # XXX DON'T REALLY DELETE CHAT USER WHEN DELETING CHATS.
    symbol_users = None
    if request.user is not None and request.user.status=="admin":
        symbol_users = {
            _.symbol: _.user
            for _ in messages
            if _.user is not None
        }
        for chat_user in Session.query(ChatUser).filter(
            ChatUser.chat_id==chat.id
        ).options(joinedload(ChatUser.user)):
            symbol_users[chat_user.symbol] = chat_user.user

    return render_to_response("chat_archive.mako", {
        "symbols": symbols,
        "continuable": continuable,
        "messages": messages,
        "paginator": paginator,
        "symbol_users": symbol_users,
    }, request=request)


@view_config(route_name="chat_send", request_method="POST", permission="chat")
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
        "message_ooc" in request.POST
        or trimmed_message_text.startswith("((")
        or trimmed_message_text.endswith("))")
        or trimmed_message_text.startswith("[[")
        or trimmed_message_text.endswith("]]")
        or trimmed_message_text.startswith("{{")
        or trimmed_message_text.endswith("}}")
    ):
        message_type="ooc"
    posted_date = datetime.datetime.now()
    Session.add(Message(
        chat_id=chat.id,
        user_id=request.user.id,
        type=message_type,
        colour=colour,
        symbol=own_chat_user.symbol,
        text=trimmed_message_text,
        posted=posted_date,
        edited=posted_date,
    ))
    chat.updated = posted_date
    own_chat_user.last_colour = colour
    try:
        # See if anyone else is online and update their ChatUser too.
        online_symbols = [
            int(_) for _ in request.pubsub.hvals("online:"+str(chat.id))
        ]
        print online_symbols
        if len(online_symbols) != 0:
            Session.query(ChatUser).filter(and_(
                ChatUser.chat_id == chat.id,
                ChatUser.symbol.in_(online_symbols),
            )).update({ "visited": posted_date }, synchronize_session=False)
    except ConnectionError:
        pass
    try:
        request.pubsub.publish("chat:"+str(chat.id), json.dumps({
            "action": "message",
            "message": {
                "type": message_type,
                "colour": colour,
                "symbol": symbols[own_chat_user.symbol],
                "text": trimmed_message_text,
            },
        }))
    except ConnectionError:
        pass
    if request.is_xhr:
        return HTTPNoContent()
    return HTTPFound(request.route_path("chat", url=request.matchdict["url"]))


def _post_end_message(request, chat, own_chat_user):
    Session.add(Message(
        chat_id=chat.id,
        type="system",
        colour="000000",
        symbol=own_chat_user.symbol,
        text=u"%s ended the chat.",
    ))
    chat.status = "ended"
    update_date = datetime.datetime.now()
    chat.updated = update_date
    own_chat_user.visited = update_date
    try:
        # See if anyone else is online and update their ChatUser too.
        online_symbols = [
            int(_) for _ in request.pubsub.hvals("online:"+str(chat.id))
        ]
        print online_symbols
        if len(online_symbols) != 0:
            Session.query(ChatUser).filter(and_(
                ChatUser.chat_id == chat.id,
                ChatUser.symbol.in_(online_symbols),
            )).update({ "visited": posted_date }, synchronize_session=False)
    except ConnectionError:
        pass
    try:
        request.pubsub.publish("chat:"+str(chat.id), json.dumps({
            "action": "end",
            "message": {
                "type": "system",
                "colour": "000000",
                "symbol": symbols[own_chat_user.symbol],
                "text": u"%s ended the chat.",
            },
        }))
    except ConnectionError:
        pass


@view_config(route_name="chat_end", renderer="chat_end.mako", request_method="GET", permission="chat")
def chat_end_get(request):
	# XXX NEEDZ MOAR DECORATORS
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
    prompt = Session.query(Message).filter(
        Message.chat_id==chat.id,
    ).order_by(Message.id).first()
    last_message = Session.query(Message).filter(
        Message.chat_id==chat.id,
    ).order_by(Message.id.desc()).first()
    return {
        "action": "end",
        "chat": chat,
        "own_chat_user": own_chat_user,
        "prompt": prompt,
        "last_message": last_message,
        "symbols": symbols,
    }


@view_config(route_name="chat_end", request_method="POST", permission="chat")
def chat_end(request):
	# XXX NEEDZ MOAR DECORATORS
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
    _post_end_message(request, chat, own_chat_user)
    if request.is_xhr:
        return HTTPNoContent()
    if "continue_search" in request.POST:
        return HTTPFound(request.route_path("home"))
    return HTTPFound(request.route_path("chat_info", url=request.matchdict["url"], _query={ "saved": "end" }))


@view_config(route_name="chat_delete", renderer="chat_end.mako", request_method="GET", permission="view")
def chat_delete_get(request):
	# XXX NEEDZ MOAR DECORATORS
    try:
        chat = Session.query(Chat).filter(
            Chat.url==request.matchdict["url"],
        ).one()
        own_chat_user = Session.query(ChatUser).filter(
            and_(
                ChatUser.chat_id==chat.id,
                ChatUser.user_id==request.user.id,
            )
        ).one()
    except NoResultFound:
        raise HTTPNotFound
    prompt = Session.query(Message).filter(
        Message.chat_id==chat.id,
    ).order_by(Message.id).first()
    last_message = Session.query(Message).filter(
        Message.chat_id==chat.id,
    ).order_by(Message.id.desc()).first()
    return {
        "action": "delete",
        "chat": chat,
        "own_chat_user": own_chat_user,
        "prompt": prompt,
        "last_message": last_message,
        "symbols": symbols,
    }


@view_config(route_name="chat_delete", request_method="POST", permission="view")
def chat_delete(request):
	# XXX NEEDZ MOAR DECORATORS
    try:
        chat = Session.query(Chat).filter(
            Chat.url==request.matchdict["url"],
        ).one()
        own_chat_user = Session.query(ChatUser).filter(
            and_(
                ChatUser.chat_id==chat.id,
                ChatUser.user_id==request.user.id,
            )
        ).one()
    except NoResultFound:
        raise HTTPNotFound
    if chat.status=="ongoing":
        _post_end_message(request, chat, own_chat_user)
    Session.delete(own_chat_user)
    if request.is_xhr:
        return HTTPNoContent()
    return HTTPFound(request.route_path("chat_list"))


@view_config(route_name="chat_info", renderer="chat_info.mako", request_method="GET", permission="view")
def chat_info_get(request):
	# XXX NEEDZ MOAR DECORATORS
    try:
        chat = Session.query(Chat).filter(
            Chat.url==request.matchdict["url"],
        ).one()
        own_chat_user = Session.query(ChatUser).filter(
            and_(
                ChatUser.chat_id==chat.id,
                ChatUser.user_id==request.user.id,
            )
        ).one()
    except NoResultFound:
        raise HTTPNotFound
    if "notes" in request.POST:
        own_chat_user.title = request.POST["title"]
        own_chat_user.notes = request.POST["notes"]
    return { "chat": chat, "own_chat_user": own_chat_user }



@view_config(route_name="chat_info", renderer="chat_info.mako", request_method="POST", permission="view")
def chat_info(request):
	# XXX NEEDZ MOAR DECORATORS
    try:
        chat = Session.query(Chat).filter(
            Chat.url==request.matchdict["url"],
        ).one()
        own_chat_user = Session.query(ChatUser).filter(
            and_(
                ChatUser.chat_id==chat.id,
                ChatUser.user_id==request.user.id,
            )
        ).one()
    except NoResultFound:
        raise HTTPNotFound
    own_chat_user.title = request.POST["title"]
    own_chat_user.notes = request.POST["notes"]
    return HTTPFound(request.route_path("chat_info", url=request.matchdict["url"], _query={ "saved": "info" }))

