from datetime import datetime
from redis import ConnectionPool, Redis, UnixDomainSocketConnection
from time import mktime
from typing import Set, Optional
from zope.interface import Interface, implementer

from cherubplay.models import Chat, ChatUser, User


class INewsStore(Interface):
    def get_news(self) -> str:
        pass

    def set_news(self, news: str):
        pass

    def should_show_news(self, user: User) -> bool:
        pass


@implementer(INewsStore)
class NewsStore(object):
    def __init__(self, redis: Redis): # Login Redis instance
        self._redis = redis

    def get_news(self) -> Optional[str]:
        news = self._redis.get("news")
        if news:
            return news.decode("utf-8")
        return None

    def set_news(self, news: str):
        news = news.strip().encode("utf-8")
        if news:
            self._redis.set("news", news)
            self._redis.set("news_last_updated", mktime(datetime.now().timetuple()))
        else:
            self._redis.delete("news", "news_last_updated")

    def should_show_news(self, user: User) -> bool:
        last_updated = self._redis.get("news_last_updated")
        if not last_updated:
            return False
        try:
            last_updated = datetime.fromtimestamp(float(last_updated))
        except (TypeError, ValueError):
            return False
        return user.last_read_news is None or user.last_read_news < last_updated


def online_key(chat: Chat) -> str:
    return "online:{}".format(chat.id)


class IOnlineUserStore(Interface):
    def connect(self, chat: Chat, chat_user: ChatUser, socket_id: str):
        pass

    def disconnect(self, chat: Chat, socket_id: str):
        pass

    def rename(self, chat: Chat, old_handle: str, new_handle: str):
        pass

    def online_handles(self, chat: Chat) -> Set:
        pass


@implementer(IOnlineUserStore)
class OnlineUserStore(object):
    def __init__(self, redis: Redis): # Pubsub Redis instance
        self.redis = redis

    def connect(self, chat_user: ChatUser, socket_id: str):
        # TODO fire online/offline messages from here too?
        self.redis.hset(online_key(chat_user.chat), socket_id, chat_user.handle)

    def disconnect(self, chat: Chat, socket_id: str):
        self.redis.hdel(online_key(chat), socket_id)

    def rename(self, chat: Chat, old_handle: str, new_handle: str):
        for socket_id, current_handle in self.redis.hgetall(online_key(chat)).items():
            if current_handle.decode() == old_handle:
                self.redis.hset(online_key(chat), socket_id, new_handle)

    def online_handles(self, chat: Chat) -> Set:
        return set(_.decode("utf-8") for _ in self.redis.hvals(online_key(chat)))


def make_redis_connection(settings, key):
    return Redis(connection_pool=ConnectionPool(
        connection_class=UnixDomainSocketConnection,
        path=settings["cherubplay.socket_" + key],
    ))


def includeme(config):
    redis_login = make_redis_connection(config.registry.settings, "login")
    config.register_service(redis_login, name="redis_login")

    redis_pubsub = make_redis_connection(config.registry.settings, "pubsub")
    config.register_service(redis_pubsub, name="redis_pubsub")

    config.register_service(NewsStore(redis_login), iface=INewsStore)
    config.register_service(OnlineUserStore(redis_pubsub), iface=IOnlineUserStore)
