import transaction
import uuid

from bcrypt import gensalt, hashpw
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render_to_response
from pyramid.view import view_config
from redis.exceptions import ConnectionError
from sqlalchemy.orm.exc import NoResultFound

from ..lib import username_validator, reserved_usernames, preset_colours
from ..models import (
    Session,
    User,
)

@view_config(route_name="home")
def home(request):
    if request.user is not None:
        return render_to_response("home.mako", {
            "preset_colours": preset_colours,
        }, request=request)
    else:
        return render_to_response("home_guest.mako", {}, request=request)

@view_config(route_name="sign_up", renderer="home_guest.mako", request_method="POST")
def sign_up(request):
    if request.POST["password"]=="":
        return { "sign_up_error": "Please don't use a blank password." }
    if request.POST["password"]!=request.POST["password_again"]:
        return { "sign_up_error": "The two passwords didn't match." }
    username = request.POST["username"].lower()[:100]
    if username_validator.match(username) is None:
        return { "sign_up_error": "Usernames can only contain letters, numbers, hyphens and underscores." }
    existing_username = Session.query(User.id).filter(User.username==username).count()
    if existing_username==1 or username in reserved_usernames:
        return { "sign_up_error": "The username \"%s\" has already been taken." % username }
    new_user = User(
        username=username,
        password=hashpw(request.POST["password"].encode(), gensalt()),
    )
    Session.add(new_user)
    Session.flush()
    # Generate session ID and add it to the login store.
    new_session_id = str(uuid.uuid4())
    try:
        request.login_store.set("session:"+new_session_id, new_user.id)
    except ConnectionError:
        return { "sign_up_error": "We can't create your account because we're having problems with the login server. Please try again later." }
    # Set cookie for session ID.
    response = HTTPFound(request.route_path("home"))
    response.set_cookie("cherubplay", new_session_id, 31536000)
    transaction.commit()
    raise response

@view_config(route_name="log_in", renderer="home_guest.mako", request_method="POST")
def log_in(request):
    try:
        user = Session.query(User).filter(User.username==request.POST["username"]).one()
    except NoResultFound:
        return { "log_in_error": "Username and/or password not recognised." }
    if hashpw(request.POST["password"].encode(), user.password.encode())!=user.password:
        return { "log_in_error": "Username and/or password not recognised." }
    # Generate session ID and add it to the login store.
    new_session_id = str(uuid.uuid4())
    try:
        request.login_store.set("session:"+new_session_id, user.id)
    except ConnectionError:
        return { "log_in_error": "We can't log you in because we're having problems with the login server. Please try again later." }
    # Set cookie for session ID.
    response = HTTPFound(request.route_path("home"))
    response.set_cookie("cherubplay", new_session_id, 31536000)
    transaction.commit()
    raise response

@view_config(route_name="log_out", renderer="log_out.mako", request_method="POST")
def log_out(request):
    if "cherubplay" in request.cookies:
        request.login_store.delete("session:"+request.cookies["cherubplay"])
    response = HTTPFound(request.route_path("home"))
    response.delete_cookie("cherubplay")
    raise response

