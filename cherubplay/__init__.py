from pyramid.config import Configurator
from redis import Redis, ConnectionPool, UnixDomainSocketConnection
from redis.exceptions import ConnectionError
from sqlalchemy import engine_from_config
from sqlalchemy.orm.exc import NoResultFound

from .models import (
    Session,
    Base,
    User,
)


def request_user(request):
    if "cherubplay" not in request.cookies:
        return None
    try:
        user_id = request.login_store.get("session:"+request.cookies["cherubplay"])
    except ConnectionError:
        return None
    if user_id is not None:
        try:
            return Session.query(User).filter(User.id==user_id).one()
        except NoResultFound:
            return None
    return None


def main(global_config, **settings):

    engine = engine_from_config(settings, "sqlalchemy.")
    Session.configure(bind=engine)
    Base.metadata.bind = engine

    config = Configurator(
        settings=settings,
    )

    login_pool = ConnectionPool(
        connection_class=UnixDomainSocketConnection,
        path=settings["cherubplay.login_store"],
    )

    # This is defined here because we need the settings to create the connection pool.
    def request_login_store(request):
        return Redis(connection_pool=login_pool)

    config.add_request_method(request_login_store, 'login_store', reify=True)
    config.add_request_method(request_user, 'user', reify=True)

    config.add_static_view("static", "static", cache_max_age=3600)

    config.add_route("home", "/")

    config.add_route("sign_up", "/sign-up/")
    config.add_route("log_in", "/log-in/")
    config.add_route("log_out", "/log-out/")

    config.add_route("chat_list", "/chats/")
    config.add_route("chat_list_archive", "/chats/archive/")

    config.add_route("chat", "/chats/{url}/")
    config.add_route("chat_archive", "/chats/url}/archive/")

    config.add_route("account", "/account/")

    config.scan()
    return config.make_wsgi_app()

