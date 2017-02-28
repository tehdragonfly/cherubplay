# -*- coding: utf-8 -*-

import datetime

from collections import OrderedDict
from pyramid.decorator import reify
from pyramid.security import Allow, Authenticated, Deny, Everyone
from pytz import timezone, utc
from sqlalchemy import (
    and_,
    func,
    Column,
    ForeignKey,
    Index,
    UniqueConstraint,
    Boolean,
    DateTime,
    Enum as SQLAlchemyEnum,
    Integer,
    String,
    Unicode,
    UnicodeText,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_enum34 import EnumType
from time import mktime

from sqlalchemy.orm import (
    relationship,
    scoped_session,
    sessionmaker,
)

from zope.sqlalchemy import ZopeTransactionExtension

from cherubplay.lib import symbols
from cherubplay.models.enums import TagType


Session = scoped_session(sessionmaker(
    extension=ZopeTransactionExtension(),
    expire_on_commit=False,
))
Base = declarative_base()


class Resource(object):
    __acl__ = (
        (Allow, Authenticated, "view"),
        (Allow, "active",      "chat"),
        (Allow, "admin",       "admin"),
        (Allow, Authenticated, "directory.read"),
        (Allow, "active",      "directory.new_request"),
        (Allow, "admin",       "directory.manage_tags"),
    )


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(Unicode(100), nullable=False, unique=True)
    password = Column(String(60), nullable=False)
    status = Column(SQLAlchemyEnum(u"active", u"banned", u"admin", name="user_status"), nullable=False, default=u"active")
    email = Column(Unicode(255))
    email_verified = Column(Boolean, nullable=False, default=False)
    created = Column(DateTime, nullable=False, default=datetime.datetime.now)
    last_online = Column(DateTime, nullable=False, default=datetime.datetime.now)
    last_ip = Column(String(40))
    unban_date = Column(DateTime)
    layout_version = Column(Integer, nullable=False, default=2)
    timezone = Column(Unicode(255))
    seen_blacklist_warning = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return "<User #%s: %s>" % (self.id, self.username)

    @reify
    def tag_status_filter(self):
        if self.status == "admin":
            return Request.status.in_(("posted", "removed"))
        return Request.status == "posted"

    @reify
    def tag_filter(self):

        has_blacklist = Session.query(BlacklistedTag).filter(BlacklistedTag.user_id == self.id).first() is not None
        if has_blacklist:
            return and_(
                self.tag_status_filter,
                ~Request.tag_ids.overlap(
                    Session.query(func.array_agg(BlacklistedTag.tag_id))
                   .filter(BlacklistedTag.user_id == self.id)
                ),
            )

        return self.tag_status_filter

    @property
    def unban_delta(self):
        return self.unban_date - datetime.datetime.now()

    def localise_time(self, input_datetime):
        utc_datetime = utc.localize(input_datetime)
        if self.timezone is None:
            return utc_datetime
        return utc_datetime.astimezone(timezone(self.timezone))


class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True)
    url = Column(Unicode(100), nullable=False, unique=True)
    status = Column(SQLAlchemyEnum(u"ongoing", u"ended", name="chat_status"), nullable=False, default=u"ongoing")
    created = Column(DateTime, nullable=False, default=datetime.datetime.now)
    updated = Column(DateTime, nullable=False, default=datetime.datetime.now)
    last_user_id = Column(Integer, ForeignKey("users.id"))
    request_id = Column(Integer, ForeignKey("requests.id"))

    def __repr__(self):
        return "<Chat #%s: %s>" % (self.id, self.url)

    def __json__(self, request=None):
        return {
            "url": self.url,
            "status": self.status,
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat(),
        }


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    # System messages don't have a user ID, and we may also need to set it to null if a user is deleted.
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(SQLAlchemyEnum(u"ic", u"ooc", u"system", name="message_type"), nullable=False, default=u"ic")
    colour = Column(String(6), nullable=False, default="000000")
    symbol = Column(Integer)
    text = Column(UnicodeText, nullable=False)
    posted = Column(DateTime, nullable=False, default=datetime.datetime.now)
    edited = Column(DateTime, nullable=False, default=datetime.datetime.now)

    def __repr__(self):
        if len(self.text) < 40:
            preview = self.text
        else:
            preview = self.text[:37] + "..."
        return "<Message #%s: \"%s\">" % (self.id, preview)

    def __json__(self, request=None):
        return {
            "id": self.id,
            "type": self.type,
            "colour": self.colour,
            "symbol": self.symbol,
            "symbol_character": self.symbol_character,
            "text": self.text,
            "posted": self.posted.isoformat(),
            "edited": self.edited.isoformat(),
            "show_edited": self.show_edited,
        }

    @property
    def show_edited(self):
        return self.edited - self.posted >= datetime.timedelta(0, 300)

    @property
    def symbol_character(self):
        return symbols[self.symbol] if self.symbol is not None else None


class ChatUser(Base):
    __tablename__ = "chat_users"
    __table_args__ = (UniqueConstraint('chat_id', 'symbol', name='chat_user_symbol_unique'),)
    chat_id = Column(Integer, ForeignKey("chats.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    last_colour = Column(String(6), nullable=False, default="000000")
    symbol = Column(Integer, nullable=False)
    anonymous = Column(Boolean, nullable=False, default=True)
    visited = Column(DateTime, nullable=False, default=datetime.datetime.now)
    status = Column(SQLAlchemyEnum(u"active", u"archived", name="chat_user_status"), nullable=False, default=u"active")
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
            "visited": self.visited.isoformat(),
            "title": self.title,
            "notes": self.notes,
            "labels": self.labels,
        }

    @property
    def symbol_character(self):
        return symbols[self.symbol] if self.symbol is not None else None


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
            "created": self.created.isoformat(),
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
    text = Column(UnicodeText, nullable=False)
    category = Column(Unicode(100))
    starter = Column(Unicode(100), nullable=False)
    level = Column(Unicode(100), nullable=False)

    def __repr__(self):
        return "<Prompt #%s: %s>" % (self.id, self.title)

    def __json__(self, request=None):
        return {
            "id": self.id,
            "title": self.title,
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat(),
            "colour": self.colour,
            "text": self.text,
            "category": self.category,
            "starter": self.starter,
            "level": self.level,
        }


class Request(Base):
    __parent__ = Resource
    def __acl__(self):
        return (
            (Allow, Authenticated, "request.read"),
            (Deny,  self.user_id,  "request.answer"),
            (Allow, "active",      "request.answer"),
            (Deny,  "banned",      "request.edit"),
            (Allow, self.user_id,  "request.edit"),
            (Allow, self.user_id,  "request.delete"),
            (Allow, "admin",       "request.remove"),
        )

    __tablename__ = "requests"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(SQLAlchemyEnum(u"draft", u"posted", u"removed", name=u"requests_status"), nullable=False, default=u"draft")
    # Created indicates when the request was created, and is never modified.
    created = Column(DateTime(), nullable=False, default=datetime.datetime.now)
    # Posted indicates when the request was first posted.
    # It's set when the status is first set to "posted". This may be the same as the created time
    # if posted directly, or when it was changed from "draft" to "posted".
    posted = Column(DateTime())
    # Edited indicates when the request was last edited.
    edited = Column(DateTime(), nullable=False, default=datetime.datetime.now)
    colour = Column(Unicode(6), nullable=False, default=u"000000")
    ooc_notes = Column(UnicodeText, nullable=False, default=u"")
    starter = Column(UnicodeText, nullable=False, default=u"")
    tag_ids = Column(ARRAY(Integer)) # this makes tag filtering easier
    duplicate_of_id = Column(Integer, ForeignKey("requests.id"))

    def __repr__(self):
        return "<Request #%s>" % self.id

    def tags_by_type(self):
        tags = { _: [] for _ in Tag.type.type.python_type }
        for tag in self.tags:
            tags[tag.type].append(tag)
        return tags

    def __json__(self, request=None):
        rd = {
            "id": self.id,
            "status": self.status,
            "posted": self.posted.isoformat(),
            "edited": self.edited.isoformat(),
            "colour": self.colour,
            "ooc_notes": self.ooc_notes,
            "starter": self.starter,
            "tags": self.tags_by_type(),
        }
        if request is not None:
            rd["yours"] = request.user.id == self.user_id
        return rd


class RequestTag(Base):
    __tablename__ = "request_tags"
    request_id = Column(Integer, ForeignKey("requests.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)

    def __repr__(self):
        return "<RequestTag: Request #%s, Tag #%s>" % (self.request_id, self.tag_id)

    def __json__(self, request=None):
        tag_dict = self.tag.__json__(request)
        return tag_dict


class BlacklistedTag(Base):
    __tablename__ = "blacklisted_tags"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)

    def __repr__(self):
        return "<BlacklistedTag: User #%s, Tag #%s>" % (self.user_id, self.tag_id)

    def __json__(self, request=None):
        tag_dict = self.tag.__json__(request)
        return tag_dict


class CreateNotAllowed(Exception): pass


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    # XXX TODO UPDATE EVERYTHING ELSE TO ACCEPT TagType
    type = Column(EnumType(TagType, name=u"tags_type"), nullable=False, default=u"misc")
    name = Column(Unicode(100), nullable=False)
    synonym_id = Column(Integer, ForeignKey("tags.id"))
    approved = Column(Boolean, nullable=False, default=False)
    blacklist_default = Column(Boolean, nullable=False, default=False)

    maturity_names = [u"Safe for work", u"Not safe for work", u"NSFW extreme"]
    type_names = [u"Fluff", u"Plot-driven", u"Sexual", u"Shippy", u"Violent"]

    def __repr__(self):
        return "<Tag #%s: %s:%s>" % (self.id, self.type.value, self.name)

    @classmethod
    def get_or_create(cls, tag_type, name, allow_maturity_and_type_creation=True, create_opposite_tag=True):
        try:
            tag = Session.query(cls).filter(and_(cls.type == tag_type, func.lower(cls.name) == name.lower())).one()
        except NoResultFound:
            if not allow_maturity_and_type_creation and tag_type in (TagType.maturity, TagType.type):
                raise CreateNotAllowed
            tag = cls(type=tag_type, name=name)
            Session.add(tag)
            Session.flush()
            if create_opposite_tag:
                if tag_type in TagType.playing_types:
                    cls.get_or_create(tag_type.wanted, name, create_opposite_tag=False)
                elif tag_type in TagType.wanted_types:
                    cls.get_or_create(tag_type.playing, name, create_opposite_tag=False)
        return tag

    @classmethod
    def name_from_url(cls, url):
        return url.replace("*s*", "/").replace("*c*", ":").replace("_", " ")

    @reify
    def url_name(self):
        return self.name.replace("/", "*s*").replace(":", "*c*").replace(" ", "_")

    @reify
    def tag_string(self):
        return ":".join((self.type.value, self.url_name))

    def __json__(self, request=None):
        tag_dict = {
            "type": self.type.value,
            "name": self.name,
            "url_name": self.url_name,
        }
        if request and request.user and request.has_permission("directory.manage_tags"):
            tag_dict["approved"] = self.approved
        return tag_dict


class TagParent(Base):
    __tablename__ = "tag_parents"
    child_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)
    parent_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)

    def __repr__(self):
        return "<TagParent: Child #%s, Parent #%s>" % (self.child_id, self.parent_id)


Chat.last_user = relationship(User)
Chat.request = relationship(Request)

Message.chat = relationship(Chat, backref="messages")
Message.user = relationship(User, backref="messages")

ChatUser.chat = relationship(Chat, backref="users")
ChatUser.user = relationship(User, backref="chats")

PromptReport.duplicate_of = relationship(PromptReport, backref="duplicates", remote_side=PromptReport.id)
PromptReport.reporting_user = relationship(User, backref="reports_sent", primaryjoin=PromptReport.reporting_user_id == User.id)
PromptReport.reported_user = relationship(User, backref="reports_recieved", primaryjoin=PromptReport.reported_user_id == User.id)

Request.user = relationship(User, backref="requests")
Request.tags = relationship(Tag, secondary=RequestTag.__table__, order_by=(Tag.type, Tag.name), backref="requests")
Request.duplicate_of = relationship(Request, remote_side=Request.id)

RequestTag.request = relationship(Request, backref="request_tags")
RequestTag.tag = relationship(Tag, backref="request_tags")

User.blacklisted_tags = relationship(BlacklistedTag, backref="user")
BlacklistedTag.tag = relationship(Tag)

Tag.synonym_of = relationship(Tag, backref="synonyms", remote_side=Tag.id)

TagParent.child = relationship(Tag, foreign_keys=TagParent.child_id, backref="parents")
TagParent.parent = relationship(Tag, foreign_keys=TagParent.parent_id, backref="children")


# XXX indexes on requests table
# index by user id for your requests?


Index("tag_type_name_unique", Tag.type, func.lower(Tag.name), unique=True)

