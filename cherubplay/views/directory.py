import datetime, re, time, transaction

from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPFound, HTTPNotFound
from pyramid.renderers import render_to_response
from pyramid.view import view_config
from sqlalchemy import and_, func, Integer, literal
from sqlalchemy.dialects.postgres import array, ARRAY
from sqlalchemy.orm import contains_eager, joinedload
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import cast
from uuid import uuid4

from cherubplay.lib import colour_validator, preset_colours
from cherubplay.models import Session, BlacklistedTag, Chat, ChatUser, CreateNotAllowed, Message, Request, RequestTag, Tag, TagParent, User
from cherubplay.models.enums import TagType
from cherubplay.tasks import update_request_tag_ids, update_missing_request_tag_ids


def _find_answered(request, requests):
    pipe = request.login_store.pipeline()
    for rq in requests:
        pipe.get("answered:%s:%s" % (request.user.id, rq.id))
    return set(int(_) for _ in pipe.execute() if _ is not None)


class ValidationError(Exception): pass


def _validate_request_form(request):
    if request.POST.get("maturity") not in Tag.maturity_names:
        raise ValidationError("blank_maturity")

    colour = request.POST.get("colour", "")
    if colour.startswith("#"):
        colour = colour[1:]
    if colour_validator.match(colour) is None:
        raise ValidationError("invalid_colour")

    ooc_notes = request.POST.get("ooc_notes", "").strip()
    starter = request.POST.get("starter", "").strip()

    if not ooc_notes and not starter:
        raise ValidationError("blank_ooc_notes_and_starter")

    return colour, ooc_notes, starter


def _normalise_tag_name(tag_type, name):
    name = Tag.name_from_url(name).strip()
    if tag_type == TagType.warning and name.lower().startswith("tw:"):
        name = name[3:].strip()
    elif name.startswith("#"):
        name = name[1:].strip()
    return name[:100]


def _request_tags_from_form(form, new_request):
    tag_set = set()
    fandoms = set()
    for tag_type in Tag.type.type.enums:

        # Enforce preset values for maturity.
        if tag_type == "maturity":
            name = form["maturity"]
            if name not in Tag.maturity_names:
                name = "NSFW extreme"
            tag_set.add((u"maturity", name))
            continue

        # Enforce preset values for type.
        elif tag_type == "type":
            for name in Tag.type_names:
                if "type_" + name in form:
                    tag_set.add((u"type", name))
            continue

        for name in form[tag_type][:1000].split(","):
            name = _normalise_tag_name(tag_type, name)
            if name == "":
                continue
            tag_set.add((tag_type, name))
            if tag_type in (u"fandom", u"fandom_wanted"):
                fandoms.add(name.lower())

    # Meta types
    if new_request.starter:
        tag_set.add((u"type", u"Starter"))
    else:
        tag_set.add((u"type", u"No starter"))

    if len(fandoms) > 1:
        tag_set.add((u"type", u"Crossover"))

    if u"homestuck" not in fandoms:
        tag_set.add((u"type", u"Not Homestuck"))

    tag_list = []
    used_ids = set()
    for tag_type, name in tag_set:
        tag = Tag.get_or_create(tag_type, name)
        tag_id = (tag.synonym_id or tag.id)
        # Remember IDs to skip synonyms.
        if tag_id in used_ids:
            continue
        used_ids.add(tag_id)
        tag_list.append(RequestTag(tag_id=tag_id))

    return tag_list


@view_config(route_name="directory_ext", request_method="GET", permission="directory.read", extension="json", renderer="json")
@view_config(route_name="directory",     request_method="GET", permission="directory.read", renderer="layout2/directory/index.mako")
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
        requests.options(joinedload(Request.tags))
        .order_by(Request.posted.desc())
        .limit(26).all()
    )

    # 404 on empty pages, unless it's the first page.
    if not requests and "before" in request.GET:
        raise HTTPNotFound

    answered = _find_answered(request, requests)

    return {"requests": requests[:25], "answered": answered, "more": len(requests) == 26}


@view_config(route_name="directory_search", request_method="GET", permission="directory.read", renderer="layout2/directory/tag_search.mako")
def directory_search(request):

    tag_name = request.GET.get("name", "").strip()[:100].lower()
    if not tag_name:
        return HTTPFound(request.route_path("directory"))

    tags = Session.query(Tag).filter(func.lower(Tag.name) == tag_name).order_by(Tag.type).all()

    visible_tags = [tag for tag in tags if tag.synonym_of not in tags]

    if len(visible_tags) == 1:
        if tag.synonym_of:
            return HTTPFound(request.route_path("directory_tag", tag_string=visible_tags[0].synonym_of.tag_string))
        return HTTPFound(request.route_path("directory_tag", tag_string=visible_tags[0].tag_string))

    return {"tags": tags}


@view_config(route_name="directory_search_autocomplete", request_method="GET", permission="directory.read", renderer="json")
def directory_search_autocomplete(request):
    if len(request.GET.get("name", "")) < 3:
        return []
    tags = []
    for tag in Session.query(Tag).filter(and_(
        func.lower(Tag.name).like(request.GET["name"].lower().replace("_", "\\_").replace("%", "\\%") + "%")
    )).options(joinedload(Tag.synonym_of)).order_by(Tag.name, Tag.type).all():
        tag_to_add = tag.synonym_of if tag.synonym_id is not None else tag
        if tag_to_add not in tags:
            tags.append(tag_to_add)
    return tags


@view_config(route_name="directory_tag_list", request_method="GET",                   permission="directory.manage_tags", renderer="layout2/directory/tag_list.mako")
@view_config(route_name="directory_tag_list_unapproved", request_method="GET",        permission="directory.manage_tags", renderer="layout2/directory/tag_list.mako")
@view_config(route_name="directory_tag_list_blacklist_default", request_method="GET", permission="directory.manage_tags", renderer="layout2/directory/tag_list.mako")
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

@view_config(route_name="directory_tag_table", request_method="GET", permission="directory.manage_tags", renderer="layout2/directory/tag_table.mako")
def directory_tag_table(request):
    rows = []
    last_tag_name = None
    for tag in Session.query(Tag).order_by(Tag.name, Tag.type).all():
        if tag.name.lower() != last_tag_name:
            last_tag_name = tag.name.lower()
            rows.append({})
        rows[-1][tag.type] = tag
    return {"rows": rows}


@view_config(route_name="directory_tag",     request_method="GET", permission="directory.read", renderer="layout2/directory/tag.mako")
@view_config(route_name="directory_tag_ext", request_method="GET", permission="directory.read", extension="json", renderer="json")
def directory_tag(context, request):

    if request.GET.get("before"):
        try:
            before_date = datetime.datetime.strptime(request.GET["before"], "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            raise HTTPNotFound
    else:
        before_date = None

    if not request.user.seen_blacklist_warning:
        return render_to_response("layout2/directory/blacklist_warning.mako", {}, request)

    resp = {
        "tags": context.tags,
        "blacklisted_tags": context.blacklisted_tags,
    }

    if context.blacklisted_tags:
        resp["requests"] = []
        resp["more"] = False
        return resp

    requests = (
        Session.query(Request)
        .filter(and_(request.user.tag_filter, Request.tag_ids.contains(context.tag_array)))
    )
    if before_date:
        requests = requests.filter(Request.posted < before_date)
    requests = (
        requests.options(joinedload(Request.tags))
        .order_by(Request.posted.desc())
        .limit(26).all()
    )

    resp["requests"] = requests[:25]
    resp["answered"] = _find_answered(request, requests)
    resp["more"]     = len(requests) == 26

    if len(context.tags) == 1:
        tag = context.tags[0]

        all_tag_types = (
            Session.query(Tag)
            .filter(func.lower(Tag.name) == tag.name.lower())
            .options(joinedload(Tag.synonym_of))
            .order_by(Tag.type).all()
        )
        resp["tag_types"] = [_ for _ in all_tag_types if _.synonym_of not in all_tag_types]

        if not "before" in request.GET:
            if request.has_permission("directory.manage_tags"):
                if not tag.approved:
                    resp["can_be_approved"] = True
                resp["synonyms"] = (
                    Session.query(Tag)
                    .filter(Tag.synonym_id == tag.id)
                    .order_by(Tag.type, Tag.name).all()
                )
            resp["parents"] = (
                Session.query(Tag)
                .join(TagParent, Tag.id == TagParent.parent_id)
                .filter(TagParent.child_id == tag.id)
                .order_by(Tag.type, Tag.name).all()
            )
            resp["children"] = (
                Session.query(Tag)
                .join(TagParent, Tag.id == TagParent.child_id)
                .filter(TagParent.parent_id == tag.id)
                .order_by(Tag.type, Tag.name).all()
            )

    return resp


def _approve(tag_type, tag_name):
    tag = Tag.get_or_create(tag_type, tag_name)
    if tag.synonym_id is not None:
        raise HTTPNotFound
    tag.approved = True


@view_config(route_name="directory_tag_approve", request_method="POST", permission="directory.manage_tags")
def directory_tag_approve(request):

    if request.matchdict["type"] not in Tag.type.type.enums:
        raise HTTPNotFound

    tag_type = request.matchdict["type"]
    tag_name = Tag.name_from_url(request.matchdict["name"])

    if tag_type in ("fandom", "fandom_wanted", "character", "character_wanted", "gender", "gender_wanted"):
        if tag_type.endswith("_wanted"):
            tag_type_without_wanted = tag_type.replace("_wanted", "")
            tag_type_with_wanted = tag_type
        else:
            tag_type_without_wanted = tag_type
            tag_type_with_wanted = tag_type + "_wanted"
        _approve(tag_type_without_wanted, tag_name)
        _approve(tag_type_with_wanted, tag_name)
    else:
        _approve(tag_type, tag_name)

    if "Referer" in request.headers:
        return HTTPFound(request.headers["Referer"])
    return HTTPFound(request.route_path("directory_tag", tag_string=request.matchdict["type"] + ":" + request.matchdict["name"]))


def _make_synonym(old_type, old_name, new_type, new_name):

    old_tag = Tag.get_or_create(old_type, old_name)

    # A tag can't be a synonym if it has synonyms.
    if Session.query(func.count("*")).select_from(Tag).filter(Tag.synonym_id == old_tag.id).scalar():
        raise HTTPNotFound

    new_tag = Tag.get_or_create(new_type, new_name)
    new_tag.approved = True

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

    # Delete the old tag from blacklists which already have the new tag.
    Session.query(BlacklistedTag).filter(and_(
        BlacklistedTag.tag_id == old_tag.id,
        BlacklistedTag.user_id.in_(Session.query(BlacklistedTag.user_id).filter(BlacklistedTag.tag_id == new_tag.id)),
    )).delete(synchronize_session=False)
    # And update the rest.
    Session.query(BlacklistedTag).filter(BlacklistedTag.tag_id == old_tag.id).update({"tag_id": new_tag.id})


@view_config(route_name="directory_tag_make_synonym", request_method="POST", permission="directory.manage_tags")
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

    return HTTPFound(request.route_path("directory_tag", tag_string=request.matchdict["type"] + ":" + request.matchdict["name"]))


def _add_parent(child_type, child_name, parent_type, parent_name):
    child_tag = Tag.get_or_create(child_type, child_name)
    parent_tag = Tag.get_or_create(parent_type, parent_name)

    if Session.query(func.count("*")).select_from(TagParent).filter(and_(
        TagParent.parent_id == parent_tag.id,
        TagParent.child_id == child_tag.id,
    )).scalar():
        # Relationship already exists.
        return

    # Check for circular references.
    ancestors = Session.execute("""
        with recursive tag_ids(id) as (
            select %s
            union all
            select parent_id from tag_parents, tag_ids where child_id=tag_ids.id
        )
        select id from tag_ids;
    """ % parent_tag.id)
    if child_tag.id in (_[0] for _ in ancestors):
        raise HTTPNotFound # TODO proper error message

    Session.add(TagParent(parent_id=parent_tag.id, child_id=child_tag.id))

    # Null the tag_ids of requests in this tag and all its children.
    Session.execute("""
        with recursive tag_ids(id) as (
            select %s
            union all
            select child_id from tag_parents, tag_ids where parent_id=tag_ids.id
        )
        update requests set tag_ids = null
        where requests.id in (
            select request_id from request_tags where tag_id in (select id from tag_ids)
        )
    """ % child_tag.id)


@view_config(route_name="directory_tag_add_parent", request_method="POST", permission="directory.manage_tags")
def directory_tag_add_parent(request):
    if request.matchdict["type"] not in Tag.type.type.enums or request.POST["tag_type"] not in Tag.type.type.enums:
        raise HTTPNotFound

    child_type = request.matchdict["type"]
    child_name = Tag.name_from_url(request.matchdict["name"])
    parent_type = request.POST["tag_type"]
    parent_name = Tag.name_from_url(request.POST["name"]).strip()[:100]

    if not child_name or not parent_name:
        raise HTTPBadRequest

    if (
        child_type in ("fandom", "fandom_wanted", "character", "character_wanted", "gender", "gender_wanted")
        and parent_type in ("fandom", "fandom_wanted", "character", "character_wanted", "gender", "gender_wanted")
    ):
        if child_type.endswith("_wanted"):
            child_type_without_wanted = child_type.replace("_wanted", "")
            child_type_with_wanted = child_type
        else:
            child_type_without_wanted = child_type
            child_type_with_wanted = child_type + "_wanted"
        if parent_type.endswith("_wanted"):
            parent_type_without_wanted = parent_type.replace("_wanted", "")
            parent_type_with_wanted = parent_type
        else:
            parent_type_without_wanted = parent_type
            parent_type_with_wanted = parent_type + "_wanted"
        _add_parent(child_type_without_wanted, child_name, parent_type_without_wanted, parent_name)
        _add_parent(child_type_with_wanted, child_name, parent_type_with_wanted, parent_name)
    else:
        _add_parent(child_type, child_name, parent_type, parent_name)

    transaction.commit()
    update_missing_request_tag_ids.delay()

    return HTTPFound(request.route_path("directory_tag", tag_string=request.matchdict["type"] + ":" + request.matchdict["name"]))


@view_config(route_name="directory_yours",     request_method="GET", permission="directory.read", renderer="layout2/directory/index.mako")
@view_config(route_name="directory_yours_ext", request_method="GET", permission="directory.read", extension="json", renderer="json")
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
        requests.options(joinedload(Request.tags))
        .order_by(func.coalesce(Request.posted, Request.created).desc())
        .limit(26).all()
    )

    # 404 on empty pages, unless it's the first page.
    if not requests and "before" in request.GET:
        raise HTTPNotFound

    return {"requests": requests[:25], "more": len(requests) == 26}


def _remove_duplicates(new_request):
    Session.query(Request).filter(and_(
        Request.id      != new_request.id,
        Request.user_id == new_request.user_id,
        Request.status  == "posted",
        func.lower(Request.ooc_notes) == new_request.ooc_notes.lower(),
        func.lower(Request.starter)   == new_request.starter.lower(),
    )).update({
        "status": "draft",
        "duplicate_of_id": new_request.id,
    }, synchronize_session=False)


@view_config(route_name="directory_new", request_method="GET", permission="directory.new_request", renderer="layout2/directory/new.mako")
def directory_new_get(request):
    return {"form_data": {}, "preset_colours": preset_colours}


@view_config(route_name="directory_new", request_method="POST", permission="directory.new_request", renderer="layout2/directory/new.mako")
def directory_new_post(request):
    try:
        colour, ooc_notes, starter = _validate_request_form(request)
    except ValidationError as e:
        return {"form_data": request.POST, "preset_colours": preset_colours, "error": e.message}

    status = "draft" if "draft" in request.POST else "posted"

    new_date = datetime.datetime.now()

    new_request = Request(
        user_id=request.user.id,
        status=status,
        created=new_date,
        posted=new_date if status == "posted" else None,
        edited=new_date,
        colour=colour,
        ooc_notes=ooc_notes,
        starter=starter,
    )
    Session.add(new_request)
    Session.flush()

    _remove_duplicates(new_request)

    new_request.request_tags += _request_tags_from_form(request.POST, new_request)

    # Commit manually to make sure the task happens after.
    transaction.commit()
    update_request_tag_ids.delay(new_request.id)

    return HTTPFound(request.route_path("directory_request", id=new_request.id))


@view_config(route_name="directory_new_autocomplete", request_method="GET", permission="directory.new_request", renderer="json")
def directory_new_autocomplete(request):

    try:
        tag_type = TagType(request.GET.get("type"))
    except ValueError:
        raise HTTPBadRequest

    if not request.GET.get("name"):
        raise HTTPBadRequest

    if len(request.GET["name"]) < 3:
        return []

    tags = Session.query(Tag).filter(and_(
        Tag.type == tag_type,
        func.lower(Tag.name).like(request.GET["name"].lower().replace("_", "\\_").replace("%", "\\%") + "%")
    )).options(joinedload(Tag.synonym_of)).order_by(Tag.name)

    return sorted(list({
        # Use the original name if this tag is a synonym.
        (tag.synonym_of.name if tag.synonym_of else tag.name)
        for tag in tags
        # Exclude tags which are a synonym of another type.
        if not tag.synonym_of or tag.synonym_of.type == tag.type
    }), key=lambda _: _.lower())


def _blacklisted_tags(request, **kwargs):
    return {
        "tags": (
            Session.query(BlacklistedTag)
            .join(BlacklistedTag.tag)
            .filter(BlacklistedTag.user_id == request.user.id)
            .options(contains_eager(BlacklistedTag.tag))
            .order_by(Tag.type, Tag.name).all()
        ),
        "maturity_tags": Session.query(Tag).filter(Tag.type == TagType.maturity).all(),
        "type_tags":     Session.query(Tag).filter(Tag.type == TagType.type).all(),
        **kwargs
    }


@view_config(route_name="directory_blacklist", request_method="GET",     permission="directory.read", renderer="layout2/directory/blacklist.mako")
@view_config(route_name="directory_blacklist_ext", request_method="GET", permission="directory.read", extension="json", renderer="json")
def directory_blacklist(request):
    return _blacklisted_tags(request)


@view_config(route_name="directory_blacklist_setup", request_method="POST", permission="directory.read")
def directory_blacklist_setup(request):

    if request.POST.get("blacklist") not in ("none", "default"):
        raise HTTPBadRequest

    if request.user.seen_blacklist_warning:
        return HTTPFound(request.headers.get("Referer") or request.route_path("directory"))

    if request.POST["blacklist"] == "default":
        Session.execute(BlacklistedTag.__table__.insert().from_select(
            ["user_id", "tag_id"],
            Session.query(literal(request.user.id), Tag.id).filter(Tag.blacklist_default == True)
        ))

    Session.query(User).filter(User.id == request.user.id).update({"seen_blacklist_warning": True})

    return HTTPFound(request.headers.get("Referer") or request.route_path("directory"))


@view_config(route_name="directory_blacklist_add", request_method="POST", permission="directory.read", renderer="layout2/directory/blacklist.mako")
def directory_blacklist_add(request):

    try:
        tag_type = TagType(request.POST.get("tag_type"))
    except ValueError:
        raise HTTPBadRequest

    if tag_type == TagType.maturity and request.POST.get("maturity_name"):
        names = request.POST["maturity_name"]
    elif tag_type == TagType.type and request.POST.get("type_name"):
        names = request.POST["type_name"]
    else:
        names = request.POST["name"][:100]

    for name in names.split(","):
        name = _normalise_tag_name(tag_type, name)
        if not name:
            continue

        try:
            tag = Tag.get_or_create(tag_type, name, allow_maturity_and_type_creation=False)
        except CreateNotAllowed:
            return _blacklisted_tags(request, error="invalid", error_tag_type=tag_type, error_name=name)
        tag_id = (tag.synonym_id or tag.id)

        if Session.query(func.count("*")).select_from(BlacklistedTag).filter(and_(
            BlacklistedTag.user_id == request.user.id,
            BlacklistedTag.tag_id == tag_id,
        )).scalar() == 0:
            Session.add(BlacklistedTag(user_id=request.user.id, tag_id=tag_id))

    return HTTPFound(request.route_path("directory_blacklist"))


@view_config(route_name="directory_blacklist_remove", request_method="POST", permission="directory.read")
def directory_blacklist_remove(request):
    try:
        Session.query(BlacklistedTag).filter(and_(
            BlacklistedTag.user_id == request.user.id,
            BlacklistedTag.tag_id == request.POST["tag_id"],
        )).delete()
    except (KeyError, ValueError):
        raise HTTPBadRequest
    return HTTPFound(request.route_path("directory_blacklist"))


@view_config(route_name="directory_request",     request_method="GET", permission="request.read", renderer="layout2/directory/request.mako")
@view_config(route_name="directory_request_ext", request_method="GET", permission="request.read", extension="json", renderer="json")
def directory_request(context, request):

    chats = Session.query(ChatUser, Chat).join(Chat).filter(
        ChatUser.user_id==request.user.id,
        Chat.request_id==context.id,
    ).order_by(Chat.updated.desc()).all()

    blacklisted_tags = Session.query(Tag).filter(Tag.id.in_(
        Session.query(RequestTag.tag_id).filter(RequestTag.request_id == context.id)
        .intersect(Session.query(BlacklistedTag.tag_id).filter(BlacklistedTag.user_id == request.user.id))
    )).order_by(Tag.type, Tag.name).all()

    if request.matched_route.name == "directory_request_ext":
        return {
            "request": context,
            "chats": [{"chat_user": _[0], "chat": _[1]} for _ in chats],
            "blacklisted_tags": blacklisted_tags,
        }

    return {
        "chats": chats,
        "blacklisted_tags": blacklisted_tags,
    }


@view_config(route_name="directory_request_answer", request_method="POST", permission="request.answer")
def directory_request_answer(context, request):

    if request.login_store.get("answered:%s:%s" % (request.user.id, context.id)):
        response = render_to_response("layout2/directory/already_answered.mako", {}, request)
        response.status_int = 403
        return response

    key = "directory_answer_limit:%s" % request.user.id
    current_time = time.time()
    if request.login_store.llen(key) >= 12:
        if current_time - float(request.login_store.lindex(key, 0)) < 3600:
            return render_to_response("layout2/directory/answered_too_many.mako", {}, request)

    request.login_store.rpush(key, current_time)
    request.login_store.ltrim(key, -12, -1)
    request.login_store.expire(key, 3600)

    request.login_store.setex("answered:%s:%s" % (request.user.id, context.id), 86400, context.id)

    new_chat = Chat(url=str(uuid4()), request_id=context.id)
    Session.add(new_chat)
    Session.flush()

    Session.add(ChatUser(chat_id=new_chat.id, user_id=context.user_id, symbol=0, last_colour=context.colour))
    Session.add(ChatUser(chat_id=new_chat.id, user_id=request.user.id, symbol=1))

    if context.ooc_notes:
        Session.add(Message(chat_id=new_chat.id, user_id=context.user_id, symbol=0, text=context.ooc_notes))
    if context.starter:
        Session.add(Message(chat_id=new_chat.id, user_id=context.user_id, symbol=0, colour=context.colour, text=context.starter))

    return HTTPFound(request.route_path("chat", url=new_chat.url))


@view_config(route_name="directory_request_edit", request_method="GET", permission="request.edit", renderer="layout2/directory/new.mako")
def directory_request_edit_get(context, request):

    form_data = {}

    for tag_type, tags in context.tags_by_type().items():
        if tag_type == TagType.maturity:
            if tags: # i don't know why we wouldn't have a maturity but don't IndexError if that does happen
                form_data["maturity"] = tags[0].name
        elif tag_type == TagType.type:
            for tag in tags:
                form_data["type_" + tag.name] = "on"
        else:
            form_data[tag_type.value] = ", ".join(tag.name for tag in tags)

    form_data["colour"]    = "#" + context.colour
    form_data["ooc_notes"] = context.ooc_notes
    form_data["starter"]   = context.starter

    return {"form_data": form_data, "preset_colours": preset_colours}


@view_config(route_name="directory_request_edit", request_method="POST", permission="request.edit", renderer="layout2/directory/new.mako")
def directory_request_edit_post(context, request):

    try:
        colour, ooc_notes, starter = _validate_request_form(request)
    except ValidationError as e:
        return {"form_data": request.POST, "preset_colours": preset_colours, "error": e.message}

    new_date = datetime.datetime.now()
    context.edited = new_date

    if context.status != "removed":
        status = "draft" if "draft" in request.POST else "posted"
        if status == "posted" and context.posted is None:
            context.posted = new_date
        context.status = status

    context.colour          = colour
    context.ooc_notes       = ooc_notes
    context.starter         = starter
    context.duplicate_of_id = None

    Session.query(RequestTag).filter(RequestTag.request_id == context.id).delete()

    new_tags = _request_tags_from_form(request.POST, context)
    context.request_tags += new_tags
    context.tag_ids = None

    _remove_duplicates(context)

    # Commit manually to make sure the task happens after.
    transaction.commit()
    update_request_tag_ids.delay(context.id)

    return HTTPFound(request.route_path("directory_request", id=context.id))


@view_config(route_name="directory_request_delete", request_method="GET", permission="request.delete", renderer="layout2/directory/request_delete.mako")
def directory_request_delete_get(context, request):
    return {}


@view_config(route_name="directory_request_delete", request_method="POST", permission="request.delete")
def directory_request_delete_post(context, request):
    Session.query(Chat).filter(Chat.request_id == context.id).update({"request_id": None})
    Session.query(RequestTag).filter(RequestTag.request_id == context.id).delete()
    Session.query(Request).filter(Request.id == context.id).delete()
    return HTTPFound(request.route_path("directory_yours"))


@view_config(route_name="directory_request_remove", request_method="POST", permission="request.remove")
def directory_request_remove(context, request):
    context.status = "removed"
    return HTTPFound(request.route_path("directory_request", id=context.id))


@view_config(route_name="directory_request_unremove", request_method="POST", permission="request.remove")
def directory_request_unremove(context, request):
    context.status = "posted"
    return HTTPFound(request.route_path("directory_request", id=context.id))

