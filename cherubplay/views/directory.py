import re

from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.view import view_config
from sqlalchemy import and_, func
from sqlalchemy.orm import joinedload, joinedload_all
from sqlalchemy.orm.exc import NoResultFound
from uuid import uuid4

from ..lib import colour_validator, preset_colours
from ..models import Session, Chat, ChatUser, Message, Request, RequestTag, Tag


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
    fandoms = set()
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
            if tag_type in (u"fandom", u"fandom_wanted"):
                fandoms.add(name)

    # Meta types
    if not new_request.prompt:
        tag_dict[(u"type", u"not_a_prompt")] = u"Not a prompt"

    if len(fandoms) > 1:
        tag_dict[(u"type", u"crossover")] = u"Crossover"

    if u"homestuck" not in fandoms:
        tag_dict[(u"type", u"not_homestuck")] = u"Not Homestuck"

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


@view_config(route_name="directory_ext", request_method="GET", permission="view", extensions=("json",), renderer="json")
@view_config(route_name="directory", request_method="GET", permission="view", renderer="layout2/directory/index.mako")
def directory(request):

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        raise HTTPNotFound

    requests = (
        Session.query(Request)
        .filter(Request.status == "posted")
        .options(joinedload_all(Request.tags, RequestTag.tag))
        .order_by(Request.posted.desc())
        .limit(25).offset((current_page-1)*25).all()
    )

    # 404 on empty pages, unless it's the first page.
    if not requests and current_page != 1:
        raise HTTPNotFound

    request_count = (
        Session.query(func.count('*')).select_from(Request)
        .filter(Request.status == "posted").scalar()
    )

    return {"requests": requests, "request_count": request_count, "current_page": current_page}


@view_config(route_name="directory_tag", request_method="GET", permission="view", renderer="layout2/directory/tag.mako")
@view_config(route_name="directory_tag_ext", request_method="GET", permission="view", extensions=("json",), renderer="json")
def directory_tag(request):

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        raise HTTPNotFound

    if request.matchdict["type"] not in Tag.type.type.enums:
        raise HTTPNotFound

    replaced_name = name_from_alias(request.matchdict["name"])
    if replaced_name != request.matchdict["name"]:
        return HTTPFound(request.current_route_path(name=replaced_name))

    tag = Session.query(Tag).filter(and_(
        Tag.type == request.matchdict["type"], Tag.name == request.matchdict["name"],
    )).options(joinedload(Tag.synonym_of)).one()
    if tag.synonym_of is not None:
        return HTTPFound(request.current_route_path(type=tag.synonym_of.type, name=tag.synonym_of.name))


    requests = (
        Session.query(Request)
        .join(Request.tags)
        .filter(and_(
            Request.status == "posted",
            RequestTag.tag_id == tag.id,
        ))
        .options(joinedload_all(Request.tags, RequestTag.tag))
        .order_by(Request.posted.desc())
        .limit(25).offset((current_page-1)*25).all()
    )

    request_count = (
        Session.query(func.count('*')).select_from(Request)
        .join(Request.tags)
        .filter(and_(
            Request.status == "posted",
            RequestTag.tag_id == tag.id,
        )).scalar()
    )

    return {"tag": tag, "requests": requests, "request_count": request_count, "current_page": current_page}


@view_config(route_name="directory_yours", request_method="GET", permission="view", renderer="layout2/directory/index.mako")
@view_config(route_name="directory_yours_ext", request_method="GET", permission="view", extensions=("json",), renderer="json")
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


@view_config(route_name="directory_request", request_method="GET", permission="view", renderer="layout2/directory/request.mako")
def directory_request(context, request):
    return {}


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


@view_config(route_name="directory_request_delete", request_method="GET", permission="chat", renderer="layout2/directory/request_delete.mako")
def directory_request_delete_get(context, request):
    return {}


@view_config(route_name="directory_request_delete", request_method="POST", permission="chat")
def directory_request_delete_post(context, request):
    Session.query(RequestTag).filter(RequestTag.request_id == context.id).delete()
    Session.query(Request).filter(Request.id == context.id).delete()
    return HTTPFound(request.route_path("directory_yours"))

