import transaction

from pyramid.view import view_config
from sqlalchemy.orm.exc import NoResultFound

from ..models import (
    Session,
    User,
)

@view_config(route_name="admin_ban", renderer="admin/ban.mako", request_method="GET", permission="admin")
def ban_get(request):
    return { "feedback": None }

@view_config(route_name="admin_ban", renderer="admin/ban.mako", request_method="POST", permission="admin")
def ban_post(request):
    try:
        user = Session.query(User).filter(User.username==request.POST["username"]).one()
    except NoResultFound:
        return { "feedback": "User %s not found." % request.POST["username"] }
    if user.status=="banned":
        return { "feedback": "User %s is already banned." % request.POST["username"] }
    user.status = "banned"
    transaction.commit()
    return { "feedback": "User %s has now been banned." % request.POST["username"] }

