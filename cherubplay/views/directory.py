import datetime, time, transaction

from itertools import zip_longest
from pyramid.httpexceptions import HTTPBadRequest, HTTPFound, HTTPNotFound
from pyramid.renderers import render_to_response
from pyramid.view import view_config
from sqlalchemy import and_, func, literal
from sqlalchemy.orm import joinedload, subqueryload
from sqlalchemy.orm.exc import NoResultFound
from uuid import uuid4

from cherubplay.lib import colour_validator, preset_colours
from cherubplay.models import Session, BlacklistedTag, Chat, ChatUser, CreateNotAllowed, Message, Request, RequestSlot, RequestTag, Tag, TagParent, User
from cherubplay.models.enums import ChatMode, ChatUserStatus, TagType
from cherubplay.resources import CircularReferenceException
from cherubplay.tasks import update_request_tag_ids


def _find_answered(request, requests):
    pipe = request.login_store.pipeline()
    for rq in requests:
        pipe.get("answered:%s:%s" % (request.user.id, rq.id))
    return set(int(_) for _ in pipe.execute() if _ is not None)


class ValidationError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


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


def _validate_request_slots(request):
    if request.POST.get("mode") != "group":
        return None, None

    slot_name = request.POST.get("slot_1_name", "").strip()[:50]
    if not slot_name:
        raise ValidationError("not_enough_slots")

    slot_descriptions = []
    for n in range(2, 6):
        slot_description = request.POST.get("slot_%s_description" % n, "").strip()[:100]
        if not slot_description:
            continue
        slot_descriptions.append(slot_description)

    if len(slot_descriptions) < 2:
        raise ValidationError("not_enough_slots")

    return slot_name, slot_descriptions


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
    for tag_type in Tag.type.type.python_type:

        # Enforce preset values for maturity.
        if tag_type == TagType.maturity:
            name = form["maturity"]
            if name not in Tag.maturity_names:
                name = "NSFW extreme"
            maturity = name
            continue

        # Enforce preset values for type.
        elif tag_type == TagType.type:
            for name in Tag.type_names:
                if "type_" + name in form:
                    tag_set.add((TagType.type, name))
            continue

        for name in form[tag_type.value][:1000].split(","):
            name = _normalise_tag_name(tag_type, name)
            if name == "":
                continue
            tag_set.add((tag_type, name))
            if tag_type in (TagType.fandom, TagType.fandom_wanted):
                fandoms.add(name.lower())

    # Meta types
    if new_request.starter:
        tag_set.add((TagType.type, u"Starter"))
    else:
        tag_set.add((TagType.type, u"No starter"))

    if len(fandoms) > 1:
        tag_set.add((TagType.type, u"Crossover"))

    if u"homestuck" not in fandoms:
        tag_set.add((TagType.type, u"Not Homestuck"))

    if form.get("mode") == "group":
        tag_set.add((TagType.type, u"Group chat"))

    bump_maturity = False

    tag_list = []
    used_ids = set()
    for tag_type, name in tag_set:
        tag = Tag.get_or_create(tag_type, name)

        if tag.bump_maturity or (tag.synonym_id and tag.synonym_of.bump_maturity):
            bump_maturity = True

        tag_id = (tag.synonym_id or tag.id)

        # Remember IDs to skip synonyms.
        if tag_id in used_ids:
            continue
        used_ids.add(tag_id)

        tag_list.append(RequestTag(tag_id=tag_id))

    if bump_maturity:
        tag_list.append(RequestTag(tag_id=Tag.get_or_create(TagType.maturity, "NSFW extreme").id))
    else:
        tag_list.append(RequestTag(tag_id=Tag.get_or_create(TagType.maturity, maturity).id))

    return tag_list


def _trigger_update_request_tag_ids(request_id: int):
    def hook(status):
        if not status:
            return
        update_request_tag_ids.delay(request_id)
    return hook


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
        requests.options(joinedload(Request.tags), subqueryload(Request.slots))
        .order_by(Request.posted.desc())
        .limit(26).all()
    )

    # 404 on empty pages, unless it's the first page.
    if not requests and "before" in request.GET:
        raise HTTPNotFound

    answered = _find_answered(request, requests)

    return {"requests": requests[:25], "answered": answered, "more": len(requests) == 26}


@view_config(route_name="directory_search",     request_method="GET", permission="directory.read", renderer="layout2/directory/tag_search.mako")
@view_config(route_name="directory_tag_search", request_method="GET", permission="directory.read", renderer="layout2/directory/tag_search.mako")
def directory_search(context, request):
    if request.matched_route.name == "directory_tag_search" and len(context.tags) == 5:
        raise HTTPNotFound

    tag_name = request.GET.get("name", "").strip()[:100].lower()
    if not tag_name:
        return HTTPFound(request.route_path("directory"))

    tags = Session.query(Tag).filter(func.lower(Tag.name) == tag_name)
    if request.matched_route.name == "directory_tag_search":
        tags = tags.filter(~Tag.id.in_(_.id for _ in context.tags))
    tags = tags.order_by(Tag.type).all()

    visible_tags = [tag for tag in tags if tag.synonym_of not in tags]

    if len(visible_tags) == 1:
        redirect_tag = visible_tags[0].synonym_of or visible_tags[0]
        if request.matched_route.name == "directory_tag_search":
            redirect_tag_string = context.tag_string_plus(redirect_tag)
        else:
            redirect_tag_string = redirect_tag.tag_string
        return HTTPFound(request.route_path("directory_tag", tag_string=redirect_tag_string))

    return {"tags": tags}


@view_config(route_name="directory_search_autocomplete",     request_method="GET", permission="directory.read", renderer="json")
@view_config(route_name="directory_tag_search_autocomplete", request_method="GET", permission="directory.read", renderer="json")
def directory_search_autocomplete(context, request):
    if len(request.GET.get("name", "")) < 3:
        return []

    added_tags = set()
    response   = []

    tag_query = Session.query(Tag).filter(
        func.lower(Tag.name)
        .like(request.GET["name"].lower().replace("_", "\\_").replace("%", "\\%") + "%")
    )
    if request.matched_route.name == "directory_tag_search_autocomplete":
        tag_query = tag_query.filter(~Tag.id.in_(_.id for _ in context.tags))
    tag_query = tag_query.options(joinedload(Tag.synonym_of)).order_by(Tag.name, Tag.type).all()

    for tag in tag_query:
        tag_to_add = tag.synonym_of if tag.synonym_id is not None else tag
        if tag_to_add not in added_tags:
            json_dict = tag_to_add.__json__()
            if request.matched_route.name == "directory_tag_search_autocomplete":
                json_dict["url"] = request.route_path("directory_tag", tag_string=context.tag_string_plus(tag_to_add))
            else:
                json_dict["url"] = request.route_path("directory_tag", tag_string=tag_to_add.tag_string)
            response.append(json_dict)
            added_tags.add(tag_to_add)

    return response


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
        tag_query = tag_query.filter(and_(Tag.synonym_id is None, Tag.approved is False))
        tag_count_query = tag_count_query.filter(and_(Tag.synonym_id is None, Tag.approved is False))
    elif request.matched_route.name == "directory_tag_list_blacklist_default":
        tag_query = tag_query.filter(Tag.blacklist_default is True)
        tag_count_query = tag_count_query.filter(Tag.blacklist_default is True)

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


@view_config(route_name="directory_user_ext", request_method="GET", permission="admin", extension="json", renderer="json")
@view_config(route_name="directory_user",     request_method="GET", permission="admin", renderer="layout2/directory/index.mako")
def directory_user(request):

    try:
        user = Session.query(User).filter(func.lower(User.username) == request.matchdict["username"].lower()).one()
    except NoResultFound:
        raise HTTPNotFound

    if user.username != request.matchdict["username"]:
        raise HTTPFound(request.current_route_path(username=user.username))

    if request.GET.get("before"):
        try:
            before_date = datetime.datetime.strptime(request.GET["before"], "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            raise HTTPNotFound
    else:
        before_date = None

    requests = Session.query(Request).filter(Request.user_id == user.id)
    if before_date:
        requests = requests.filter(Request.posted < before_date)
    requests = (
        requests.options(joinedload(Request.tags), subqueryload(Request.slots))
        .order_by(Request.posted.desc())
        .limit(26).all()
    )

    # 404 on empty pages, unless it's the first page.
    if not requests and "before" in request.GET:
        raise HTTPNotFound

    answered = _find_answered(request, requests)

    return {"requests": requests[:25], "answered": answered, "more": len(requests) == 26}


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
        requests.options(joinedload(Request.tags), subqueryload(Request.slots))
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

        if "before" not in request.GET:
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


@view_config(route_name="directory_tag_approve", request_method="POST", permission="directory.manage_tags")
def directory_tag_approve(context, request):
    for tag in context.tags:
        if tag.synonym_id is not None:
            raise HTTPNotFound
        tag.approved = True

    if "Referer" in request.headers:
        return HTTPFound(request.headers["Referer"])
    return HTTPFound(request.route_path("directory_tag", tag_string=request.matchdict["type"] + ":" + request.matchdict["name"]))


@view_config(route_name="directory_tag_make_synonym", request_method="POST", permission="directory.manage_tags")
def directory_tag_make_synonym(context, request):
    try:
        new_type = TagType(request.POST["tag_type"])
    except ValueError:
        raise HTTPBadRequest

    new_name = Tag.name_from_url(request.POST["name"]).strip()[:100]
    if not new_name:
        raise HTTPBadRequest

    try:
        context.make_synonym(new_type, new_name)
    except CircularReferenceException:
        return HTTPFound(request.route_path(
            "directory_tag",
            tag_string=request.matchdict["type"] + ":" + request.matchdict["name"],
            _query={"error": "circular_reference"},
        ))

    return HTTPFound(request.route_path("directory_tag", tag_string=request.matchdict["type"] + ":" + request.matchdict["name"]))


@view_config(route_name="directory_tag_add_parent", request_method="POST", permission="directory.manage_tags")
def directory_tag_add_parent(context, request):
    try:
        parent_type = TagType(request.POST["tag_type"])
    except ValueError:
        raise HTTPBadRequest

    parent_name = Tag.name_from_url(request.POST["name"]).strip()[:100]
    if not parent_name:
        raise HTTPBadRequest

    try:
        context.add_parent(parent_type, parent_name)
    except ValueError:
        raise HTTPNotFound

    return HTTPFound(request.route_path("directory_tag", tag_string=request.matchdict["type"] + ":" + request.matchdict["name"]))


@view_config(route_name="directory_tag_bump_maturity", request_method="POST", permission="directory.manage_tags")
def directory_tag_bump_maturity(context, request):
    context.set_bump_maturity(request.POST.get("bump_maturity") == "on")
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
        requests.options(joinedload(Request.tags), subqueryload(Request.slots))
        .order_by(func.coalesce(Request.posted, Request.created).desc())
        .limit(26).all()
    )

    # 404 on empty pages, unless it's the first page.
    if not requests and "before" in request.GET:
        raise HTTPNotFound

    return {"requests": requests[:25], "more": len(requests) == 26}


@view_config(route_name="directory_random", request_method="GET", permission="directory.read", renderer="layout2/directory/lucky_dip_failed.mako")
def directory_random(request):
    request_query = (
        Session.query(Request.id)
        .filter(and_(
            Request.user_id != request.user.id,
            request.user.tag_filter,
        ))
        .order_by(func.random()).first()
    )
    if request_query:
        return HTTPFound(request.route_path("directory_request", id=request_query[0]))
    return {}


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
        slot_name, slot_descriptions = _validate_request_slots(request)
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

    if slot_name and slot_descriptions:
        Session.add(RequestSlot(
            request=new_request,
            order=1,
            description=slot_name,
            user_id=request.user.id,
            user_name=slot_name,
        ))
        for order, description in enumerate(slot_descriptions, 2):
            Session.add(RequestSlot(request=new_request, order=order, description=description))

    transaction.get().addAfterCommitHook(_trigger_update_request_tag_ids(new_request.id))

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
    tags = (
        Session.query(Tag).join(BlacklistedTag)
        .filter(BlacklistedTag.user_id == request.user.id)
        .order_by(Tag.type, Tag.name).all()
    )
    return {
        "tags": tags,
        "maturity_tags": [tag for tag in Session.query(Tag).filter(Tag.type == TagType.maturity).all() if tag not in tags],
        "type_tags":     [tag for tag in Session.query(Tag).filter(Tag.type == TagType.type).all()     if tag not in tags],
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
            Session.query(literal(request.user.id), Tag.id).filter(Tag.blacklist_default is True)
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
        ChatUser.user_id == request.user.id,
        ChatUser.status == ChatUserStatus.active,
        Chat.request_id == context.id,
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


def _get_current_slot(context, request):
    try:
        order = int(request.GET.get("slot"))
    except (TypeError, ValueError):
        raise HTTPNotFound

    for slot in context.slots:
        if slot.order == order:
            current_slot = slot
            break
    else:
        raise HTTPNotFound

    if slot.taken:
        raise ValidationError("slot_taken")

    if context.user_has_any_slot(request.user):
        raise ValidationError("already_answered")

    return current_slot


@view_config(route_name="directory_request_answer", request_method="GET", permission="request.answer")
def directory_request_answer_get(context, request):
    if not context.slots:
        raise HTTPNotFound

    try:
        _get_current_slot(context, request)
    except ValidationError as e:
        response = render_to_response("layout2/directory/%s.mako" % e.message, {}, request)
        response.status_int = 403
        return response

    return render_to_response("layout2/directory/slot_name.mako", {}, request)


@view_config(route_name="directory_request_answer", request_method="POST", permission="request.answer")
def directory_request_answer_post(context, request):

    if request.login_store.get("answered:%s:%s" % (request.user.id, context.id)):
        response = render_to_response("layout2/directory/already_answered.mako", {}, request)
        response.status_int = 403
        return response

    key = "directory_answer_limit:%s" % request.user.id
    current_time = time.time()
    if request.login_store.llen(key) >= 12:
        if current_time - float(request.login_store.lindex(key, 0)) < 3600:
            return render_to_response("layout2/directory/answered_too_many.mako", {}, request)

    if context.slots:
        try:
            current_slot = _get_current_slot(context, request)
        except ValidationError as e:
            response = render_to_response("layout2/directory/%s.mako" % e.message, {}, request)
            response.status_int = 403
            return response

        slot_name = request.POST.get("name", "").strip()[:50]
        if not slot_name:
            return render_to_response("layout2/directory/slot_name.mako", {"error": "blank_name"}, request)

        current_slot.user_id   = request.user.id
        current_slot.user_name = slot_name

        if not context.all_slots_taken:
            return HTTPFound(request.route_path("directory_request", id=context.id, _query={"answer_status": "waiting"}))

    request.login_store.rpush(key, current_time)
    request.login_store.ltrim(key, -12, -1)
    request.login_store.expire(key, 3600)

    new_chat = Chat(url=str(uuid4()), request_id=context.id)

    if context.slots:
        new_chat.mode = ChatMode.group

    Session.add(new_chat)
    Session.flush()

    if context.slots:
        used_names = set()
        for slot in context.slots:

            if slot.user_id != context.user_id:
                request.login_store.setex("answered:%s:%s" % (slot.user_id, context.id), 86400, context.id)

            if slot.user_name in used_names:
                for n in range(2, 6):
                    attempt = slot.user_name + (" (%s)" % n)
                    if attempt not in used_names:
                        slot.user_name = attempt
                        break

            used_names.add(slot.user_name)

            new_chat_user = ChatUser(chat_id=new_chat.id, user_id=slot.user_id, name=slot.user_name)

            if slot.user_id == context.user_id:
                new_chat_user.last_colour = context.colour
            else:
                slot.user_id   = None
                slot.user_name = None

            Session.add(new_chat_user)
    else:
        request.login_store.setex("answered:%s:%s" % (request.user.id, context.id), 86400, context.id)
        Session.add(ChatUser(chat_id=new_chat.id, user_id=context.user_id, symbol=0, last_colour=context.colour))
        Session.add(ChatUser(chat_id=new_chat.id, user_id=request.user.id, symbol=1))

    if context.ooc_notes:
        Session.add(Message(chat_id=new_chat.id, user_id=context.user_id, symbol=None if context.slots else 0, text=context.ooc_notes))
    if context.starter:
        Session.add(Message(chat_id=new_chat.id, user_id=context.user_id, symbol=None if context.slots else 0, colour=context.colour, text=context.starter))

    return HTTPFound(request.route_path("chat", url=new_chat.url))


@view_config(route_name="directory_request_unanswer", request_method="POST", permission="request.answer")
def directory_request_unanswer_get(context, request):
    if request.user.id == context.user_id:
        raise HTTPNotFound

    for slot in context.slots:
        if request.user.id == slot.user_id:
            slot.user_id = None
            slot.user_name = None
            return HTTPFound(
                request.headers.get("Referer")
                or request.route_path("directory_request", id=context.id)
            )

    raise HTTPNotFound


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
    form_data["mode"]      = "group" if context.slots else "1-on-1"

    for slot in context.slots:
        if slot.order == 1:
            form_data["slot_1_name"] = slot.user_name or ""
        else:
            form_data["slot_%s_description" % slot.order] = slot.description or ""

    return {"form_data": form_data, "preset_colours": preset_colours}


@view_config(route_name="directory_request_edit", request_method="POST", permission="request.edit", renderer="layout2/directory/new.mako")
def directory_request_edit_post(context, request):

    try:
        colour, ooc_notes, starter   = _validate_request_form(request)
        slot_name, slot_descriptions = _validate_request_slots(request)
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

    if slot_name and slot_descriptions:
        for order, new_description, existing_slot in zip_longest(range(1, 6), [slot_name] + slot_descriptions, context.slots):
            if new_description and existing_slot:
                existing_slot.order       = order
                existing_slot.description = new_description
                if order == 1:
                    existing_slot.user_name = new_description
            elif new_description:
                new_slot = RequestSlot(request=context, order=order, description=new_description)
                if order == 1:
                    new_slot.user_id   = context.user_id
                    new_slot.user_name = new_description
                Session.add(new_slot)
            elif existing_slot:
                Session.delete(existing_slot)
    else:
        Session.query(RequestSlot).filter(RequestSlot.request_id == context.id).delete()

    _remove_duplicates(context)

    transaction.get().addAfterCommitHook(_trigger_update_request_tag_ids(context.id))

    return HTTPFound(request.route_path("directory_request", id=context.id))


@view_config(route_name="directory_request_delete", request_method="GET", permission="request.delete", renderer="layout2/directory/request_delete.mako")
def directory_request_delete_get(context, request):
    return {}


@view_config(route_name="directory_request_delete", request_method="POST", permission="request.delete")
def directory_request_delete_post(context, request):
    Session.query(Chat).filter(Chat.request_id == context.id).update({"request_id": None})
    Session.query(Request).filter(Request.duplicate_of_id == context.id).update({"duplicate_of_id": None})
    Session.query(RequestTag).filter(RequestTag.request_id == context.id).delete()
    Session.query(RequestSlot).filter(RequestSlot.request_id == context.id).delete()
    Session.query(Request).filter(Request.id == context.id).delete()
    return HTTPFound(request.route_path("directory_yours"))


@view_config(route_name="directory_request_remove", request_method="POST", permission="request.remove")
def directory_request_remove(context, request):
    context.status = "removed"
    return HTTPFound(request.route_path("directory_request", id=context.id))


@view_config(route_name="directory_request_unremove", request_method="POST", permission="request.remove")
def directory_request_unremove(context, request):
    context.status = "draft"
    return HTTPFound(request.route_path("directory_request", id=context.id))

