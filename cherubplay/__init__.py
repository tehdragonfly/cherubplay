import datetime
import transaction

from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.security import Allow, Authenticated, Everyone
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


class CherubplayAuthenticationPolicy(object):

    def authenticated_userid(self, request):
        if request.user is not None:
            return request.user.id

    def unauthenticated_userid(self, request):
        if request.user is not None:
            return request.user.id

    def effective_principals(self, request):
        if request.user is not None:
            if request.user.status=="banned":
                return (Everyone, Authenticated)
            elif request.user.status=="admin":
                return (Everyone, Authenticated, "active", "admin")
            return (Everyone, Authenticated, "active")
        return (Everyone,)

    def remember(self, request, principal, **kw):
        raise NotImplementedError

    def forget(self, request):
        raise NotImplementedError


class CherubplayRootFactory(object):

    __acl__ = (
        (Allow, Authenticated, "view"),
        (Allow, "active", "chat"),
        (Allow, "admin", "admin"),
    )

    def __init__(self, *args):
        pass

def request_user(request):
    if "cherubplay" not in request.cookies:
        return None
    # If we're in read only mode, make everyone a guest.
    if "cherubplay.read_only" in request.registry.settings:
        return None
    try:
        user_id = request.login_store.get("session:"+request.cookies["cherubplay"])
    except ConnectionError:
        return None
    if user_id is not None:
        try:
            user = Session.query(User).filter(User.id==user_id).one()
            user.last_online = datetime.datetime.now()
            user.last_ip = request.environ["REMOTE_ADDR"]
            if user.status == "banned" and user.unban_date is not None:
                if user.unban_delta().total_seconds() < 0:
                    user.status = "active"
                    user.unban_date = None
            # The ACL stuff means the user object belongs to a different
            # transaction to the rest of the request, so we have to manually
            # commit it here (and set the Session to not expire on commit).
            transaction.commit()
            return user
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
        authentication_policy=CherubplayAuthenticationPolicy(),
        authorization_policy=ACLAuthorizationPolicy(),
        root_factory=CherubplayRootFactory,
        settings=settings,
    )

    login_pool = ConnectionPool(
        connection_class=UnixDomainSocketConnection,
        path=settings["cherubplay.socket_login"],
    )

    pubsub_pool = ConnectionPool(
        connection_class=UnixDomainSocketConnection,
        path=settings["cherubplay.socket_pubsub"],
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
    config.add_route("chat_list_unanswered", "/chats/unanswered/")
    config.add_route("chat_list_ongoing", "/chats/ongoing/")
    config.add_route("chat_list_ended", "/chats/ended/")
    config.add_route("chat_list_label", "/chats/labels/{label}/")

    config.add_route("chat", "/chats/{url}/")
    config.add_route("chat_archive", "/chats/{url}/archive/")
    config.add_route("chat_info", "/chats/{url}/info/")

    config.add_route("chat_send", "/chats/{url}/send/")
    config.add_route("chat_edit", "/chats/{url}/edit/{message_id}/")
    config.add_route("chat_end", "/chats/{url}/end/")
    config.add_route("chat_delete", "/chats/{url}/delete/")

    config.add_route("account", "/account/")
    config.add_route("account_password", "/account/password/")

    config.add_route("admin_report_list", "/admin/reports/")
    config.add_route("admin_report_list_closed", "/admin/reports/closed/")
    config.add_route("admin_report_list_invalid", "/admin/reports/invalid/")
    config.add_route("admin_report", "/admin/reports/{id}/")
    config.add_route("admin_user", "/admin/user/{username}/")
    config.add_route("admin_user_status", "/admin/user/{username}/status/")
    config.add_route("admin_user_chat", "/admin/user/{username}/chat/")
    config.add_route("admin_user_ban", "/admin/user/{username}/ban/")

    config.scan()
    return config.make_wsgi_app()

