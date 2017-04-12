import datetime
import transaction

from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import JSON
from pyramid.security import Allow, Authenticated, Everyone
from redis import ConnectionPool, StrictRedis, UnixDomainSocketConnection
from redis.exceptions import ConnectionError
from sqlalchemy import and_, engine_from_config, func
from sqlalchemy.orm.exc import NoResultFound

from cherubplay.models import Session, Base, Chat, ChatUser, Resource, User
from cherubplay.models.enums import ChatUserStatus
from cherubplay.resources import ChatContext, prompt_factory, report_factory, TagList, TagPair, request_factory


JSONRenderer = JSON()
JSONRenderer.add_adapter(set, lambda obj, request: list(obj))


class ExtensionPredicate(object):
    def __init__(self, extension, config):
        self.extension = extension

    def text(self):
        return "extension == %s" % self.extension

    phash = text

    def __call__(self, context, request):
        # Redirect to no extension if extension is html.
        if request.matchdict["ext"] == "html":
            del request.matchdict["ext"]
            plain_route = request.matched_route.name.split("_ext")[0]
            raise HTTPFound(request.route_path(plain_route, **request.matchdict))
        return request.matchdict["ext"] == self.extension


class CherubplayConfigurator(Configurator):
    def add_ext_route(self, name, pattern, **kwargs):
        self.add_route(name, pattern, **kwargs)
        ext_name = name + "_ext"
        ext_pattern = (pattern[:-1] if pattern.endswith("/") else pattern) + ".{ext}"
        self.add_route(ext_name, ext_pattern, **kwargs)


class CherubplayAuthenticationPolicy(object):

    def authenticated_userid(self, request):
        if request.user is not None:
            return request.user.id

    def unauthenticated_userid(self, request):
        if request.user is not None:
            return request.user.id

    def effective_principals(self, request):
        if request.user is None:
            return (Everyone,)
        elif request.user.status == "banned":
            return (Everyone, Authenticated, "banned")
        elif request.user.status == "admin":
            return (Everyone, Authenticated, request.user.id, "active", "admin")
        return (Everyone, Authenticated, request.user.id, "active")

    def remember(self, request, principal, **kw):
        raise NotImplementedError

    def forget(self, request):
        raise NotImplementedError


class CherubplayRootFactory(Resource):
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
            user = Session.query(User).filter(User.id==int(user_id)).one()
            user.last_online = datetime.datetime.now()
            user.last_ip = request.environ["REMOTE_ADDR"]
            if user.status == "banned" and user.unban_date is not None:
                if user.unban_delta.total_seconds() < 0:
                    user.status = "active"
                    user.unban_date = None
            # The ACL stuff means the user object belongs to a different
            # transaction to the rest of the request, so we have to manually
            # commit it here (and set the Session to not expire on commit).
            transaction.commit()
            return user
        except (ValueError, NoResultFound):
            return None
    return None


def request_unread_chats(request):
    if request.user is None:
        return 0
    return Session.query(func.count('*')).select_from(ChatUser).join(Chat).filter(and_(
        ChatUser.user_id == request.user.id,
        ChatUser.status == ChatUserStatus.active,
        Chat.updated > ChatUser.visited,
    )).scalar()


def main(global_config, **settings):

    engine = engine_from_config(settings, "sqlalchemy.")
    Session.configure(bind=engine)
    Base.metadata.bind = engine

    config = CherubplayConfigurator(
        authentication_policy=CherubplayAuthenticationPolicy(),
        authorization_policy=ACLAuthorizationPolicy(),
        root_factory=CherubplayRootFactory,
        settings=settings,
    )
    config.configure_celery(global_config['__file__'])

    # Replace the JSON renderer so we can serialise sets.
    config.add_renderer("json", JSONRenderer)

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
        return StrictRedis(connection_pool=login_pool)
    def request_pubsub(request):
        return StrictRedis(connection_pool=pubsub_pool)

    config.add_request_method(request_login_store, 'login_store', reify=True)
    config.add_request_method(request_pubsub, 'pubsub', reify=True)
    config.add_request_method(request_user, 'user', reify=True)
    config.add_request_method(request_unread_chats, 'unread_chats', reify=True)

    config.add_static_view("static", "static", cache_max_age=3600)

    config.add_view_predicate("extension", ExtensionPredicate)

    config.add_route("home", "/")

    config.add_route("sign_up", "/sign-up/")
    config.add_route("log_in", "/log-in/")
    config.add_route("log_out", "/log-out/")

    config.add_ext_route("chat_list", "/chats/")
    config.add_ext_route("chat_list_unanswered", "/chats/unanswered/")
    config.add_ext_route("chat_list_ongoing", "/chats/ongoing/")
    config.add_ext_route("chat_list_ended", "/chats/ended/")
    config.add_ext_route("chat_list_label", "/chats/labels/{label}/")

    config.add_ext_route("chat",     "/chats/{url}/",      factory=ChatContext)
    config.add_route("chat_info",    "/chats/{url}/info/", factory=ChatContext)

    config.add_route("chat_draft",  "/chats/{url}/draft/",             factory=ChatContext)
    config.add_route("chat_send",   "/chats/{url}/send/",              factory=ChatContext)
    config.add_route("chat_edit",   "/chats/{url}/edit/{message_id}/", factory=ChatContext)
    config.add_route("chat_end",    "/chats/{url}/end/",               factory=ChatContext)
    config.add_route("chat_delete", "/chats/{url}/delete/",            factory=ChatContext)
    config.add_route("chat_leave",  "/chats/{url}/leave/",             factory=ChatContext)

    config.add_ext_route("prompt_list", "/prompts/")
    config.add_route("new_prompt", "/prompts/new/")
    config.add_ext_route("prompt", "/prompts/{id:\d+}/", factory=prompt_factory)
    config.add_route("edit_prompt", "/prompts/{id:\d+}/edit/", factory=prompt_factory)
    config.add_route("delete_prompt", "/prompts/{id:\d+}/delete/", factory=prompt_factory)

    config.add_ext_route("directory", "/directory/")

    config.add_ext_route("directory_yours", "/directory/yours/")

    config.add_route("directory_search", "/directory/search/")
    config.add_route("directory_search_autocomplete", "/directory/search/autocomplete/")

    config.add_route("directory_tag_list", "/directory/tags/")
    config.add_route("directory_tag_list_unapproved", "/directory/tags/unapproved/")
    config.add_route("directory_tag_list_blacklist_default", "/directory/tags/blacklist_default/")
    config.add_route("directory_tag_table", "/directory/tags/table/")

    config.add_ext_route("directory_tag", "/directory/{tag_string:[^:]+:[^/,]+(,[^:]+:[^/,]+){0,4}}/", factory=TagList)

    config.add_ext_route("directory_tag_approve",      "/directory/{type}:{name}/approve/",      factory=TagPair)
    config.add_ext_route("directory_tag_make_synonym", "/directory/{type}:{name}/make_synonym/", factory=TagPair)
    config.add_ext_route("directory_tag_add_parent",   "/directory/{type}:{name}/add_parent/",   factory=TagPair)

    config.add_route("directory_random", "/directory/random/")

    config.add_ext_route("directory_new", "/directory/new/")
    config.add_route("directory_new_autocomplete", "/directory/new/autocomplete/")

    config.add_ext_route("directory_blacklist", "/directory/blacklist/")
    config.add_route("directory_blacklist_setup", "/directory/blacklist/setup/")
    config.add_route("directory_blacklist_add", "/directory/blacklist/add/")
    config.add_route("directory_blacklist_remove", "/directory/blacklist/remove/")

    config.add_ext_route("directory_request",      "/directory/{id:\d+}/",          factory=request_factory)
    config.add_route("directory_request_answer",   "/directory/{id:\d+}/answer/",   factory=request_factory)
    config.add_route("directory_request_unanswer", "/directory/{id:\d+}/unanswer/", factory=request_factory)
    config.add_route("directory_request_edit",     "/directory/{id:\d+}/edit/",     factory=request_factory)
    config.add_route("directory_request_delete",   "/directory/{id:\d+}/delete/",   factory=request_factory)
    config.add_route("directory_request_remove",   "/directory/{id:\d+}/remove/",   factory=request_factory)
    config.add_route("directory_request_unremove", "/directory/{id:\d+}/unremove/", factory=request_factory)

    config.add_route("account",                  "/account/")
    config.add_route("account_email_address",    "/account/email_address/")
    config.add_route("account_verify_email",     "/account/verify_email/")
    config.add_route("account_password",         "/account/password/")
    config.add_route("account_timezone",         "/account/timezone/")
    config.add_route("account_layout_version",   "/account/layout_version/")
    config.add_route("account_forgot_password",  "/account/forgot_password/")
    config.add_route("account_reset_password",   "/account/reset_password/")
    config.add_route("account_push_subscribe",   "/account/push/subscribe/")
    config.add_route("account_push_unsubscribe", "/account/push/unsubscribe/")

    config.add_route("admin_report_list", "/admin/reports/")
    config.add_route("admin_report_list_closed", "/admin/reports/closed/")
    config.add_route("admin_report_list_invalid", "/admin/reports/invalid/")
    config.add_ext_route("admin_report", "/admin/reports/{id}/", factory=report_factory)
    config.add_route("admin_user", "/admin/user/{username}/")
    config.add_route("admin_user_status", "/admin/user/{username}/status/")
    config.add_route("admin_user_chat", "/admin/user/{username}/chat/")
    config.add_route("admin_user_ban", "/admin/user/{username}/ban/")

    config.add_route("api_users", "/api/users.json")

    config.scan()
    return config.make_wsgi_app()

