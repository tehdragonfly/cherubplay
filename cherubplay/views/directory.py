from pyramid.view import view_config
from sqlalchemy.orm import joinedload_all

from ..lib import preset_colours
from ..models import Session, Request, RequestTag, Tag


@view_config(route_name="directory", request_method="GET", permission="view", renderer="layout2/directory/index.mako")
def directory(request):
    return {"requests": (
        Session.query(Request)
        .filter(Request.status == "posted")
        .options(joinedload_all(Request.tags, RequestTag.tag))
        .order_by(Request.posted.desc()).all()
    )}


@view_config(route_name="directory_new", request_method="GET", permission="chat", renderer="layout2/directory/new.mako")
def directory_new(request):
    return {"preset_colours": preset_colours}

