from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from sqlalchemy.orm import joinedload_all

from ..lib import colour_validator, preset_colours
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
def directory_new_get(request):
    return {"preset_colours": preset_colours}


@view_config(route_name="directory_new", request_method="POST", permission="chat", renderer="layout2/directory/new.mako")
def directory_new_post(request):

    if request.POST.get("maturity") not in Tag.maturity_names:
        return {"preset_colours": preset_colours, "error": "blank_maturity"}

    colour = request.POST.get("colour", "")
    if colour.startswith("#"):
        colour = colour[1:]
    if colour_validator.match(colour) is None:
        return {"preset_colours": preset_colours, "error": "invalid_colour"}

    scenario = request.POST.get("scenario", "").strip()
    prompt = request.POST.get("prompt", "").strip()

    if not scenario and not prompt:
        return {"preset_colours": preset_colours, "error": "blank_scenario_and_prompt"}

    new_request = Request(
        user_id=request.user.id,
        status="draft" if "draft" in request.POST else "posted",
        colour=colour,
        scenario=scenario,
        prompt=prompt,
    )
    Session.add(new_request)

    return HTTPFound(request.route_path("directory"))

