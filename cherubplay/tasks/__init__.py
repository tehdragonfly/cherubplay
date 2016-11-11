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
    with db_session() as db:
        db.query(Request).filter(Request.id == request_id).update({
            "tag_ids": func.array(
                db.query(RequestTag.tag_id)
                .filter(RequestTag.request_id == request_id)
                .order_by(RequestTag.tag_id).subquery()
            ),
        }, synchronize_session=False)

