from pyramid.httpexceptions import HTTPBadRequest, HTTPFound, HTTPNotFound
from pyramid.renderers import render_to_response
from pyramid.view import view_config
from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound

from ..lib import colour_validator, preset_colours, prompt_categories, prompt_levels
from ..models import Session, Prompt


@view_config(route_name="prompt_list", request_method="GET", permission="view", renderer="layout2/prompt_list.mako")
def prompt_list(request):
    prompts = Session.query(Prompt).filter(Prompt.user_id == request.user.id).order_by(Prompt.id.desc()).all()
    return {
        "prompts": prompts,
        "prompt_categories": prompt_categories,
        "prompt_levels": prompt_levels,
    }


@view_config(route_name="new_prompt", request_method="GET", permission="view", renderer="layout2/new_prompt.mako")
def new_prompt_get(request):
    return {
        "preset_colours": preset_colours,
        "prompt_categories": prompt_categories,
        "prompt_levels": prompt_levels,
    }


@view_config(route_name="new_prompt", request_method="POST", permission="view", renderer="layout2/new_prompt.mako")
def new_prompt_post(request):

    trimmed_prompt_title = request.POST.get("prompt_title", "").strip()
    if trimmed_prompt_title == "":
        raise HTTPBadRequest("Prompt title can't be empty.")

    colour = request.POST.get("prompt_colour", "")
    if colour.startswith("#"):
        colour = colour[1:]
    if colour_validator.match(colour) is None:
        raise HTTPBadRequest("Invalid text colour. The colour needs to be a 6-digit hex code.")

    trimmed_prompt_text = request.POST.get("prompt_text", "").strip()
    if trimmed_prompt_text == "":
        raise HTTPBadRequest("Prompt text can't be empty.")

    if request.POST.get("prompt_category") not in prompt_categories:
        raise HTTPBadRequest("Please choose a category for your prompt.")

    if request.POST.get("prompt_level") not in prompt_levels:
        raise HTTPBadRequest("Please choose a level for your prompt.")

    new_prompt = Prompt(
        user_id=request.user.id,
        title=trimmed_prompt_title,
        colour=colour,
        text=trimmed_prompt_text,
        category=request.POST["prompt_category"],
        level=request.POST["prompt_level"],
    )
    Session.add(new_prompt)
    Session.flush()

    return HTTPFound(request.route_path("prompt_list"))


@view_config(route_name="prompt", request_method="GET", permission="view", renderer="layout2/prompt.mako")
def prompt(request):
    try:
        prompt = Session.query(Prompt).filter(and_(
            Prompt.user_id == request.user.id,
            Prompt.id == int(request.matchdict["id"]),
        )).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound
    return {
        "prompt": prompt,
        "prompt_categories": prompt_categories,
        "prompt_levels": prompt_levels,
    }

