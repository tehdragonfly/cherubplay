from pyramid.httpexceptions import HTTPBadRequest, HTTPFound, HTTPNotFound
from pyramid.renderers import render_to_response
from pyramid.view import view_config
from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound

from ..lib import alt_formats, colour_validator, preset_colours, prompt_categories, prompt_levels
from ..models import Session, Prompt


@view_config(route_name="prompt_list", request_method="GET", permission="view")
@view_config(route_name="prompt_list_fmt", request_method="GET", permission="view")
@alt_formats({"json"})
def prompt_list(request):
    prompts = Session.query(Prompt).filter(Prompt.user_id == request.user.id).order_by(Prompt.id.desc()).all()
    if request.matchdict.get("fmt") == "json":
        return render_to_response("json", {
            "prompts": prompts,
            "prompt_count": len(prompts),
        }, request)
    return render_to_response("layout2/prompt_list.mako", {
        "prompts": prompts,
        "prompt_categories": prompt_categories,
        "prompt_levels": prompt_levels,
    }, request)


def _new_prompt_form(**kwargs):
    return dict(
        preset_colours=preset_colours,
        prompt_categories=prompt_categories,
        prompt_levels=prompt_levels,
        **kwargs
    )


@view_config(route_name="new_prompt", request_method="GET", permission="view", renderer="layout2/new_prompt.mako")
def new_prompt_get(request):
    return _new_prompt_form()


@view_config(route_name="new_prompt", request_method="POST", permission="view", renderer="layout2/new_prompt.mako")
def new_prompt_post(request):

    trimmed_prompt_title = request.POST.get("prompt_title", "").strip()
    if trimmed_prompt_title == "":
        return _new_prompt_form(error="blank_title")

    colour = request.POST.get("prompt_colour", "")
    if colour.startswith("#"):
        colour = colour[1:]
    if colour_validator.match(colour) is None:
        return _new_prompt_form(error="invalid_colour")

    trimmed_prompt_text = request.POST.get("prompt_text", "").strip()
    if trimmed_prompt_text == "":
        return _new_prompt_form(error="blank_text")

    if request.POST.get("prompt_category") not in prompt_categories:
        return _new_prompt_form(error="blank_category")

    if request.POST.get("prompt_level") not in prompt_levels:
        return _new_prompt_form(error="blank_level")

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


def _get_prompt(request):
    try:
        return Session.query(Prompt).filter(and_(
            Prompt.user_id == request.user.id,
            Prompt.id == int(request.matchdict["id"]),
        )).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound


@view_config(route_name="prompt", request_method="GET", permission="view")
@view_config(route_name="prompt_fmt", request_method="GET", permission="view")
@alt_formats({"json"})
def prompt(request):
    prompt = _get_prompt(request)
    if request.matchdict.get("fmt") == "json":
        return render_to_response("json", prompt, request=request)
    return render_to_response("layout2/prompt.mako", {
        "prompt": prompt,
        "prompt_categories": prompt_categories,
        "prompt_levels": prompt_levels,
    }, request)


def _edit_prompt_form(prompt, **kwargs):
    return dict(
        prompt=prompt,
        preset_colours=preset_colours,
        prompt_categories=prompt_categories,
        prompt_levels=prompt_levels,
        **kwargs
    )


@view_config(route_name="edit_prompt", request_method="GET", permission="view", renderer="layout2/edit_prompt.mako")
def edit_prompt_get(request):
    return _edit_prompt_form(_get_prompt(request))


@view_config(route_name="edit_prompt", request_method="POST", permission="view", renderer="layout2/edit_prompt.mako")
def edit_prompt_post(request):
    prompt = _get_prompt(request)

    trimmed_prompt_title = request.POST.get("prompt_title", "").strip()
    if trimmed_prompt_title == "":
        return _edit_prompt_form(prompt, error="blank_title")

    colour = request.POST.get("prompt_colour", "")
    if colour.startswith("#"):
        colour = colour[1:]
    if colour_validator.match(colour) is None:
        return _edit_prompt_form(prompt, error="invalid_colour")

    trimmed_prompt_text = request.POST.get("prompt_text", "").strip()
    if trimmed_prompt_text == "":
        return _edit_prompt_form(prompt, error="blank_text")

    if request.POST.get("prompt_category") not in prompt_categories:
        return _edit_prompt_form(prompt, error="blank_category")

    if request.POST.get("prompt_level") not in prompt_levels:
        return _edit_prompt_form(prompt, error="blank_level")

    prompt.title = trimmed_prompt_title
    prompt.colour = colour
    prompt.text = trimmed_prompt_text
    prompt.category = request.POST["prompt_category"]
    prompt.level = request.POST["prompt_level"]

    return HTTPFound(request.route_path("prompt", id=prompt.id))

