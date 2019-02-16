from datetime import datetime
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.view import view_config
from sqlalchemy import func

from cherubplay.lib import colour_validator, prompt_categories, prompt_starters, prompt_levels
from cherubplay.models import Prompt


@view_config(route_name="prompt_list", request_method="GET", permission="view", renderer="layout2/prompt_list.mako")
@view_config(route_name="prompt_list_ext", request_method="GET", permission="view", extension="json", renderer="json")
def prompt_list(request):

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        raise HTTPNotFound

    db = request.find_service(name="db")
    prompts = (
        db.query(Prompt).filter(Prompt.user_id == request.user.id)
        .order_by(Prompt.id.desc()).limit(25).offset((current_page-1)*25).all()
    )
    prompt_count = (
        db.query(func.count('*')).select_from(Prompt)
        .filter(Prompt.user_id == request.user.id).scalar()
    )

    if request.matched_route.name == "prompt_list_ext":
        return {"prompts": prompts, "prompt_count": prompt_count}

    return {
        "prompts": prompts,
        "prompt_count": prompt_count,
        "current_page": current_page,
    }


@view_config(route_name="new_prompt", request_method="GET", permission="view", renderer="layout2/new_prompt.mako")
def new_prompt_get(request):
    return {}


@view_config(route_name="new_prompt", request_method="POST", permission="view", renderer="layout2/new_prompt.mako")
def new_prompt_post(request):

    trimmed_prompt_title = request.POST.get("prompt_title", "").strip()
    if trimmed_prompt_title == "":
        return {"error": "blank_title"}

    colour = request.POST.get("prompt_colour", "")
    if colour.startswith("#"):
        colour = colour[1:]
    if colour_validator.match(colour) is None:
        return {"error": "invalid_colour"}

    trimmed_prompt_text = request.POST.get("prompt_text", "").strip()
    if trimmed_prompt_text == "":
        return {"error": "blank_text"}

    if request.POST.get("prompt_category") not in prompt_categories:
        return {"error": "blank_category"}

    if request.POST.get("prompt_starter") not in prompt_starters:
        return {"error": "blank_starter"}

    if request.POST.get("prompt_level") not in prompt_levels:
        return {"error": "blank_level"}

    new_prompt = Prompt(
        user_id=request.user.id,
        title=trimmed_prompt_title,
        colour=colour,
        _text=trimmed_prompt_text,
        category=request.POST["prompt_category"],
        starter=request.POST["prompt_starter"],
        level=request.POST["prompt_level"],
    )
    new_prompt.text.update(request.registry.settings["default_format"], trimmed_prompt_text)
    db = request.find_service(name="db")
    db.add(new_prompt)
    db.flush()

    return HTTPFound(request.route_path("prompt_list"))


@view_config(route_name="prompt", request_method="GET", permission="prompt.read", renderer="layout2/prompt.mako")
def prompt(context, request):
    return {}


@view_config(route_name="prompt_ext", request_method="GET", permission="prompt.read", extension="json", renderer="json")
def prompt_ext(context, request):
    return context


@view_config(route_name="edit_prompt", request_method="GET", permission="prompt.edit", renderer="layout2/edit_prompt.mako")
def edit_prompt_get(context, request):
    return {}


@view_config(route_name="edit_prompt", request_method="POST", permission="prompt.edit", renderer="layout2/edit_prompt.mako")
def edit_prompt_post(context, request):

    trimmed_prompt_title = request.POST.get("prompt_title", "").strip()
    if trimmed_prompt_title == "":
        return {"error": "blank_title"}

    colour = request.POST.get("prompt_colour", "")
    if colour.startswith("#"):
        colour = colour[1:]
    if colour_validator.match(colour) is None:
        return {"error": "invalid_colour"}

    trimmed_prompt_text = request.POST.get("prompt_text", "").strip()
    if trimmed_prompt_text == "":
        return {"error": "blank_text"}

    if request.POST.get("prompt_category") not in prompt_categories:
        return {"error": "blank_category"}

    if request.POST.get("prompt_starter") not in prompt_starters:
        return {"error": "blank_starter"}

    if request.POST.get("prompt_level") not in prompt_levels:
        return {"error": "blank_level"}

    context.title = trimmed_prompt_title
    context.colour = colour
    context.text = trimmed_prompt_text
    context.category = request.POST["prompt_category"]
    context.starter = request.POST["prompt_starter"]
    context.level = request.POST["prompt_level"]
    context.updated = datetime.now()

    return HTTPFound(request.route_path("prompt", id=context.id))


@view_config(route_name="delete_prompt", request_method="GET", permission="prompt.delete", renderer="layout2/delete_prompt.mako")
def delete_prompt_get(context, request):
    return {}


@view_config(route_name="delete_prompt", request_method="POST", permission="prompt.delete")
def delete_prompt_post(context, request):
    db = request.find_service(name="db")
    db.delete(context)
    return HTTPFound(request.route_path("prompt_list"))
