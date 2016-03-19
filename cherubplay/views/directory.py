import datetime, re

from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPFound, HTTPNotFound
from pyramid.renderers import render_to_response
from pyramid.view import view_config
from sqlalchemy import and_, func, Integer, literal
from sqlalchemy.dialects.postgres import array, ARRAY
from sqlalchemy.orm import contains_eager, joinedload, joinedload_all
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import cast
from uuid import uuid4

from ..lib import colour_validator, preset_colours
from ..models import Session, BlacklistedTag, Chat, ChatUser, Message, Request, RequestTag, Tag, TagParent, User


class ValidationError(Exception): pass
class CreateNotAllowed(Exception): pass


def _get_or_create_tag(tag_type, name, allow_maturity_and_type_creation=True):
    try:
        tag = Session.query(Tag).filter(and_(Tag.type == tag_type, func.lower(Tag.name) == name.lower())).one()
    except NoResultFound:
        if not allow_maturity_and_type_creation and tag_type in ("maturity", "type"):
            raise CreateNotAllowed()
        tag = Tag(type=tag_type, name=name)
        Session.add(tag)
        Session.flush()
    return tag


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
            if tag_type == "trigger" and alias.lower().startswith("tw:"):
                alias = alias[3:]
            alias = alias.strip()
            name = Tag.name_from_url(alias).strip()
            if name == "":
                continue
            tag_dict[(tag_type, name)] = alias
            if tag_type in (u"fandom", u"fandom_wanted"):
                fandoms.add(name.lower())

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
        tag = _get_or_create_tag(tag_type, name)
        tag_id = (tag.synonym_id or tag.id)
        # Remember IDs to skip synonyms.
        if tag_id in used_ids:
            continue
        used_ids.add(tag_id)
        tag_list.append(RequestTag(tag_id=tag_id, alias=alias))

    return tag_list


@view_config(route_name="directory_ext", request_method="GET", permission="admin", extension="json", renderer="json")
@view_config(route_name="directory", request_method="GET", permission="admin", renderer="layout2/directory/index.mako")
def directory(request):

    if request.GET.get("before"):
        try:
            before_date = datetime.datetime.strptime(request.GET["before"], "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            raise HTTPNotFound
    else:
        before_date = None

    if not request.user.seen_blacklist_warning:
        return render_to_response("layout2/directory/blacklist_warning.mako", {}, request)

    requests = (
        Session.query(Request)
        .filter(request.user.tag_filter)
    )
    if before_date:
        requests = requests.filter(Request.posted < before_date)
    requests = (
        requests.options(joinedload_all(Request.tags, RequestTag.tag))
        .order_by(Request.posted.desc())
        .limit(26).all()
    )

    # 404 on empty pages, unless it's the first page.
    if not requests and "before" in request.GET:
        raise HTTPNotFound

    return {"requests": requests[:25], "more": len(requests) == 26}


@view_config(route_name="directory_tag_list", request_method="GET", permission="admin", renderer="layout2/directory/tag_list.mako")
@view_config(route_name="directory_tag_list_unapproved", request_method="GET", permission="admin", renderer="layout2/directory/tag_list.mako")
@view_config(route_name="directory_tag_list_blacklist_default", request_method="GET", permission="admin", renderer="layout2/directory/tag_list.mako")
def directory_tag_list(request):

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        raise HTTPNotFound

    tag_query = Session.query(Tag)
    tag_count_query = Session.query(func.count("*")).select_from(Tag)
    if request.matched_route.name == "directory_tag_list_unapproved":
        tag_query = tag_query.filter(and_(Tag.synonym_id == None, Tag.approved == False))
        tag_count_query = tag_count_query.filter(and_(Tag.synonym_id == None, Tag.approved == False))
    elif request.matched_route.name == "directory_tag_list_blacklist_default":
        tag_query = tag_query.filter(Tag.blacklist_default == True)
        tag_count_query = tag_count_query.filter(Tag.blacklist_default == True)

    return {
        "tags": tag_query.options(joinedload(Tag.synonym_of)).order_by(Tag.type, Tag.name).limit(250).offset((current_page-1)*250).all(),
        "tag_count": tag_count_query.scalar(),
        "current_page": current_page,
    }

@view_config(route_name="directory_tag_table", request_method="GET", permission="admin", renderer="layout2/directory/tag_table.mako")
def directory_tag_table(request):
    rows = []
    last_tag_name = None
    for tag in Session.query(Tag).order_by(Tag.name, Tag.type).all():
        if tag.name.lower() != last_tag_name:
            last_tag_name = tag.name.lower()
            rows.append({})
        rows[-1][tag.type] = tag
    return {"rows": rows}


@view_config(route_name="directory_tag", request_method="GET", permission="admin", renderer="layout2/directory/tag.mako")
@view_config(route_name="directory_tag_ext", request_method="GET", permission="admin", extension="json", renderer="json")
def directory_tag(request):

    if request.GET.get("before"):
        try:
            before_date = datetime.datetime.strptime(request.GET["before"], "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            raise HTTPNotFound
    else:
        before_date = None

    if request.matchdict["type"] not in Tag.type.type.enums:
        raise HTTPNotFound

    if not request.user.seen_blacklist_warning:
        return render_to_response("layout2/directory/blacklist_warning.mako", {}, request)

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
        }, "blacklisted": False, "requests": [], "more": False}

    if tag.synonym_of is not None:
        return HTTPFound(request.current_route_path(type=tag.synonym_of.type, name=tag.synonym_of.url_name))

    if tag.name != name:
        return HTTPFound(request.current_route_path(name=tag.url_name))

    tag_dict = tag.__json__(request)

    blacklisted = Session.query(func.count("*")).select_from(BlacklistedTag).filter(and_(
        BlacklistedTag.user_id == request.user.id, BlacklistedTag.tag_id == tag.id,
    )).scalar()

    if blacklisted:
        return {"tag": tag_dict, "blacklisted": True, "requests": [], "more": False}

    tag_array = cast([tag.id], ARRAY(Integer))
    requests = (
        Session.query(Request)
        .filter(and_(request.user.tag_filter, Request.tag_ids.contains(tag_array)))
    )
    if before_date:
        requests = requests.filter(Request.posted < before_date)
    requests = (
        requests.options(joinedload_all(Request.tags, RequestTag.tag))
        .order_by(Request.posted.desc())
        .limit(26).all()
    )

    resp = {"tag": tag_dict, "blacklisted": False, "requests": requests[:25], "more": len(requests) == 26}

    if request.has_permission("tag_wrangling"):
        if not tag.approved:
            resp["can_be_approved"] = True
        resp["synonyms"] = Session.query(Tag).filter(Tag.synonym_id == tag.id).order_by(Tag.type, Tag.name).all()
        resp["parents"] = Session.query(Tag).join(TagParent, Tag.id == TagParent.parent_id).filter(TagParent.child_id == tag.id).order_by(Tag.type, Tag.name).all()
        resp["children"] = Session.query(Tag).join(TagParent, Tag.id == TagParent.child_id).filter(TagParent.parent_id == tag.id).order_by(Tag.type, Tag.name).all()

    return resp


@view_config(route_name="directory_tag_approve", request_method="POST", permission="admin")
def directory_tag_approve(request):

    if request.matchdict["type"] not in Tag.type.type.enums:
        raise HTTPNotFound

    tag = _get_or_create_tag(request.matchdict["type"], Tag.name_from_url(request.matchdict["name"]))
    if tag.synonym_id is not None:
        raise HTTPNotFound
    tag.approved = True

    if "Referer" in request.headers:
        return HTTPFound(request.headers["Referer"])
    return HTTPFound(request.route_path("directory_tag", **request.matchdict))


def _make_synonym(old_type, old_name, new_type, new_name):

    old_tag = _get_or_create_tag(old_type, old_name)

    # A tag can't be a synonym if it has synonyms.
    if Session.query(func.count("*")).select_from(Tag).filter(Tag.synonym_id == old_tag.id).scalar():
        raise HTTPNotFound

    new_tag = _get_or_create_tag(new_type, new_name)

    if old_tag.id == new_tag.id:
        raise HTTPNotFound

    old_tag.synonym_id = new_tag.id

    # Delete the old tag from reqests which already have the new tag.
    Session.query(RequestTag).filter(and_(
        RequestTag.tag_id == old_tag.id,
        RequestTag.request_id.in_(Session.query(RequestTag.request_id).filter(RequestTag.tag_id == new_tag.id)),
    )).delete(synchronize_session=False)
    # And update the rest.
    Session.query(RequestTag).filter(RequestTag.tag_id == old_tag.id).update({"tag_id": new_tag.id})

    # And the same for the tag_ids arrays.
    Session.query(Request).filter(
        Request.tag_ids.contains(cast([old_tag.id, new_tag.id], ARRAY(Integer)))
    ).update({"tag_ids": func.array_remove(Request.tag_ids, old_tag.id)}, synchronize_session=False)
    Session.query(Request).filter(
        Request.tag_ids.contains(cast([old_tag.id], ARRAY(Integer)))
    ).update({"tag_ids": func.array_replace(Request.tag_ids, old_tag.id, new_tag.id)}, synchronize_session=False)


@view_config(route_name="directory_tag_make_synonym", request_method="POST", permission="admin")
def directory_tag_make_synonym(request):

    if request.matchdict["type"] not in Tag.type.type.enums or request.POST["tag_type"] not in Tag.type.type.enums:
        raise HTTPNotFound

    old_type = request.matchdict["type"]
    old_name = Tag.name_from_url(request.matchdict["name"])
    new_type = request.POST["tag_type"]
    new_name = Tag.name_from_url(request.POST["name"]).strip()[:100]

    if not old_name or not new_name:
        raise HTTPBadRequest

    if (
        old_type in ("fandom", "fandom_wanted", "character", "character_wanted", "gender", "gender_wanted")
        and new_type in ("fandom", "fandom_wanted", "character", "character_wanted", "gender", "gender_wanted")
    ):
        if old_type.endswith("_wanted"):
            old_type_without_wanted = old_type.replace("_wanted", "")
            old_type_with_wanted = old_type
        else:
            old_type_without_wanted = old_type
            old_type_with_wanted = old_type + "_wanted"
        if new_type.endswith("_wanted"):
            new_type_without_wanted = new_type.replace("_wanted", "")
            new_type_with_wanted = new_type
        else:
            new_type_without_wanted = new_type
            new_type_with_wanted = new_type + "_wanted"
        _make_synonym(old_type_without_wanted, old_name, new_type_without_wanted, new_name)
        _make_synonym(old_type_with_wanted, old_name, new_type_with_wanted, new_name)
    else:
        _make_synonym(old_type, old_name, new_type, new_name)

    return HTTPFound(request.route_path("directory_tag", **request.matchdict))


@view_config(route_name="directory_yours", request_method="GET", permission="admin", renderer="layout2/directory/index.mako")
@view_config(route_name="directory_yours_ext", request_method="GET", permission="admin", extension="json", renderer="json")
def directory_yours(request):

    if request.GET.get("before"):
        try:
            before_date = datetime.datetime.strptime(request.GET["before"], "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            raise HTTPNotFound
    else:
        before_date = None

    requests = (
        Session.query(Request)
        .filter(Request.user_id == request.user.id)
    )
    if before_date:
        requests = requests.filter(Request.posted < before_date)
    requests = (
        requests.options(joinedload_all(Request.tags, RequestTag.tag))
        .order_by(Request.posted.desc())
        .limit(26).all()
    )

    # 404 on empty pages, unless it's the first page.
    if not requests and "before" in request.GET:
        raise HTTPNotFound

    return {"requests": requests[:25], "more": len(requests) == 26}


@view_config(route_name="directory_new", request_method="GET", permission="admin", renderer="layout2/directory/new.mako")
def directory_new_get(request):
    return {"form_data": {}, "preset_colours": preset_colours}


@view_config(route_name="directory_new", request_method="POST", permission="admin", renderer="layout2/directory/new.mako")
def directory_new_post(request):
    try:
        colour, scenario, prompt = _validate_request_form(request)
    except ValidationError as e:
        return {"form_data": request.POST, "preset_colours": preset_colours, "error": e.message}

    status = "posted"
    too_many_requests = False
    if "draft" in request.POST:
        status = "draft"
    elif Session.query(func.count("*")).select_from(Request).filter(and_(
        Request.user_id == request.user.id,
        Request.status == "posted",
    )).scalar() >= 10:
        status = "draft"
        too_many_requests = True

    new_request = Request(
        user_id=request.user.id,
        status=status,
        colour=colour,
        scenario=scenario,
        prompt=prompt,
    )
    Session.add(new_request)
    Session.flush()

    new_request.tags += _tags_from_form(request.POST, new_request)
    new_request.tag_ids = sorted([_.tag_id for _ in new_request.tags])

    return HTTPFound(request.route_path(
        "directory_request",
        id=new_request.id,
        _query={"too_many_requests": "true"} if too_many_requests else None,
    ))


def _blacklisted_tags(request, **kwargs):
    return dict(
        tags=(
            Session.query(BlacklistedTag)
            .join(BlacklistedTag.tag)
            .filter(BlacklistedTag.user_id == request.user.id)
            .options(contains_eager(BlacklistedTag.tag))
            .order_by(Tag.type, BlacklistedTag.alias).all()
        ),
        **kwargs
    )


@view_config(route_name="directory_blacklist", request_method="GET", permission="admin", renderer="layout2/directory/blacklist.mako")
@view_config(route_name="directory_blacklist_ext", request_method="GET", permission="admin", extension="json", renderer="json")
def directory_blacklist(request):
    return _blacklisted_tags(request)


@view_config(route_name="directory_blacklist_setup", request_method="POST", permission="admin")
def directory_blacklist_setup(request):

    if request.POST.get("blacklist") not in ("none", "default"):
        raise HTTPBadRequest

    if request.user.seen_blacklist_warning:
        return HTTPFound(request.headers.get("Referer") or request.route_path("directory"))

    if request.POST["blacklist"] == "default":
        print "default"
        Session.execute(BlacklistedTag.__table__.insert().from_select(
            ["user_id", "tag_id", "alias"],
            Session.query(literal(request.user.id), Tag.id, Tag.name).filter(Tag.blacklist_default == True)
        ))

    Session.query(User).filter(User.id == request.user.id).update({"seen_blacklist_warning": True})

    return HTTPFound(request.headers.get("Referer") or request.route_path("directory"))


@view_config(route_name="directory_blacklist_add", request_method="POST", permission="admin", renderer="layout2/directory/blacklist.mako")
def directory_blacklist_add(request):

    if request.POST.get("tag_type") not in Tag.type.type.enums:
        raise HTTPBadRequest
    tag_type = request.POST["tag_type"]

    aliases = request.POST["alias"][:100]
    for alias in aliases.split(","):

        alias = alias.strip()
        if not alias:
            continue

        name = Tag.name_from_url(alias).strip()
        if not name:
            continue

        try:
            tag = _get_or_create_tag(tag_type, name, allow_maturity_and_type_creation=False)
        except CreateNotAllowed:
            return _blacklisted_tags(request, error="invalid", error_tag_type=tag_type, error_alias=alias)
        tag_id = (tag.synonym_id or tag.id)

        if Session.query(func.count("*")).select_from(BlacklistedTag).filter(and_(
            BlacklistedTag.user_id == request.user.id,
            BlacklistedTag.tag_id == tag_id,
        )).scalar() == 0:
            Session.add(BlacklistedTag(user_id=request.user.id, tag_id=tag_id, alias=alias))

    return HTTPFound(request.route_path("directory_blacklist"))


@view_config(route_name="directory_blacklist_remove", request_method="POST", permission="admin")
def directory_blacklist_remove(request):
    try:
        Session.query(BlacklistedTag).filter(and_(
            BlacklistedTag.user_id == request.user.id,
            BlacklistedTag.tag_id == request.POST["tag_id"],
        )).delete()
    except KeyError, ValueError:
        raise HTTPBadRequest
    return HTTPFound(request.route_path("directory_blacklist"))


@view_config(route_name="directory_request", request_method="GET", permission="admin", renderer="layout2/directory/request.mako")
@view_config(route_name="directory_request_ext", request_method="GET", permission="admin", extension="json", renderer="json")
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


@view_config(route_name="directory_request_answer", request_method="POST", permission="admin")
def directory_request_answer(context, request):

    # Can't answer your own request.
    if request.user.id == context.user_id:
        raise HTTPNotFound

    new_chat = Chat(url=str(uuid4()), request_id=context.id)
    Session.add(new_chat)
    Session.flush()

    Session.add(ChatUser(chat_id=new_chat.id, user_id=context.user_id, symbol=0, last_colour=context.colour))
    Session.add(ChatUser(chat_id=new_chat.id, user_id=request.user.id, symbol=1))

    if context.scenario:
        Session.add(Message(chat_id=new_chat.id, user_id=context.user_id, symbol=0, text=context.scenario))
    if context.prompt:
        Session.add(Message(chat_id=new_chat.id, user_id=context.user_id, symbol=0, colour=context.colour, text=context.prompt))

    return HTTPFound(request.route_path("chat", url=new_chat.url))


@view_config(route_name="directory_request_edit", request_method="GET", permission="admin", renderer="layout2/directory/new.mako")
def directory_request_edit_get(context, request):

    if context.user_id != request.user.id:
        raise HTTPForbidden

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


@view_config(route_name="directory_request_edit", request_method="POST", permission="admin", renderer="layout2/directory/new.mako")
def directory_request_edit_post(context, request):

    if context.user_id != request.user.id:
        raise HTTPForbidden

    try:
        colour, scenario, prompt = _validate_request_form(request)
    except ValidationError as e:
        return {"form_data": request.POST, "preset_colours": preset_colours, "error": e.message}

    new_date = datetime.datetime.now()
    context.edited = new_date

    too_many_requests = False
    if context.status != "removed":
        status = "posted"
        if "draft" in request.POST:
            status = "draft"
        elif Session.query(func.count("*")).select_from(Request).filter(and_(
            Request.user_id == request.user.id,
            Request.status == "posted",
            Request.id != context.id,
        )).scalar() >= 10:
            status = "draft"
            too_many_requests = True
        if context.status == "draft" and status == "posted":
            context.posted = new_date
        context.status = status

    context.colour = colour
    context.scenario = scenario
    context.prompt = prompt

    Session.query(RequestTag).filter(RequestTag.request_id == context.id).delete()

    new_tags = _tags_from_form(request.POST, context)
    context.tags += new_tags
    context.tag_ids = sorted([_.tag_id for _ in new_tags])

    return HTTPFound(request.route_path(
        "directory_request",
        id=context.id,
        _query={"too_many_requests": "true"} if too_many_requests else None,
    ))


@view_config(route_name="directory_request_delete", request_method="GET", permission="admin", renderer="layout2/directory/request_delete.mako")
def directory_request_delete_get(context, request):
    if context.user_id != request.user.id:
        raise HTTPForbidden
    return {}


@view_config(route_name="directory_request_delete", request_method="POST", permission="admin")
def directory_request_delete_post(context, request):
    if context.user_id != request.user.id:
        raise HTTPForbidden
    Session.query(Chat).filter(Chat.request_id == context.id).update({"request_id": None})
    Session.query(RequestTag).filter(RequestTag.request_id == context.id).delete()
    Session.query(Request).filter(Request.id == context.id).delete()
    return HTTPFound(request.route_path("directory_yours"))


@view_config(route_name="directory_request_remove", request_method="POST", permission="admin")
def directory_request_remove(context, request):
    context.status = "removed"
    return HTTPFound(request.route_path("directory_request", id=context.id))


@view_config(route_name="directory_request_unremove", request_method="POST", permission="admin")
def directory_request_unremove(context, request):
    context.status = "posted"
    return HTTPFound(request.route_path("directory_request", id=context.id))

