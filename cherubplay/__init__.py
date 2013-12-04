from pyramid.config import Configurator
from redis import Redis, ConnectionPool, UnixDomainSocketConnection
from redis.exceptions import ConnectionError
from sqlalchemy import and_, engine_from_config, func
from sqlalchemy.orm.exc import NoResultFound

from .models import (
    Session,
    Base,
    Chat,
    ChatUser,
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

def request_unread_chats(request):
    if request.user is None:
        return 0
    return Session.query(func.count('*')).select_from(ChatUser).join(Chat).filter(and_(
        ChatUser.user_id==request.user.id,
        Chat.updated>ChatUser.visited,
    )).scalar()


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

    pubsub_pool = ConnectionPool(
        connection_class=UnixDomainSocketConnection,
        path=settings["cherubplay.pubsub"],
    )

    # These are defined here because we need the settings to create the connection pools.
    def request_login_store(request):
        return Redis(connection_pool=login_pool)
    def request_pubsub(request):
        return Redis(connection_pool=pubsub_pool)

    config.add_request_method(request_login_store, 'login_store', reify=True)
    config.add_request_method(request_pubsub, 'pubsub', reify=True)
    config.add_request_method(request_user, 'user', reify=True)
    config.add_request_method(request_unread_chats, 'unread_chats', reify=True)

    config.add_static_view("static", "static", cache_max_age=3600)

    config.add_route("home", "/")

    config.add_route("sign_up", "/sign-up/")
    config.add_route("log_in", "/log-in/")
    config.add_route("log_out", "/log-out/")

    config.add_route("chat_list", "/chats/")
    config.add_route("chat_list_archive", "/chats/archive/")

    config.add_route("chat", "/chats/{url}/")
    config.add_route("chat_archive", "/chats/{url}/archive/")

    config.add_route("chat_send", "/chats/{url}/send/")
    config.add_route("chat_end", "/chats/{url}/end/")
    config.add_route("chat_delete", "/chats/url}/delete/")

    config.add_route("account", "/account/")

    config.scan()
    return config.make_wsgi_app()

