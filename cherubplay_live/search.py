import json
import re
import time

from uuid import uuid4

from sqlalchemy.orm.exc import NoResultFound
from tornado.gen import engine, Task
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.netutil import bind_unix_socket
from tornado.web import Application, HTTPError
from tornado.websocket import WebSocketHandler

from cherubplay.lib import colour_validator, prompt_categories, prompt_levels
from cherubplay.models import Chat, ChatUser, Message, PromptReport

from db import config, get_user, login_client, sm

prompters = {}
searchers = {}

deduplicate_regex = re.compile("[\W_]+")

def check_answer_limit(user_id):
    key = "answer_limit:%s" % user_id
    current_time = time.time()
    if login_client.llen(key) >= 6:
        if current_time - float(login_client.lindex(key, 0)) < 1800:
            return False
    login_client.rpush(key, current_time)
    login_client.ltrim(key, -6, -1)
    login_client.expire(key, 1800)
    return True

def write_message_to_searchers(message, category, level):
    for socket in searchers.values():
        if category in socket.categories and level in socket.levels:
            socket.write_message(message)

class SearchHandler(WebSocketHandler):

    def check_origin(self, origin):
        return True

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
            }), self.category, self.level)
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
            self.categories = set(_ for _ in message["categories"].split(",") if _ in prompt_categories)
            self.levels = set(_ for _ in message["levels"].split(",") if _ in prompt_levels)
            searchers[self.socket_id] = self
            print "SEARCHERS:", searchers
            self.write_message(json.dumps({
                "action": "prompts",
                "prompts": [
                    {
                        "id": _.socket_id,
                        "colour": _.colour,
                        "prompt": _.prompt,
                        "category": _.category,
                        "level": _.level,
                    }
                    for _ in prompters.values()
                    if _.category in self.categories and _.level in self.levels
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
            if message["category"] not in prompt_categories:
                self.write_message(json.dumps({
                    "action": "prompt_error",
                    "error": "The specified category doesn't seem to exist.",
                }))
                return
            if message["level"] not in prompt_levels:
                self.write_message(json.dumps({
                    "action": "prompt_error",
                    "error": "The specified level doesn't seem to exist.",
                }))
                return
            deduplicated_prompt = deduplicate_regex.sub("", message["prompt"])
            for prompter in prompters.values():
                if deduplicated_prompt == prompter.deduplicated_prompt:
                    self.write_message(json.dumps({
                        "action": "prompt_error",
                        "error": "This prompt is already on the front page. Please don't post the same prompt more than once.",
                    }))
            self.state = "prompting"
            prompters[self.socket_id] = self
            print "PROMPTERS:", prompters
            self.colour = message["colour"]
            self.prompt = message["prompt"]
            self.deduplicated_prompt = deduplicated_prompt
            self.category = message["category"]
            self.level = message["level"]
            write_message_to_searchers(json.dumps({
                "action": "new_prompt",
                "id": self.socket_id,
                "colour": self.colour,
                "prompt": self.prompt,
                "category": self.category,
                "level": self.level,
            }), self.category, self.level)
        elif message["action"]=="idle":
            self.reset_state()
            self.state = "idle"
        elif message["action"]=="report":
            if self.socket_id not in searchers or message["id"] not in prompters:
                return
            prompter = prompters[message["id"]]
            # Validate reason
            if message["reason"] not in PromptReport.reason.type.enums:
                return
            if message["reason"] == "wrong_category" and (
                message["category"] not in prompt_categories
                or message["level"] not in prompt_levels
            ):
                return
            # Make a new session for thread safety.
            Session = sm()
            Session.add(PromptReport(
                reporting_user_id=self.user.id,
                reported_user_id=prompter.user.id,
                colour=prompter.colour,
                prompt=prompter.prompt,
                category=prompter.category,
                level=prompter.level,
                reason=message["reason"],
                reason_category=message["category"] if message["reason"] == "wrong_category" else None,
                reason_level=message["level"] if message["reason"] == "wrong_category" else None,
            ))
            Session.commit()
            del Session
        elif message["action"]=="answer":
            if not check_answer_limit(self.user.id):
                self.write_message(json.dumps({
                    "action": "answer_error",
                    "error": "NO NO THAT IS TOO MUCH ANSWER",
                }))
                return
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

