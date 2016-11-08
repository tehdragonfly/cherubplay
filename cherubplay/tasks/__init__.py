import transaction

from datetime import datetime, timedelta
from pyramid_celery import celery_app as app
from sqlalchemy import and_, engine_from_config, func

from cherubplay.models import Session, Request, RequestTag, User

@app.task
def reap_requests():
    engine = engine_from_config(app.conf["PYRAMID_REGISTRY"].settings, "sqlalchemy.")
    # TODO don't use scoped_session
    Session.configure(bind=engine)

    Session.query(Request).filter(and_(
        Request.status == "posted",
        Request.user_id.in_(
            Session.query(User.id)
            .filter(User.last_online < datetime.now() - timedelta(7))
        ),
    )).update({"status": "draft"}, synchronize_session=False),
    transaction.commit()
    Session.close()


@app.task
def update_request_tag_ids(request_id):
    engine = engine_from_config(app.conf["PYRAMID_REGISTRY"].settings, "sqlalchemy.")
    # TODO don't use scoped_session
    Session.configure(bind=engine)
    Session.query(Request).filter(Request.id == request_id).update({
        "tag_ids": func.array(
            Session.query(RequestTag.tag_id)
            .filter(RequestTag.request_id == request_id)
            .order_by(RequestTag.tag_id).subquery()
        ),
    }, synchronize_session=False)
    transaction.commit()
    Session.close()
