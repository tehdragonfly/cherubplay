import sys

from configparser import ConfigParser
from contextlib import contextmanager

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from cherubplay.models import Chat, ChatUser, User
from cherubplay.models.enums import ChatUserStatus
from cherubplay.services.redis import make_redis_connection

config_path = sys.argv[1]
config = ConfigParser()
config.read(config_path)

engine = create_engine(
    config.get("app:main", "sqlalchemy.url"),
    convert_unicode=True,
    pool_recycle=3600,
)
sm = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


@contextmanager
def db_session():
    db = sm()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


login_redis   = make_redis_connection(config["app:main"], "login")
publish_redis = make_redis_connection(config["app:main"], "pubsub")


def get_user(db, cookies):
    if "cherubplay" not in cookies:
        return None
    user_id = login_redis.get("session:" + cookies["cherubplay"].value)
    if user_id is None:
        return None
    try:
        return db.query(User).filter(and_(
            User.id == int(user_id),
            User.status != "banned",
        )).one()
    except (ValueError, NoResultFound):
        return None


def get_chat(db, chat_url):
    try:
        return db.query(Chat).filter(Chat.url == chat_url).one()
    except NoResultFound:
        return None


def get_chat_user(db, chat_id, user_id):
    try:
        return db.query(ChatUser).filter(and_(
            ChatUser.chat_id == chat_id,
            ChatUser.user_id == user_id,
            ChatUser.status == ChatUserStatus.active,
        )).one()
    except NoResultFound:
        return None

