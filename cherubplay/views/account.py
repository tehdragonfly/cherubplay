import datetime, json

from bcrypt import gensalt, hashpw
from pyramid.httpexceptions import HTTPBadRequest, HTTPFound, HTTPNoContent, HTTPNotFound, HTTPRequestEntityTooLarge
from pyramid.renderers import render, render_to_response
from pyramid.view import view_config
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message as EmailMessage
from sqlalchemy.orm.exc import NoResultFound
from uuid import uuid4

from cherubplay.lib import email_validator, timezones, username_validator, reserved_usernames
from cherubplay.models import Chat, ChatUser, PushSubscription, User, UserConnection
from cherubplay.models.enums import ChatSource
from cherubplay.services.user_connection import IUserConnectionService


def send_email(request, action, user, email_address):
    email_token = str(uuid4())
    request.find_service(name="redis_login").setex(
        ":".join([action, str(user.id), email_address]),
        86400 if action == "verify_email" else 600,
        email_token,
    )

    mailer = get_mailer(request)
    message = EmailMessage(
        subject="Verify your e-mail address" if action == "verify_email" else "Reset your password",
        sender="Cherubplay <cherubplay@msparp.com>",
        recipients=["Cherubplay user %s <%s>" % (user.username, email_address)],
        body=render("email/%s_plain.mako" % action, {"user": user, "email_address": email_address, "email_token": email_token}, request),
        html=render("email/%s.mako" % action, {"user": user, "email_address": email_address, "email_token": email_token}, request),
    )
    mailer.send(message)


@view_config(route_name="account", request_method="GET", permission="view")
def account(request):
    template = "layout2/account/index.mako" if request.user.layout_version == 2 else "account.mako"
    return render_to_response(template, {}, request)


@view_config(route_name="account_email_address", renderer="layout2/account/index.mako", request_method="POST", permission="view")
def account_email_address(request):
    login_store = request.find_service(name="redis_login")

    email_address = request.POST.get("email_address", "").strip()[:100]
    if not email_validator.match(email_address):
        return {"email_address_error": "Please enter a valid e-mail address."}

    if email_address == request.user.email:
        return HTTPFound(request.route_path("account"))

    if login_store.get("verify_email_limit:%s" % request.user.id):
        return {"email_address_error": "Sorry, you can only change your e-mail address once per day. Please wait until tomorrow."}

    send_email(request, "verify_email", request.user, email_address)
    login_store.setex("verify_email_limit:%s" % request.user.id, 86400, 1)

    return HTTPFound(request.route_path("account", _query={"saved": "verify_email"}))


@view_config(route_name="account_verify_email", request_method="GET")
def account_verify_email(request):
    login_store = request.find_service(name="redis_login")

    try:
        user_id = int(request.GET["user_id"].strip())
        email_address = request.GET["email_address"].strip()
        token = request.GET["token"].strip()
    except (KeyError, ValueError):
        raise HTTPNotFound
    stored_token = login_store.get("verify_email:%s:%s" % (user_id, email_address))
    if not user_id or not email_address or not token or not stored_token:
        raise HTTPNotFound

    stored_token = stored_token.decode("utf-8")

    if not stored_token == token:
        raise HTTPNotFound

    try:
        db = request.find_service(name="db")
        user = db.query(User).filter(User.id == user_id).one()
    except NoResultFound:
        raise HTTPNotFound

    user.email = email_address
    user.email_verified = True

    response = HTTPFound(request.route_path("account", _query={"saved": "email_address"}))

    if not request.user or request.user.id != user.id:
        new_session_id = str(uuid4())
        login_store.set("session:" + new_session_id, user.id)
        response.set_cookie("cherubplay", new_session_id, 31536000)

    return response


@view_config(route_name="account_email_address_remove", request_method="POST")
def account_email_address_remove(request):
    request.user.email          = None
    request.user.email_verified = False
    return HTTPFound(request.route_path("account"))


@view_config(route_name="account_username", renderer="layout2/account/index.mako", request_method="POST", permission="view")
def account_username(request):
    ucs = request.find_service(IUserConnectionService)

    username = request.POST.get("username", "").lower()[:100]
    if username_validator.match(username) is None:
        return {"username_error": "Usernames can only contain letters, numbers, hyphens and underscores."}

    db = request.find_service(name="db")
    if (
        username in reserved_usernames
        or db.query(User.id).filter(User.username == username).count() == 1
    ):
        return {"username_error": "The username \"%s\" has already been taken." % username}

    ucs.revert_non_mutual_connections(request.user)
    request.user.username = username
    ucs.convert_virtual_connections(request.user)

    return HTTPFound(request.route_path("account", _query={"saved": "username"}))


@view_config(route_name="account_password", renderer="layout2/account/index.mako", request_method="POST", permission="view")
def account_password(request):

    if hashpw(request.POST["old_password"].encode(), request.user.password.encode()).decode() != request.user.password:
        return {"password_error": "That isn't your old password."}
    if request.POST["password"] == "":
        return {"password_error": "Please don't use a blank password."}
    if request.POST["password"] != request.POST["password_again"]:
        return {"password_error": "The two passwords didn't match."}

    request.user.password = hashpw(request.POST["password"].encode(), gensalt()).decode()

    return HTTPFound(request.route_path("account", _query={"saved": "password"}))


@view_config(route_name="account_timezone", request_method="POST", permission="view")
def account_timezone(request):
    if request.POST["timezone"] in timezones:
        request.user.timezone = request.POST["timezone"]
    return HTTPNoContent()


@view_config(route_name="account_layout_version", request_method="POST", permission="view")
def account_layout_version(request):
    if request.POST["layout_version"] in ("1", "2"):
        request.user.layout_version = int(request.POST["layout_version"])
    return HTTPFound(request.environ["HTTP_REFERER"])


@view_config(route_name="account_forgot_password", request_method="GET", renderer="layout2/forgot_password.mako")
def forgot_password_get(request):
    return {}


@view_config(route_name="account_forgot_password", request_method="POST", renderer="layout2/forgot_password.mako")
def forgot_password_post(request):
    login_store = request.find_service(name="redis_login")

    if login_store.get("reset_password_limit:%s" % request.remote_addr):
        return {"error": "limit"}

    username = request.POST["username"].strip()[:User.username.type.length]
    try:
        db = request.find_service(name="db")
        user = db.query(User).filter(User.username == username.lower()).one()
    except NoResultFound:
        return {"error": "no_user", "username": username}

    if login_store.get("reset_password_limit:%s" % user.id):
        return {"error": "limit"}

    if not user.email or not user.email_verified:
        return {"error": "no_email"}

    send_email(request, "reset_password", user, user.email)
    login_store.setex("reset_password_limit:%s" % request.remote_addr, 86400, 1)
    login_store.setex("reset_password_limit:%s" % user.id, 86400, 1)

    return {"saved": "saved"}


def _validate_reset_token(request):
    try:
        user_id = int(request.GET["user_id"].strip())
        email_address = request.GET["email_address"].strip()
        token = request.GET["token"].strip()
    except (KeyError, ValueError):
        raise HTTPNotFound
    stored_token = request.find_service(name="redis_login").get("reset_password:%s:%s" % (user_id, email_address))
    if not user_id or not email_address or not token or not stored_token:
        raise HTTPNotFound

    stored_token = stored_token.decode("utf-8")

    if not stored_token == token:
        raise HTTPNotFound

    try:
        db = request.find_service(name="db")
        return db.query(User).filter(User.id == user_id).one()
    except NoResultFound:
        raise HTTPNotFound


@view_config(route_name="account_reset_password", request_method="GET", renderer="layout2/reset_password.mako")
def account_reset_password_get(request):
    _validate_reset_token(request)
    return {}


@view_config(route_name="account_reset_password", request_method="POST", renderer="layout2/reset_password.mako")
def account_reset_password_post(request):
    login_store = request.find_service(name="redis_login")
    user = _validate_reset_token(request)

    if not request.POST.get("password"):
        return {"error": "no_password"}

    if request.POST["password"] != request.POST["password_again"]:
        return {"error": "passwords_didnt_match"}

    user.password = hashpw(request.POST["password"].encode(), gensalt()).decode()

    login_store.delete("reset_password:%s:%s" % (user.id, request.GET["email_address"].strip()))

    response = HTTPFound(request.route_path("home"))

    new_session_id = str(uuid4())
    login_store.set("session:"+new_session_id, user.id)
    response.set_cookie("cherubplay", new_session_id, 31536000)

    return response


def validate_push_subscription_payload(request):
    if len(request.POST.get("subscription", "")) > 5000:
        raise HTTPRequestEntityTooLarge

    try:
        subscription = json.loads(request.POST.get("subscription", ""))
    except ValueError:
        raise HTTPBadRequest

    if not subscription.get("endpoint", "").startswith("https://"):
        raise HTTPBadRequest

    return subscription


@view_config(route_name="account_push_subscribe", request_method="POST", permission="view")
def account_push_subscribe(request):
    subscription = validate_push_subscription_payload(request)

    db = request.find_service(name="db")
    for existing_subscription in db.query(PushSubscription).filter(
        PushSubscription.user_id == request.user.id,
    ):
        if existing_subscription.data["endpoint"] == subscription["endpoint"]:
            existing_subscription.data = subscription
            return HTTPNoContent()

    db.add(PushSubscription(user_id=request.user.id, data=subscription))

    return HTTPNoContent()


@view_config(route_name="account_push_unsubscribe", request_method="POST", permission="view")
def account_push_unsubscribe(request):
    subscription = validate_push_subscription_payload(request)

    db = request.find_service(name="db")
    for existing_subscription in db.query(PushSubscription).filter(
        PushSubscription.user_id == request.user.id,
    ):
        if existing_subscription.data["endpoint"] == subscription["endpoint"]:
            db.delete(existing_subscription)

    return HTTPNoContent()


@view_config(route_name="account_away_message", request_method="POST", permission="chat")
def account_away_message(request):
    db = request.find_service(name="db")
    db.query(User).filter(User.id == request.user.id).update({
        "away_message": request.POST.get("away_message", "").strip()[:500] or None,
    })
    return HTTPFound(request.route_path("account"))


@view_config(route_name="account_read_news", request_method="POST", permission="view")
def account_read_news(request):
    db = request.find_service(name="db")
    db.query(User).filter(User.id == request.user.id).update({
        "last_read_news": datetime.datetime.now(),
    })
    return HTTPNoContent()


@view_config(route_name="account_connections",     request_method="GET", permission="view", renderer="layout2/account/connections.mako")
@view_config(route_name="account_connections_ext", request_method="GET", permission="view", extension="json", renderer="json")
def account_connections(request):
    return {"connections": request.find_service(IUserConnectionService).search(request.user)}


@view_config(route_name="account_connections_new", request_method="POST", permission="chat", renderer="layout2/account/connections.mako")
def account_connections_new(request):
    ucs = request.find_service(IUserConnectionService)
    to_username = request.POST.get("to", "").lower()
    if to_username == request.user.username:
        return {"connections": ucs.search(request.user), "error": "to_self"}
    try:
        ucs.create(request.user, to_username)
    except ValueError:
        return {"connections": ucs.search(request.user), "error": "to_invalid"}
    return HTTPFound(request.route_path("account_connections"))


@view_config(route_name="account_connection_chat", request_method="POST", permission="user_connection.chat")
def account_connection_chat(context: UserConnection, request):
    db = request.find_service(name="db")
    new_chat = Chat(url=str(uuid4()), source=ChatSource.user_connection)
    db.add(new_chat)
    db.flush()
    db.add(ChatUser(
        chat_id=new_chat.id,
        user_id=request.user.id,
        symbol=0,
        title="Chat with %s" % context.to_username,
        labels=["user_connection", context.to_username],
    ))
    db.add(ChatUser(
        chat_id=new_chat.id,
        user_id=context.to_id,
        symbol=1,
        title="Chat with %s" % request.user.username,
        labels=["user_connection", request.user.username],
    ))
    return HTTPFound(request.route_path("chat", url=new_chat.url))


@view_config(route_name="account_connection_delete", request_method="GET", permission="user_connection.delete", renderer="layout2/account/connection_delete.mako")
def account_connection_delete_get(request):
    return {}


@view_config(route_name="account_connection_delete", request_method="POST", permission="user_connection.delete")
def account_connection_delete_post(context, request):
    request.find_service(name="db").delete(context)
    if request.is_xhr:
        return HTTPNoContent()
    return HTTPFound(request.route_path("account_connections"))
