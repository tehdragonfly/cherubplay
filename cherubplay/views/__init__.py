import uuid

from bcrypt import gensalt, hashpw
from pyramid.httpexceptions import HTTPForbidden, HTTPFound, HTTPNotFound
from pyramid.renderers import render_to_response
from pyramid.security import Authenticated
from pyramid.view import view_config
from redis.exceptions import ConnectionError
from sqlalchemy.orm.exc import NoResultFound

from cherubplay.lib import username_validator, reserved_usernames, preset_colours, prompt_categories, prompt_starters, prompt_levels
from cherubplay.models import Prompt, User
from cherubplay.tasks import convert_virtual_connections


@view_config(route_name="home", effective_principals=Authenticated)
def home(request):
    template = "layout2/home.mako" if request.user.layout_version == 2 else "home.mako"
    return render_to_response(template, {
        "saved_prompts": (
            request.find_service(name="db").query(Prompt)
            .filter(Prompt.user_id == request.user.id)
            .order_by(Prompt.title).all()
        ),
        "preset_colours":    preset_colours,
        "prompt_categories": prompt_categories,
        "prompt_starters":   prompt_starters,
        "prompt_levels":     prompt_levels,
    }, request=request)


@view_config(route_name="home", renderer="layout2/home_guest.mako")
def home_guest(request):
    return {"forbidden": False}


@view_config(route_name="sign_up", request_method="POST", renderer="layout2/home_guest.mako")
def sign_up(request):
    if "disable_registration" in request.registry.settings:
        raise HTTPNotFound

    login_store = request.find_service(name="redis_login")

    # Make sure this IP address hasn't created an account recently.
    # Also don't explode if Redis is down.
    ip_check_key = "ip:" + request.remote_addr
    try:
        ip_check = login_store.get(ip_check_key)
    except ConnectionError:
        return {"sign_up_error": "We can't create your account because we're having problems with the login server. Please try again later."}
    if ip_check is not None:
        return {"sign_up_error": "An account has already been created from your IP address. Please try again in a few hours."}

    # Validate password.
    if request.POST["password"] == "":
        return {"sign_up_error": "Please don't use a blank password."}

    if request.POST["password"] != request.POST["password_again"]:
        return {"sign_up_error": "The two passwords didn't match."}

    # Make sure username hasn't been taken.
    username = request.POST["username"].lower()[:100]
    if username_validator.match(username) is None:
        return {"sign_up_error": "Usernames can only contain letters, numbers, hyphens and underscores."}

    db = request.find_service(name="db")
    if (
        username in reserved_usernames
        or db.query(User.id).filter(User.username == username).count() == 1
    ):
        return {"sign_up_error": "The username \"%s\" has already been taken." % username}

    # Create the user.
    new_user = User(
        username=username,
        password=hashpw(request.POST["password"].encode(), gensalt()).decode(),
        last_ip=request.remote_addr,
    )
    db.add(new_user)
    db.flush()

    convert_virtual_connections.delay(new_user.id)

    # Generate session ID and add it to the login store.
    new_session_id = str(uuid.uuid4())
    login_store.set("session:" + new_session_id, new_user.id)

    # Remember their IP address for 12 hours.
    login_store.set(ip_check_key, "1")
    login_store.expire(ip_check_key, 43200)

    # Set cookie for session ID.
    response = HTTPFound(request.route_path("home"))
    response.set_cookie("cherubplay", new_session_id, 31536000)

    return response


@view_config(route_name="log_in", request_method="POST", renderer="layout2/home_guest.mako")
def log_in(request):

    db = request.find_service(name="db")
    try:
        user = db.query(User).filter(User.username == request.POST["username"].lower()).one()
    except NoResultFound:
        return {"log_in_error": "Username and/or password not recognised."}

    if hashpw(request.POST["password"].encode(), user.password.encode()).decode() != user.password:
        return {"log_in_error": "Username and/or password not recognised."}

    # Generate session ID and add it to the login store.
    new_session_id = str(uuid.uuid4())
    try:
        request.find_service(name="redis_login").set("session:" + new_session_id, user.id)
    except ConnectionError:
        return {"log_in_error": "We can't log you in because we're having problems with the login server. Please try again later."}

    # Set cookie for session ID.
    response = HTTPFound(request.route_path("home"))
    response.set_cookie("cherubplay", new_session_id, 31536000)

    return response


@view_config(route_name="log_out", renderer="log_out.mako", request_method="POST")
def log_out(request):
    if "cherubplay" in request.cookies:
        request.find_service(name="redis_login").delete("session:" + request.cookies["cherubplay"])
    response = HTTPFound(request.route_path("home"))
    response.delete_cookie("cherubplay")
    return response


@view_config(route_name="rules", permission="view", renderer="layout2/content.mako")
def rules(request):
    if not request.regstry.settings("rules_file"):
        raise HTTPNotFound
    with open(request.registry.settings["rules_file"]) as f:
        content = f.read()
    return {"title": "Rules", "content": content}
