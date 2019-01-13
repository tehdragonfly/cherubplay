import datetime, re, time, transaction

from itertools import zip_longest
from pyramid.httpexceptions import (
    HTTPBadRequest, HTTPFound, HTTPNoContent, HTTPNotFound,
)
from pyramid.renderers import render_to_response
from pyramid.view import view_config
from sqlalchemy import and_, func, literal
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound

from cherubplay.lib import colour_validator
from cherubplay.models import (
    BlacklistedTag, Chat, ChatUser, Request, RequestSlot, RequestTag, Tag,
    TagParent, TagAddParentSuggestion, TagBumpMaturitySuggestion,
    TagMakeSynonymSuggestion, User,
)
from cherubplay.models.enums import ChatUserStatus, TagType
from cherubplay.resources import CircularReferenceException, TagPair
from cherubplay.services.request import IRequestService
from cherubplay.services.tag import CreateNotAllowed, ITagService
from cherubplay.tasks import update_request_tag_ids


LINEBREAK_REGEX = re.compile(r"\n\n+")


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
    starter   = request.POST.get("starter", "").strip()

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


def _tags_from_form(request, form, new_request):
    tag_set = set()
    fandoms = set()
    for tag_type in Tag.type.type.python_type:

        # Maturity is set after checking bump_maturity.
        if tag_type == TagType.maturity:
            continue

        # Enforce preset values for type.
        elif tag_type == TagType.type:
            for name in Tag.type_names:
                if "type_" + name in form:
                    tag_set.add((TagType.type, name))
            continue

        for name in request.registry.settings["checkbox_tags." + tag_type.value]:
            if tag_type.value + "_" + name in form:
                tag_set.add((tag_type, name))
                if tag_type in (TagType.fandom, TagType.fandom_wanted):
                    fandoms.add(name.lower())

        for name in form[tag_type.value][:1000].split(","):
            name = Tag.normalise_tag_name(tag_type, name)
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
    tag_service = request.find_service(ITagService)
    for tag_type, name in tag_set:
        tag = tag_service.get_or_create(tag_type, name)

        if tag.bump_maturity or (tag.synonym_id and tag.synonym_of.bump_maturity):
            bump_maturity = True

        tag_id = (tag.synonym_id or tag.id)

        # Remember IDs to skip synonyms.
        if tag_id in used_ids:
            continue
        used_ids.add(tag_id)

        tag_list.append(tag_id)

    if bump_maturity or form.get("maturity") not in Tag.maturity_names:
        maturity_name = "NSFW extreme"
    else:
        maturity_name = form["maturity"]
    tag_list.append(tag_service.get_or_create(TagType.maturity, maturity_name).id)

    return tag_list


def _request_tags_from_form(request, form, new_request):
    return [
        RequestTag(tag_id=tag_id)
        for tag_id in _tags_from_form(request, form, new_request)
    ]


def _trigger_update_request_tag_ids(request_id: int):
    def hook(status):
        if not status:
            return
        update_request_tag_ids.delay(request_id)
    return hook


def _forbidden_response(*args):
    response = render_to_response(*args)
    response.status_int = 403
    return response


class ShowBlacklistWarning(Exception): pass


@view_config(context=ShowBlacklistWarning, renderer="layout2/directory/blacklist_warning.mako")
def blacklist_warning(request):
    if request.matchdict.get("ext") == "json":
        return render_to_response("json", {"seen_blacklist_warning": False}, request)
    return {}


class RequestListView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def search_args(self):
        raise NotImplementedError

    def render_args(self):
        raise NotImplementedError

    def __call__(self):
        if not self.request.user.seen_blacklist_warning:
            raise ShowBlacklistWarning

        request_service = self.request.find_service(IRequestService)
        kwargs = {}

        if self.request.GET.get("before"):
            try:
                kwargs["start"] = datetime.datetime.strptime(
                    self.request.GET["before"],
                    "%Y-%m-%dT%H:%M:%S.%f",
                )
            except ValueError:
                raise HTTPNotFound
        else:
            kwargs["start"] = None

        if self.request.GET.get("sort"):
            kwargs["sort"] = self.request.GET["sort"]

        kwargs.update(self.search_args())

        try:
            requests = request_service.search(**kwargs)
        except ValueError:
            raise HTTPNotFound

        # 404 on empty pages, unless it's the first page.
        if len(requests) == 0 and "before" in self.request.GET:
            raise HTTPNotFound

        if self.request.matchdict.get("ext") == "json":
            return {
                **requests.__json__(self.request),
                **self.render_args(),
            }

        response = {"requests": requests, **self.render_args()}
        return response


@view_config(route_name="directory_ext", request_method="GET", permission="directory.read", extension="json", renderer="json")
@view_config(route_name="directory",     request_method="GET", permission="directory.read", renderer="layout2/directory/index.mako")
class DirectoryIndex(RequestListView):
    def search_args(self):
        return {"for_user": self.request.user}

    def render_args(self):
        return {}


@view_config(route_name="directory_user_ext", request_method="GET", permission="admin", extension="json", renderer="json")
@view_config(route_name="directory_user",     request_method="GET", permission="admin", renderer="layout2/directory/index.mako")
class DirectoryUser(RequestListView):
    def search_args(self):
        return {
            "by_user": self.context,
            "posted_only": False,
        }

    def render_args(self):
        return {}


@view_config(route_name="directory_search",     request_method="GET", permission="directory.read", renderer="layout2/directory/tag_search.mako")
@view_config(route_name="directory_tag_search", request_method="GET", permission="directory.read", renderer="layout2/directory/tag_search.mako")
def directory_search(context, request):
    if request.matched_route.name == "directory_tag_search" and len(context.tags) == 5:
        raise HTTPNotFound

    tag_name = request.GET.get("name", "").strip()[:100].lower()
    if not tag_name:
        return HTTPFound(request.route_path("directory"))

    tags = (
        request.find_service(name="db")
        .query(Tag).filter(func.lower(Tag.name) == tag_name)
    )
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

    tag_query = request.find_service(name="db").query(Tag).filter(
        func.lower(Tag.name)
        .like(request.GET["name"].lower().replace("_", "\\_").replace("%", "\\%") + "%")
    )
    if request.matched_route.name == "directory_tag_search_autocomplete":
        tag_query = tag_query.filter(~Tag.id.in_(_.id for _ in context.tags))
    tag_query = (
        tag_query.options(joinedload(Tag.synonym_of))
        .order_by(Tag.approved.desc(), Tag.name, Tag.type).all()
    )

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
    if current_page < 1:
        raise HTTPNotFound

    db = request.find_service(name="db")
    tag_query = db.query(Tag)
    tag_count_query = db.query(func.count("*")).select_from(Tag)
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
    for tag in request.find_service(name="db").query(Tag).order_by(Tag.name, Tag.type).all():
        if tag.name.lower() != last_tag_name:
            last_tag_name = tag.name.lower()
            rows.append({})
        rows[-1][tag.type] = tag
    return {"rows": rows}


@view_config(route_name="directory_tag",     request_method="GET", permission="directory.read", renderer="layout2/directory/tag.mako")
@view_config(route_name="directory_tag_ext", request_method="GET", permission="directory.read", extension="json", renderer="json")
class DirectoryTag(RequestListView):
    def search_args(self):
        return {
            "for_user": self.request.user,
            "with_tags": self.context.tags,
        }

    def render_args(self):
        return {
            "tags": self.context.tags,
            "blacklisted_tags": self.context.blacklisted_tags,
        }

    def __call__(self):
        if self.context.blacklisted_tags and "for_user" in self.search_args():
            response = self.render_args()
            response["requests"] = []
        else:
            response = super().__call__()

        if len(self.context.tags) == 1:
            tag = self.context.tags[0]

            db = self.request.find_service(name="db")
            all_tag_types = (
                db.query(Tag)
                .filter(func.lower(Tag.name) == tag.name.lower())
                .options(joinedload(Tag.synonym_of))
                .order_by(Tag.type).all()
            )
            response["tag_types"] = [_ for _ in all_tag_types if _.synonym_of not in all_tag_types]

            if "before" not in self.request.GET:
                if self.request.has_permission("directory.manage_tags"):
                    if not tag.approved:
                        response["can_be_approved"] = True
                    response["synonyms"] = (
                        db.query(Tag)
                        .filter(Tag.synonym_id == tag.id)
                        .order_by(Tag.type, Tag.name).all()
                    )
                response["parents"] = (
                    db.query(Tag)
                    .join(TagParent, Tag.id == TagParent.parent_id)
                    .filter(TagParent.child_id == tag.id)
                    .order_by(Tag.type, Tag.name).all()
                )
                response["children"] = (
                    db.query(Tag)
                    .join(TagParent, Tag.id == TagParent.child_id)
                    .filter(TagParent.parent_id == tag.id)
                    .order_by(Tag.type, Tag.name).all()
                )

        return response


@view_config(route_name="directory_tag_approve", request_method="POST", permission="directory.manage_tags")
def directory_tag_approve(context: TagPair, request):
    for tag in context.tags:
        if tag.synonym_id is not None:
            raise HTTPNotFound
        tag.approved = True

    if "Referer" in request.headers:
        return HTTPFound(request.headers["Referer"])
    return HTTPFound(request.route_path("directory_tag", tag_string=request.matchdict["type"] + ":" + request.matchdict["name"]))


@view_config(route_name="directory_tag_suggest", request_method="GET", permission="directory.suggest", renderer="layout2/directory/tag_suggest.mako")
def directory_tag_suggest_get(context: TagPair, request):
    if context.tags[0].type in (TagType.maturity, TagType.type):
        raise HTTPNotFound
    db = request.find_service(name="db")
    return {
        "make_synonym": db.query(TagMakeSynonymSuggestion).filter(and_(
            TagMakeSynonymSuggestion.tag_id  == context.tags[0].id,
            TagMakeSynonymSuggestion.user_id == request.user.id,
        )).options(joinedload(TagMakeSynonymSuggestion.target)).first(),
        "parent_tags": (
            db.query(TagParent)
            .filter(TagParent.child_id == context.tags[0].id)
            .options(joinedload(TagParent.parent)).all()
        ),
        "add_parent": db.query(TagAddParentSuggestion).filter(and_(
            TagAddParentSuggestion.tag_id  == context.tags[0].id,
            TagAddParentSuggestion.user_id == request.user.id,
        )).options(joinedload(TagAddParentSuggestion.target)).all(),
        "set_bump_maturity": db.query(TagBumpMaturitySuggestion).filter(and_(
            TagBumpMaturitySuggestion.tag_id  == context.tags[0].id,
            TagBumpMaturitySuggestion.user_id == request.user.id,
        )).first(),
    }


@view_config(route_name="directory_tag_suggest_make_synonym", request_method="POST", permission="directory.suggest")
def directory_tag_suggest_make_synonym_post(context: TagPair, request):
    if context.tags[0].synonym_id:
        return HTTPFound(request.route_path("directory_tag_suggest", **request.matchdict))

    try:
        new_type = TagType(request.POST["tag_type"]).pair[0]
    except ValueError:
        raise HTTPBadRequest

    new_name = Tag.name_from_url(request.POST["name"]).strip()[:100]
    if not new_name:
        raise HTTPBadRequest

    try:
        tag_service = request.find_service(ITagService)
        tag = tag_service.get_or_create(new_type, new_name, allow_maturity_and_type_creation=False)
    except CreateNotAllowed:
        raise HTTPBadRequest

    db = request.find_service(name="db")
    suggestion = db.query(TagMakeSynonymSuggestion).filter(and_(
        TagMakeSynonymSuggestion.tag_id     == context.tags[0].id,
        TagMakeSynonymSuggestion.user_id    == request.user.id,
        TagMakeSynonymSuggestion.target_id  == tag.id,
    )).first()

    if suggestion and suggestion.target_id != tag.id:
        suggestion.target_id = tag.id
        suggestion.created   = datetime.datetime.now()
    elif not suggestion:
        db.add(TagMakeSynonymSuggestion(
            # Don't mirror these, just use the playing tag.
            tag_id=context.tags[0].id,
            user_id=request.user.id,
            target_id=tag.id,
        ))

    return HTTPFound(request.route_path("directory_tag_suggest", **request.matchdict))


@view_config(route_name="directory_tag_suggest_add_parent", request_method="POST", permission="directory.suggest")
def directory_tag_suggest_add_parent_post(context: TagPair, request):
    try:
        new_type = TagType(request.POST["tag_type"]).pair[0]
    except ValueError:
        raise HTTPBadRequest

    new_name = Tag.name_from_url(request.POST["name"]).strip()[:100]
    if not new_name:
        raise HTTPBadRequest

    try:
        tag_service = request.find_service(ITagService)
        tag = tag_service.get_or_create(new_type, new_name, allow_maturity_and_type_creation=False)
    except CreateNotAllowed:
        raise HTTPBadRequest

    db = request.find_service(name="db")
    if db.query(TagParent).filter(and_(
        TagParent.child_id  == context.tags[0].id,
        TagParent.parent_id == tag.id,
    )).first():
        return HTTPFound(request.route_path("directory_tag_suggest", **request.matchdict))

    suggestion = db.query(TagAddParentSuggestion).filter(and_(
        TagAddParentSuggestion.tag_id     == context.tags[0].id,
        TagAddParentSuggestion.user_id    == request.user.id,
        TagAddParentSuggestion.target_id  == tag.id,
    )).first()

    if suggestion and suggestion.target_id != tag.id:
        suggestion.target_id = tag.id
        suggestion.created   = datetime.datetime.now()
    elif not suggestion:
        db.add(TagAddParentSuggestion(
            # Don't mirror these, just use the playing tag.
            tag_id=context.tags[0].id,
            user_id=request.user.id,
            target_id=tag.id,
        ))

    return HTTPFound(request.route_path("directory_tag_suggest", **request.matchdict))


@view_config(route_name="directory_tag_suggest_bump_maturity", request_method="POST", permission="directory.suggest")
def directory_tag_suggest_bump_maturity_post(context: TagPair, request):
    if context.tags[0].bump_maturity:
        return HTTPFound(request.route_path("directory_tag_suggest", **request.matchdict))

    db = request.find_service(name="db")
    suggestion = db.query(TagBumpMaturitySuggestion).filter(and_(
        TagBumpMaturitySuggestion.tag_id  == context.tags[0].id,
        TagBumpMaturitySuggestion.user_id == request.user.id,
    )).first()

    if not suggestion:
        suggestion = TagBumpMaturitySuggestion(
            # Don't mirror these, just use the playing tag.
            tag_id=context.tags[0].id,
            user_id=request.user.id,
        )
        db.add(suggestion)

    return HTTPFound(request.route_path("directory_tag_suggest", **request.matchdict))


@view_config(route_name="directory_tag_make_synonym", request_method="POST", permission="directory.manage_tags")
def directory_tag_make_synonym(context: TagPair, request):
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
def directory_tag_add_parent(context: TagPair, request):
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
def directory_tag_bump_maturity(context: TagPair, request):
    context.set_bump_maturity(request.POST.get("bump_maturity") == "on")
    return HTTPFound(request.route_path("directory_tag", tag_string=request.matchdict["type"] + ":" + request.matchdict["name"]))


@view_config(route_name="directory_yours",     request_method="GET", permission="directory.read", renderer="layout2/directory/index.mako")
@view_config(route_name="directory_yours_ext", request_method="GET", permission="directory.read", extension="json", renderer="json")
class DirectoryYours(RequestListView):
    def search_args(self):
        return {
            "by_user": self.request.user,
            "posted_only": False,
        }

    def render_args(self):
        return {}


@view_config(route_name="directory_yours_tag", request_method="GET", permission="directory.read", renderer="layout2/directory/tag.mako")
@view_config(route_name="directory_yours_tag_ext", request_method="GET", permission="directory.read", extension="json", renderer="json")
class DirectoryYoursTag(DirectoryTag):
    def search_args(self):
        return {
            # No super() because we don't want to inherit for_user.
            "by_user": self.request.user,
            "with_tags": self.context.tags,
            "posted_only": False,
        }


@view_config(route_name="directory_random", request_method="GET", permission="directory.read", renderer="layout2/directory/lucky_dip_failed.mako")
def directory_random(request):
    request_id = request.find_service(IRequestService).random(for_user=request.user)
    if request_id:
        return HTTPFound(request.route_path("directory_request", id=request_id))
    return {}


@view_config(route_name="directory_new", request_method="GET", permission="directory.new_request", renderer="layout2/directory/new.mako")
def directory_new_get(request):
    if "shutdown.directory" in request.registry.settings:
        raise HTTPNotFound
    return {"form_data": {"fandom_Homestuck": "on", "fandom_wanted_Homestuck": "on"}}


@view_config(route_name="directory_new", request_method="POST", permission="directory.new_request", renderer="layout2/directory/new.mako")
def directory_new_post(request):
    if "shutdown.directory" in request.registry.settings:
        raise HTTPNotFound

    try:
        colour, ooc_notes, starter = _validate_request_form(request)
        slot_name, slot_descriptions = _validate_request_slots(request)
    except ValidationError as e:
        return {"form_data": request.POST, "error": e.message}

    if request.POST.get("status") in ("posted", "locked", "draft"):
        status = request.POST["status"]
    else:
        status = "posted"

    new_date = datetime.datetime.now()

    new_request = Request(
        user_id=request.user.id,
        status=status,
        created=new_date,
        posted=new_date if status == "posted" else None,
        edited=new_date,
        colour=colour,
    )
    default_format = request.user.default_format or request.registry.settings["default_format"]
    new_request.ooc_notes.update(default_format, ooc_notes)
    new_request.starter.update(default_format, starter)
    db = request.find_service(name="db")
    db.add(new_request)
    db.flush()

    request.find_service(IRequestService).remove_duplicates(new_request)

    new_request.request_tags += _request_tags_from_form(request, request.POST, new_request)

    if slot_name and slot_descriptions:
        db.add(RequestSlot(
            request=new_request,
            order=1,
            description=slot_name,
            user_id=request.user.id,
            user_name=slot_name,
        ))
        for order, description in enumerate(slot_descriptions, 2):
            db.add(RequestSlot(request=new_request, order=order, description=description))

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

    tags = request.find_service(name="db").query(Tag).filter(and_(
        Tag.type == tag_type,
        func.lower(Tag.name).like(request.GET["name"].lower().replace("_", "\\_").replace("%", "\\%") + "%")
    )).options(joinedload(Tag.synonym_of)).order_by(Tag.approved.desc(), Tag.name)

    return sorted(list({
        # Use the original name if this tag is a synonym.
        (tag.synonym_of.name if tag.synonym_of else tag.name)
        for tag in tags
        # Exclude tags which are a synonym of another type.
        if not tag.synonym_of or tag.synonym_of.type == tag.type
    }), key=lambda _: _.lower())


def _blacklisted_tags(request, **kwargs):
    db = request.find_service(name="db")
    tags = (
        db.query(Tag).join(BlacklistedTag)
        .filter(BlacklistedTag.user_id == request.user.id)
        .order_by(Tag.type, Tag.name).all()
    )
    return {
        "tags": tags,
        "maturity_tags": [tag for tag in db.query(Tag).filter(Tag.type == TagType.maturity).all() if tag not in tags],
        "type_tags":     [tag for tag in db.query(Tag).filter(Tag.type == TagType.type).all()     if tag not in tags],
        **kwargs
    }


@view_config(route_name="directory_blacklist", request_method="GET",     permission="directory.read", renderer="layout2/directory/blacklist.mako")
@view_config(route_name="directory_blacklist_ext", request_method="GET", permission="directory.read", extension="json", renderer="json")
def directory_blacklist(request):
    return _blacklisted_tags(request)


@view_config(route_name="directory_blacklist_setup", request_method="POST", permission="directory.read")
def directory_blacklist_setup(request):
    if request.user.seen_blacklist_warning:
        return HTTPFound(request.headers.get("Referer") or request.route_path("directory"))

    if request.POST.get("blacklist") not in ("none", "default"):
        raise HTTPBadRequest

    db = request.find_service(name="db")
    if request.POST["blacklist"] == "default":
        db.execute(BlacklistedTag.__table__.insert().from_select(
            ["user_id", "tag_id"],
            db.query(literal(request.user.id), Tag.id).filter(Tag.blacklist_default is True)
        ))
    else:
        request.user.show_nsfw = True

    db.query(User).filter(User.id == request.user.id).update({"seen_blacklist_warning": True})

    return HTTPFound(request.headers.get("Referer") or request.route_path("directory"))


@view_config(route_name="directory_blacklist_add", request_method="POST", permission="directory.read", renderer="layout2/directory/blacklist.mako")
def directory_blacklist_add(request):
    if "shutdown.directory" in request.registry.settings:
        raise HTTPNotFound

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

    db = request.find_service(name="db")

    for name in names.split(","):
        name = Tag.normalise_tag_name(tag_type, name)
        if not name:
            continue

        try:
            tag_service = request.find_service(ITagService)
            tag = tag_service.get_or_create(tag_type, name, allow_maturity_and_type_creation=False)
        except CreateNotAllowed:
            return _blacklisted_tags(request, error="invalid", error_tag_type=tag_type, error_name=name)
        tag_id = (tag.synonym_id or tag.id)

        if db.query(func.count("*")).select_from(BlacklistedTag).filter(and_(
            BlacklistedTag.user_id == request.user.id,
            BlacklistedTag.tag_id == tag_id,
        )).scalar() == 0:
            db.add(BlacklistedTag(user_id=request.user.id, tag_id=tag_id))

    if request.is_xhr:
        return HTTPNoContent()
    return HTTPFound(request.headers.get("Referer") or request.route_path("directory_blacklist"))


@view_config(route_name="directory_blacklist_remove", request_method="POST", permission="directory.read")
def directory_blacklist_remove(request):
    if "shutdown.directory" in request.registry.settings:
        raise HTTPNotFound

    db = request.find_service(name="db")

    try:
        tag = db.query(Tag).filter(Tag.id == request.POST["tag_id"]).one()
    except (KeyError, ValueError, NoResultFound):
        raise HTTPBadRequest

    if tag.type == TagType.maturity and not request.user.show_nsfw and tag.name != "Safe for work":
        raise HTTPBadRequest

    db.query(BlacklistedTag).filter(and_(
        BlacklistedTag.user_id == request.user.id,
        BlacklistedTag.tag_id == request.POST["tag_id"],
    )).delete()

    if request.is_xhr:
        return HTTPNoContent()
    return HTTPFound(request.headers.get("Referer") or request.route_path("directory_blacklist"))


@view_config(route_name="directory_request",     request_method="GET", permission="request.read", renderer="layout2/directory/request.mako")
@view_config(route_name="directory_request_ext", request_method="GET", permission="request.read", extension="json", renderer="json")
def directory_request(context: Request, request):

    db = request.find_service(name="db")
    chats = db.query(ChatUser, Chat).join(Chat).filter(
        ChatUser.user_id == request.user.id,
        ChatUser.status == ChatUserStatus.active,
        Chat.request_id == context.id,
    ).order_by(Chat.updated.desc()).all()

    blacklisted_tags = db.query(Tag).filter(Tag.id.in_(
        db.query(RequestTag.tag_id).filter(RequestTag.request_id == context.id)
        .intersect(db.query(BlacklistedTag.tag_id).filter(BlacklistedTag.user_id == request.user.id))
    )).order_by(Tag.type, Tag.name).all()

    login_store = request.find_service(name="redis_login")
    answered = bool(
        login_store.get("answered:%s:%s" % (request.user.id, context.id))
        or login_store.get("answered:%s:%s" % (request.user.id, context.prompt_hash))
    )

    if request.matched_route.name == "directory_request_ext":
        return {
            "request": context,
            "chats": [{"chat_user": _[0], "chat": _[1]} for _ in chats],
            "blacklisted_tags": blacklisted_tags,
            "answered": answered,
        }

    return {
        "chats": chats,
        "blacklisted_tags": blacklisted_tags,
        "answered": answered,
    }


def _get_current_slot(context: Request, request):
    try:
        order = int(request.GET.get("slot"))
    except (TypeError, ValueError):
        raise HTTPNotFound

    slot = context.slots.by_order(order)
    if not slot:
        raise HTTPNotFound

    if slot.taken:
        raise ValidationError("slot_taken")

    if context.slots.by_user(request.user) is not None:
        raise ValidationError("already_answered")

    return slot


@view_config(route_name="directory_request_answer", request_method="GET", permission="request.answer")
def directory_request_answer_get(context: Request, request):
    if "shutdown.directory" in request.registry.settings:
        raise HTTPNotFound

    if not context.slots:
        raise HTTPNotFound

    try:
        _get_current_slot(context, request)
    except ValidationError as e:
        return _forbidden_response("layout2/directory/%s.mako" % e.message, {}, request)

    return render_to_response("layout2/directory/slot_name.mako", {}, request)


@view_config(route_name="directory_request_answer", request_method="POST", permission="request.answer")
def directory_request_answer_post(context: Request, request):
    if "shutdown.directory" in request.registry.settings:
        raise HTTPNotFound

    login_store = request.find_service(name="redis_login")

    if (
        login_store.get("answered:%s:%s" % (request.user.id, context.id))
        or login_store.get("answered:%s:%s" % (request.user.id, context.prompt_hash))
    ):
        return _forbidden_response("layout2/directory/already_answered.mako", {}, request)

    key = "directory_answer_limit:%s" % request.user.id
    current_time = time.time()
    if login_store.llen(key) >= 12:
        if current_time - float(login_store.lindex(key, 0)) < 3600:
            return render_to_response("layout2/directory/answered_too_many.mako", {}, request)

    if context.slots:
        try:
            current_slot = _get_current_slot(context, request)
        except ValidationError as e:
            return _forbidden_response("layout2/directory/%s.mako" % e.message, {}, request)

        slot_name = request.POST.get("name", "").strip()[:50]
        if not slot_name:
            return render_to_response("layout2/directory/slot_name.mako", {"error": "blank_name"}, request)

        current_slot.user_id   = request.user.id
        current_slot.user_name = slot_name

        if not context.slots.all_taken:
            return HTTPFound(request.route_path("directory_request", id=context.id, _query={"answer_status": "waiting"}))

    login_store.rpush(key, current_time)
    login_store.ltrim(key, -12, -1)
    login_store.expire(key, 3600)

    new_chat = request.find_service(IRequestService).answer(context, request.user)

    return HTTPFound(request.route_path("chat", url=new_chat.url))


@view_config(route_name="directory_request_unanswer", request_method="POST", permission="request.answer")
def directory_request_unanswer_post(context: Request, request):
    if "shutdown.directory" in request.registry.settings:
        raise HTTPNotFound

    if request.user.id == context.user_id:
        raise HTTPNotFound

    slot = context.slots.by_user(request.user)
    if not slot:
        raise HTTPNotFound

    slot.user_id = None
    slot.user_name = None
    return HTTPFound(
        request.headers.get("Referer")
        or request.route_path("directory_request", id=context.id)
    )


@view_config(route_name="directory_request_kick", request_method="POST", permission="request.edit")
def directory_request_kick_post(context: Request, request):
    if "shutdown.directory" in request.registry.settings:
        raise HTTPNotFound

    try:
        order = int(request.POST.get("slot"))
    except (TypeError, ValueError):
        raise HTTPNotFound

    slot = context.slots.by_order(order)
    if slot is None or slot.user_id == request.user.id:
        raise HTTPNotFound

    slot.user_id = None
    slot.user_name = None
    return HTTPFound(
        request.headers.get("Referer")
        or request.route_path("directory_request", id=context.id)
    )


@view_config(route_name="directory_request_edit", request_method="GET", permission="request.edit", renderer="layout2/directory/new.mako")
def directory_request_edit_get(context: Request, request):
    if "shutdown.directory" in request.registry.settings:
        raise HTTPNotFound

    form_data = {
        "colour":    "#" + context.colour,
        "ooc_notes": context.ooc_notes.raw,
        "starter":   context.starter.raw,
        "mode":      "group" if context.slots else "1-on-1",
        "status":    context.status,
    }

    for tag_type, tags in context.tags_by_type().items():
        if tag_type == TagType.maturity:
            if tags: # i don't know why we wouldn't have a maturity but don't IndexError if that does happen
                form_data["maturity"] = tags[0].name
        elif tag_type == TagType.type:
            for tag in tags:
                form_data["type_" + tag.name] = "on"
        else:
            for tag in tags:
                if tag.name in request.registry.settings["checkbox_tags." + tag_type.value]:
                    form_data[tag_type.value + "_" + tag.name] = "on"
            form_data[tag_type.value] = ", ".join(
                tag.name for tag in tags
                if tag.name not in request.registry.settings["checkbox_tags." + tag_type.value]
            )

    for slot in context.slots:
        if slot.order == 1:
            form_data["slot_1_name"] = slot.user_name or ""
        else:
            form_data["slot_%s_description" % slot.order] = slot.description or ""

    return {"form_data": form_data}


@view_config(route_name="directory_request_edit", request_method="POST", permission="request.edit", renderer="layout2/directory/new.mako")
def directory_request_edit_post(context: Request, request):
    if "shutdown.directory" in request.registry.settings:
        raise HTTPNotFound

    try:
        colour, ooc_notes, starter   = _validate_request_form(request)
        slot_name, slot_descriptions = _validate_request_slots(request)
    except ValidationError as e:
        return {"form_data": request.POST, "error": e.message}

    new_date = datetime.datetime.now()
    context.edited = new_date

    if context.status != "removed" and request.POST.get("status") in ("posted", "locked", "draft"):
        if request.POST["status"] == "posted" and context.posted is None:
            context.posted = new_date
        context.status = request.POST["status"]

    context.colour          = colour
    context.ooc_notes       = ooc_notes
    context.starter         = starter
    context.duplicate_of_id = None

    db = request.find_service(name="db")
    db.query(RequestTag).filter(RequestTag.request_id == context.id).delete()

    new_tags = _request_tags_from_form(request, request.POST, context)
    context.request_tags += new_tags
    context.tag_ids = None

    if slot_name and slot_descriptions:
        for order, new_description, existing_slot in zip_longest(range(1, 6), [slot_name] + slot_descriptions, context.slots):
            if new_description and existing_slot:
                existing_slot.order       = order
                existing_slot.description = new_description
                if order == 1:
                    existing_slot.user_name = new_description
                elif context.status == "locked":
                    existing_slot.user_id = None
            elif new_description:
                new_slot = RequestSlot(request=context, order=order, description=new_description)
                if order == 1:
                    new_slot.user_id   = context.user_id
                    new_slot.user_name = new_description
                db.add(new_slot)
            elif existing_slot:
                db.delete(existing_slot)
    else:
        db.query(RequestSlot).filter(RequestSlot.request_id == context.id).delete()

    if context.status == "posted":
        request.find_service(IRequestService).remove_duplicates(context)

    transaction.get().addAfterCommitHook(_trigger_update_request_tag_ids(context.id))

    return HTTPFound(request.route_path("directory_request", id=context.id))


@view_config(route_name="directory_request_delete", request_method="GET", permission="request.delete", renderer="layout2/directory/request_delete.mako")
def directory_request_delete_get(context: Request, request):
    if "shutdown.directory" in request.registry.settings:
        raise HTTPNotFound
    return {}


@view_config(route_name="directory_request_delete", request_method="POST", permission="request.delete")
def directory_request_delete_post(context: Request, request):
    if "shutdown.directory" in request.registry.settings:
        raise HTTPNotFound
    request.find_service(IRequestService).delete(context)
    return HTTPFound(request.route_path("directory_yours"))


@view_config(route_name="directory_request_remove", request_method="POST", permission="request.remove")
def directory_request_remove(context: Request, request):
    context.status = "removed"
    return HTTPFound(request.headers.get("Referer") or request.route_path("directory_request", id=context.id))


@view_config(route_name="directory_request_unremove", request_method="POST", permission="request.remove")
def directory_request_unremove(context: Request, request):
    context.status = "draft"
    return HTTPFound(request.headers.get("Referer") or request.route_path("directory_request", id=context.id))

