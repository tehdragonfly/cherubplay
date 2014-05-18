from bcrypt import gensalt, hashpw
from pyramid.httpexceptions import HTTPFound
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
        "password": hashpw(request.POST["password"].encode(), gensalt())
    })

    return HTTPFound(request.route_path("account", _query={ "saved": "password" }))

