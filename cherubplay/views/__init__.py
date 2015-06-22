import transaction
import uuid

from bcrypt import gensalt, hashpw
from pyramid.httpexceptions import HTTPForbidden, HTTPFound
from pyramid.renderers import render_to_response
from pyramid.view import view_config
from redis.exceptions import ConnectionError
from sqlalchemy.orm.exc import NoResultFound

from ..lib import username_validator, reserved_usernames, preset_colours, prompt_categories, prompt_levels
from ..models import (
    Session,
    User,
)

@view_config(route_name="home")
def home(request):
    if request.user is not None:
        return render_to_response("home.mako", {
            "preset_colours": preset_colours,
            "prompt_categories": prompt_categories,
            "prompt_levels": prompt_levels,
        }, request=request)
    else:
        return render_to_response("layout2/home_guest.mako", { "forbidden": False }, request=request)

@view_config(route_name="sign_up", renderer="layout2/home_guest.mako", request_method="POST")
def sign_up(request):
    # Disable signing up in read-only mode.
    if "cherubplay.read_only" in request.registry.settings:
        raise HTTPForbidden
    # Make sure this IP address hasn't created an account recently.
    # Also don't explode if Redis is down.
    ip_check_key = "ip:"+request.environ["REMOTE_ADDR"]
    try:
        ip_check = request.login_store.get(ip_check_key)
    except ConnectionError:
        return { "sign_up_error": "We can't create your account because we're having problems with the login server. Please try again later." }
    if ip_check is not None:
        return { "sign_up_error": "An account has already been created from your IP address. Please try again in a few hours." }
    # Validate password.
    if request.POST["password"]=="":
        return { "sign_up_error": "Please don't use a blank password." }
    if request.POST["password"]!=request.POST["password_again"]:
        return { "sign_up_error": "The two passwords didn't match." }
    # Make sure username hasn't been taken.
    username = request.POST["username"].lower()[:100]
    if username_validator.match(username) is None:
        return { "sign_up_error": "Usernames can only contain letters, numbers, hyphens and underscores." }
    existing_username = Session.query(User.id).filter(User.username==username).count()
    if existing_username==1 or username in reserved_usernames:
        return { "sign_up_error": "The username \"%s\" has already been taken." % username }
    # Create the user.
    new_user = User(
        username=username,
        password=hashpw(request.POST["password"].encode(), gensalt()),
        last_ip=request.environ["REMOTE_ADDR"],
    )
    Session.add(new_user)
    Session.flush()
    # Generate session ID and add it to the login store.
    new_session_id = str(uuid.uuid4())
    request.login_store.set("session:"+new_session_id, new_user.id)
    # Remember their IP address for 12 hours.
    ip_check = request.login_store.set(ip_check_key, "1")
    ip_check = request.login_store.expire(ip_check_key, 43200)
    # Set cookie for session ID.
    response = HTTPFound(request.route_path("home"))
    response.set_cookie("cherubplay", new_session_id, 31536000)
    return response

@view_config(route_name="log_in", renderer="layout2/home_guest.mako", request_method="POST")
def log_in(request):
    # Disable logging in in read-only mode.
    if "cherubplay.read_only" in request.registry.settings:
        raise HTTPForbidden
    try:
        user = Session.query(User).filter(User.username==request.POST["username"].lower()).one()
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
    return response

@view_config(route_name="log_out", renderer="log_out.mako", request_method="POST")
def log_out(request):
    if "cherubplay" in request.cookies:
        request.login_store.delete("session:"+request.cookies["cherubplay"])
    response = HTTPFound(request.route_path("home"))
    response.delete_cookie("cherubplay")
    return response

