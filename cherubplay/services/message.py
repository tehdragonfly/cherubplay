import datetime, json

from sqlalchemy import and_
from zope.interface import Interface, implementer

from cherubplay.lib import OnlineUserStore
from cherubplay.models import Chat, ChatUser, ChatUserStatus, Message
from cherubplay.models.enums import MessageType
from cherubplay.tasks import trigger_push_notification


class IMessageService(Interface):
    def __init__(self, request): # Pyramid request, not Request
        pass

    def send_message(self, chat_user: ChatUser, type: MessageType, colour: str, text: str):
        pass

    def send_end_message(self, chat_user: ChatUser):
        pass

    def send_leave_message(self, chat_user: ChatUser):
        pass

    def send_kick_message(self, chat_user: ChatUser):
        pass


@implementer(IMessageService)
class MessageService(object):
    def __init__(self, request):
        self._db     = request.find_service(name="db")
        self._pubsub = request.pubsub

    def send_message(self, chat_user: ChatUser, type: MessageType, colour: str, text: str):
        chat = chat_user.chat

        # Only trigger notifications if the user has seen the most recent message.
        # This stops us from sending multiple notifications about the same chat.
        most_recent_message = (
            self._db.query(Message)
            .filter(Message.chat_id == chat.id)
            .order_by(Message.id.desc()).first()
        )

        posted_date = datetime.datetime.now()

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
        chat.last_user_id = chat_user.user_id

        chat_user.last_colour = colour
        chat_user.draft = ""

        try:
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
                    self._pubsub.publish("user:" + str(other_chat_user.user_id), json.dumps({
                        "action": "notification",
                        "url": chat.url,
                        "title": other_chat_user.title or chat.url,
                        "colour": colour,
                        "symbol": chat_user.symbol_character,
                        "name": chat_user.name,
                        "text": text if len(text) < 100 else text[:97] + "...",
                    }))
                    trigger_push_notification.delay(other_chat_user.user_id)
        except ConnectionError:
            pass

        self._publish_message(new_message, chat_user)

    def _publish_message(self, message: Message, chat_user: ChatUser, action="message"):
        try:
            self._pubsub.publish("chat:%s" % message.chat_id, json.dumps({
                "action": action,
                "message": {
                    "id": message.id,
                    "type": message.type.value,
                    "colour": message.colour,
                    "symbol": chat_user.symbol_character,
                    "name": chat_user.name,
                    "text": message.text,
                },
            }))
        except ConnectionError:
            pass

    def send_end_message(self, chat_user: ChatUser):
        raise NotImplementedError

    def send_leave_message(self, chat_user: ChatUser):
        raise NotImplementedError

    def send_kick_message(self, chat_user: ChatUser):
        raise NotImplementedError


def includeme(config):
    config.register_service_factory(lambda context, request: MessageService(request), iface=IMessageService)
