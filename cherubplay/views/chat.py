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
from sqlalchemy import and_, func, Unicode
from sqlalchemy.dialects.postgres import array, ARRAY
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import cast
from webhelpers import paginate

from ..lib import alt_formats, colour_validator, symbols, preset_colours
from ..models import (
    Session,
    Chat,
    ChatUser,
    Message,
    User,
)


@alt_formats({"json"})
def chat_list(request):

    current_page = int(request.GET.get("page", 1))

    if request.matched_route.name.startswith("chat_list_unanswered"):
        current_status = "unanswered"
    elif request.matched_route.name.startswith("chat_list_ongoing"):
        current_status = "ongoing"
    elif request.matched_route.name.startswith("chat_list_ended"):
        current_status = "ended"
    else:
        current_status = None

    if request.matched_route.name.startswith("chat_list_label"):
        current_label = request.matchdict["label"].lower().strip().replace(" ", "_")
        if current_label != request.matchdict["label"]:
            raise HTTPFound(request.route_path("chat_list_label", label=current_label))
    else:
        current_label = None

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

    chat_count = Session.query(func.count('*')).select_from(ChatUser).filter(
        ChatUser.user_id==request.user.id,
    )

    if current_status == "unanswered":
        chats = chats.filter(and_(
            Chat.last_user_id is not None,
            Chat.last_user_id != request.user.id,
        ))
        chat_count = chat_count.join(Chat).filter(and_(
            Chat.last_user_id is not None,
            Chat.last_user_id != request.user.id,
        ))
    elif current_status is not None:
        chats = chats.filter(Chat.status==current_status)
        chat_count = chat_count.join(Chat).filter(Chat.status==current_status)

    if current_label is not None:
        label_array = cast([current_label], ARRAY(Unicode(500)))
        chats = chats.filter(ChatUser.labels.contains(label_array))
        chat_count = chat_count.filter(ChatUser.labels.contains(label_array))

    chats = chats.order_by(Chat.updated.desc()).limit(25).offset((current_page-1)*25).all()

    # 404 on empty pages, unless it's the first page.
    if current_page!=1 and len(chats)==0:
        raise HTTPNotFound

    chat_count = chat_count.scalar()

    if request.matchdict.get("fmt") == "json":
        return render_to_response("json", {
            "chats": [{
                "chat_user": chat_user,
                "chat": chat,
                "prompt": prompt,
            } for chat_user, chat, prompt in chats],
            "chat_count": chat_count,
        }, request=request)

    paginator = paginate.Page(
        [],
        page=current_page,
        items_per_page=25,
        item_count=chat_count,
        url=paginate.PageURL(
            request.route_path(request.matched_route.name, label=current_label),
            { "page": current_page }
        ),
    )

    labels = (
        Session.query(func.unnest(ChatUser.labels), func.count("*"))
        .filter(ChatUser.user_id == request.user.id)
        .group_by(func.unnest(ChatUser.labels))
        .order_by(func.count("*").desc(), func.unnest(ChatUser.labels).asc()).all()
    )

    return render_to_response("chat_list.mako", {
        "chats": chats,
        "paginator": paginator,
        "labels": labels,
        "current_status": current_status,
        "current_label": current_label,
    }, request=request)


@alt_formats({"json"})
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

        if message_count < 30:

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
            ).order_by(Message.id.desc()).limit(25)
            messages = messages.options(joinedload(Message.user))
            messages = messages.all()
            messages.reverse()

        if request.matchdict.get("fmt") == "json":
            return render_to_response("json",{
                "chat": chat,
                "chat_user": own_chat_user,
                "message_count": message_count,
                "prompt": prompt,
                "messages": messages,
            }, request=request)

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

        template = "layout2/chat.mako" if request.user.layout_version == 2 else "chat.mako"
        return render_to_response(template, {
            "page": "chat",
            "symbols": symbols,
            "preset_colours": preset_colours,
            "chat": chat,
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

    messages = messages.order_by(Message.id.asc()).limit(25).offset((current_page-1)*25).all()
    message_count = message_count.scalar()

    if request.matchdict.get("fmt") == "json":
        return render_to_response("json",{
            "chat": chat,
            "chat_user": own_chat_user,
            "message_count": message_count,
            "messages": messages,
        }, request=request)

    paginator = paginate.Page(
        [],
        page=current_page,
        items_per_page=25,
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

    template = "layout2/chat_archive.mako" if (
        request.user is None or request.user.layout_version == 2
    ) else "chat_archive.mako"
    return render_to_response(template, {
        "page": "archive",
        "symbols": symbols,
        "continuable": continuable,
        "chat": chat,
        "own_chat_user": own_chat_user,
        "messages": messages,
        "paginator": paginator,
        "symbol_users": symbol_users,
    }, request=request)


def _get_chat(request, ongoing=True):
    try:
        chat = Session.query(Chat).filter(
            Chat.url==request.matchdict["url"],
        )
        if ongoing:
            chat = chat.filter(Chat.status=="ongoing")
        chat = chat.one()
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
    return chat, own_chat_user


@view_config(route_name="chat_draft", request_method="POST", permission="chat")
def chat_draft(request):
    chat, own_chat_user = _get_chat(request)
    own_chat_user.draft = request.POST["message_text"].strip()
    return HTTPNoContent()


def _validate_message_form(request):
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
    return colour, trimmed_message_text, message_type


@view_config(route_name="chat_send", request_method="POST", permission="chat")
def chat_send(request):
    chat, own_chat_user = _get_chat(request)
    colour, trimmed_message_text, message_type = _validate_message_form(request)
    posted_date = datetime.datetime.now()
    new_message = Message(
        chat_id=chat.id,
        user_id=request.user.id,
        type=message_type,
        colour=colour,
        symbol=own_chat_user.symbol,
        text=trimmed_message_text,
        posted=posted_date,
        edited=posted_date,
    )
    Session.add(new_message)
    Session.flush()
    chat.updated = posted_date
    chat.last_user_id = request.user.id
    own_chat_user.last_colour = colour
    own_chat_user.draft = ""
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
                "id": new_message.id,
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


@view_config(route_name="chat_edit", request_method="POST", permission="chat")
def chat_edit(request):
    chat, own_chat_user = _get_chat(request)
    try:
        message = Session.query(Message).filter(and_(
            Message.id == request.matchdict["message_id"],
            Message.chat_id == chat.id,
            Message.user_id == request.user.id,
            # XXX DATE FILTER?
        )).one()
    except NoResultFound:
        raise HTTPNotFound
    colour, trimmed_message_text, message_type = _validate_message_form(request)
    message.type = message_type
    message.colour = colour
    message.text = trimmed_message_text
    message.edited = datetime.datetime.now()
    try:
        request.pubsub.publish("chat:"+str(chat.id), json.dumps({
            "action": "edit",
            "message": {
                "id": message.id,
                "type": message.type,
                "colour": message.colour,
                "symbol": symbols[message.symbol],
                "text": message.text,
                "show_edited": message.show_edited(),
            },
        }))
    except ConnectionError:
        pass
    if request.is_xhr:
        return HTTPNoContent()
    return HTTPFound(request.environ["HTTP_REFERER"])


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
    chat.last_user_id = None
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
            )).update({ "visited": update_date }, synchronize_session=False)
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
    chat, own_chat_user = _get_chat(request)
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
    chat, own_chat_user = _get_chat(request)
    _post_end_message(request, chat, own_chat_user)
    if request.is_xhr:
        return HTTPNoContent()
    if "continue_search" in request.POST:
        return HTTPFound(request.route_path("home"))
    return HTTPFound(request.route_path("chat_info", url=request.matchdict["url"], _query={ "saved": "end" }))


@view_config(route_name="chat_delete", renderer="chat_end.mako", request_method="GET", permission="view")
def chat_delete_get(request):
    chat, own_chat_user = _get_chat(request, ongoing=False)
    prompt = Session.query(Message).filter(
        Message.chat_id==chat.id,
    ).order_by(Message.id).first()
    last_message = Session.query(Message).filter(and_(
        Message.chat_id==chat.id,
        Message.type!="system",
    )).order_by(Message.id.desc()).first()
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
    chat, own_chat_user = _get_chat(request, ongoing=False)
    if chat.status=="ongoing":
        _post_end_message(request, chat, own_chat_user)
    Session.delete(own_chat_user)
    if request.is_xhr:
        return HTTPNoContent()
    return HTTPFound(request.route_path("chat_list"))


@view_config(route_name="chat_info", renderer="chat_info.mako", request_method="GET", permission="view")
def chat_info_get(request):
    chat, own_chat_user = _get_chat(request, ongoing=False)
    return { "chat": chat, "own_chat_user": own_chat_user }


@view_config(route_name="chat_info", renderer="chat_info.mako", request_method="POST", permission="view")
def chat_info(request):
    chat, own_chat_user = _get_chat(request, ongoing=False)
    own_chat_user.title = request.POST["title"][:100]
    own_chat_user.notes = request.POST["notes"]
    labels_set = set()
    for label in request.POST["labels"].lower().replace("\n", " ").split(","):
        label = label.strip()
        if label == "":
            continue
        labels_set.add(label.replace(" ", "_"))
    labels_list = list(labels_set)
    labels_list.sort()
    own_chat_user.labels = labels_list
    return HTTPFound(request.route_path("chat_info", url=request.matchdict["url"], _query={ "saved": "info" }))

