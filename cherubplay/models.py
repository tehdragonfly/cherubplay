# -*- coding: utf-8 -*-

import datetime

from pyramid.security import Allow, Authenticated, Everyone
from pytz import timezone, utc
from sqlalchemy import (
    and_,
    Column,
    ForeignKey,
    Index,
    UniqueConstraint,
    Boolean,
    DateTime,
    Enum,
    Integer,
    String,
    Unicode,
    UnicodeText,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import (
    relationship,
    scoped_session,
    sessionmaker,
)

from zope.sqlalchemy import ZopeTransactionExtension

from lib import symbols


Session = scoped_session(sessionmaker(
    extension=ZopeTransactionExtension(),
    expire_on_commit=False,
))
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(Unicode(100), nullable=False, unique=True)
    password = Column(String(60), nullable=False)
    status = Column(Enum(u"active", u"banned", u"admin", name="user_status"), nullable=False, default=u"active")
    email = Column(Unicode(255))
    created = Column(DateTime, nullable=False, default=datetime.datetime.now)
    last_online = Column(DateTime, nullable=False, default=datetime.datetime.now)
    last_ip = Column(String(40))
    unban_date = Column(DateTime)
    layout_version = Column(Integer, nullable=False, default=2)
    timezone = Column(Unicode(255))

    def __repr__(self):
        return "<User #%s: %s>" % (self.id, self.username)

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
    status = Column(Enum(u"ongoing", u"ended", name="chat_status"), nullable=False, default=u"ongoing")
    created = Column(DateTime, nullable=False, default=datetime.datetime.now)
    updated = Column(DateTime, nullable=False, default=datetime.datetime.now)
    last_user_id = Column(Integer, ForeignKey("users.id"))

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
    type = Column(Enum(u"ic", u"ooc", u"system", name="message_type"), nullable=False, default=u"ic")
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
    status = Column(Enum(u"active", u"archived", name="chat_user_status"), nullable=False, default=u"active")
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


class PromptReport(Base):
    __tablename__ = "prompt_reports"
    id = Column(Integer, primary_key=True)
    status = Column(Enum(
        u"open",
        u"closed",
        u"invalid",
        name="prompt_report_status",
    ), nullable=False, default=u"open")
    reporting_user_id = Column(Integer, ForeignKey("users.id"))
    reported_user_id = Column(Integer, ForeignKey("users.id"))
    created = Column(DateTime, nullable=False, default=datetime.datetime.now)
    colour = Column(String(6), nullable=False)
    prompt = Column(UnicodeText, nullable=False)
    category = Column(Unicode(100), nullable=False)
    level = Column(Unicode(100), nullable=False)
    reason = Column(Enum(
        u"wrong_category",
        u"spam",
        u"stolen",
        u"multiple",
        u"advert",
        u"ooc",
        name="prompt_report_reason",
    ), nullable=False)
    reason_category = Column(Unicode(100))
    reason_level = Column(Unicode(100))
    notes = Column(UnicodeText, nullable=False, default=u"")


class Prompt(Base):

    __acl__ = (
        (Allow, Authenticated, "view"),
        (Allow, "active", "chat"),
        (Allow, "admin", "admin"),
    )

    __tablename__ = "prompts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(Unicode(100), nullable=False, default=u"")
    created = Column(DateTime, nullable=False, default=datetime.datetime.now)
    updated = Column(DateTime, nullable=False, default=datetime.datetime.now)
    colour = Column(String(6), nullable=False)
    text = Column(UnicodeText, nullable=False)
    category = Column(Unicode(100), nullable=False)
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
            "level": self.level,
        }


class Request(Base):
    __tablename__ = "requests"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(Enum(u"draft", u"posted", name=u"requests_status"), nullable=False, default=u"draft")
    posted = Column(DateTime(), nullable=False, default=datetime.datetime.now)
    edited = Column(DateTime(), nullable=False, default=datetime.datetime.now)
    colour = Column(Unicode(6), nullable=False, default=u"000000")
    scenario = Column(UnicodeText, nullable=False, default=u"")
    prompt = Column(UnicodeText, nullable=False, default=u"")

    def tags_by_type(self):
        tags = { _: [] for _ in Tag.type.type.enums }
        for request_tag in self.tags:
            tags[request_tag.tag.type].append({
                "type": request_tag.tag.type,
                "name": request_tag.tag.name,
                "alias": request_tag.alias,
            })
        return tags

    def __json__(self, request=None):
        rd = {
            "id": self.id,
            "status": self.status,
            "posted": self.posted.isoformat(),
            "edited": self.edited.isoformat(),
            "color": self.color,
            "scenario": self.scenario,
            "prompt": self.prompt,
            "tags": self.tags_by_type(),
        }
        if request is not None:
            rd["yours"] = request.user.id == self.user_id
        return rd


class RequestTag(Base):
    __tablename__ = "request_tags"
    request_id = Column(Integer, ForeignKey("requests.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)
    alias = Column(Unicode(50))


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("type", "name", name="tag_unique"),)
    id = Column(Integer, primary_key=True)
    type = Column(Enum(
        u"maturity", u"trigger", u"type", u"fandom", u"fandom_wanted",
        u"character", u"character_wanted", u"gender", u"gender_wanted", u"misc",
        name=u"tags_type",
    ), nullable=False, default=u"misc")
    name = Column(Unicode(50), nullable=False)
    synonym_id = Column(Integer, ForeignKey("tags.id"))

    # XXX OrderedDict
    maturity_names = ["safe_for_work", "not_safe_for_work", "nsfw_extreme"]
    type_names = ["fluff", "plot-driven", "sexual", "shippy", "violent"]


Chat.last_user = relationship(User)

Message.chat = relationship(Chat, backref="messages")
Message.user = relationship(User, backref="messages")

ChatUser.chat = relationship(Chat, backref="users")
ChatUser.user = relationship(User, backref="chats")

PromptReport.reporting_user = relationship(User, backref="reports_sent", primaryjoin=PromptReport.reporting_user_id==User.id)
PromptReport.reported_user = relationship(User, backref="reports_recieved", primaryjoin=PromptReport.reported_user_id==User.id)

Request.user = relationship(User, backref="requests")
Request.tags = relationship(RequestTag, backref="request", order_by=RequestTag.alias)

Tag.requests = relationship(RequestTag, backref="tag")
Tag.synonym_of = relationship(Tag, backref="synonyms", remote_side=Tag.id)


# XXX indexes on requests table
# index by user id for your requests?

# Index for searching requests by tag.
Index("request_tags_tag_id", RequestTag.tag_id)

