import re

from pyramid.httpexceptions import HTTPBadRequest, HTTPFound, HTTPNotFound
from pyramid.view import view_config
from sqlalchemy import and_, func, Integer
from sqlalchemy.dialects.postgres import array, ARRAY
from sqlalchemy.orm import joinedload, joinedload_all
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import cast
from uuid import uuid4

from ..lib import colour_validator, preset_colours
from ..models import Session, BlacklistedTag, Chat, ChatUser, Message, Request, RequestTag, Tag


class ValidationError(Exception): pass


def _validate_request_form(request):
    if request.POST.get("maturity") not in Tag.maturity_names:
        raise ValidationError("blank_maturity")

    colour = request.POST.get("colour", "")
    if colour.startswith("#"):
        colour = colour[1:]
    if colour_validator.match(colour) is None:
        raise ValidationError("invalid_colour")

    scenario = request.POST.get("scenario", "").strip()
    prompt = request.POST.get("prompt", "").strip()

    if not scenario and not prompt:
        raise ValidationError("blank_scenario_and_prompt")

    return colour, scenario, prompt


def _tags_from_form(form, new_request):
    tag_dict = {}
    fandoms = set()
    for tag_type in Tag.type.type.enums:

        # Enforce preset values for maturity.
        if tag_type == "maturity":
            name = form["maturity"]
            if name not in Tag.maturity_names:
                name = "NSFW extreme"
            tag_dict[(u"maturity", name)] = name
            continue

        # Enforce preset values for type.
        elif tag_type == "type":
            for name in Tag.type_names:
                if "type_" + name in form:
                    tag_dict[(u"type", name)] = name
            continue

        for alias in form[tag_type][:100].split(","):
            alias = alias.strip()
            name = Tag.name_from_url(alias).strip()
            if name == "":
                continue
            tag_dict[(tag_type, name)] = alias
            if tag_type in (u"fandom", u"fandom_wanted"):
                fandoms.add(name)

    # Meta types
    if not new_request.prompt:
        tag_dict[(u"type", u"Not a prompt")] = u"Not a prompt"

    if len(fandoms) > 1:
        tag_dict[(u"type", u"Crossover")] = u"Crossover"

    if u"homestuck" not in fandoms:
        tag_dict[(u"type", u"Not Homestuck")] = u"Not Homestuck"

    tag_list = []
    used_ids = set()
    for (tag_type, name), alias in tag_dict.iteritems():
        try:
            tag = Session.query(Tag).filter(and_(Tag.type == tag_type, func.lower(Tag.name) == name.lower())).one()
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


@view_config(route_name="directory_ext", request_method="GET", permission="view", extension="json", renderer="json")
@view_config(route_name="directory", request_method="GET", permission="view", renderer="layout2/directory/index.mako")
def directory(request):

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        raise HTTPNotFound

    requests = (
        Session.query(Request)
        .filter(request.user.tag_filter)
        .options(joinedload_all(Request.tags, RequestTag.tag))
        .order_by(Request.posted.desc())
        .limit(25).offset((current_page-1)*25).all()
    )

    # 404 on empty pages, unless it's the first page.
    if not requests and current_page != 1:
        raise HTTPNotFound

    request_count = (
        Session.query(func.count('*')).select_from(Request)
        .filter(request.user.tag_filter).scalar()
    )

    return {"requests": requests, "request_count": request_count, "current_page": current_page}


@view_config(route_name="directory_tag", request_method="GET", permission="view", renderer="layout2/directory/tag.mako")
@view_config(route_name="directory_tag_ext", request_method="GET", permission="view", extension="json", renderer="json")
def directory_tag(request):

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        raise HTTPNotFound

    if request.matchdict["type"] not in Tag.type.type.enums:
        raise HTTPNotFound

    name = Tag.name_from_url(request.matchdict["name"])

    try:
        tag = Session.query(Tag).filter(and_(
            Tag.type == request.matchdict["type"], func.lower(Tag.name) == name.lower(),
        )).options(joinedload(Tag.synonym_of)).one()
    except NoResultFound:
        return {"tag": {
            "type": request.matchdict["type"],
            "name": request.matchdict["name"],
            "alias": request.matchdict["name"],
        }, "blacklisted": False, "requests": [], "request_count": 0, "current_page": current_page}

    if tag.synonym_of is not None:
        return HTTPFound(request.current_route_path(type=tag.synonym_of.type, name=tag.synonym_of.url_name))

    if tag.name != name:
        return HTTPFound(request.current_route_path(name=tag.url_name))

    tag_dict = tag.__json__(request)

    blacklisted = Session.query(func.count("*")).select_from(BlacklistedTag).filter(and_(
        BlacklistedTag.user_id == request.user.id, BlacklistedTag.tag_id == tag.id,
    )).scalar()

    if blacklisted:
        return {"tag": tag_dict, "blacklisted": True, "requests": [], "request_count": 0, "current_page": current_page}

    tag_array = cast([tag.id], ARRAY(Integer))
    requests = (
        Session.query(Request)
        .filter(and_(
            request.user.tag_filter,
            Request.tag_ids.contains(tag_array),
        ))
        .options(joinedload_all(Request.tags, RequestTag.tag))
        .order_by(Request.posted.desc())
        .limit(25).offset((current_page-1)*25).all()
    )

    request_count = (
        Session.query(func.count('*')).select_from(Request)
        .filter(and_(
            request.user.tag_filter,
            Request.tag_ids.contains(tag_array),
        )).scalar()
    )

    return {"tag": tag_dict, "blacklisted": False, "requests": requests, "request_count": request_count, "current_page": current_page}


@view_config(route_name="directory_yours", request_method="GET", permission="view", renderer="layout2/directory/index.mako")
@view_config(route_name="directory_yours_ext", request_method="GET", permission="view", extension="json", renderer="json")
def directory_yours(request):

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        raise HTTPNotFound

    requests = (
        Session.query(Request)
        .filter(Request.user_id == request.user.id)
        .options(joinedload_all(Request.tags, RequestTag.tag))
        .order_by(Request.posted.desc())
        .limit(25).offset((current_page-1)*25).all()
    )

    # 404 on empty pages, unless it's the first page.
    if not requests and current_page != 1:
        raise HTTPNotFound

    request_count = (
        Session.query(func.count('*')).select_from(Request)
        .filter(Request.user_id == request.user.id).scalar()
    )

    return {"requests": requests, "request_count": request_count, "current_page": current_page}


@view_config(route_name="directory_new", request_method="GET", permission="chat", renderer="layout2/directory/new.mako")
def directory_new_get(request):
    return {"form_data": {}, "preset_colours": preset_colours}


@view_config(route_name="directory_new", request_method="POST", permission="chat", renderer="layout2/directory/new.mako")
def directory_new_post(request):
    try:
        colour, scenario, prompt = _validate_request_form(request)
    except ValidationError as e:
        return {"form_data": request.POST, "preset_colours": preset_colours, "error": e.message}

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
    new_request.tag_ids = [_.tag_id for _ in new_request.tags]

    return HTTPFound(request.route_path("directory_request", id=new_request.id))


def _blacklisted_tags(request, **kwargs):
    return dict(
        tags=(
            Session.query(BlacklistedTag)
            .filter(BlacklistedTag.user_id == request.user.id)
            .options(joinedload(BlacklistedTag.tag))
            .order_by(BlacklistedTag.alias).all()
        ),
        **kwargs
    )


@view_config(route_name="directory_blacklist", request_method="GET", permission="view", renderer="layout2/directory/blacklist.mako")
@view_config(route_name="directory_blacklist_ext", request_method="GET", permission="view", extension="json", renderer="json")
def directory_blacklist(request):
    return _blacklisted_tags(request)


@view_config(route_name="directory_blacklist_add", request_method="POST", permission="view", renderer="layout2/directory/blacklist.mako")
def directory_blacklist_add(request):

    if request.POST.get("tag_type") not in Tag.type.type.enums:
        raise HTTPBadRequest
    tag_type = request.POST["tag_type"]

    alias = request.POST["alias"].strip()[:100]

    name = Tag.name_from_url(alias).strip()
    if not name:
        raise HTTPBadRequest

    try:
        tag = Session.query(Tag).filter(and_(Tag.type == tag_type, func.lower(Tag.name) == name.lower())).one()
    except NoResultFound:
        if tag_type in ("maturity", "type"):
            return _blacklisted_tags(request, error="invalid", error_tag_type=tag_type, error_alias=alias)
        tag = Tag(type=tag_type, name=name)
        Session.add(tag)
        Session.flush()
    tag_id = (tag.synonym_id or tag.id)

    Session.add(BlacklistedTag(user_id=request.user.id, tag_id=tag_id, alias=alias))

    return HTTPFound(request.route_path("directory_blacklist"))


@view_config(route_name="directory_blacklist_remove", request_method="POST", permission="view")
def directory_blacklist_remove(request):
    try:
        Session.query(BlacklistedTag).filter(and_(
            BlacklistedTag.user_id == request.user.id,
            BlacklistedTag.tag_id == request.POST["tag_id"],
        )).delete()
    except KeyError, ValueError:
        raise HTTPBadRequest
    return HTTPFound(request.route_path("directory_blacklist"))


@view_config(route_name="directory_request", request_method="GET", permission="view", renderer="layout2/directory/request.mako")
@view_config(route_name="directory_request_ext", request_method="GET", permission="view", extension="json", renderer="json")
def directory_request(context, request):

    if context.user_id == request.user.id:
        chats = Session.query(ChatUser, Chat).join(Chat).filter(
            ChatUser.user_id==request.user.id,
            Chat.request_id==context.id,
        ).order_by(Chat.updated.desc()).all()
    else:
        chats = []

    if request.matched_route.name == "directory_request_ext":
        return {"request": context, "chats": [{"chat_user": _[0], "chat": _[1]} for _ in chats]}

    return {"chats": chats}


@view_config(route_name="directory_request_answer", request_method="POST", permission="chat")
def directory_request_answer(context, request):

    # Can't answer your own request.
    if request.user.id == context.user_id:
        raise HTTPNotFound

    new_chat = Chat(url=str(uuid4()), request_id=context.id)
    Session.add(new_chat)
    Session.flush()

    Session.add(ChatUser(chat_id=new_chat.id, user_id=context.user_id, symbol=0, last_colour=context.colour))
    Session.add(ChatUser(chat_id=new_chat.id, user_id=request.user.id, symbol=1))

    Session.add(Message(chat_id=new_chat.id, user_id=context.user_id, symbol=0, text=context.scenario))
    Session.add(Message(chat_id=new_chat.id, user_id=context.user_id, symbol=0, colour=context.colour, text=context.prompt))

    return HTTPFound(request.route_path("chat", url=new_chat.url))


@view_config(route_name="directory_request_edit", request_method="GET", permission="chat", renderer="layout2/directory/new.mako")
def directory_request_edit_get(context, request):

    form_data = {}

    for tag_type, tags in context.tags_by_type().items():
        if tag_type == "maturity":
            if tags: # i don't know why we wouldn't have a maturity but don't IndexError if that does happen
                form_data["maturity"] = tags[0].tag.name
        elif tag_type == "type":
            for tag in tags:
                form_data["type_" + tag.tag.name] = "on"
        else:
            form_data[tag_type] = ", ".join(tag.alias for tag in tags)

    form_data["colour"] = "#" + context.colour
    form_data["scenario"] = context.scenario
    form_data["prompt"] = context.prompt

    return {"form_data": form_data, "preset_colours": preset_colours}


@view_config(route_name="directory_request_edit", request_method="POST", permission="chat", renderer="layout2/directory/new.mako")
def directory_request_edit_post(context, request):
    try:
        colour, scenario, prompt = _validate_request_form(request)
    except ValidationError as e:
        return {"form_data": request.POST, "preset_colours": preset_colours, "error": e.message}

    context.status = "draft" if "draft" in request.POST else "posted" # TODO update date if going from draft to posted
    context.colour = colour
    context.scenario = scenario
    context.prompt = prompt

    for request_tag in context.tags:
        Session.delete(request_tag)

    context.tags += _tags_from_form(request.POST, context)
    context.tag_ids = [_.tag_id for _ in context.tags]

    return HTTPFound(request.route_path("directory_request", id=context.id))


@view_config(route_name="directory_request_delete", request_method="GET", permission="chat", renderer="layout2/directory/request_delete.mako")
def directory_request_delete_get(context, request):
    return {}


@view_config(route_name="directory_request_delete", request_method="POST", permission="chat")
def directory_request_delete_post(context, request):
    # TODO remove request_id from chats
    Session.query(RequestTag).filter(RequestTag.request_id == context.id).delete()
    Session.query(Request).filter(Request.id == context.id).delete()
    return HTTPFound(request.route_path("directory_yours"))

