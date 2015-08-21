from pyramid.httpexceptions import HTTPNotFound
from pyramid.renderers import render_to_response
from pyramid.view import view_config
from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound

from ..lib import prompt_categories, prompt_levels
from ..models import Session, Prompt


@view_config(route_name="prompt_list", request_method="GET", permission="view")
def prompt_list(request):
    prompts = Session.query(Prompt).filter(Prompt.user_id == request.user.id).all()
    return render_to_response("layout2/prompt_list.mako", {
        "prompts": prompts,
        "prompt_categories": prompt_categories,
        "prompt_levels": prompt_levels,
    }, request)


@view_config(route_name="prompt", request_method="GET", permission="view")
def prompt(request):
    try:
        prompt = Session.query(Prompt).filter(and_(
            Prompt.user_id == request.user.id,
            Prompt.id == int(request.matchdict["id"]),
        )).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound
    return render_to_response("layout2/prompt.mako", {
        "prompt": prompt,
        "prompt_categories": prompt_categories,
        "prompt_levels": prompt_levels,
    }, request)

