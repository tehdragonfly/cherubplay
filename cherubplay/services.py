import datetime, json

from sqlalchemy import and_

from cherubplay.lib import OnlineUserStore
from cherubplay.models import ChatUser, ChatUserStatus, Message, Session
from cherubplay.tasks import trigger_push_notification


class MessageService(object):
    def __init__(self, pubsub, chat):
        self.pubsub = pubsub
        self.chat   = chat

    def _send_message(self, chat_user, type, colour, text):
        posted_date = datetime.datetime.now()

        new_message = Message(
            chat_id=self.chat.id,
            user_id=chat_user.user_id,
            type=type,
            colour=colour,
            symbol=chat_user.symbol,
            text=text,
            posted=posted_date,
            edited=posted_date,
        )
        Session.add(new_message)
        Session.flush()

        self.chat.updated      = posted_date
        self.chat.last_user_id = chat_user.user_id

        try:
            # See if anyone else is online and update their ChatUser too.
            online_handles = OnlineUserStore(self.pubsub).online_handles(self.chat)
            for other_chat_user in Session.query(ChatUser).filter(and_(
                ChatUser.chat_id == self.chat.id,
                ChatUser.status == ChatUserStatus.active,
            )):
                if other_chat_user.handle in online_handles:
                    other_chat_user.visited = posted_date
                else:
                    self.pubsub.publish("user:" + str(other_chat_user.user_id), json.dumps({
                        "action": "notification",
                        "url":    self.chat.url,
                        "title":  other_chat_user.title or self.chat.url,
                        "colour": colour,
                        "symbol": chat_user.symbol_character,
                        "name":   chat_user.name,
                        "text":   text if len(text) < 100 else text[:97] + "...",
                    }))
                    trigger_push_notification.delay(other_chat_user.user_id)
        except ConnectionError:
            pass

        try:
            self.pubsub.publish("chat:%s" % self.chat.id, json.dumps({
                "action": "message",
                "message": {
                    "id":     new_message.id,
                    "type":   type,
                    "colour": colour,
                    "symbol": chat_user.symbol_character,
                    "name":   chat_user.name,
                    "text":   text,
                },
            }))
        except ConnectionError:
            pass

    def send_message(self, chat_user, type, colour, text):
        self._send_message(chat_user, type, colour, text)
        chat_user.last_colour = colour
        chat_user.draft = ""

    def send_end_message(self, chat_user):
        raise NotImplementedError

    def send_leave_message(self, chat_user):
        raise NotImplementedError

    def send_kick_message(self, chat_user):
        raise NotImplementedError

