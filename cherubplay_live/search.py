import json

from uuid import uuid4

from sqlalchemy.orm.exc import NoResultFound
from tornado.gen import engine, Task
from tornado.ioloop import IOLoop
from tornado.web import Application, HTTPError
from tornado.websocket import WebSocketHandler

from cherubplay.lib import colour_validator

from db import get_user

prompters = {}
searchers = {}

def write_message_to_searchers(message):
    for socket in searchers.values():
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
            }))
            print "PROMPTERS:", prompters
        if self.socket_id in searchers:
            searchers.pop(self.socket_id)
            print "SEARCHERS:", searchers

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
            self.write_message(json.dumps({
                "action": "prompts",
                "prompts": [
                    {
                        "id": _.socket_id,
                        "colour": _.colour,
                        "prompt": _.prompt,
                    } for _ in prompters.values()
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
            self.state = "prompting"
            prompters[self.socket_id] = self
            print "PROMPTERS:", prompters
            self.colour = message["colour"]
            self.prompt = message["prompt"]
            write_message_to_searchers(json.dumps({
                "action": "new_prompt",
                "id": self.socket_id,
                "colour": self.colour,
                "prompt": self.prompt,
            }))
        elif message["action"]=="idle":
            self.reset_state()
            self.state = "idle"

    def on_close(self):
        self.reset_state()

def main():
    application = Application([(r"/", SearchHandler)])
    application.listen(8000)
    IOLoop.instance().start()

