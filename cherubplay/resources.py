import transaction

from collections import OrderedDict
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.security import Allow, Everyone
from sqlalchemy import and_, func, or_, Integer
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import contains_eager, joinedload
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import cast

from cherubplay.models import (
    Session, BlacklistedTag, Chat, ChatUser, Message, Prompt, PromptReport,
    Request, RequestTag, Resource, Tag, TagParent, TagAddParentSuggestion,
    TagBumpMaturitySuggestion, TagMakeSynonymSuggestion, Tag, User,
)
from cherubplay.models.enums import ChatUserStatus, TagType
from cherubplay.tasks import update_missing_request_tag_ids


class ChatContext(object):
    __parent__ = Resource

    @reify
    def __acl__(self):
        acl = [
            (Allow, Everyone, "chat.read"),
            (Allow, "admin",  "chat.read_ooc"),
            (Allow, "admin",  "chat.full_user_list"),
        ]
        if self.chat_user:
            acl += [
                (Allow, self.chat_user.user_id, "chat.read_ooc"),
                (Allow, self.chat_user.user_id, "chat.info"),
            ]
        if self.chat_user and self.chat.status == "ongoing":
            acl += [
                (Allow, "active",        "chat.send"),
                (Allow, "active",        "chat.change_name"),
                (Allow, self.chat.op_id, "chat.remove_user"),
            ]
        return acl

    def __init__(self, request):
        self.request = request
        try:
            if request.user:
                self.chat, self.chat_user = Session.query(Chat, ChatUser).filter(
                    Chat.url == request.matchdict["url"],
                ).outerjoin(ChatUser, and_(
                    ChatUser.chat_id == Chat.id,
                    ChatUser.user_id == request.user.id,
                    ChatUser.status == ChatUserStatus.active,
                )).one()
            else:
                self.chat = Session.query(Chat).filter(Chat.url == request.matchdict["url"]).one()
                self.chat_user = None
        except NoResultFound:
            raise HTTPNotFound

    def __repr__(self):
        if self.chat_user:
            return "<ChatContext: User #%s in Chat %s>" % (self.chat_user.user_id, self.chat.id)
        return "<ChatContext: guest in Chat %s>" % self.chat.id

    @reify
    def is_continuable(self):
        return self.chat.status == "ongoing" and self.request.has_permission("chat.send")

    @reify
    def chat_users(self):
        return OrderedDict([
            (chat_user.user_id, chat_user)
            for chat_user in Session.query(ChatUser).join(User).filter(and_(
                ChatUser.chat_id == self.chat.id,
            )).options(contains_eager(ChatUser.user)).order_by(ChatUser.name).all()
        ])

    @reify
    def active_chat_users(self):
        return [
            _ for _ in self.chat_users.values()
            if _.status == ChatUserStatus.active
        ]

    @reify
    def banned_chat_users(self):
        return [
            _ for _ in self.chat_users.values()
            if _.status == ChatUserStatus.active
            and _.user.status == "banned"
        ]

    @reify
    def away_chat_users(self):
        return [
            _ for _ in self.chat_users.values()
            if _.status == ChatUserStatus.active
            and _.user.away_message
        ]


def prompt_factory(request):
    if not request.user:
        raise HTTPNotFound

    try:
        db = request.find_service(name="db")
        return db.query(Prompt).filter(and_(
            Prompt.user_id == request.user.id,
            Prompt.id == int(request.matchdict["id"]),
        )).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound


def report_factory(request):
    try:
        db = request.find_service(name="db")
        return db.query(PromptReport).filter(
            PromptReport.id == int(request.matchdict["id"])
        ).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound


class TagList(object):
    __parent__ = Resource

    def __init__(self, request):
        if not request.user:
            raise HTTPNotFound

        tag_filters = []

        split_tag_string = request.matchdict["tag_string"].split(",")[:5]
        for pair in split_tag_string:
            try:
                tag_type_string, name = pair.split(":")
            except ValueError:
                raise HTTPNotFound
            try:
                tag_type = TagType(tag_type_string)
            except ValueError:
                raise HTTPNotFound

            tag_filters.append(and_(
                Tag.type == tag_type,
                func.lower(Tag.name) == Tag.name_from_url(name.strip().lower()),
            ))

        self.tags = [
            tag.synonym_of or tag for tag in
            Session.query(Tag).filter(or_(*tag_filters))
            .options(joinedload(Tag.synonym_of))
            .order_by(Tag.type, Tag.name)
        ]

        if len(self.tags) < len(split_tag_string):
            # One or more tags don't exist, so there won't be any results here.
            raise HTTPNotFound

        actual_tag_string = ",".join(tag.tag_string for tag in self.tags)
        if actual_tag_string != request.matchdict["tag_string"]:
            raise HTTPFound(request.current_route_path(tag_string=actual_tag_string))

        self.blacklisted_tags = [
            _.tag for _ in
            Session.query(BlacklistedTag)
            .filter(and_(
                BlacklistedTag.user_id == request.user.id,
                BlacklistedTag.tag_id.in_(tag.id for tag in self.tags),
            )).all()
        ]

        self.tag_array = cast([tag.id for tag in self.tags], ARRAY(Integer))

    def tag_string_plus(self, extra_tag):
        tag_list = list(self.tags)
        tag_list.append(extra_tag)
        tag_list.sort(key=lambda tag: (Tag.type, Tag.name))
        return ",".join(tag.tag_string for tag in tag_list)


class CircularReferenceException(Exception): pass


def _trigger_update_missing_request_tag_ids(status):
    if not status:
        return
    update_missing_request_tag_ids.delay()


class TagPair(object):
    __parent__ = Resource

    def __init__(self, first_tag: Tag, **kwargs):
        self.tags = [
            first_tag if first_tag.type == pair_tag_type
            else Tag.get_or_create(pair_tag_type, first_tag.name, **kwargs)
            for pair_tag_type in first_tag.type.pair
        ]

    @classmethod
    def from_tag_name(cls, tag_type: TagType, tag_name: str, **kwargs):
        return cls(Tag.get_or_create(tag_type, tag_name, **kwargs))

    @classmethod
    def from_request(cls, request):
        try:
            request_tag_type = TagType(request.matchdict["type"])
        except ValueError:
            raise HTTPNotFound
        tag_name = Tag.name_from_url(request.matchdict["name"])
        return cls.from_tag_name(request_tag_type, tag_name)

    def set_bump_maturity(self, value: bool):
        for tag in self.tags:
            tag.bump_maturity = value

            if value:
                Session.query(RequestTag).filter(and_(
                    RequestTag.request_id.in_(
                        Session.query(RequestTag.request_id)
                        .filter(RequestTag.tag_id == tag.id)
                    ),
                    RequestTag.tag_id.in_(
                        Session.query(Tag.id).filter(and_(
                            Tag.type == TagType.maturity,
                            Tag.name.in_(("Safe for work", "Not safe for work")),
                        ))
                    ),
                )).update({"tag_id": Session.query(Tag.id).filter(and_(
                    Tag.type == TagType.maturity,
                    Tag.name == "NSFW extreme",
                )).as_scalar()}, synchronize_session=False)

                Session.query(Request).filter(and_(
                    Request.id.in_(
                        Session.query(RequestTag.request_id)
                        .filter(RequestTag.tag_id == tag.id)
                    ),
                )).update({"tag_ids": None}, synchronize_session=False)

        transaction.get().addAfterCommitHook(_trigger_update_missing_request_tag_ids)

    def make_synonym(self, new_type: TagType, new_name: str):
        new_types = new_type.pair

        # If one set of types is a pair and the other isn't, double them up.
        if len(self.tags) < len(new_types):
            self.tags = self.tags * 2
        elif len(self.tags) > len(new_types):
            new_types = new_types * 2

        for old_tag, new_type in zip(self.tags, new_types):
            # A tag can't be made a synonym if it's already a synonym.
            if old_tag.synonym_id:
                raise ValueError("tag %s is already a synonym" % old_tag)
            # A tag can't be a synonym if it has synonyms.
            if Session.query(func.count("*")).select_from(Tag).filter(Tag.synonym_id == old_tag.id).scalar():
                raise ValueError("tag %s has synonyms" % old_tag)

            new_tag = Tag.get_or_create(new_type, new_name)

            if old_tag.id == new_tag.id:
                raise ValueError("can't synonym tag %s to itself" % old_tag)

            new_tag.approved = True
            old_tag.synonym_id = new_tag.id

            # Bump maturity if necessary.
            if new_tag.bump_maturity and not old_tag.bump_maturity:
                Session.query(RequestTag).filter(and_(
                    RequestTag.request_id.in_(
                        Session.query(RequestTag.request_id)
                        .filter(RequestTag.tag_id == old_tag.id)
                    ),
                    RequestTag.tag_id.in_(
                        Session.query(Tag.id).filter(and_(
                            Tag.type == TagType.maturity,
                            Tag.name.in_(("Safe for work", "Not safe for work")),
                        ))
                    ),
                )).update({"tag_id": Session.query(Tag.id).filter(and_(
                    Tag.type == TagType.maturity,
                    Tag.name == "NSFW extreme",
                )).as_scalar()}, synchronize_session=False)

            # Delete the old tag from reqests which already have the new tag.
            Session.query(RequestTag).filter(and_(
                RequestTag.tag_id == old_tag.id,
                RequestTag.request_id.in_(Session.query(RequestTag.request_id).filter(RequestTag.tag_id == new_tag.id)),
            )).delete(synchronize_session=False)
            # And update the rest.
            Session.query(RequestTag).filter(RequestTag.tag_id == old_tag.id).update({"tag_id": new_tag.id})

            # Null the tag_ids arrays.
            Session.query(Request).filter(
                Request.tag_ids.contains(cast([old_tag.id, new_tag.id], ARRAY(Integer)))
            ).update({"tag_ids": None}, synchronize_session=False)
            Session.query(Request).filter(
                Request.tag_ids.contains(cast([old_tag.id], ARRAY(Integer)))
            ).update({"tag_ids": None}, synchronize_session=False)

            # Delete the old tag from blacklists which already have the new tag.
            Session.query(BlacklistedTag).filter(and_(
                BlacklistedTag.tag_id == old_tag.id,
                BlacklistedTag.user_id.in_(
                    Session.query(BlacklistedTag.user_id).filter(BlacklistedTag.tag_id == new_tag.id)),
            )).delete(synchronize_session=False)
            # And update the rest.
            Session.query(BlacklistedTag).filter(BlacklistedTag.tag_id == old_tag.id).update({"tag_id": new_tag.id})

        transaction.get().addAfterCommitHook(_trigger_update_missing_request_tag_ids)

    def add_parent(self, parent_type: TagType, parent_name: str):
        parent_types = parent_type.pair

        # If one set of types is a pair and the other isn't, double them up.
        if len(self.tags) < len(parent_types):
            self.tags = self.tags * 2
        elif len(self.tags) > len(parent_types):
            parent_types = parent_types * 2

        for child_tag, parent_type in zip(self.tags, parent_types):
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
                raise CircularReferenceException

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

        transaction.get().addAfterCommitHook(_trigger_update_missing_request_tag_ids)

    def apply_suggestion(self, suggestion):
        if type(suggestion) == TagMakeSynonymSuggestion:
            return self.make_synonym(suggestion.target.type, suggestion.target.name)
        if type(suggestion) == TagAddParentSuggestion:
            return self.add_parent(suggestion.target.type, suggestion.target.name)
        if type(suggestion) == TagBumpMaturitySuggestion:
            return self.set_bump_maturity(True)


def request_factory(request):
    if not request.user:
        raise HTTPNotFound

    try:
        query = Session.query(Request).filter(Request.id == int(request.matchdict["id"]))
        if request.user.status != "admin":
            query = query.filter(or_(
                request.user.tag_status_filter,
                Request.user_id == request.user.id,
            ))
        return query.options(joinedload(Request.tags)).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound


def user_factory(request):
    try:
        db = request.find_service(name="db")
        return db.query(User).filter(User.username == request.matchdict["username"]).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound
