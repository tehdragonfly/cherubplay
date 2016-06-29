from bcrypt import gensalt, hashpw
from pyramid.httpexceptions import HTTPFound, HTTPNoContent, HTTPNotFound
from pyramid.renderers import render_to_response
from pyramid.view import view_config
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message as EmailMessage
from sqlalchemy.orm.exc import NoResultFound
from uuid import uuid4

from ..lib import email_validator
from ..models import (
    Session,
    User,
)


def send_email(request, action, user, email_address):
    email_token = str(uuid4())
    # XXX we're not using StrictRedis so value and expiry are the wrong way round
    request.login_store.setex(":".join([action, str(user.id), email_address]), email_token, 86400 if action == "verify" else 600)

    mailer = get_mailer(request)
    message = EmailMessage(
        subject="Verify your e-mail address" if action == "verify" else "Reset your password",
        sender="Cherubplay <cherubplay@msparp.com>",
        recipients=[email_address],
        body=request.route_url("account_" + ("verify_email" if action == "verify" else "reset_password"), _query={
            "user_id": user.id, "email_address": email_address, "token": email_token,
        }),
    )
    mailer.send(message)


@view_config(route_name="account", request_method="GET", permission="view")
def account(request):
    template = "layout2/account.mako" if request.user.layout_version == 2 else "account.mako"
    return render_to_response(template, {}, request)


@view_config(route_name="account_email_address", renderer="layout2/account.mako", request_method="POST", permission="view")
def account_email_address(request):
    email_address = request.POST.get("email_address", "").strip()[:100]
    if not email_validator.match(email_address):
        return { "email_address_error": "Please enter a valid e-mail address." }
    send_email(request, "verify", request.user, email_address)
    return HTTPFound(request.route_path("account", _query={ "saved": "verify_email" }))



@view_config(route_name="account_verify_email", request_method="GET")
def account_verify_email(request):
    try:
        user_id = int(request.GET["user_id"].strip())
        email_address = request.GET["email_address"].strip()
        token = request.GET["token"].strip()
    except (KeyError, ValueError):
        raise HTTPNotFound
    stored_token = request.login_store.get("verify:%s:%s" % (user_id, email_address))
    if not user_id or not email_address or not token or not stored_token:
        raise HTTPNotFound

    stored_token = stored_token.decode("utf-8")

    print token
    print stored_token

    if not stored_token == token:
        raise HTTPNotFound

    if request.user and request.user.id == user_id:
        user = request.user
    else:
        try:
            user = Session.query(User).filter(User.id == user_id).one()
        except NoResultFound:
            raise HTTPNotFound

    user.email = email_address
    user.email_verified = True

    response = HTTPFound(request.route_path("account", _query={ "saved": "email_address" }))

    if not request.user or request.user.id != user.id:
        new_session_id = str(uuid4())
        request.login_store.set("session:"+new_session_id, user.id)
        response.set_cookie("cherubplay", new_session_id, 31536000)

    return response


@view_config(route_name="account_password", renderer="account.mako", request_method="POST", permission="view")
def account_password(request):

    if hashpw(request.POST["old_password"].encode(), request.user.password.encode())!=request.user.password:
        return { "password_error": "That isn't your old password." }
    if request.POST["password"]=="":
        return { "password_error": "Please don't use a blank password." }
    if request.POST["password"]!=request.POST["password_again"]:
        return { "password_error": "The two passwords didn't match." }

    Session.query(User).filter(User.id==request.user.id).update({
        "password": hashpw(request.POST["password"].encode(), gensalt()),
    })

    return HTTPFound(request.route_path("account", _query={ "saved": "password" }))


timezones = {
    "Africa/Johannesburg", "Africa/Lagos", "Africa/Windhoek", "America/Adak",
    "America/Anchorage", "America/Argentina/Buenos_Aires", "America/Bogota",
    "America/Caracas", "America/Chicago", "America/Denver", "America/Godthab",
    "America/Guatemala", "America/Halifax", "America/Los_Angeles",
    "America/Montevideo", "America/New_York", "America/Noronha",
    "America/Noronha", "America/Phoenix", "America/Santiago",
    "America/Santo_Domingo", "America/St_Johns", "Asia/Baghdad", "Asia/Baku",
    "Asia/Beirut", "Asia/Dhaka", "Asia/Dubai", "Asia/Irkutsk", "Asia/Jakarta",
    "Asia/Kabul", "Asia/Kamchatka", "Asia/Karachi", "Asia/Kathmandu",
    "Asia/Kolkata", "Asia/Krasnoyarsk", "Asia/Omsk", "Asia/Rangoon",
    "Asia/Shanghai", "Asia/Tehran", "Asia/Tokyo", "Asia/Vladivostok",
    "Asia/Yakutsk", "Asia/Yekaterinburg", "Atlantic/Azores",
    "Atlantic/Cape_Verde", "Australia/Adelaide", "Australia/Brisbane",
    "Australia/Darwin", "Australia/Eucla", "Australia/Eucla",
    "Australia/Lord_Howe", "Australia/Sydney", "Etc/GMT+12", "Europe/Berlin",
    "Europe/London", "Europe/Moscow", "Pacific/Apia", "Pacific/Apia",
    "Pacific/Auckland", "Pacific/Chatham", "Pacific/Easter", "Pacific/Gambier",
    "Pacific/Honolulu", "Pacific/Kiritimati", "Pacific/Majuro",
    "Pacific/Marquesas", "Pacific/Norfolk", "Pacific/Noumea",
    "Pacific/Pago_Pago", "Pacific/Pitcairn", "Pacific/Tongatapu", "UTC",
}


@view_config(route_name="account_timezone", request_method="POST", permission="view")
def account_timezone(request):
    if request.POST["timezone"] in timezones:
        Session.query(User).filter(User.id==request.user.id).update({
            "timezone": request.POST["timezone"],
        })
    return HTTPNoContent()


@view_config(route_name="account_layout_version", request_method="POST", permission="view")
def account_layout_version(request):
    if request.POST["layout_version"] in ("1", "2"):
        Session.query(User).filter(User.id==request.user.id).update({
            "layout_version": int(request.POST["layout_version"]),
        })
    return HTTPFound(request.environ["HTTP_REFERER"])

