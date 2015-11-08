import re

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from sqlalchemy import and_
from sqlalchemy.orm import joinedload_all
from sqlalchemy.orm.exc import NoResultFound

from ..lib import colour_validator, preset_colours
from ..models import Session, Request, RequestTag, Tag


special_char_regex = re.compile("[\\ \\./]+")
underscore_strip_regex = re.compile("^_+|_+$")


def name_from_alias(alias):
    # 1. Change to lowercase.
    # 2. Change spaces to underscores.
    # 3. Change . and / to underscores because they screw up the routing.
    # 4. Strip extra underscores from the start and end.
    # TODO change slashes to *s* or something like ao3
    return underscore_strip_regex.sub("", special_char_regex.sub("_", alias)).lower()


def _tags_from_form(form, new_request):
    tag_dict = {}
    for tag_type in Tag.type.type.enums:

        # Enforce preset values for maturity.
        if tag_type == "maturity":
            name = form["maturity"]
            if name not in Tag.maturity_names:
                name = u"nsfw_extreme"
            tag_dict[(u"maturity", name)] = Tag.maturity_names[name]
            continue

        # Enforce preset values for type.
        elif tag_type == "type":
            for name in Tag.type_names:
                if "type_" + name in form:
                    tag_dict[(u"type", name)] = Tag.type_names[name]
            continue

        for alias in form[tag_type][:100].split(","):
            alias = alias.strip()
            if alias == "":
                continue
            name = name_from_alias(alias)
            if name == "":
                continue
            tag_dict[(tag_type, name)] = alias

    tag_list = []
    used_ids = set()
    for (tag_type, name), alias in tag_dict.iteritems():
        try:
            tag = Session.query(Tag).filter(and_(Tag.type == tag_type, Tag.name == name)).one()
        except NoResultFound:
            tag = Tag(type=tag_type, name=name)
            Session.add(tag)
            Session.flush()
        tag_id = (tag.synonym_id or tag.id)
        # Remember IDs to skip synonyms.
        if tag_id in used_ids:
            continue
        used_ids.add(tag_id)
        tag_list.append(RequestTag(tag_id=tag_id, alias=alias))

    return tag_list


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
    Session.flush()

    new_request.tags += _tags_from_form(request.POST, new_request)

    return HTTPFound(request.route_path("directory"))

