from bcrypt import gensalt, hashpw
from pyramid.httpexceptions import HTTPFound, HTTPNoContent
from pyramid.view import view_config

from ..models import (
    Session,
    User,
)


@view_config(route_name="account", renderer="account.mako", request_method="GET")
def account(request):
    return {}


@view_config(route_name="account_password", renderer="account.mako", request_method="POST")
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


@view_config(route_name="account_timezone", request_method="POST")
def account_timezone(request):
    if request.POST["timezone"] in timezones:
        Session.query(User).filter(User.id==request.user.id).update({
            "timezone": request.POST["timezone"],
        })
    return HTTPNoContent()

