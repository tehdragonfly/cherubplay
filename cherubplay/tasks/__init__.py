import transaction

from datetime import datetime, timedelta
from pyramid_celery import celery_app as app
from sqlalchemy import and_, engine_from_config

from cherubplay.models import Session, Request, User

@app.task
def reap_requests():
    print app.conf["PYRAMID_REGISTRY"].settings

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


