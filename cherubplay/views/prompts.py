from datetime import datetime
from pyramid.httpexceptions import HTTPBadRequest, HTTPFound, HTTPNotFound
from pyramid.view import view_config
from sqlalchemy import and_, func
from sqlalchemy.orm.exc import NoResultFound

from ..lib import colour_validator, preset_colours, prompt_categories, prompt_levels
from ..models import Session, Prompt


@view_config(route_name="prompt_list", request_method="GET", permission="view", renderer="layout2/prompt_list.mako")
@view_config(route_name="prompt_list_ext", request_method="GET", permission="view", extensions={"json"}, renderer="json")
def prompt_list(request):

    current_page = int(request.GET.get("page", 1))

    prompts = (
        Session.query(Prompt).filter(Prompt.user_id == request.user.id)
        .order_by(Prompt.id.desc()).limit(25).offset((current_page-1)*25).all()
    )
    prompt_count = (
        Session.query(func.count('*')).select_from(Prompt)
        .filter(Prompt.user_id==request.user.id).scalar()
    )

    if request.matched_route.name == "prompt_list_ext":
        return {"prompts": prompts, "prompt_count": prompt_count}

    return {
        "prompts": prompts,
        "prompt_count": prompt_count,
        "current_page": current_page,
        "prompt_categories": prompt_categories,
        "prompt_levels": prompt_levels,
    }


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


@view_config(route_name="prompt", request_method="GET", permission="view", renderer="layout2/prompt.mako")
def prompt(context, request):
    return {"prompt_categories": prompt_categories, "prompt_levels": prompt_levels}


@view_config(route_name="prompt_ext", request_method="GET", permission="view", extensions={"json"}, renderer="json")
def prompt_ext(context, request):
    return context


def _edit_prompt_form(**kwargs):
    return dict(
        preset_colours=preset_colours,
        prompt_categories=prompt_categories,
        prompt_levels=prompt_levels,
        **kwargs
    )


@view_config(route_name="edit_prompt", request_method="GET", permission="view", renderer="layout2/edit_prompt.mako")
def edit_prompt_get(context, request):
    return _edit_prompt_form()


@view_config(route_name="edit_prompt", request_method="POST", permission="view", renderer="layout2/edit_prompt.mako")
def edit_prompt_post(context, request):

    trimmed_prompt_title = request.POST.get("prompt_title", "").strip()
    if trimmed_prompt_title == "":
        return _edit_prompt_form(error="blank_title")

    colour = request.POST.get("prompt_colour", "")
    if colour.startswith("#"):
        colour = colour[1:]
    if colour_validator.match(colour) is None:
        return _edit_prompt_form(error="invalid_colour")

    trimmed_prompt_text = request.POST.get("prompt_text", "").strip()
    if trimmed_prompt_text == "":
        return _edit_prompt_form(error="blank_text")

    if request.POST.get("prompt_category") not in prompt_categories:
        return _edit_prompt_form(error="blank_category")

    if request.POST.get("prompt_level") not in prompt_levels:
        return _edit_prompt_form(error="blank_level")

    context.title = trimmed_prompt_title
    context.colour = colour
    context.text = trimmed_prompt_text
    context.category = request.POST["prompt_category"]
    context.level = request.POST["prompt_level"]
    context.updated = datetime.now()

    return HTTPFound(request.route_path("prompt", id=context.id))


@view_config(route_name="delete_prompt", request_method="GET", permission="view", renderer="layout2/delete_prompt.mako")
def delete_prompt_get(context, request):
    return _edit_prompt_form()


@view_config(route_name="delete_prompt", request_method="POST", permission="view")
def delete_prompt_post(context, request):
    Session.delete(context)
    return HTTPFound(request.route_path("prompt_list"))

