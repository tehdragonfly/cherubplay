import datetime, json, logging

from sqlalchemy import and_
from typing import Dict, Union
from zope.interface import Interface, implementer

from cherubplay.lib import OnlineUserStore
from cherubplay.models import ChatUser, ChatUserStatus, Message
from cherubplay.models.enums import MessageType
from cherubplay.tasks import trigger_push_notification


log = logging.getLogger(__name__)


class IMessageService(Interface):
    def __init__(self, request): # Pyramid request, not Request
        pass

    def send_message(self, chat_user: ChatUser, type: MessageType, colour: str, text: str, action: str="message"):
        pass

    def send_end_message(self, chat_user: ChatUser, deleted: bool=False):
        pass

    def send_leave_message(self, chat_user: ChatUser):
        pass

    def send_kick_message(self, kicking_chat_user: ChatUser, kicked_chat_user: ChatUser):
        pass


@implementer(IMessageService)
class MessageService(object):
    def __init__(self, request):
        self._db     = request.find_service(name="db")
        self._pubsub = request.pubsub

    def _publish(self, key: str, message: Union[str, Dict]):
        if isinstance(message, dict):
            message = json.dumps(message)
        try:
            self._pubsub.publish(key, message)
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

        if type == MessageType.system:
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
        online_handles = OnlineUserStore(self._pubsub).online_handles(chat)
        for other_chat_user in self._db.query(ChatUser).filter(and_(
            ChatUser.chat_id == chat.id,
            ChatUser.status == ChatUserStatus.active,
        )):
            if other_chat_user.handle in online_handles:
                other_chat_user.visited = posted_date
            # Only trigger notifications if the user has seen the most recent message.
            # This stops us from getting multiple notifications about the same chat.
            elif not most_recent_message or other_chat_user.visited > most_recent_message.posted:
                self._publish("user:" + str(other_chat_user.user_id), {
                    "action": "notification",
                    "url": chat.url,
                    "title": other_chat_user.title or chat.url,
                    "colour": colour,
                    "symbol": chat_user.symbol_character,
                    "name": chat_user.name,
                    "text": notification_text if len(notification_text) < 100 else notification_text[:97] + "...",
                })
                trigger_push_notification.delay(other_chat_user.user_id)

        self._publish("chat:%s" % new_message.chat_id, {
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

    def send_end_message(self, chat_user: ChatUser, deleted: bool=False):
        text = "%%s %s the chat." % ("deleted" if deleted else "ended")
        self.send_message(chat_user, MessageType.system, "000000", text, "end")
        chat_user.visited = datetime.datetime.now()

    def send_leave_message(self, chat_user: ChatUser):
        self.send_message(chat_user, MessageType.system, "000000", "%%s left the chat.", "message")
        chat_user.visited = datetime.datetime.now()

    def send_kick_message(self, kicking_chat_user: ChatUser, kicked_chat_user: ChatUser):
        text = "%s has been removed from the chat." % kicked_chat_user.name
        self.send_message(kicked_chat_user, MessageType.system, "000000", text, "message")
        self._publish(
            "chat:%s:user:%s" % (kicked_chat_user.chat_id, kicked_chat_user.user_id),
            "kicked",
        )
        kicking_chat_user.visited = datetime.datetime.now()

    def send_change_name_message(self, chat_user: ChatUser, old_name: str):
        text = "%s is now %s." % (old_name, chat_user.name)
        self.send_message(chat_user, MessageType.system, "000000", text, "end")
        self._publish("chat:" + str(chat_user.chat.id), {
            "action":   "name_change",
            "old_name": old_name,
            "new_name": chat_user.name,
        })


def includeme(config):
    config.register_service_factory(lambda context, request: MessageService(request), iface=IMessageService)