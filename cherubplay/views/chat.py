import datetime
import json

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
from sqlalchemy.dialects.postgres import ARRAY
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import cast

from cherubplay.lib import colour_validator, preset_colours, OnlineUserStore
from cherubplay.models import Session, Chat, ChatUser, Message
from cherubplay.models.enums import ChatMode, ChatUserStatus
from cherubplay.tasks import trigger_push_notification


@view_config(route_name="chat_list",                request_method="GET", permission="view")
@view_config(route_name="chat_list_ext",            request_method="GET", permission="view", extension="json", renderer="json")
@view_config(route_name="chat_list_unanswered",     request_method="GET", permission="view")
@view_config(route_name="chat_list_unanswered_ext", request_method="GET", permission="view", extension="json", renderer="json")
@view_config(route_name="chat_list_ongoing",        request_method="GET", permission="view")
@view_config(route_name="chat_list_ongoing_ext",    request_method="GET", permission="view", extension="json", renderer="json")
@view_config(route_name="chat_list_ended",          request_method="GET", permission="view")
@view_config(route_name="chat_list_ended_ext",      request_method="GET", permission="view", extension="json", renderer="json")
@view_config(route_name="chat_list_label",          request_method="GET", permission="view")
@view_config(route_name="chat_list_label_ext",      request_method="GET", permission="view", extension="json", renderer="json")
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
        Message.id == Session.query(
            func.min(Message.id),
        ).filter(
            Message.chat_id == Chat.id,
        ).correlate(Chat),
    ).filter(
        ChatUser.user_id == request.user.id,
        ChatUser.status == ChatUserStatus.active,
    )

    chat_count = Session.query(func.count('*')).select_from(ChatUser).filter(
        ChatUser.user_id == request.user.id,
        ChatUser.status == ChatUserStatus.active,
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
        chats = chats.filter(Chat.status == current_status)
        chat_count = chat_count.join(Chat).filter(Chat.status == current_status)

    if current_label is not None:
        label_array = cast([current_label], ARRAY(Unicode(500)))
        chats = chats.filter(ChatUser.labels.contains(label_array))
        chat_count = chat_count.filter(ChatUser.labels.contains(label_array))

    chats = chats.options(joinedload(Chat.request)).order_by(Chat.updated.desc()).limit(25).offset((current_page-1)*25).all()

    # 404 on empty pages, unless it's the first page.
    if current_page != 1 and len(chats) == 0:
        raise HTTPNotFound

    chat_count = chat_count.scalar()

    if request.matched_route.name.endswith("_ext"):
        return {
            "chats": [{
                "chat_user": chat_user,
                "chat": chat,
                "prompt": prompt,
            } for chat_user, chat, prompt in chats],
            "chat_count": chat_count,
        }

    labels = (
        Session.query(func.unnest(ChatUser.labels), func.count("*"))
        .filter(and_(
            ChatUser.user_id == request.user.id,
            ChatUser.status  == ChatUserStatus.active,
        ))
        .group_by(func.unnest(ChatUser.labels))
        .order_by(func.count("*").desc(), func.unnest(ChatUser.labels).asc()).all()
    )

    template = "layout2/chat_list.mako" if request.user.layout_version == 2 else "chat_list.mako"
    return render_to_response(template, {
        "chats": chats,
        "chat_count": chat_count,
        "current_page": current_page,
        "labels": labels,
        "current_status": current_status,
        "current_label": current_label,
    }, request=request)


@view_config(route_name="chat_notification", request_method="GET", permission="chat", renderer="json")
def chat_notification(request):
    result = Session.query(ChatUser, Chat).join(Chat).filter(and_(
        ChatUser.user_id == request.user.id,
        ChatUser.status == ChatUserStatus.active,
        Chat.updated > ChatUser.visited,
    )).order_by(Chat.updated.desc()).first()
    if not result:
        return None

    own_chat_user, chat = result

    message = (
        Session.query(Message)
        .filter(Message.chat_id == chat.id)
        .options(joinedload(Message.chat_user))
        .order_by(Message.id.desc()).first()
    )
    if not message:
        return None

    return {
        "action": "notification",
        "url":    chat.url,
        "title":  own_chat_user.title or chat.url,
        "colour": message.colour,
        "handle": message.chat_user.handle,
        "text":   message.text if len(message.text) < 100 else message.text[:97] + "...",
    }


@view_config(route_name="chat",     request_method="GET", permission="chat.read")
@view_config(route_name="chat_ext", request_method="GET", permission="chat.read", extension="json", renderer="json")
def chat(context, request):
    # If we can continue the chat and there isn't a page number, show the
    # full chat window.
    if "page" not in request.GET and context.is_continuable:

        context.chat_user.visited = datetime.datetime.now()

        # Test if we came here from the homepage, for automatically resuming the search.
        from_homepage = request.environ.get("HTTP_REFERER") == request.route_url("home")

        message_count = (
            Session.query(func.count('*')).select_from(Message)
            .filter(Message.chat_id == context.chat.id).scalar()
        )

        if message_count < 30:
            prompt = None
            messages = (
                Session.query(Message)
                .filter(Message.chat_id == context.chat.id)
                .order_by(Message.id.asc()).all()
            )
        else:
            prompt = (
                Session.query(Message)
                .filter(Message.chat_id == context.chat.id)
                .order_by(Message.id.asc())
                .options(joinedload(Message.user))
                .first()
            )
            messages = (
                Session.query(Message)
                .filter(Message.chat_id == context.chat.id)
                .order_by(Message.id.desc())
                .options(joinedload(Message.user))
                .limit(25).all()
            )
            messages.reverse()

        if request.matched_route.name == "chat_ext":
            data = {
                "chat":              context.chat,
                "chat_user":         context.chat_user,
                "message_count":     message_count,
                "prompt":            prompt,
                "messages":          messages,
                "banned_chat_users": [_.handle for _ in context.banned_chat_users],
            }
            if context.chat.mode == ChatMode.group:
                data["chat_users"] = [
                    {"name": chat_user.name, "last_colour": chat_user.last_colour}
                    for chat_user in context.chat_users.values()
                ]
            return data

        # List users if we're an admin.
        # Get this from both message users and chat users, because the latter is
        # removed if they delete the chat.
        symbol_users = None
        if context.chat.mode == ChatMode.one_on_one and request.has_permission("chat.full_user_list"):
            symbol_users = {
                _.symbol_character: _.user
                for _ in messages
                if _.user is not None
            }
            for chat_user in Session.query(ChatUser).filter(
                ChatUser.chat_id == context.chat.id
            ).options(joinedload(ChatUser.user)):
                symbol_users[chat_user.symbol_character] = chat_user.user

        template = "layout2/chat.mako" if (
            context.chat.mode == ChatMode.group
            or request.user.layout_version == 2
        ) else "chat.mako"
        return render_to_response(template, {
            "page":              "chat",
            "preset_colours":    preset_colours,
            "chat":              context.chat,
            "own_chat_user":     context.chat_user,
            "from_homepage":     from_homepage,
            "prompt":            prompt,
            "messages":          messages,
            "message_count":     message_count,
            "symbol_users":      symbol_users,
        }, request=request)

    # Otherwise show the archive view.

    # Update the visited time in archive view if the chat is ended.
    # We need to do this because otherwise it's impossible to mark an ended
    # chat as read.
    if context.chat_user and context.chat.status == "ended":
        context.chat_user.visited = datetime.datetime.now()

    try:
        current_page = int(request.GET["page"])
    except (KeyError, ValueError):
        current_page = 1

    messages = (
        Session.query(Message)
        .filter(Message.chat_id == context.chat.id)
    )
    message_count = (
        Session.query(func.count('*')).select_from(Message)
        .filter(Message.chat_id == context.chat.id)
    )

    # Hide OOC messages if the chat doesn't belong to us.
    # Also don't hide OOC messages for admins.
    if not request.has_permission("chat.read_ooc"):
        messages = messages.filter(Message.type != "ooc")
        message_count = message_count.filter(Message.type != "ooc")

    # Join users if we're an admin.
    if request.has_permission("chat.full_user_list"):
        messages = messages.options(joinedload(Message.user))

    messages = (
        messages.order_by(Message.id.asc())
        .limit(25).offset((current_page - 1) * 25).all()
    )
    message_count = message_count.scalar()

    if request.matched_route.name == "chat_ext":
        return {
            "chat":          context.chat,
            "chat_user":     context.chat_user,
            "message_count": message_count,
            "messages":      messages,
        }

    # List users if we're an admin.
    # Get this from both message users and chat users, because the latter may be
    # removed if they delete the chat.
    symbol_users = None

    if context.chat.mode == ChatMode.one_on_one and request.has_permission("chat.full_user_list"):
        symbol_users = {
            _.symbol_character: _.user
            for _ in messages
            if _.user is not None
        }
        for chat_user in Session.query(ChatUser).filter(
            ChatUser.chat_id == context.chat.id
        ).options(joinedload(ChatUser.user)):
            symbol_users[chat_user.symbol_character] = chat_user.user

    template = "layout2/chat_archive.mako" if (
        context.chat.mode == ChatMode.group
        or request.user is None
        or request.user.layout_version == 2
    ) else "chat_archive.mako"
    return render_to_response(template, {
        "page":          "archive",
        "continuable":   context.is_continuable,
        "chat":          context.chat,
        "own_chat_user": context.chat_user,
        "messages":      messages,
        "message_count": message_count,
        "current_page":  current_page,
        "symbol_users":  symbol_users,
    }, request=request)


@view_config(route_name="chat_draft", request_method="POST", permission="chat.info")
def chat_draft(context, request):
    context.chat_user.draft = request.POST["message_text"].strip()
    return HTTPNoContent()


def _validate_message_form(request, editing=False):
    colour = request.POST.get("message_colour", "000000")
    if colour.startswith("#"):
        colour = colour[1:]
    if colour_validator.match(colour) is None:
        raise HTTPBadRequest("Invalid text colour. The colour needs to be a 6-digit hex code.")

    trimmed_message_text = request.POST["message_text"].strip()
    if trimmed_message_text == "":
        raise HTTPBadRequest("Message text can't be empty.")

    message_type = "ooc" if "message_ooc" in request.POST else "ic"
    if not editing and (
        trimmed_message_text.startswith("((")
        or trimmed_message_text.endswith("))")
        or trimmed_message_text.startswith("[[")
        or trimmed_message_text.endswith("]]")
        or trimmed_message_text.startswith("{{")
        or trimmed_message_text.endswith("}}")
    ):
        message_type = "ooc"

    return colour, trimmed_message_text, message_type


@view_config(route_name="chat_send", request_method="POST", permission="chat.send")
def chat_send(context, request):
    colour, trimmed_message_text, message_type = _validate_message_form(request)
    posted_date = datetime.datetime.now()

    new_message = Message(
        chat_id=context.chat.id,
        user_id=request.user.id,
        type=message_type,
        colour=colour,
        symbol=context.chat_user.symbol,
        text=trimmed_message_text,
        posted=posted_date,
        edited=posted_date,
    )
    Session.add(new_message)
    Session.flush()

    context.chat.updated = posted_date
    context.chat.last_user_id = request.user.id

    context.chat_user.last_colour = colour
    context.chat_user.draft = ""

    try:
        # See if anyone else is online and update their ChatUser too.
        online_handles = OnlineUserStore(request.pubsub).online_handles(context.chat)
        for other_chat_user in Session.query(ChatUser).filter(and_(
            ChatUser.chat_id == context.chat.id,
            ChatUser.status == ChatUserStatus.active,
        )):
            if other_chat_user.handle in online_handles:
                other_chat_user.visited = posted_date
            else:
                request.pubsub.publish("user:" + str(other_chat_user.user_id), json.dumps({
                    "action": "notification",
                    "url":    context.chat.url,
                    "title":  other_chat_user.title or context.chat.url,
                    "colour": colour,
                    "symbol": context.chat_user.symbol_character,
                    "name":   context.chat_user.name,
                    "text":   trimmed_message_text if len(trimmed_message_text) < 100 else trimmed_message_text[:97] + "...",
                }))
                trigger_push_notification.delay(other_chat_user.user_id)
    except ConnectionError:
        pass

    try:
        request.pubsub.publish("chat:%s" % context.chat.id, json.dumps({
            "action": "message",
            "message": {
                "id":     new_message.id,
                "type":   message_type,
                "colour": colour,
                "symbol": context.chat_user.symbol_character,
                "name":   context.chat_user.name,
                "text":   trimmed_message_text,
            },
        }))
    except ConnectionError:
        pass

    if request.is_xhr:
        return HTTPNoContent()
    return HTTPFound(request.route_path("chat", url=request.matchdict["url"]))


@view_config(route_name="chat_edit", request_method="POST", permission="chat.send")
def chat_edit(context, request):
    try:
        message = Session.query(Message).filter(and_(
            Message.id == request.matchdict["message_id"],
            Message.chat_id == context.chat.id,
            Message.user_id == request.user.id,
        )).one()
    except NoResultFound:
        raise HTTPNotFound

    colour, trimmed_message_text, message_type = _validate_message_form(request, editing=True)

    message.type   = message_type
    message.colour = colour
    message.text   = trimmed_message_text
    message.edited = datetime.datetime.now()

    try:
        request.pubsub.publish("chat:%s" % context.chat.id, json.dumps({
            "action": "edit",
            "message": {
                "id":          message.id,
                "type":        message.type,
                "colour":      message.colour,
                "symbol":      message.symbol_character,
                "name":        message.chat_user.name,
                "text":        message.text,
                "show_edited": message.show_edited,
            },
        }))
    except ConnectionError:
        pass

    if request.is_xhr:
        return HTTPNoContent()
    return HTTPFound(request.environ["HTTP_REFERER"])


def _post_end_message(request, chat, own_chat_user, action="ended"):
    update_date = datetime.datetime.now()

    text = "%%s %s the chat." % action
    notification_text = text % own_chat_user.handle
    if own_chat_user.name:
        text = notification_text

    message = Message(
        chat_id=chat.id,
        type="system",
        colour="000000",
        symbol=own_chat_user.symbol,
        text=text,
        posted=update_date,
        edited=update_date,
    )
    Session.add(message)
    Session.flush()

    if action == "ended":
        chat.status       = "ended"
        chat.last_user_id = None

    chat.updated          = update_date
    own_chat_user.visited = update_date

    try:
        # See if anyone else is online and update their ChatUser too.
        online_handles = OnlineUserStore(request.pubsub).online_handles(chat)
        for other_chat_user in Session.query(ChatUser).filter(and_(
            ChatUser.chat_id == chat.id,
            ChatUser.status == ChatUserStatus.active,
        )):
            if other_chat_user.handle in online_handles:
                other_chat_user.visited = update_date
    except ConnectionError:
        pass

    try:
        request.pubsub.publish("chat:"+str(chat.id), json.dumps({
            "action": "end" if action == "ended" else "message",
            "message": {
                "id":     message.id,
                "type":   "system",
                "colour": "000000",
                "symbol": own_chat_user.symbol_character,
                "name":   own_chat_user.name,
                "text":   notification_text,
            },
        }))
    except ConnectionError:
        pass


@view_config(route_name="chat_end", request_method="GET", permission="chat.info")
def chat_end_get(context, request):
    if context.chat.status == "ended" or len(context.active_chat_users) > 2:
        raise HTTPNotFound

    prompt = Session.query(Message).filter(
        Message.chat_id == context.chat.id,
    ).order_by(Message.id).first()

    last_message = Session.query(Message).filter(
        Message.chat_id == context.chat.id,
    ).order_by(Message.id.desc()).first()

    template = "layout2/chat_end.mako" if request.user.layout_version == 2 else "chat_end.mako"
    return render_to_response(template, {
        "action":        "end",
        "chat":          context.chat,
        "own_chat_user": context.chat_user,
        "prompt":        prompt,
        "last_message":  last_message,
    }, request)


@view_config(route_name="chat_end", request_method="POST", permission="chat.info")
def chat_end_post(context, request):
    if context.chat.status == "ended" or len(context.active_chat_users) > 2:
        raise HTTPNotFound

    _post_end_message(request, context.chat, context.chat_user)

    if request.is_xhr:
        return HTTPNoContent()

    if "continue_search" in request.POST:
        return HTTPFound(request.route_path("home"))

    return HTTPFound(request.route_path("chat_info", url=request.matchdict["url"], _query={"saved": "end"}))


@view_config(route_name="chat_delete", request_method="GET", permission="chat.info")
def chat_delete_get(context, request):
    if context.chat.status == "ongoing" and len(context.active_chat_users) > 2:
        raise HTTPNotFound

    prompt = Session.query(Message).filter(
        Message.chat_id == context.chat.id,
    ).order_by(Message.id).first()

    last_message = Session.query(Message).filter(and_(
        Message.chat_id == context.chat.id,
        Message.type != "system",
    )).order_by(Message.id.desc()).first()

    template = "layout2/chat_end.mako" if request.user.layout_version == 2 else "chat_end.mako"
    return render_to_response(template, {
        "action":        "delete",
        "chat":          context.chat,
        "own_chat_user": context.chat_user,
        "prompt":        prompt,
        "last_message":  last_message,
    }, request)


@view_config(route_name="chat_delete", request_method="POST", permission="chat.info")
def chat_delete_post(context, request):
    if context.chat.status == "ongoing" and len(context.active_chat_users) > 2:
        raise HTTPNotFound

    if context.chat.status == "ongoing":
        _post_end_message(request, context.chat, context.chat_user)

    if context.chat.mode == ChatMode.group:
        context.chat_user.status = ChatUserStatus.deleted
    else:
        Session.delete(context.chat_user)

    if request.is_xhr:
        return HTTPNoContent()
    return HTTPFound(request.route_path("chat_list"))


@view_config(route_name="chat_leave", request_method="GET", permission="chat.info")
def chat_leave_get(context, request):
    if context.chat.status == "ended" or len(context.active_chat_users) <= 2:
        raise HTTPNotFound

    prompt = Session.query(Message).filter(
        Message.chat_id == context.chat.id,
    ).order_by(Message.id).first()

    last_message = Session.query(Message).filter(and_(
        Message.chat_id == context.chat.id,
        Message.type != "system",
    )).order_by(Message.id.desc()).first()

    return render_to_response("layout2/chat_end.mako", {
        "action":        "leave",
        "chat":          context.chat,
        "own_chat_user": context.chat_user,
        "prompt":        prompt,
        "last_message":  last_message,
    }, request)


@view_config(route_name="chat_leave", request_method="POST", permission="chat.info")
def chat_leave_post(context, request):
    if context.chat.status == "ongoing" and len(context.active_chat_users) <= 2:
        raise HTTPNotFound

    if context.chat.status == "ongoing":
        _post_end_message(request, context.chat, context.chat_user, "left")

    if context.chat.mode == ChatMode.group:
        context.chat_user.status = ChatUserStatus.deleted
    else:
        Session.delete(context.chat_user)

    return HTTPFound(request.route_path("chat_list"))


@view_config(route_name="chat_info", request_method="GET", permission="chat.info")
def chat_info_get(context, request):
    template = "layout2/chat_info.mako" if request.user.layout_version == 2 else "chat_info.mako"
    return render_to_response(template, {
        "page":          "info",
        "chat":          context.chat,
        "own_chat_user": context.chat_user,
    }, request)


@view_config(route_name="chat_info", request_method="POST", permission="chat.info")
def chat_info_post(context, request):
    context.chat_user.title = request.POST["title"][:100]
    context.chat_user.notes = request.POST["notes"]

    labels_set = set()
    for label in request.POST["labels"].lower().replace("\n", " ").split(","):
        label = label.strip()
        if label == "":
            continue
        labels_set.add(label.replace(" ", "_"))
    labels_list = list(labels_set)
    labels_list.sort()
    context.chat_user.labels = labels_list

    return HTTPFound(request.route_path("chat_info", url=request.matchdict["url"], _query={"saved": "info"}))


@view_config(route_name="chat_change_name", request_method="POST", permission="chat.change_name")
def chat_change_name(context, request):
    if not request.POST.get("name", "").strip():
        raise HTTPBadRequest

    chosen_name = request.POST["name"].strip()[:50]

    if chosen_name == context.chat_user.name:
        return HTTPFound(request.route_path("chat_info", url=request.matchdict["url"], _query={"saved": "name"}))

    for chat_user in context.chat_users.values():
        if chat_user == context.chat_user:
            continue
        if chat_user.name == chosen_name:
            return HTTPFound(request.route_path("chat_info", url=request.matchdict["url"], _query={"error": "name_taken"}))

    old_name = context.chat_user.name
    context.chat_user.name = chosen_name

    update_date = datetime.datetime.now()
    text        = "%s is now %s." % (old_name, context.chat_user.name)

    message = Message(
        chat_id=context.chat.id,
        type="system",
        colour="000000",
        symbol=context.chat_user.symbol,
        text=text,
        posted=update_date,
        edited=update_date,
    )
    Session.add(message)
    Session.flush()

    context.chat.updated      = update_date
    context.chat_user.visited = update_date

    try:
        # See if anyone else is online and update their ChatUser too.
        # TODO make a MessageService or something for this
        online_handles = OnlineUserStore(request.pubsub).online_handles(context.chat)
        for other_chat_user in Session.query(ChatUser).filter(and_(
            ChatUser.chat_id == context.chat.id,
            ChatUser.status == ChatUserStatus.active,
        )):
            if other_chat_user.handle in online_handles:
                other_chat_user.visited = update_date
    except ConnectionError:
        pass

    try:
        request.pubsub.publish("chat:" + str(context.chat.id), json.dumps({
            "action": "message",
            "message": {
                "id":     message.id,
                "type":   "system",
                "colour": "000000",
                "symbol": context.chat_user.symbol_character,
                "name":   context.chat_user.name,
                "text":   text,
            },
        }))
        request.pubsub.publish("chat:" + str(context.chat.id), json.dumps({
            "action":   "name_change",
            "old_name": old_name,
            "new_name": context.chat_user.name,
        }))
    except ConnectionError:
        pass

    return HTTPFound(request.route_path("chat_info", url=request.matchdict["url"], _query={"saved": "name"}))


@view_config(route_name="chat_remove_user", request_method="POST", permission="chat.send")
def chat_remove_user(context, request):
    # Not a permission so we don't have to calculate it every time we generate
    # the ACL.
    if context.first_message.user_id != request.user.id:
        raise HTTPForbidden

    if not request.POST.get("name", "").strip():
        raise HTTPBadRequest

    for chat_user in context.chat_users.values():
        if chat_user.name == request.POST["name"]:
            if chat_user == context.chat_user:
                raise HTTPBadRequest
            break
    else:
        raise HTTPNotFound

    end_chat = len(context.active_chat_users) <= 2

    chat_user.status = ChatUserStatus.deleted

    # Don't leave the OP on their own.
    if end_chat:
        return chat_end_post(context, request)

    update_date = datetime.datetime.now()
    text        = "%s has been removed from the chat." % chat_user.name

    message = Message(
        chat_id=context.chat.id,
        type="system",
        colour="000000",
        symbol=chat_user.symbol,
        text=text,
        posted=update_date,
        edited=update_date,
    )
    Session.add(message)
    Session.flush()

    chat.updated              = update_date
    context.chat_user.visited = update_date

    try:
        # See if anyone else is online and update their ChatUser too.
        # TODO make a MessageService or something for this
        online_handles = OnlineUserStore(request.pubsub).online_handles(context.chat)
        for other_chat_user in Session.query(ChatUser).filter(and_(
            ChatUser.chat_id == context.chat.id,
            ChatUser.status == ChatUserStatus.active,
        )):
            if other_chat_user.handle in online_handles:
                other_chat_user.visited = update_date
    except ConnectionError:
        pass

    try:
        request.pubsub.publish("chat:" + str(context.chat.id), json.dumps({
            "action": "message",
            "message": {
                "id":     message.id,
                "type":   "system",
                "colour": "000000",
                "symbol": chat_user.symbol_character,
                "name":   chat_user.name,
                "text":   text,
            },
        }))
        request.pubsub.publish(
            "chat:%s:user:%s" % (chat_user.chat_id, chat_user.user_id),
            "kicked",
        )
    except ConnectionError:
        pass

    return HTTPFound(request.route_path("chat_info", url=request.matchdict["url"]))

