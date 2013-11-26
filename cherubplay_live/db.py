from ConfigParser import ConfigParser
import sys

from redis import Redis

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from cherubplay.models import User

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
    bind=engine
)
Session = sm()

login_client = Redis(unix_socket_path=config.get("app:main", "cherubplay.login_store"))

def get_user(cookies):
    if "cherubplay" not in cookies:
        return None
    user_id = login_client.get("session:"+cookies["cherubplay"].value)
    if user_id is None:
        return None
    try:
        return Session.query(User).filter(User.id==user_id).one()
    except NoResultFound:
        return None

