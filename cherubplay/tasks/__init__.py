import datetime, jwt, math, os.path, pathlib, requests, time

from celery import group
from contextlib import contextmanager
from logging import getLogger
from pkg_resources import resource_filename
from pyramid.renderers import render
from pyramid_celery import celery_app as app
from sqlalchemy import and_, func
from sqlalchemy.dialects.postgresql import INTERVAL
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import cast
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from zipfile import ZipFile, ZIP_DEFLATED

from cherubplay.models import get_sessionmaker, PushSubscription, Request, RequestSlot, User, VirtualUserConnection, \
    Chat, ChatUser, Message, ChatExport
from cherubplay.services.redis import make_redis_login
from cherubplay.services.request import RequestService
from cherubplay.services.user_connection import UserConnectionService

log = getLogger(__name__)


sm = None


@contextmanager
def db_session():
    global sm
    if not sm:
        sm = get_sessionmaker(app.conf["PYRAMID_REGISTRY"].settings, for_worker=True)
    db = sm()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@app.task
def reap_requests():
    with db_session() as db:
        user_query = db.query(User.id).filter(User.last_online < func.now() - cast("7 days", INTERVAL))
        db.query(Request).filter(and_(
            Request.status == "posted",
            Request.user_id.in_(user_query),
        )).update({"status": "draft"}, synchronize_session=False)
        db.query(RequestSlot).filter(and_(
            RequestSlot.order != 1,
            RequestSlot.user_id.in_(user_query),
        )).update({"user_id": None, "user_name": None}, synchronize_session=False)


@app.task
def update_request_tag_ids(request_id):
    """
    Populate Request.tag_ids with normal tag ids and parent tag ids.
    """
    with db_session() as db:
        db.execute("""
            update requests set tag_ids = array(
                with recursive tag_ids(id) as (
                    select tag_id from request_tags where request_id=requests.id
                    union all
                    select parent_id from tag_parents, tag_ids where child_id=tag_ids.id
                )
                select distinct id from tag_ids order by id
            ) where id=%s;
        """ % request_id)


@app.task
def update_missing_request_tag_ids():
    with db_session() as db:
        requests_without_tags = db.query(Request.id).filter(Request.tag_ids == None).all()
    group(update_request_tag_ids.s(_.id) for _ in requests_without_tags).delay()


@app.task
def check_tag_consistency():
    with db_session() as db:
        # TODO check parent tags
        inconsistent_requests = db.execute("""
            select id
            from (
                select
                    id,
                    array((
                        select unnest(tag_ids) as u
                        from requests as requests_inner
                        where requests_outer.id=requests_inner.id
                        order by u
                    )) as sorted_tag_ids,
                    array(select tag_id from request_tags where request_id=id order by tag_id) as actual_tags
                from requests as requests_outer
            ) as anon_1
            where sorted_tag_ids != actual_tags order by id;
        """)
    group(update_request_tag_ids.s(_.id) for _ in inconsistent_requests).delay()


@app.task(queue="cleanup")
def remove_unused_tags():
    """
    Unused tags are not approved, not a synonym, don't have a synonym, have no
    RequestTags, no BlacklistedTags, no TagParents and no sugggestions. With
    playing/wanted pairs both tags in the pair must have none of the above.
    """
    remove_unused_warning_and_misc_tags.delay()
    remove_unused_tag_pairs.delay("fandom")
    remove_unused_tag_pairs.delay("character")
    remove_unused_tag_pairs.delay("gender")


@app.task(queue="cleanup")
def remove_unused_warning_and_misc_tags():
    with db_session() as db:
        db.execute("""
            delete from tags where id in (
                select id from tags
                where type in ('warning', 'misc')
                and approved=false and synonym_id is null
                except (
                    select tag_id from request_tags
                    union select synonym_id from tags where synonym_id is not null
                    union select tag_id from blacklisted_tags
                    union select parent_id from tag_parents
                    union select child_id from tag_parents
                    union select tag_id from tag_make_synonym_suggestions
                    union select target_id from tag_make_synonym_suggestions
                    union select tag_id from tag_add_parent_suggestions
                    union select target_id from tag_add_parent_suggestions
                    union select tag_id from tag_bump_maturity_suggestions
                )
            );
        """)


@app.task(queue="cleanup")
def remove_unused_tag_pairs(tag_type):
    with db_session() as db:
        db.execute("""
            delete from tags
            where type in ('{tag_type}', '{tag_type}_wanted')
            and lower(name) in (
                select lower(name) from tags where id in (
                    select id from tags
                    where type='{tag_type}'
                    and approved=false and synonym_id is null
                    except (
                        select tag_id from request_tags
                        union select synonym_id from tags where synonym_id is not null
                        union select tag_id from blacklisted_tags
                        union select parent_id from tag_parents
                        union select child_id from tag_parents
                        union select tag_id from tag_make_synonym_suggestions
                        union select target_id from tag_make_synonym_suggestions
                        union select tag_id from tag_add_parent_suggestions
                        union select target_id from tag_add_parent_suggestions
                        union select tag_id from tag_bump_maturity_suggestions
                    )
                )
                intersect
                select lower(name) from tags where id in (
                    select id from tags
                    where type='{tag_type}_wanted'
                    and approved=false and synonym_id is null
                    except (
                        select tag_id from request_tags
                        union select synonym_id from tags where synonym_id is not null
                        union select tag_id from blacklisted_tags
                        union select parent_id from tag_parents
                        union select child_id from tag_parents
                        union select tag_id from tag_make_synonym_suggestions
                        union select target_id from tag_make_synonym_suggestions
                        union select tag_id from tag_add_parent_suggestions
                        union select target_id from tag_add_parent_suggestions
                        union select tag_id from tag_bump_maturity_suggestions
                    )
                )
            );
        """.format(tag_type=tag_type))


@app.task
def trigger_push_notification(user_id):
    with db_session() as db:
        subscriptions = db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()
        group(post_push_notification.s(_.id, _.data["endpoint"]) for _ in subscriptions).delay()


@app.task
def post_push_notification(subscription_id, endpoint):
    settings = app.conf["PYRAMID_REGISTRY"].settings
    response = requests.post(
        endpoint,
        headers={
            "Authorization": "Bearer " + jwt.encode(
                {
                    "aud": "https://" + urlparse(endpoint).hostname,
                    "sub": "mailto:mysticdragonfly@hotmail.co.uk",
                    "exp": int(time.time()) + 86400,
                },
                settings["push.private_key"],
                algorithm="ES256",
            ).decode(),
            "Crypto-Key": "p256ecdsa=" + settings["push.public_key"],
            "Ttl": "86400",
        },
    )
    if response.status_code in (404, 410):
        log.info("Subscription %s no longer exists." % subscription_id)
        with db_session() as db:
            db.query(PushSubscription).filter(PushSubscription.id == subscription_id).delete()
    elif response.status_code not in (200, 201):
        log.warning("Push endpoint for subscription %s returned status %s:" % (subscription_id, response.status_code))
        log.debug(response.request.headers)
        log.debug(response.headers)
        log.debug(response.text)


@app.task
def check_virtual_connection_consistency():
    with db_session() as db:
        group(convert_virtual_connections.s(_) for _, in (
            db.query(User.id).filter(
                func.lower(User.username)
                .in_(db.query(func.lower(VirtualUserConnection.to_username).distinct()))
            )
        )).delay()


@app.task
def convert_virtual_connections(user_id: int):
    with db_session() as db:
        user = db.query(User).filter(User.id == user_id).one()
        UserConnectionService(db).convert_virtual_connections(user)


@app.task
def answer_requests_with_full_slots():
    with db_session() as db:
        redis = make_redis_login(app.conf["PYRAMID_REGISTRY"].settings)
        request_service = RequestService(db, redis)
        for request in request_service.requests_with_full_slots():
            request_service.answer(request)


MESSAGES_PER_PAGE = 25
EXPIRY_TIME = datetime.timedelta(3)


@app.task(queue="export")
def export_chat(chat_id: int, user_id: int):
    log.info("Starting export for chat %s, user %s." % (chat_id, user_id))
    with db_session() as db, TemporaryDirectory() as workspace:
        start_time    = datetime.datetime.now()
        chat          = db.query(Chat).filter(Chat.id == chat_id).one()
        chat_user     = db.query(ChatUser).filter(and_(ChatUser.chat_id == chat_id, ChatUser.user_id == user_id)).one()

        chat_export   = db.query(ChatExport).filter(and_(ChatExport.chat_id == chat_id, ChatExport.user_id == user_id)).one()
        if export_chat.request.id and chat_export.celery_task_id != export_chat.request.id:
            raise RuntimeError("Current task ID doesn't match value in database.")

        message_count = db.query(func.count("*")).select_from(Message).scalar()
        page_count    = int(math.ceil(message_count/MESSAGES_PER_PAGE))

        filename = "%s.zip" % chat.url
        file_in_workspace = os.path.join(workspace, filename)

        with ZipFile(file_in_workspace, "w", ZIP_DEFLATED) as f:

            f.write(resource_filename("cherubplay", "static/cherubplay2.css"), "cherubplay2.css")
            f.write(resource_filename("cherubplay", "static/logo.png"), "logo.png")

            for n in range(page_count):
                log.info("Processing page %s of %s." % (n+1, page_count))
                messages = (
                    db.query(Message)
                    .filter(Message.chat_id == chat_id)
                    .order_by(Message.id)
                    .offset(n * MESSAGES_PER_PAGE).limit(MESSAGES_PER_PAGE).all()
                )
                f.writestr("%s.html" % (n+1), render("export/chat.mako", {
                    "chat": chat,
                    "chat_user": chat_user,
                    "messages": messages,
                    "current_page": n+1,
                    "messages_per_page": MESSAGES_PER_PAGE,
                    "message_count": message_count,
                }))
                f.writestr("%s.json" % (n+1), render("json", messages))

            f.writestr("chat.json",      render("json", chat))
            f.writestr("chat_user.json", render("json", chat_user))

        chat_export.filename = filename

        chat_export.generated = start_time
        chat_export.expires   = datetime.datetime.now() + EXPIRY_TIME

        pathlib.Path(os.path.join(app.conf["PYRAMID_REGISTRY"].settings["export_destination"], chat_export.file_directory)).mkdir(parents=True, exist_ok=True)
        os.rename(file_in_workspace, os.path.join(app.conf["PYRAMID_REGISTRY"].settings["export_destination"], chat_export.file_path))

        log.info("Finished export for chat %s, user %s." % (chat_id, user_id))


@app.task(queue="cleanup")
def cleanup_expired_exports():
    with db_session() as db:
        group(
            delete_expired_export.s(_.chat_id, _.user_id)
            for _ in db.query(ChatExport).filter(ChatExport.expires < func.now())
        ).delay()


@app.task(queue="cleanup")
def delete_expired_export(chat_id: int, user_id: int):
    with db_session() as db:
        try:
            chat_export = db.query(ChatExport).filter(and_(ChatExport.chat_id == chat_id, ChatExport.user_id == user_id)).one()
        except NoResultFound:
            return
        if chat_export.filename:
            try:
                os.remove(os.path.join(app.conf["PYRAMID_REGISTRY"].settings["export_destination"], chat_export.file_path))
            except FileNotFoundError:
                pass
            os.rmdir(os.path.join(app.conf["PYRAMID_REGISTRY"].settings["export_destination"], chat_export.file_directory))
            # Try to delete the chat directory.
            # May fail if there's another export, so ignore.
            try:
                os.rmdir(os.path.join(
                    app.conf["PYRAMID_REGISTRY"].settings["export_destination"],
                    chat_export.file_directory.rsplit("/", 1)[0]
                ))
            except OSError:
                pass
        db.delete(chat_export)
