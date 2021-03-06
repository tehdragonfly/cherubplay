# -*- coding: utf-8 -*-

import datetime
import os.path
import zope.sqlalchemy

from bcrypt import checkpw, gensalt, hashpw
from pyramid.decorator import reify
from pyramid.security import Allow, Authenticated, Deny
from pytz import timezone, utc

from sqlalchemy import (
    engine_from_config,
    and_,
    func,
    Column,
    ForeignKey,
    Index,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SQLAlchemyEnum,
    Integer,
    String,
    Unicode,
    UnicodeText,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (
    configure_mappers,
    relationship,
    sessionmaker,
    object_session,
    foreign,
)
from sqlalchemy_enum34 import EnumType
from zope.sqlalchemy import ZopeTransactionExtension

from cherubplay.lib import prompt_hash, symbols, trim_with_ellipsis
from cherubplay.lib.formatters import FormattedField
from cherubplay.models.enums import ChatMode, ChatSource, ChatUserStatus, MessageFormat, MessageType, TagType

Base = declarative_base()


class Resource(object):
    __acl__ = (
        (Allow, Authenticated, "view"),
        (Allow, "active",      "chat"),
        (Allow, "admin",       "admin"),
        (Allow, Authenticated, "directory.read"),
        (Allow, "active",      "directory.new_request"),
        (Allow, "active",      "directory.suggest"),
        (Allow, "admin",       "directory.manage_tags"),
    )


class User(Base):
    __parent__ = Resource
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(Unicode(100), nullable=False, unique=True)
    password = Column(String(60), nullable=False)
    status = Column(SQLAlchemyEnum(u"active", u"banned", u"admin", name="user_status"), nullable=False, default=u"active")
    email = Column(Unicode(255))
    created = Column(DateTime, nullable=False, default=datetime.datetime.now)
    last_online = Column(DateTime, nullable=False, default=datetime.datetime.now)
    last_ip = Column(String(40))
    unban_date = Column(DateTime)
    layout_version = Column(Integer, nullable=False, default=2)
    timezone = Column(Unicode(255))
    seen_blacklist_warning = Column(Boolean, nullable=False, default=False)
    show_nsfw = Column(Boolean)
    last_read_news = Column(DateTime)
    away_message = Column(Unicode(255))
    flags = Column(ARRAY(Unicode(500)), nullable=False, default=list)
    default_request_order = Column(SQLAlchemyEnum(
        u"posted", u"edited", u"posted_oldest", u"edited_oldest",
        name="user_default_request_order",
    ), nullable=False, default=u"posted")
    default_format = Column(EnumType(MessageFormat, name=u"message_format"))

    def __repr__(self):
        return "<User #%s: %s>" % (self.id, self.username)

    @reify
    def blacklist_filter(self):
        db = object_session(self)
        if db.query(BlacklistedTag).filter(BlacklistedTag.user_id == self.id).first() is None:
            return None
        return ~Request.tag_ids.overlap(
            db.query(func.array_agg(BlacklistedTag.tag_id))
            .filter(BlacklistedTag.user_id == self.id)
        )

    @property
    def unban_delta(self):
        return self.unban_date - datetime.datetime.now()

    def localise_time(self, input_datetime):
        utc_datetime = utc.localize(input_datetime)
        if self.timezone is None:
            return utc_datetime
        return utc_datetime.astimezone(timezone(self.timezone))

    def check_password(self, password):
        return checkpw(password.encode(), self.password.encode())

    def set_password(self, new_password):
        self.password = hashpw(new_password.encode(), gensalt()).decode()


class UserExport(Base):
    __tablename__ = "user_exports"
    __table_args__ = (
        CheckConstraint("""
            (generated is not null) = (expires is not null)
            and (generated is not null) = (filename is not null)
        """),
    )
    user_id        = Column(Integer, ForeignKey("users.id"), primary_key=True)
    celery_task_id = Column(UUID, nullable=False)
    triggered      = Column(DateTime, nullable=False, default=datetime.datetime.now)
    generated      = Column(DateTime)
    expires        = Column(DateTime)
    filename       = Column(Unicode(100))

    @property
    def file_directory(self):
        return os.path.join("user", self.celery_task_id)

    @property
    def file_path(self):
        if self.filename:
            return os.path.join(self.file_directory, self.filename)

    def __json__(self, request=None):
        return {
            "task_id": self.celery_task_id,
            "generated": self.generated,
            "expires": self.expires,
            "filename": self.filename,
            "file_path": self.file_path,
        }


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    data = Column(JSONB(), nullable=False)


class Chat(Base):
    __tablename__ = "chats"
    id           = Column(Integer, primary_key=True)
    url          = Column(Unicode(100), nullable=False, unique=True)
    mode         = Column(EnumType(ChatMode, name=u"chat_mode"), nullable=False, default=ChatMode.one_on_one)
    status       = Column(SQLAlchemyEnum(u"ongoing", u"ended", name="chat_status"), nullable=False, default=u"ongoing")
    created      = Column(DateTime, nullable=False, default=datetime.datetime.now)
    updated      = Column(DateTime, nullable=False, default=datetime.datetime.now)
    last_user_id = Column(Integer, ForeignKey("users.id"))
    request_id   = Column(Integer, ForeignKey("requests.id"))
    op_id        = Column(Integer, ForeignKey("users.id"))
    source       = Column(EnumType(ChatSource, name="chat_source"))

    def __repr__(self):
        return "<Chat #%s: %s>" % (self.id, self.url)

    def __json__(self, request=None):
        return {
            "url": self.url,
            "mode": self.mode,
            "status": self.status,
            "created": self.created,
            "updated": self.updated,
        }


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    # System messages don't have a user ID, and we may also need to set it to null if a user is deleted.
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(EnumType(MessageType, name=u"message_type"), nullable=False, default=MessageType.ic)
    colour = Column(String(6), nullable=False, default="000000")
    symbol = Column(Integer)
    _format = Column("format", EnumType(MessageFormat, name=u"message_format"), nullable=False, default=MessageFormat.raw)
    _text = Column("text", UnicodeText, nullable=False)
    text = FormattedField("_format", "_text")
    posted = Column(DateTime, nullable=False, default=datetime.datetime.now)
    edited = Column(DateTime, nullable=False, default=datetime.datetime.now)

    def __repr__(self):
        return "<Message #%s: \"%s\">" % (self.id, trim_with_ellipsis(self.text.as_plain_text(), 37))

    def __json__(self, request=None):
        return {
            "id": self.id,
            "type": self.type,
            "colour": self.colour,
            "symbol": self.symbol,
            "symbol_character": self.symbol_character,
            "handle": self.handle,
            "text": self.text,
            "posted": self.posted,
            "edited": self.edited,
            "show_edited": self.show_edited,
        }

    @property
    def show_edited(self):
        return self.edited - self.posted >= datetime.timedelta(0, 300)

    @property
    def symbol_character(self):
        return symbols[self.symbol] if self.symbol is not None else None

    @property
    def handle(self):
        if self.symbol_character:
            return self.symbol_character
        if self.user_id and self.chat_user:
            return self.chat_user.handle


class ChatUser(Base):
    __tablename__ = "chat_users"
    __table_args__ = (
        UniqueConstraint("chat_id", "symbol", name="chat_user_symbol_unique"),
        CheckConstraint("(symbol is not null) != (name is not null)", name="chat_user_symbol_or_name"),
    )
    chat_id = Column(Integer, ForeignKey("chats.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    last_colour = Column(String(6), nullable=False, default="000000")
    symbol = Column(Integer)
    name = Column(Unicode(50))
    visited = Column(DateTime, nullable=False, default=datetime.datetime.now)
    status = Column(EnumType(ChatUserStatus, name=u"chat_user_status"), nullable=False, default=ChatUserStatus.active)
    title = Column(Unicode(100), nullable=False, default=u"")
    notes = Column(UnicodeText, nullable=False, default=u"")
    labels = Column(ARRAY(Unicode(500)), nullable=False, default=list)
    draft = Column(UnicodeText, nullable=False, default=u"")

    def __repr__(self):
        return "<ChatUser: Chat #%s, User #%s>" % (self.chat_id, self.user_id)

    def __json__(self, request=None):
        return {
            "last_colour": self.last_colour,
            "symbol": self.symbol,
            "symbol_character": self.symbol_character,
            "name": self.name,
            "visited": self.visited,
            "title": self.title,
            "notes": self.notes,
            "labels": self.labels,
            "draft": self.draft,
        }

    @property
    def display_title(self):
        return self.title or self.chat.url

    @property
    def symbol_character(self):
        return symbols[self.symbol] if self.symbol is not None else None

    @property
    def handle(self):
        return self.symbol_character or self.name


class ChatExport(Base):
    __tablename__ = "chat_exports"
    __table_args__ = (
        CheckConstraint("""
            (generated is not null) = (expires is not null)
            and (generated is not null) = (filename is not null)
        """),
    )
    chat_id        = Column(Integer, ForeignKey("chats.id"), primary_key=True)
    user_id        = Column(Integer, ForeignKey("users.id"), primary_key=True)
    celery_task_id = Column(UUID, nullable=False)
    triggered      = Column(DateTime, nullable=False, default=datetime.datetime.now)
    generated      = Column(DateTime)
    expires        = Column(DateTime)
    filename       = Column(Unicode(100))

    @property
    def file_directory(self):
        return os.path.join(self.chat.url, self.celery_task_id)

    @property
    def file_path(self):
        if self.filename:
            return os.path.join(self.file_directory, self.filename)

    def __json__(self, request=None):
        return {
            "task_id": self.celery_task_id,
            "generated": self.generated,
            "expires": self.expires,
            "filename": self.filename,
            "file_path": self.file_path,
        }


class PromptReport(Base, Resource):
    __tablename__ = "prompt_reports"
    id = Column(Integer, primary_key=True)
    status = Column(SQLAlchemyEnum(
        u"open",
        u"closed",
        u"invalid",
        u"duplicate",
        name="prompt_report_status",
    ), nullable=False, default=u"open")
    duplicate_of_id = Column(Integer, ForeignKey("prompt_reports.id"), nullable=True)
    reporting_user_id = Column(Integer, ForeignKey("users.id"))
    reported_user_id = Column(Integer, ForeignKey("users.id"))
    created = Column(DateTime, nullable=False, default=datetime.datetime.now)
    colour = Column(String(6), nullable=False)
    prompt = Column(UnicodeText, nullable=False)
    category = Column(Unicode(100), nullable=False)
    starter = Column(Unicode(100))
    level = Column(Unicode(100), nullable=False)
    reason = Column(SQLAlchemyEnum(
        u"wrong_category",
        u"spam",
        u"stolen",
        u"multiple",
        u"advert",
        u"ooc",
        name="prompt_report_reason",
    ), nullable=False)
    reason_category = Column(Unicode(100))
    reason_starter = Column(Unicode(100))
    reason_level = Column(Unicode(100))
    chat_ids = Column(ARRAY(Integer), nullable=False, default=list)
    notes = Column(UnicodeText, nullable=False, default=u"")

    def __json__(self, request=None):
        return {
            "id": self.id,
            "status": self.status,
            "created": self.created,
            "colour": self.colour,
            "prompt": self.prompt,
            "category": self.category,
            "starter": self.starter,
            "level": self.level,
            "reason": self.reason,
            "reason_category": self.reason_category,
            "reason_starter": self.reason_starter,
            "reason_level": self.reason_level,
            "notes": self.notes,
        }


class Prompt(Base):
    def __acl__(self):
        return (
            (Allow, self.user_id, "prompt.read"),
            (Allow, self.user_id, "prompt.edit"),
            (Allow, self.user_id, "prompt.delete"),
        )

    __tablename__ = "prompts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(Unicode(100), nullable=False, default=u"")
    created = Column(DateTime, nullable=False, default=datetime.datetime.now)
    updated = Column(DateTime, nullable=False, default=datetime.datetime.now)
    colour = Column(String(6), nullable=False)
    _format = Column("format", EnumType(MessageFormat, name=u"message_format"), nullable=False, default=MessageFormat.raw)
    _text = Column("text", UnicodeText, nullable=False)
    text = FormattedField("_format", "_text")
    category = Column(Unicode(100))
    starter = Column(Unicode(100), nullable=False)
    level = Column(Unicode(100), nullable=False)

    def __repr__(self):
        return "<Prompt #%s: %s>" % (self.id, self.title)

    @property
    def prompt_hash(self):
        return prompt_hash(self.text.as_plain_text())

    def __json__(self, request=None):
        return {
            "id": self.id,
            "title": self.title,
            "created": self.created,
            "updated": self.updated,
            "colour": self.colour,
            "text": self.text,
            "category": self.category,
            "starter": self.starter,
            "level": self.level,
        }


class Request(Base):
    __parent__ = Resource

    def __acl__(self):
        acl = [
            (Allow, self.user_id, "request.read"),
            (Deny,  self.user_id, "request.answer"),
            (Deny,  "banned",     "request.edit"),
            (Allow, self.user_id, "request.edit"),
            (Allow, self.user_id, "request.delete"),
            (Allow, "admin",      "request.remove"),
        ]
        if self.status in ("posted", "locked"):
            acl.append((Allow, Authenticated, "request.read"))
        else:
            acl.append((Allow, "admin", "request.read"))
        if self.status == "posted":
            acl.append((Allow, "active", "request.answer"))
        elif self.status == "removed":
            acl.append((Allow, "admin", "request.answer"))
        return acl

    __tablename__ = "requests"
    __table_args__ = (
        CheckConstraint("(posted IS NOT NULL) or (status = 'draft')", name="requests_posted"),
    )
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(SQLAlchemyEnum(u"draft", u"locked", u"posted", u"removed", name=u"requests_status"), nullable=False, default=u"draft")
    lock_after_answers = Column(Integer)
    # Created indicates when the request was created, and is never modified.
    created = Column(DateTime(), nullable=False, default=datetime.datetime.now)
    # Posted indicates when the request was first posted.
    # It's set when the status is first set to "posted". This may be the same as the created time
    # if posted directly, or when it was changed from "draft" to "posted".
    posted = Column(DateTime())
    # Edited indicates when the request was last edited.
    edited = Column(DateTime(), nullable=False, default=datetime.datetime.now)
    colour = Column(Unicode(6), nullable=False, default=u"000000")
    _format = Column("format", EnumType(MessageFormat, name=u"message_format"), nullable=False, default=MessageFormat.raw)
    _ooc_notes = Column("ooc_notes", UnicodeText, nullable=False, default=u"")
    ooc_notes = FormattedField("_format", "_ooc_notes")
    _starter = Column("starter", UnicodeText, nullable=False, default=u"")
    starter = FormattedField("_format", "_starter")
    # This stores a copy of the relevant values from RequestTags.tag_id.
    # It was created to make tag searching easier but was probably a premature
    # optimisation.
    tag_ids = Column(ARRAY(Integer))
    duplicate_of_id = Column(Integer, ForeignKey("requests.id"))

    def __repr__(self):
        return "<Request #%s>" % self.id

    @property
    def prompt_hash(self):
        return prompt_hash(self.ooc_notes.as_plain_text() + self.starter.as_plain_text())

    def tags_by_type(self):
        tags = {_: [] for _ in Tag.type.type.python_type}
        for tag in self.tags:
            tags[tag.type].append(tag)
        return tags

    def __json__(self, request=None):
        rd = {
            "id": self.id,
            "status": self.status,
            "posted": self.posted or self.created,
            "edited": self.edited,
            "colour": self.colour,
            "ooc_notes": self.ooc_notes,
            "starter": self.starter,
            # Gotta have string keys.
            "tags": {k.value: v for k, v in self.tags_by_type().items()},
            "slots": self.slots,
        }
        if request is not None and request.user is not None:
            rd["yours"] = request.user.id == self.user_id
        return rd


class SlotList(list):
    def by_order(self, order: int):
        for slot in self:
            if slot.order == order:
                return slot

    def by_user(self, user: User):
        return self.by_user_id(user.id)

    def by_user_id(self, user_id: int):
        for slot in self:
            if slot.user_id == user_id:
                return slot

    @property
    def all_taken(self):
        return all(slot.taken for slot in self)

    def __json__(self, request=None):
        return list(self)


class RequestSlot(Base):
    __tablename__ = "request_slots"
    __table_args__ = (
        UniqueConstraint("request_id", "user_id", name="request_slots_request_id_user_id_idx"),
        # Slot 1 always belongs to the prompter and can't be empty.
        CheckConstraint("user_id IS NOT NULL OR \"order\" <> 1", name="request_slots_slot_1_taken"),
        CheckConstraint("(user_id IS NOT NULL) = (user_name IS NOT NULL)", name="request_slots_user_id_match"),
    )
    request_id = Column(Integer, ForeignKey("requests.id"), primary_key=True)
    order = Column(Integer, primary_key=True)
    description = Column(Unicode(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    user_name = Column(Unicode(50))

    def __repr__(self):
        return "<RequestSlot: Request #%s, slot #%s>" % (self.request_id, self.order)

    @property
    def taken(self):
        return self.user_id is not None

    def __json__(self, request=None):
        data = {
            "order": self.order,
            "description": self.description,
            "user_name": self.user_name,
            "taken": self.taken,
        }
        if request and request.user:
            data["taken_by_you"] = self.user_id == request.user.id
        return data


class RequestTag(Base):
    __tablename__ = "request_tags"
    request_id = Column(Integer, ForeignKey("requests.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)

    def __repr__(self):
        return "<RequestTag: Request #%s, Tag #%s>" % (self.request_id, self.tag_id)

    def __json__(self, request=None):
        return self.tag.__json__(request)


class BlacklistedTag(Base):
    __tablename__ = "blacklisted_tags"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)

    def __repr__(self):
        return "<BlacklistedTag: User #%s, Tag #%s>" % (self.user_id, self.tag_id)

    def __json__(self, request=None):
        return self.tag.__json__(request)


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    type              = Column(EnumType(TagType, name=u"tags_type"), nullable=False, default=u"misc")
    name              = Column(Unicode(100), nullable=False)
    synonym_id        = Column(Integer, ForeignKey("tags.id"))
    approved          = Column(Boolean, nullable=False, default=False)
    blacklist_default = Column(Boolean, nullable=False, default=False)
    bump_maturity     = Column(Boolean, nullable=False, default=False)

    maturity_names = [u"Safe for work", u"Not safe for work", u"NSFW extreme"]
    type_names = [u"Fluff", u"Plot-driven", u"Sexual", u"Shippy", u"Violent", u"Missed connection"]

    def __repr__(self):
        return "<Tag #%s: %s:%s>" % (self.id, self.type.value, self.name)

    @staticmethod
    def name_from_url(url):
        return url.replace("*s*", "/").replace("*c*", ":").replace("_", " ")

    @staticmethod
    def normalise_tag_name(tag_type: TagType, name):
        name = Tag.name_from_url(name).strip()
        if tag_type == TagType.warning and name.lower().startswith("tw:"):
            name = name[3:].strip()
        elif name.startswith("#"):
            name = name[1:].strip()
        return name[:100]

    @reify
    def url_name(self):
        return self.name.replace("/", "*s*").replace(":", "*c*").replace(" ", "_")

    @reify
    def tag_string(self):
        return ":".join((self.type.value, self.url_name))

    def __json__(self, request=None):
        tag_dict = {
            "type": self.type,
            "name": self.name,
            "url_name": self.url_name,
        }
        if request and request.user and request.has_permission("directory.manage_tags"):
            tag_dict.update({
                "approved": self.approved,
                "blacklist_default": self.blacklist_default,
                "bump_maturity": self.bump_maturity,
            })
        return tag_dict


class TagParent(Base):
    __tablename__ = "tag_parents"
    child_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)
    parent_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)

    def __repr__(self):
        return "<TagParent: Child #%s, Parent #%s>" % (self.child_id, self.parent_id)


class TagMakeSynonymSuggestion(Base):
    __tablename__ = "tag_make_synonym_suggestions"
    tag_id  = Column(Integer, ForeignKey("tags.id"),  primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    target_id = Column(Integer, ForeignKey("tags.id"))
    created = Column(DateTime, nullable=False, default=datetime.datetime.now)

    def __repr__(self):
        return "<TagMakeSynonymSuggestion: Tag #%s, Target %s>" % (self.tag_id, self.target_id)


class TagAddParentSuggestion(Base):
    __tablename__ = "tag_add_parent_suggestions"
    id = Column(Integer, primary_key=True)
    tag_id  = Column(Integer, ForeignKey("tags.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    target_id = Column(Integer, ForeignKey("tags.id"))
    created = Column(DateTime, nullable=False, default=datetime.datetime.now)

    def __repr__(self):
        return "<TagAddParentSuggestion #%s: Tag #%s, Target %s>" % (self.id, self.tag_id, self.target_id)


class TagBumpMaturitySuggestion(Base):
    __tablename__ = "tag_bump_maturity_suggestions"
    tag_id = Column(Integer, ForeignKey("tags.id"),  primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    created = Column(DateTime, nullable=False, default=datetime.datetime.now)

    def __repr__(self):
        return "<TagBumpMaturitySuggestion: Tag #%s>" % self.tag_id


class BaseUserConnection(object):
    def __acl__(self):
        if self.is_mutual:
            return (
                (Allow, self.from_id, "user_connection.chat"),
                (Allow, self.from_id, "user_connection.delete"),
            )
        return (
            (Allow, self.from_id, "user_connection.delete"),
        )

    @property
    def from_id(self): raise NotImplementedError

    @property
    def to_username(self): raise NotImplementedError

    @property
    def is_mutual(self): raise NotImplementedError

    def __json__(self, request=None):
        return {
            "to": self.to_username,
            "is_mutual": self.is_mutual,
        }


class UserConnection(BaseUserConnection, Base):
    __tablename__ = "user_connections"
    from_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    to_id   = Column(Integer, ForeignKey("users.id"), primary_key=True)

    @property
    def to_username(self):
        return self.to.username

    @property
    def is_mutual(self):
        return self.reverse is not None

    def __repr__(self):
        return "<UserConnection: #%s to #%s>" % (self.from_id, self.to_id)


class VirtualUserConnection(BaseUserConnection, Base):
    """
    Placeholder for connections where the username of a non-existent user was
    entered.
    """
    __tablename__ = "virtual_user_connections"
    from_id     = Column(Integer, ForeignKey("users.id"), primary_key=True)
    to_id       = None
    to_username = Column(Unicode(100), primary_key=True)
    is_mutual   = False

    def __repr__(self):
        return "<VirtualUserConnection: #%s to %s>" % (self.from_id, self.to_username)


PushSubscription.user = relationship(User, backref="push_subscriptions")

Chat.last_user = relationship(User, foreign_keys=Chat.last_user_id)
Chat.op        = relationship(User, foreign_keys=Chat.op_id)
Chat.request   = relationship(Request)

Message.chat = relationship(Chat, backref="messages")
Message.user = relationship(User, backref="messages")
Message.chat_user = relationship(
    ChatUser,
    primaryjoin=and_(Message.chat_id == ChatUser.chat_id, Message.user_id == ChatUser.user_id),
    foreign_keys=[Message.chat_id, Message.user_id],
)

ChatUser.chat = relationship(Chat, backref="users")
ChatUser.user = relationship(User, backref="chats")
ChatUser.export = relationship(
    ChatExport,
    primaryjoin=and_(
        ChatUser.chat_id == foreign(ChatExport.chat_id),
        ChatUser.user_id == foreign(ChatExport.user_id),
    ),
    uselist=False,
    viewonly=True,
)

ChatExport.chat = relationship(Chat)
ChatExport.user = relationship(User)
ChatExport.chat_user = relationship(
    ChatUser,
    primaryjoin=and_(ChatExport.chat_id == ChatUser.chat_id, ChatExport.user_id == ChatUser.user_id),
    foreign_keys=[ChatExport.chat_id, ChatExport.user_id],
)

PromptReport.duplicate_of = relationship(PromptReport, backref="duplicates", remote_side=PromptReport.id)
PromptReport.reporting_user = relationship(User, backref="reports_sent", primaryjoin=PromptReport.reporting_user_id == User.id)
PromptReport.reported_user = relationship(User, backref="reports_recieved", primaryjoin=PromptReport.reported_user_id == User.id)

Request.user = relationship(User, backref="requests")
Request.tags = relationship(Tag, secondary=RequestTag.__table__, order_by=(Tag.type, Tag.name), backref="requests")
Request.duplicate_of = relationship(Request, remote_side=Request.id)
Request.slots = relationship(RequestSlot, backref="request", order_by=RequestSlot.order, collection_class=SlotList)

RequestSlot.user = relationship(User)

RequestTag.request = relationship(Request, backref="request_tags")
RequestTag.tag = relationship(Tag, backref="request_tags")

User.blacklisted_tags = relationship(BlacklistedTag, backref="user")
BlacklistedTag.tag = relationship(Tag)

Tag.synonym_of = relationship(Tag, backref="synonyms", remote_side=Tag.id)

TagParent.child = relationship(Tag, foreign_keys=TagParent.child_id, backref="parents")
TagParent.parent = relationship(Tag, foreign_keys=TagParent.parent_id, backref="children")

TagMakeSynonymSuggestion.tag     = relationship(Tag, foreign_keys=TagMakeSynonymSuggestion.tag_id)
TagMakeSynonymSuggestion.user    = relationship(User)
TagMakeSynonymSuggestion.target  = relationship(Tag, foreign_keys=TagMakeSynonymSuggestion.target_id)

TagAddParentSuggestion.tag     = relationship(Tag, foreign_keys=TagAddParentSuggestion.tag_id)
TagAddParentSuggestion.user    = relationship(User)
TagAddParentSuggestion.target  = relationship(Tag, foreign_keys=TagAddParentSuggestion.target_id)

TagBumpMaturitySuggestion.tag  = relationship(Tag)
TagBumpMaturitySuggestion.user = relationship(User)

UserConnection.from_ = relationship(User, foreign_keys=UserConnection.from_id)
UserConnection.to    = relationship(User, foreign_keys=UserConnection.to_id)
UserConnection.reverse = relationship(
    UserConnection,
    primaryjoin=and_(
        UserConnection.from_id == foreign(UserConnection.to_id),
        UserConnection.to_id == foreign(UserConnection.from_id),
    ),
    uselist=False,
    viewonly=True,
)

VirtualUserConnection.from_ = relationship(User)


# Index to make usernames case insensitively unique.
Index("users_username", func.lower(User.username), unique=True)


# XXX indexes on requests table
# index by user id for your requests?


Index("tag_type_name_unique", Tag.type, func.lower(Tag.name), unique=True)


# run configure_mappers after defining all of the models to ensure
# all relationships can be setup
configure_mappers()


def get_sessionmaker(settings, prefix="sqlalchemy.", for_worker=False):
    engine = engine_from_config(settings, prefix)
    sm = sessionmaker(extension=None if for_worker else ZopeTransactionExtension())
    sm.configure(bind=engine)
    return sm


def includeme(config):
    """
    Initialize the model for a Pyramid app.

    Activate this setup using ``config.include("cherubplay.models")``.

    """
    settings = config.get_settings()

    # use pyramid_tm to hook the transaction lifecycle to the request
    config.include("pyramid_tm")

    sm = get_sessionmaker(settings)

    def db_factory(context, request):
        db = sm()
        # register the session with pyramid_tm for managing transactions
        zope.sqlalchemy.register(db, transaction_manager=request.tm)
        return db

    config.register_service_factory(db_factory, name="db")

