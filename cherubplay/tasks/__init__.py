import requests

from celery import group
from contextlib import contextmanager
from datetime import datetime, timedelta
from logging import getLogger
from pyramid_celery import celery_app as app
from sqlalchemy import and_, engine_from_config, func
from sqlalchemy.dialects.postgresql import INTERVAL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import cast

from cherubplay.models import PushSubscription, Request, RequestTag, User


log = getLogger(__name__)


engine = engine_from_config(app.conf["PYRAMID_REGISTRY"].settings, "sqlalchemy.")
sm = sessionmaker(bind=engine, autoflush=False)


@contextmanager
def db_session():
    db = sm()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()


@app.task
def reap_requests():
    with db_session() as db:
        db.query(Request).filter(and_(
            Request.status == "posted",
            Request.user_id.in_(
                db.query(User.id)
                .filter(User.last_online < func.now() - cast("7 days", INTERVAL))
            ),
        )).update({"status": "draft"}, synchronize_session=False)


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


@app.task
def remove_unused_tags():
    """
    Unused tags are not approved, not a synonym, have no RequestTags, no
    BlacklistedTags and no TagParents. With playing/wanted pairs both tags in
    the pair must have none of the above.
    """
    remove_unused_warning_and_misc_tags.delay()
    remove_unused_tag_pairs.delay("fandom")
    remove_unused_tag_pairs.delay("character")
    remove_unused_tag_pairs.delay("gender")


@app.task
def remove_unused_warning_and_misc_tags():
    with db_session() as db:
        db.execute("""
            delete from tags where id in (
                select id from tags
                where type in ('warning', 'misc')
                and approved=false and synonym_id is null
                except (
                    select tag_id from request_tags
                    union select tag_id from blacklisted_tags
                    union select parent_id from tag_parents
                    union select child_id from tag_parents
                )
            );
        """)


@app.task
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
                        union select tag_id from blacklisted_tags
                        union select parent_id from tag_parents
                        union select child_id from tag_parents
                    )
                )
                intersect
                select lower(name) from tags where id in (
                    select id from tags
                    where type='{tag_type}_wanted'
                    and approved=false and synonym_id is null
                    except (
                        select tag_id from request_tags
                        union select tag_id from blacklisted_tags
                        union select parent_id from tag_parents
                        union select child_id from tag_parents
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
    response = requests.post(endpoint)
    if response.status_code in (404, 410):
        log.info("Subscription %s no longer exists." % subscription_id)
        with db_session() as db:
            db.query(PushSubscription).filter(PushSubscription)
    elif response.status_code not in (200, 201):
        log.warn("Push endpoint for subscription %s returned status %s" % (subscription_id, response.status_code))


