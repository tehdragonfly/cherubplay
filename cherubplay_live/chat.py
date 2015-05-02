import json

from uuid import uuid4

from tornado.gen import engine, Task
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.netutil import bind_unix_socket
from tornado.web import Application
from tornado.websocket import WebSocketHandler

from tornadoredis import Client

from cherubplay.lib import colour_validator, symbols
from cherubplay.models import Chat, ChatUser, Message

from db import config, get_chat, get_chat_user, get_user, publish_client

class ChatHandler(WebSocketHandler):

    def check_origin(self, origin):
        return True

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
        # Fire online message, but only if this is the only tab we have open.
        online_symbols = set(int(_) for _ in publish_client.hvals("online:"+str(self.chat.id)))
        if self.chat_user.symbol not in online_symbols:
            publish_client.publish("chat:"+str(self.chat.id), json.dumps({
                "action": "online",
                "symbol": symbols[self.chat_user.symbol],
            }))
        # See if the other person is online.
        for symbol in online_symbols:
            if symbol == self.chat_user.symbol:
                continue
            self.write_message({
                "action": "online",
                "symbol": symbols[symbol],
            })
        publish_client.hset("online:"+str(self.chat.id), self.socket_id, self.chat_user.symbol)
        self.redis_listen()
        self.ignore_next_message = False

    def on_message(self, message_string):
        message = json.loads(message_string)
        if message["action"] in ("typing", "stopped_typing"):
            publish_client.publish("chat:"+str(self.chat.id), json.dumps({
                "action": message["action"],
                "symbol": symbols[self.chat_user.symbol],
            }))
            # Ignore our own typing messages.
            self.ignore_next_message = True
        print message

    def on_close(self):
        # Unsubscribe here and let the exit callback handle disconnecting.
        self.redis_client.unsubscribe("chat:"+str(self.chat.id))
        publish_client.hdel("online:"+str(self.chat.id), self.socket_id)
        # Fire offline message, but only if we don't have any other tabs open.
        if str(self.chat_user.symbol) not in publish_client.hvals("online:"+str(self.chat.id)):
            publish_client.publish("chat:"+str(self.chat.id), json.dumps({
                "action": "offline",
                "symbol": symbols[self.chat_user.symbol],
            }))

    @engine
    def redis_listen(self):
        self.redis_client = Client(unix_socket_path=config.get("app:main", "cherubplay.socket_pubsub"))
        yield Task(self.redis_client.subscribe, "chat:"+str(self.chat.id))
        self.redis_client.listen(self.on_redis_message, self.on_redis_unsubscribe)

    def on_redis_message(self, message):
        if message.kind=="message":
            if not self.ignore_next_message:
                self.write_message(message.body)
                print "redis message:", message.body
            else:
                self.ignore_next_message = False

    def on_redis_unsubscribe(self, callback):
        self.redis_client.disconnect()

def main():
    application = Application([(r"/(.*)/", ChatHandler)])
    server = HTTPServer(application)
    socket = bind_unix_socket(config.get("app:main", "cherubplay.socket_chat"), mode=0777)
    server.add_socket(socket)
    IOLoop.instance().start()

