import datetime

from sqlalchemy import (
    and_,
    Column,
    ForeignKey,
    UniqueConstraint,
    Boolean,
    DateTime,
    Enum,
    Integer,
    String,
    Unicode,
    UnicodeText,
)

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import (
    relationship,
    scoped_session,
    sessionmaker,
)

from zope.sqlalchemy import ZopeTransactionExtension

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

    def __repr__(self):
        return "<User #%s: %s>" % (self.id, self.username)

    def unban_delta(self):
        return self.unban_date - datetime.datetime.now()


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

    def dict(self):
        return {
            "url": self.url,
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

    def dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "colour": self.colour,
            "symbol": self.symbol,
            "text": self.text,
            "posted": self.posted,
            "edited": self.edited,
            "show_edited": self.show_edited,
        }

    def show_edited(self):
        return self.edited - self.posted >= datetime.timedelta(0, 300)


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

    def __repr__(self):
        return "<ChatUser: Chat #%s, User #%s>" % (self.chat_id, self.user_id)

    def dict(self):
        return {
            "last_colour": self.last_colour,
            "symbol": self.symbol,
            "visited": self.visited,
            "title": self.title,
            "notes": self.notes,
        }


class PromptReport(Base):
    __tablename__ = "prompt_reports"
    id = Column(Integer, primary_key=True)
    reporting_user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    reported_user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    created = Column(DateTime, nullable=False, default=datetime.datetime.now)
    colour = Column(String(6), nullable=False)
    prompt = Column(UnicodeText, nullable=False)
    category = Column(Unicode(100), nullable=False)
    reason = Column(UnicodeText, nullable=False)
    notes = Column(UnicodeText, nullable=False, default=u"")


Chat.last_user = relationship(User)

Message.chat = relationship(Chat, backref="messages")
Message.user = relationship(User, backref="messages")

ChatUser.chat = relationship(Chat, backref="users")
ChatUser.user = relationship(User, backref="chats")

PromptReport.reporting_user = relationship(User, backref="reports_sent", primaryjoin=PromptReport.reporting_user_id==User.id)
PromptReport.reported_user = relationship(User, backref="reports_recieved", primaryjoin=PromptReport.reported_user_id==User.id)

