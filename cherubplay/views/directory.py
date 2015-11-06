from pyramid.view import view_config

from ..models import Session, Request, Tag


@view_config(route_name="directory", request_method="GET", permission="view", renderer="layout2/directory/index.mako")
def directory(request):
    # XXX joinedload on tags
    return {"requests": Session.query(Request).filter(Request.status == "posted").order_by(Request.posted.desc())}

