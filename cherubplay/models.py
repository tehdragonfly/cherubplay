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


class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True)
    url = Column(Unicode(100), nullable=False, unique=True)
    status = Column(Enum(u"ongoing", u"ended", name="chat_status"), nullable=False, default=u"ongoing")
    created = Column(DateTime, nullable=False, default=datetime.datetime.now)
    updated = Column(DateTime, nullable=False, default=datetime.datetime.now)


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


Message.chat = relationship(Chat, backref="messages")
Message.user = relationship(User, backref="messages")

ChatUser.chat = relationship(Chat, backref="users")
ChatUser.user = relationship(User, backref="chats")

