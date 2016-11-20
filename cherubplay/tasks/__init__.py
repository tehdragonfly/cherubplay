from celery import group
from contextlib import contextmanager
from datetime import datetime, timedelta
from pyramid_celery import celery_app as app
from sqlalchemy import and_, engine_from_config, func
from sqlalchemy.dialects.postgresql import INTERVAL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import cast

from cherubplay.models import Request, RequestTag, User


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

