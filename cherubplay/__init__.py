import binascii

from base64 import urlsafe_b64decode
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1, derive_private_key
from datetime import datetime
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import JSON
from pyramid.security import Authenticated, Everyone
from redis.exceptions import ConnectionError
from sqlalchemy import and_, func
from sqlalchemy.orm.exc import NoResultFound

from cherubplay.models import Base, Chat, ChatUser, Resource, User
from cherubplay.models.enums import ChatUserStatus, TagType
from cherubplay.resources import (
    ChatContext, prompt_factory, report_factory, TagList, TagPair,
    request_factory, user_factory,
)


JSONRenderer = JSON()
JSONRenderer.add_adapter(datetime, lambda obj, request: obj.isoformat())
JSONRenderer.add_adapter(set,      lambda obj, request: list(obj))


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


def add_ext_route(configurator, name, pattern, **kwargs):
    configurator.add_route(name, pattern, **kwargs)
    ext_name = name + "_ext"
    ext_pattern = (pattern[:-1] if pattern.endswith("/") else pattern) + ".{ext}"
    configurator.add_route(ext_name, ext_pattern, **kwargs)


class CherubplayAuthenticationPolicy(object):

    def authenticated_userid(self, request):
        if request.user is not None:
            return request.user.id

    def unauthenticated_userid(self, request):
        if request.user is not None:
            return request.user.id

    def effective_principals(self, request):
        if request.user is None:
            return Everyone,
        elif request.user.status == "banned":
            return Everyone, Authenticated, "banned"
        elif request.user.status == "admin":
            return Everyone, Authenticated, request.user.id, "active", "admin"
        return Everyone, Authenticated, request.user.id, "active"

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
        user_id = request.login_store.get("session:" + request.cookies["cherubplay"])
    except ConnectionError:
        return None
    if user_id is not None:
        try:
            db = request.find_service(name="db")
            user = db.query(User).filter(User.id == int(user_id)).one()
            user.last_online = datetime.now()
            user.last_ip = request.environ["REMOTE_ADDR"]
            if user.status == "banned" and user.unban_date is not None:
                if user.unban_delta.total_seconds() < 0:
                    user.status = "active"
                    user.unban_date = None
            return user
        except (ValueError, NoResultFound):
            return None
    return None


def request_unread_chats(request):
    if request.user is None:
        return 0
    db = request.find_service(name="db")
    return db.query(func.count('*')).select_from(ChatUser).join(Chat).filter(and_(
        ChatUser.user_id == request.user.id,
        ChatUser.status == ChatUserStatus.active,
        Chat.updated > ChatUser.visited,
    )).scalar()


def request_show_news(request):
    if request.user is None:
        return False

    try:
        last_updated = datetime.fromtimestamp(float(request.login_store.get("news_last_updated")))
    except (TypeError, ValueError):
        return False

    return request.user.last_read_news is None or request.user.last_read_news < last_updated


def main(global_config, **settings):

    if "push.private_key" in settings:
        settings["push.private_key"] = derive_private_key(
            int(binascii.hexlify(urlsafe_b64decode(
                settings["push.private_key"].encode()
                + b"===="[len(settings["push.private_key"]) % 4:]
            )), 16),
            curve=SECP256R1(),
            backend=default_backend(),
        )

    for tag_type in TagType:
        settings["checkbox_tags." + tag_type.value] = [
            name.strip()
            for name in settings.get("checkbox_tags." + tag_type.value, "").split("\n")
            if name.strip()
        ]

    config = Configurator(
        authentication_policy=CherubplayAuthenticationPolicy(),
        authorization_policy=ACLAuthorizationPolicy(),
        root_factory=CherubplayRootFactory,
        settings=settings,
    )
    config.configure_celery(global_config['__file__'])

    config.include("pyramid_services")
    config.include("cherubplay.models")
    config.include("cherubplay.services.redis")
    config.include("cherubplay.services.message")
    config.include("cherubplay.services.request")
    config.include("cherubplay.services.tag")

    config.add_renderer("json", JSONRenderer)

    # These are defined here because we need the settings to create the connection pools.
    def request_login_store(request):
        return request.find_service(name="redis_login")

    config.add_request_method(request_login_store,  "login_store",  reify=True)
    config.add_request_method(request_user,         "user",         reify=True)
    config.add_request_method(request_unread_chats, "unread_chats", reify=True)
    config.add_request_method(request_show_news,    "show_news",    reify=True)

    config.add_static_view("static", "static", cache_max_age=3600)

    # Method for adding routes with extensions.
    config.add_directive("add_ext_route", add_ext_route)
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

    config.add_ext_route("chat_notification", "/chats/notification/")

    config.add_ext_route("chat",         "/chats/{url}/",             factory=ChatContext)
    config.add_route("chat_info",        "/chats/{url}/info/",        factory=ChatContext)
    config.add_route("chat_change_name", "/chats/{url}/change_name/", factory=ChatContext)
    config.add_route("chat_remove_user", "/chats/{url}/remove_user/", factory=ChatContext)

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
    config.add_ext_route("directory_yours_tag", "/directory/yours/{tag_string:[^:]+:[^/,]+(,[^:]+:[^/,]+){0,4}}/", factory=TagList)

    config.add_route("directory_search", "/directory/search/")
    config.add_route("directory_search_autocomplete", "/directory/search/autocomplete/")

    config.add_route("directory_tag_list", "/directory/tags/")
    config.add_route("directory_tag_list_unapproved", "/directory/tags/unapproved/")
    config.add_route("directory_tag_list_blacklist_default", "/directory/tags/blacklist_default/")
    config.add_route("directory_tag_table", "/directory/tags/table/")

    config.add_ext_route("directory_user", "/directory/user:{username}/")

    config.add_ext_route("directory_tag", "/directory/{tag_string:[^:]+:[^/,]+(,[^:]+:[^/,]+){0,4}}/", factory=TagList)
    config.add_ext_route("directory_tag_search", "/directory/{tag_string:[^:]+:[^/,]+(,[^:]+:[^/,]+){0,4}}/search/", factory=TagList)
    config.add_ext_route("directory_tag_search_autocomplete", "/directory/{tag_string:[^:]+:[^/,]+(,[^:]+:[^/,]+){0,4}}/search/autocomplete/", factory=TagList)

    config.add_ext_route("directory_tag_approve",       "/directory/{type}:{name}/approve/",       factory=TagPair.from_request)
    config.add_ext_route("directory_tag_suggest",       "/directory/{type}:{name}/suggest/",       factory=TagPair.from_request)
    config.add_ext_route("directory_tag_suggest_make_synonym",  "/directory/{type}:{name}/suggest/make_synonym/",  factory=TagPair.from_request)
    config.add_ext_route("directory_tag_suggest_add_parent",    "/directory/{type}:{name}/suggest/add_parent/",    factory=TagPair.from_request)
    config.add_ext_route("directory_tag_suggest_bump_maturity", "/directory/{type}:{name}/suggest/bump_maturity/", factory=TagPair.from_request)
    config.add_ext_route("directory_tag_make_synonym",  "/directory/{type}:{name}/make_synonym/",  factory=TagPair.from_request)
    config.add_ext_route("directory_tag_add_parent",    "/directory/{type}:{name}/add_parent/",    factory=TagPair.from_request)
    config.add_ext_route("directory_tag_bump_maturity", "/directory/{type}:{name}/bump_maturity/", factory=TagPair.from_request)

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
    config.add_route("directory_request_kick",     "/directory/{id:\d+}/kick/",     factory=request_factory)
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
    config.add_route("account_away_message",     "/account/away_message/")
    config.add_route("account_read_news",        "/account/read_news/")

    config.add_route("admin_report_list",         "/admin/reports/")
    config.add_route("admin_report_list_closed",  "/admin/reports/closed/")
    config.add_route("admin_report_list_invalid", "/admin/reports/invalid/")
    config.add_ext_route("admin_report",          "/admin/reports/{id}/",                   factory=report_factory)
    config.add_route("admin_user",                "/admin/user/{username}/",                factory=user_factory)
    config.add_route("admin_user_status",         "/admin/user/{username}/status/",         factory=user_factory)
    config.add_route("admin_user_chat",           "/admin/user/{username}/chat/",           factory=user_factory)
    config.add_route("admin_user_ban",            "/admin/user/{username}/ban/",            factory=user_factory)
    config.add_route("admin_user_reset_password", "/admin/user/{username}/reset_password/", factory=user_factory)
    config.add_route("admin_news",                "/admin/news/")

    config.scan()
    return config.make_wsgi_app()
