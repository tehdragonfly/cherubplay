import datetime

from pyramid.httpexceptions import (
    HTTPBadRequest,
    HTTPFound,
    HTTPNoContent,
    HTTPNotFound,
)
from pyramid.renderers import render_to_response
from pyramid.view import view_config
from sqlalchemy import and_, func, Unicode
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import cast

from cherubplay import ChatContext
from cherubplay.lib import colour_validator, trim_with_ellipsis
from cherubplay.models import Chat, ChatExport, ChatUser, Message
from cherubplay.models.enums import ChatMode, ChatUserStatus, MessageType
from cherubplay.services.message import IMessageService
from cherubplay.tasks import export_chat


@view_config(route_name="chat_list",                  request_method="GET", permission="view")
@view_config(route_name="chat_list_ext",              request_method="GET", permission="view", extension="json", renderer="json")
@view_config(route_name="chat_list_status",           request_method="GET", permission="view")
@view_config(route_name="chat_list_status_ext",       request_method="GET", permission="view", extension="json", renderer="json")
@view_config(route_name="chat_list_label",            request_method="GET", permission="view")
@view_config(route_name="chat_list_label_ext",        request_method="GET", permission="view", extension="json", renderer="json")
@view_config(route_name="chat_list_status_label",     request_method="GET", permission="view")
@view_config(route_name="chat_list_status_label_ext", request_method="GET", permission="view", extension="json", renderer="json")
def chat_list(request):

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        raise HTTPNotFound

    if "status" in request.matchdict:
        current_status = request.matchdict["status"]
    else:
        current_status = None

    if "label" in request.matchdict:
        current_label = request.matchdict["label"].lower().strip().replace(" ", "_")
        if current_label != request.matchdict["label"]:
            raise HTTPFound(request.route_path("chat_list_label", label=current_label))
    else:
        current_label = None

    db = request.find_service(name="db")
    chats = db.query(ChatUser, Chat, Message).join(Chat).outerjoin(
        Message,
        Message.id == db.query(
            func.min(Message.id),
        ).filter(
            Message.chat_id == Chat.id,
        ).correlate(Chat),
    ).filter(
        ChatUser.user_id == request.user.id,
        ChatUser.status == ChatUserStatus.active,
    )

    chat_count = db.query(func.count('*')).select_from(ChatUser).filter(
        ChatUser.user_id == request.user.id,
        ChatUser.status == ChatUserStatus.active,
    )

    if current_status == "unanswered":
        chats = chats.filter(and_(
            Chat.last_user_id != None,
            Chat.last_user_id != request.user.id,
        ))
        chat_count = chat_count.join(Chat).filter(and_(
            Chat.last_user_id != None,
            Chat.last_user_id != request.user.id,
        ))
    elif current_status is not None:
        chats = chats.filter(Chat.status == current_status)
        chat_count = chat_count.join(Chat).filter(Chat.status == current_status)

    if current_label is not None:
        label_array = cast([current_label], ARRAY(Unicode(500)))
        chats = chats.filter(ChatUser.labels.contains(label_array))
        chat_count = chat_count.filter(ChatUser.labels.contains(label_array))

    chats = (
        chats.options(joinedload(Chat.request))
        .order_by(Chat.updated.desc())
        .limit(25).offset((current_page-1)*25).all()
    )

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
        db.query(func.unnest(ChatUser.labels), func.count("*"))
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
    db = request.find_service(name="db")
    result = db.query(ChatUser, Chat).join(Chat).filter(and_(
        ChatUser.user_id == request.user.id,
        ChatUser.status == ChatUserStatus.active,
        Chat.updated > ChatUser.visited,
    )).order_by(Chat.updated.desc()).first()
    if not result:
        return None

    own_chat_user, chat = result

    message = (
        db.query(Message)
        .filter(Message.chat_id == chat.id)
        .options(joinedload(Message.chat_user))
        .order_by(Message.id.desc()).first()
    )
    if not message:
        return None

    return {
        "action": "notification",
        "url":    chat.url,
        "title":  own_chat_user.display_title,
        "colour": message.colour,
        "handle": message.symbol_character or message.chat_user.handle,
        "text":   trim_with_ellipsis(message.text, 100),
    }


@view_config(route_name="chat",     request_method="GET", permission="chat.read")
@view_config(route_name="chat_ext", request_method="GET", permission="chat.read", extension="json", renderer="json")
def chat(context: ChatContext, request):
    db = request.find_service(name="db")
    # If we can continue the chat and there isn't a page number, show the
    # full chat window.
    if "page" not in request.GET and context.is_continuable:

        context.chat_user.visited = datetime.datetime.now()

        # Test if we came here from the homepage, for automatically resuming the search.
        from_homepage = request.environ.get("HTTP_REFERER") == request.route_url("home")

        message_count = (
            db.query(func.count('*')).select_from(Message)
            .filter(Message.chat_id == context.chat.id).scalar()
        )

        if message_count < 30:
            prompt = None
            messages = (
                db.query(Message)
                .filter(Message.chat_id == context.chat.id)
                .order_by(Message.id.asc()).all()
            )
        else:
            prompt = (
                db.query(Message)
                .filter(Message.chat_id == context.chat.id)
                .order_by(Message.id.asc())
                .options(joinedload(Message.user))
                .first()
            )
            messages = (
                db.query(Message)
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
            for chat_user in db.query(ChatUser).filter(
                ChatUser.chat_id == context.chat.id
            ).options(joinedload(ChatUser.user)):
                symbol_users[chat_user.symbol_character] = chat_user.user

        template = "layout2/chat.mako" if (
            context.chat.mode == ChatMode.group
            or request.user.layout_version == 2
        ) else "chat.mako"
        return render_to_response(template, {
            "page":              "chat",
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
    if context.chat_user and context.chat_user.visited < context.chat.updated and context.chat.status == "ended":
        context.chat_user.visited = datetime.datetime.now()

    try:
        current_page = int(request.GET["page"])
    except KeyError:
        current_page = 1
    except ValueError:
        raise HTTPNotFound

    messages = (
        db.query(Message)
        .filter(Message.chat_id == context.chat.id)
    )
    message_count = (
        db.query(func.count('*')).select_from(Message)
        .filter(Message.chat_id == context.chat.id)
    )

    # Hide OOC messages if the chat doesn't belong to us.
    # Also don't hide OOC messages for admins.
    if not request.has_permission("chat.read_ooc"):
        messages = messages.filter(Message.type != MessageType.ooc)
        message_count = message_count.filter(Message.type != MessageType.ooc)

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
        for chat_user in db.query(ChatUser).filter(
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
        "messages":      messages,
        "message_count": message_count,
        "current_page":  current_page,
        "symbol_users":  symbol_users,
    }, request=request)


@view_config(route_name="chat_draft", request_method="POST", permission="chat.send")
def chat_draft(context: ChatContext, request):
    context.chat_user.draft = request.POST["message_text"].strip()
    return HTTPNoContent()


def _validate_message_form(request, editing=False):
    if (
        "message_colour" not in request.POST
        or "message_text" not in request.POST
    ):
        raise HTTPBadRequest("Colour and text are required.")

    colour = request.POST["message_colour"]
    if colour.startswith("#"):
        colour = colour[1:]
    if not colour_validator.match(colour):
        raise HTTPBadRequest("Invalid text colour. The colour needs to be a 6-digit hex code.")

    trimmed_message_text = request.POST["message_text"].strip()
    if trimmed_message_text == "":
        raise HTTPBadRequest("Message text can't be empty.")

    if not editing and (
        trimmed_message_text.startswith("((")
        or trimmed_message_text.endswith("))")
        or trimmed_message_text.startswith("[[")
        or trimmed_message_text.endswith("]]")
        or trimmed_message_text.startswith("{{")
        or trimmed_message_text.endswith("}}")
    ):
        message_type = MessageType.ooc
    else:
        message_type = MessageType.ooc if "message_ooc" in request.POST else MessageType.ic

    return colour, trimmed_message_text, message_type


@view_config(route_name="chat_send", request_method="POST", permission="chat.send")
def chat_send(context: ChatContext, request):
    colour, trimmed_message_text, message_type = _validate_message_form(request)
    message_service = request.find_service(IMessageService)
    message_service.send_message(context.chat_user, message_type, colour, trimmed_message_text)

    if request.is_xhr:
        return HTTPNoContent()
    return HTTPFound(request.route_path("chat", url=request.matchdict["url"]))


@view_config(route_name="chat_edit", request_method="POST", permission="chat.send")
def chat_edit(context: ChatContext, request):
    db = request.find_service(name="db")
    try:
        message = db.query(Message).filter(and_(
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

    request.find_service(IMessageService).publish_edit(message)

    if request.is_xhr:
        return HTTPNoContent()
    return HTTPFound(request.environ["HTTP_REFERER"])


class ChatEndViewBase(object):
    def __init__(self, context: ChatContext, request):
        self.context = context
        self.request = request

    @property
    def action_name(self):
        """Name of the action to pass to the template."""
        raise NotImplementedError

    @property
    def allowed_property(self):
        """ChatContext property which tells us whether this action is allowed."""
        raise NotImplementedError

    def __call__(self):
        if not getattr(self.context, self.allowed_property):
            raise HTTPNotFound

        db = self.request.find_service(name="db")
        prompt = db.query(Message).filter(
            Message.chat_id == self.context.chat.id,
        ).order_by(Message.id).first()

        last_message = db.query(Message).filter(and_(
            Message.chat_id == self.context.chat.id,
            Message.type != MessageType.system,
        )).order_by(Message.id.desc()).first()

        template = "layout2/chat_end.mako" if self.request.user.layout_version == 2 else "chat_end.mako"
        return render_to_response(template, {
            "action":       self.action_name,
            "prompt":       prompt,
            "last_message": last_message,
        }, self.request)


@view_config(route_name="chat_end", request_method="GET", permission="chat.info")
class ChatEndView(ChatEndViewBase):
    action_name = "end"
    allowed_property = "is_endable"


@view_config(route_name="chat_end", request_method="POST", permission="chat.info")
def chat_end_post(context: ChatContext, request):
    if not context.is_endable:
        raise HTTPNotFound

    context.chat.status = "ended"
    context.chat.last_user_id = None
    request.find_service(IMessageService).send_end_message(context.chat_user)

    if request.is_xhr:
        return HTTPNoContent()

    if "continue_search" in request.POST:
        return HTTPFound(request.route_path("home"))

    return HTTPFound(request.route_path("chat_info", url=request.matchdict["url"], _query={"saved": "end"}))


@view_config(route_name="chat_delete", request_method="GET", permission="chat.info")
class ChatDeleteView(ChatEndViewBase):
    action_name = "delete"
    allowed_property = "is_deletable"


@view_config(route_name="chat_delete", request_method="POST", permission="chat.info")
def chat_delete_post(context: ChatContext, request):
    if not context.is_deletable:
        raise HTTPNotFound

    if context.chat.status == "ongoing":
        context.chat.status = "ended"
        context.chat.last_user_id = None
        request.find_service(IMessageService).send_end_message(context.chat_user)

    if context.chat.mode == ChatMode.group:
        context.chat_user.status = ChatUserStatus.deleted
    else:
        db = request.find_service(name="db")
        db.delete(context.chat_user)

    if request.is_xhr:
        return HTTPNoContent()
    return HTTPFound(request.route_path("chat_list"))


@view_config(route_name="chat_leave", request_method="GET", permission="chat.info")
class ChatLeaveView(ChatEndViewBase):
    action_name = "leave"
    allowed_property = "is_leavable"


@view_config(route_name="chat_leave", request_method="POST", permission="chat.info")
def chat_leave_post(context: ChatContext, request):
    if not context.is_leavable:
        raise HTTPNotFound

    if context.chat.status == "ongoing":
        request.find_service(IMessageService).send_leave_message(context.chat_user)

    if context.chat.mode == ChatMode.group:
        context.chat_user.status = ChatUserStatus.deleted
    else:
        db = request.find_service(name="db")
        db.delete(context.chat_user)

    return HTTPFound(request.route_path("chat_list"))


@view_config(route_name="chat_info", request_method="GET", permission="chat.info")
def chat_info_get(context: ChatContext, request):
    template = "layout2/chat_info.mako" if request.user.layout_version == 2 else "chat_info.mako"
    return render_to_response(template, {"page": "info"}, request)


@view_config(route_name="chat_info", request_method="POST", permission="chat.info")
def chat_info_post(context: ChatContext, request):
    if "title" not in request.POST or "notes" not in request.POST or "labels" not in request.POST:
        raise HTTPBadRequest

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
def chat_change_name(context: ChatContext, request):
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

    message_service = request.find_service(IMessageService)
    message_service.send_change_name_message(context.chat_user, old_name)

    return HTTPFound(request.route_path("chat_info", url=request.matchdict["url"], _query={"saved": "name"}))


@view_config(route_name="chat_remove_user", request_method="POST", permission="chat.remove_user")
def chat_remove_user(context: ChatContext, request):
    if not request.POST.get("name", "").strip():
        raise HTTPBadRequest

    for kicked_chat_user in context.chat_users.values():
        if kicked_chat_user.name == request.POST["name"]:
            if kicked_chat_user == context.chat_user:
                raise HTTPBadRequest
            break
    else:
        raise HTTPNotFound

    end_chat = len(context.active_chat_users) <= 2

    kicked_chat_user.status = ChatUserStatus.deleted

    # Don't leave the OP on their own.
    if end_chat:
        return chat_end_post(context, request)

    request.find_service(IMessageService).send_kick_message(context.chat_user, kicked_chat_user)

    return HTTPFound(request.route_path("chat_info", url=request.matchdict["url"]))


@view_config(route_name="chat_export",     request_method="GET", permission="chat.export", renderer="layout2/chat_export.mako")
@view_config(route_name="chat_export_ext", request_method="GET", permission="chat.export", extension="json", renderer="json")
def chat_export_get(context: ChatContext, request):
    db = request.find_service(name="db")
    export = db.query(ChatExport).filter(
        ChatExport.chat_id == context.chat.id,
        ChatExport.user_id == request.user.id,
    ).first()

    if request.matched_route.name == "chat_export_ext":
        return export

    return {"page": "export", "export": export}


@view_config(route_name="chat_export", request_method="POST", permission="chat.export", renderer="layout2/chat_export.mako")
def chat_export_post(context: ChatContext, request):
    db = request.find_service(name="db")
    export = db.query(ChatExport).filter(
        ChatExport.chat_id == context.chat.id,
        ChatExport.user_id == request.user.id,
    ).first()

    if not export:
        # This task can't be called until after the ChatExport row has been committed to the database.
        # But we can't trigger it in a post-commit hook because we need to include the task ID in the ChatExport.
        result = export_chat.apply_async((context.chat.id, request.user.id), countdown=5)
        db.add(ChatExport(
            chat_id=context.chat.id,
            user_id=request.user.id,
            celery_task_id=result.id,
        ))

    return HTTPFound(request.route_path("chat_export", url=context.chat.url))
