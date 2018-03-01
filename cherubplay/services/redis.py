from redis import ConnectionPool, StrictRedis, UnixDomainSocketConnection
from typing import Set
from zope.interface import Interface, implementer

from cherubplay.models import Chat, ChatUser


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
    def __init__(self, redis: StrictRedis): # Pubsub Redis instance
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


def make_redis_login(settings):
    return StrictRedis(connection_pool=ConnectionPool(
        connection_class=UnixDomainSocketConnection,
        path=settings["cherubplay.socket_login"],
    ))


def make_redis_pubsub(settings):
    return StrictRedis(connection_pool=ConnectionPool(
        connection_class=UnixDomainSocketConnection,
        path=settings["cherubplay.socket_pubsub"],
    ))


def includeme(config):
    redis_login = make_redis_login(config.registry.settings)
    config.register_service(redis_login, name="redis_login")

    redis_pubsub = make_redis_pubsub(config.registry.settings)
    config.register_service(redis_pubsub, name="redis_pubsub")

    config.register_service(OnlineUserStore(redis_pubsub), iface=IOnlineUserStore)
