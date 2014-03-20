import json

from uuid import uuid4

from sqlalchemy.orm.exc import NoResultFound
from tornado.gen import engine, Task
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.netutil import bind_unix_socket
from tornado.web import Application, HTTPError
from tornado.websocket import WebSocketHandler

from cherubplay.lib import colour_validator
from cherubplay.models import Chat, ChatUser, Message

from db import config, get_user, sm

prompters = {}
searchers = {}
nsfw_searchers = {}

def write_message_to_searchers(message, nsfw):
    for socket in (nsfw_searchers if nsfw else searchers).values():
        socket.write_message(message)

class SearchHandler(WebSocketHandler):

    def open(self):
        self.user = get_user(self.cookies)
        if self.user is None:
            self.close()
            return
        self.socket_id = str(uuid4())
        print "NEW SOCKET: ", self.socket_id
        self.state = "idle"
        self.write_message(json.dumps({ "username": self.user.username}))

    def reset_state(self):
        if self.socket_id in prompters:
            prompters.pop(self.socket_id)
            write_message_to_searchers(json.dumps({
                "action": "remove_prompt",
                "id": self.socket_id,
            }), self.nsfw)
            print "PROMPTERS:", prompters
        if self.socket_id in searchers:
            searchers.pop(self.socket_id)
            print "SEARCHERS:", searchers
        if self.socket_id in nsfw_searchers:
            nsfw_searchers.pop(self.socket_id)
            print "NSFW SEARCHERS:", nsfw_searchers

    def on_message(self, message_string):
        try:
            message = json.loads(message_string)
        except ValueError:
            return
        if message["action"]=="search":
            self.reset_state()
            self.state = "searching"
            searchers[self.socket_id] = self
            print "SEARCHERS:", searchers
            if message["nsfw"]:
                nsfw_searchers[self.socket_id] = self
                print "NSFW SEARCHERS:", nsfw_searchers
            self.write_message(json.dumps({
                "action": "prompts",
                "prompts": [
                    {
                        "id": _.socket_id,
                        "colour": _.colour,
                        "prompt": _.prompt,
                        "nsfw": _.nsfw,
                    }
                    for _ in prompters.values()
                    if message["nsfw"] or not _.nsfw
                ]
            }))
        elif message["action"]=="prompt":
            self.reset_state()
            if colour_validator.match(message["colour"]) is None:
                self.write_message(json.dumps({
                    "action": "prompt_error",
                    "error": "The colour needs to be a valid hex code, for example \"#0715CD\" or \"#A15000\".",
                }))
                return
            if message["prompt"].strip()=="":
                self.write_message(json.dumps({
                    "action": "prompt_error",
                    "error": "You can't submit a blank prompt.",
                }))
                return
            if "Oan you believe this is happening?" in message["prompt"]:
                for line in message["prompt"].split("\n"):
                    if line.strip()!="":
                        self.write_message(json.dumps({
                            "action": "prompt_error",
                            "error": line,
                        }))
                self.close()
                return
            self.state = "prompting"
            prompters[self.socket_id] = self
            print "PROMPTERS:", prompters
            self.colour = message["colour"]
            self.prompt = message["prompt"]
            self.nsfw = message["nsfw"]
            write_message_to_searchers(json.dumps({
                "action": "new_prompt",
                "id": self.socket_id,
                "colour": self.colour,
                "prompt": self.prompt,
                "nsfw": self.nsfw,
            }), self.nsfw)
        elif message["action"]=="idle":
            self.reset_state()
            self.state = "idle"
        elif message["action"]=="answer":
            if self.socket_id not in searchers or message["id"] not in prompters:
                self.write_message(json.dumps({
                    "action": "answer_error",
                    "error": "Sorry, either this prompt has already been taken or the prompter has disconnected.",
                }))
                return
            prompter = prompters[message["id"]]
            # Make a new session for thread safety.
            Session = sm()
            new_chat_url = str(uuid4())
            new_chat = Chat(url=new_chat_url)
            Session.add(new_chat)
            Session.flush()
            Session.add(ChatUser(
                chat_id=new_chat.id,
                user_id=prompter.user.id,
                last_colour=prompter.colour,
                symbol=0,
            ))
            # Only create one ChatUser if prompter and searcher are the same person.
            if self.user.id!=prompter.user.id:
                Session.add(ChatUser(
                    chat_id=new_chat.id,
                    user_id=self.user.id,
                    symbol=1,
                ))
            Session.add(Message(
                chat_id=new_chat.id,
                user_id=prompter.user.id,
                colour=prompter.colour,
                symbol=0,
                text=prompter.prompt,
            ))
            Session.commit()
            response = json.dumps({ "action": "chat", "url": new_chat_url })
            prompter.write_message(response)
            self.write_message(response)
            del Session

    def on_close(self):
        self.reset_state()

def main():
    application = Application([(r"/", SearchHandler)])
    server = HTTPServer(application)
    socket = bind_unix_socket(config.get("app:main", "cherubplay.socket_search"), mode=0777)
    server.add_socket(socket)
    IOLoop.instance().start()

