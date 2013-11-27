import json

from uuid import uuid4

from tornado.gen import engine, Task
from tornado.ioloop import IOLoop
from tornado.web import Application
from tornado.websocket import WebSocketHandler

from tornadoredis import Client

from cherubplay.lib import colour_validator
from cherubplay.models import Chat, ChatUser, Message

from db import config, get_chat, get_chat_user, get_user

class ChatHandler(WebSocketHandler):

    def open(self, chat_url):
        print chat_url
        self.user = get_user(self.cookies)
        if self.user is None:
            self.close()
            return
        self.chat = get_chat(chat_url)
        if self.chat is None:
            self.close()
            return
        self.chat_user = get_chat_user(self.chat.id, self.user.id)
        if self.chat_user is None:
            self.close()
            return
        self.socket_id = str(uuid4())
        self.redis_listen()

    def on_message(self, message_string):
        pass

    def on_close(self):
        self.redis_client.disconnect()

    @engine
    def redis_listen(self):
        self.redis_client = Client(unix_socket_path=config.get("app:main", "cherubplay.pubsub"))
        yield Task(self.redis_client.subscribe, "chat:"+str(self.chat.id))
        self.redis_client.listen(self.on_redis_message)

    def on_redis_message(self, message):
        if message.kind=="message":
            self.write_message(message.body)

def main():
    application = Application([(r"/(.*)/", ChatHandler)])
    application.listen(8001)
    IOLoop.instance().start()

