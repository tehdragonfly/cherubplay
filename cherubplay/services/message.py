import datetime, json, logging

from redis import StrictRedis
from sqlalchemy import and_
from typing import Dict, Union
from zope.interface import Interface, implementer

from cherubplay.lib import trim_with_ellipsis
from cherubplay.models import Chat, ChatUser, ChatUserStatus, Message, User
from cherubplay.models.enums import MessageType
from cherubplay.services.redis import IOnlineUserStore
from cherubplay.tasks import trigger_push_notification


log = logging.getLogger(__name__)


def pubsub_channel(destination: Union[Chat, ChatUser, User]):
    if type(destination) == Chat:
        # Chat channel: used for sending ordinary messages.
        return "chat:%s" % destination.id
    elif type(destination) == ChatUser:
        # ChatUser channel: used for single-user messages like kicking.
        return "chat:%s:user:%s" % (destination.chat_id, destination.user_id)
    elif type(destination) == User:
        # User channel: used for cross-chat notifications.
        return "user:%s" % destination.id
    else:
        raise ValueError("object must be Chat, ChatUser or User")


class IMessageService(Interface):
    def send_message(self, chat_user: ChatUser, type: MessageType, colour: str, text: str, action: str="message"):
        pass

    def send_end_message(self, chat_user: ChatUser):
        pass

    def send_leave_message(self, chat_user: ChatUser):
        pass

    def send_kick_message(self, kicking_chat_user: ChatUser, kicked_chat_user: ChatUser):
        pass

    def send_change_name_message(self, chat_user: ChatUser, old_name: str):
        pass

    def publish_edit(self, message: Message):
        pass


@implementer(IMessageService)
class MessageService(object):
    def __init__(self, db, pubsub: StrictRedis, online_user_store: IOnlineUserStore):
        self._db     = db
        self._pubsub = pubsub
        self._online_user_store = online_user_store

    def _publish(self, destination: Union[Chat, ChatUser, User], message: Union[str, Dict]):
        if isinstance(message, dict):
            message = json.dumps(message)
        try:
            self._pubsub.publish(pubsub_channel(destination), message)
        except ConnectionError:
            log.error("Failed to send pubsub message.")

    def send_message(self, chat_user: ChatUser, type: MessageType, colour: str, text: str, action: str="message"):
        chat = chat_user.chat

        # Only trigger notifications if the user has seen the most recent message.
        # This stops us from sending multiple notifications about the same chat.
        most_recent_message = (
            self._db.query(Message)
            .filter(Message.chat_id == chat.id)
            .order_by(Message.id.desc()).first()
        )

        posted_date = datetime.datetime.now()

        if type == MessageType.system and "%s" in text:
            notification_text = text % chat_user.handle
            if chat_user.name:
                text = notification_text
        else:
            notification_text = text

        new_message = Message(
            chat_id=chat.id,
            user_id=chat_user.user_id,
            type=type,
            colour=colour,
            symbol=chat_user.symbol,
            text=text,
            posted=posted_date,
            edited=posted_date,
        )
        self._db.add(new_message)
        self._db.flush()

        chat.updated = posted_date
        if type != MessageType.system:
            chat.last_user_id = chat_user.user_id

        chat_user.last_colour = colour
        chat_user.draft = ""

        # See if anyone else is online and update their ChatUser too.
        online_handles = self._online_user_store.online_handles(chat)
        for other_chat_user in self._db.query(ChatUser).filter(and_(
            ChatUser.chat_id == chat.id,
            ChatUser.status == ChatUserStatus.active,
        )):
            if other_chat_user.handle in online_handles:
                other_chat_user.visited = posted_date
            # Only trigger notifications if the user has seen the most recent message.
            # This stops us from getting multiple notifications about the same chat.
            elif not most_recent_message or other_chat_user.visited > most_recent_message.posted:
                self._publish(other_chat_user, {
                    "action": "notification",
                    "url": chat.url,
                    "title": other_chat_user.display_title,
                    "colour": colour,
                    "symbol": chat_user.symbol_character,
                    "name": chat_user.name,
                    "text": trim_with_ellipsis(notification_text, 100),
                })
                trigger_push_notification.delay(other_chat_user.user_id)

        self._publish(chat, {
            "action": action,
            "message": {
                "id": new_message.id,
                "type": new_message.type.value,
                "colour": new_message.colour,
                "symbol": chat_user.symbol_character,
                "name": chat_user.name,
                "text": new_message.text,
            },
        })

    def send_end_message(self, chat_user: ChatUser):
        self.send_message(chat_user, MessageType.system, "000000", "%s ended the chat.", "end")
        chat_user.visited = datetime.datetime.now()

    def send_leave_message(self, chat_user: ChatUser):
        self.send_message(chat_user, MessageType.system, "000000", "%s left the chat.", "message")
        chat_user.visited = datetime.datetime.now()

    def send_kick_message(self, kicking_chat_user: ChatUser, kicked_chat_user: ChatUser):
        text = "%s has been removed from the chat." % kicked_chat_user.name
        self.send_message(kicked_chat_user, MessageType.system, "000000", text, "message")
        self._publish(kicked_chat_user, "kicked")
        kicking_chat_user.visited = datetime.datetime.now()

    def send_change_name_message(self, chat_user: ChatUser, old_name: str):
        text = "%s is now %s." % (old_name, chat_user.name)
        self.send_message(chat_user, MessageType.system, "000000", text, "end")
        self._publish(chat_user.chat, {
            "action":   "name_change",
            "old_name": old_name,
            "new_name": chat_user.name,
        })

    def publish_edit(self, message: Message):
        self._publish(message.chat, {
            "action": "edit",
            "message": {
                "id": message.id,
                "type": message.type.value,
                "colour": message.colour,
                "symbol": message.symbol_character,
                "name": message.chat_user.name,
                "text": message.text,
                "show_edited": message.show_edited,
            },
        })


def includeme(config):
    config.register_service_factory(lambda context, request: MessageService(
        request.find_service(name="db"),
        request.find_service(name="redis_pubsub"),
        request.find_service(IOnlineUserStore),
    ), iface=IMessageService)