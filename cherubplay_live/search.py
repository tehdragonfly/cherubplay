import json
import re
import time

from datetime import datetime, timedelta
from urllib.parse import urlparse
from uuid import uuid4

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.netutil import bind_unix_socket
from tornado.web import Application
from tornado.websocket import WebSocketHandler, WebSocketClosedError

from cherubplay.lib import colour_validator, prompt_hash, prompt_categories, prompt_starters, prompt_levels
from cherubplay.lib.formatters import html_formatters
from cherubplay.models import Chat, ChatUser, Message, PromptReport
from cherubplay.models.enums import ChatSource, MessageFormat

from cherubplay_live.db import config, db_session, get_user, login_client

prompters = {}
searchers = {}

url_regex = re.compile("https?:\/\/\S+")


class AnswerDenied(Exception):
    pass


ANSWER_LIMIT_TIME = 3600 # 1 hour
PROMPT_HASH_TIME = 86400 # 24 hours


def check_answer_limit(user_id):
    key = "answer_limit:%s" % user_id
    current_time = time.time()
    if login_client.llen(key) >= 12:
        if current_time - float(login_client.lindex(key, 0)) < ANSWER_LIMIT_TIME:
            raise AnswerDenied("User %s has exceeded the answer limit." % user_id)
    login_client.rpush(key, current_time)
    login_client.ltrim(key, -12, -1)
    login_client.expire(key, ANSWER_LIMIT_TIME)


def check_prompt_hash(user_id, prompt_hash):
    key = "answered:%s:%s" % (user_id, prompt_hash)
    if login_client.exists(key):
        raise AnswerDenied("User %s has answered prompt %s too recently." % (user_id, prompt_hash))
    login_client.setex(key, time=PROMPT_HASH_TIME, value="1")


def write_message_to_searchers(message, category, starter, level):
    closed_sockets = []
    for socket_id, socket in searchers.items():
        if category in socket.categories and starter in socket.starters and level in socket.levels:
            try:
                socket.write_message(message)
            except WebSocketClosedError:
                closed_sockets.append(socket_id)
    for socket_id in closed_sockets:
        print("Removing dead searcher %s" % socket_id)
        searchers.pop(socket_id)


class SearchHandler(WebSocketHandler):

    user      = None
    socket_id = None
    state     = "idle"

    def check_origin(self, origin):
        return origin == config.get("app:main", "cherubplay.socket_origin")

    def open(self):
        with db_session() as db:
            self.user = get_user(db, self.cookies)
            if self.user is None:
                self.close()
                return
        self.socket_id = str(uuid4())

    def reset_state(self):
        if not self.socket_id:
            return
        if self.socket_id in prompters:
            prompters.pop(self.socket_id)
            write_message_to_searchers(json.dumps({
                "action": "remove_prompt",
                "id": self.socket_id,
            }), self.category, self.starter, self.level)
        if self.socket_id in searchers:
            searchers.pop(self.socket_id)

    def on_message(self, message_string):
        try:
            message = json.loads(message_string)
        except ValueError:
            return
        if message["action"] == "search":
            self.reset_state()
            self.state = "searching"
            self.categories = {_ for _ in message["categories"].split(",") if _ in prompt_categories}
            self.starters   = {_ for _ in message["starters"].split(",")   if _ in prompt_starters  }
            self.levels     = {_ for _ in message["levels"].split(",")     if _ in prompt_levels    }
            searchers[self.socket_id] = self
            self.write_message(json.dumps({
                "action": "prompts",
                "prompts": [
                    {
                        "id":       _.socket_id,
                        "colour":   _.colour,
                        "prompt": _.prompt,
                        "prompt_html": _.prompt_html,
                        "category": _.category,
                        "starter":  _.starter,
                        "level":    _.level,
                        "images":   _.images,
                    }
                    for _ in prompters.values()
                    if _.category in self.categories and _.starter in self.starters and _.level in self.levels
                ]
            }))
        elif message["action"] == "prompt":
            self.reset_state()
            if colour_validator.match(message["colour"]) is None:
                self.write_message(json.dumps({
                    "action": "prompt_error",
                    "error": "The colour needs to be a valid hex code, for example \"#0715CD\" or \"#A15000\".",
                }))
                return
            try:
                format_ = MessageFormat(message["format"])
            except ValueError:
                self.write_message(json.dumps({
                    "action": "prompt_error",
                    "error": "Bad format.",
                }))
                return
            if message["prompt"].strip() == "":
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
            if message["starter"] not in prompt_starters:
                self.write_message(json.dumps({
                    "action": "prompt_error",
                    "error": "Please specify whether your prompt has a starter.",
                }))
                return
            if message["level"] not in prompt_levels:
                self.write_message(json.dumps({
                    "action": "prompt_error",
                    "error": "The specified level doesn't seem to exist.",
                }))
                return
            message_hash = prompt_hash(message["prompt"])
            for prompter in prompters.values():
                if message_hash == prompter.hash:
                    self.write_message(json.dumps({
                        "action": "prompt_error",
                        "error": "This prompt is already on the front page. Please don't post the same prompt more than once.",
                    }))
            self.state = "prompting"
            prompters[self.socket_id] = self
            self.colour   = message["colour"]
            self.prompt   = message["prompt"]
            self.format   = format_
            self.prompt_html = html_formatters[format_](self.prompt)
            self.hash     = message_hash
            self.category = message["category"]
            self.starter  = message["starter"]
            self.level    = message["level"]

            self.images = []
            for url in url_regex.findall(self.prompt):
                parsed_url = urlparse(url)
                if parsed_url.netloc == "imgur.com":
                    # Skip album links
                    if parsed_url.path.rindex("/") != 0:
                        continue
                    path_with_extension = parsed_url.path if "." in parsed_url.path else parsed_url.path + ".jpg"
                    self.images.append("https://i.imgur.com" + path_with_extension)
                elif (
                    parsed_url.netloc == "i.imgur.com"
                    or parsed_url.netloc.endswith(".media.tumblr.com")
                    or parsed_url.netloc == "media.tumblr.com"
                    or parsed_url.netloc == "cdn.discordapp.com"
                    or parsed_url.netloc == "pbs.twimg.com"
                ):
                    extension = parsed_url.path.split(".")[-1]
                    if extension in ("jpg", "jpeg", "png", "gif", "webp"):
                        # Rewrite URL to force HTTPS
                        self.images.append("https://" + parsed_url.netloc + parsed_url.path)
                    elif parsed_url.netloc == "i.imgur.com" and extension == "gifv":
                        self.images.append("https://" + parsed_url.netloc + parsed_url.path[:-1])
                if len(self.images) == 3:
                    break

            write_message_to_searchers(json.dumps({
                "action":   "new_prompt",
                "id":       self.socket_id,
                "colour":   self.colour,
                "prompt":   self.prompt,
                "prompt_html":   self.prompt_html,
                "category": self.category,
                "starter":  self.starter,
                "level":    self.level,
                "images":   self.images,
            }), self.category, self.starter, self.level)
        elif message["action"] == "idle":
            self.reset_state()
            self.state = "idle"
        elif message["action"] == "report":
            if self.socket_id not in searchers or message["id"] not in prompters:
                return
            prompter = prompters[message["id"]]
            # Validate reason
            if message["reason"] not in PromptReport.reason.type.enums:
                return
            if message["reason"] == "wrong_category" and (
                message["category"] not in prompt_categories
                or message["starter"] not in prompt_starters
                or message["level"] not in prompt_levels
            ):
                return
            with db_session() as db:
                db.add(PromptReport(
                    reporting_user_id=self.user.id,
                    reported_user_id=prompter.user.id,
                    colour=prompter.colour,
                    prompt=prompter.prompt,
                    category=prompter.category,
                    starter=prompter.starter,
                    level=prompter.level,
                    reason=message["reason"],
                    reason_category=message["category"] if message["reason"] == "wrong_category" else None,
                    reason_starter=message["starter"] if message["reason"] == "wrong_category" else None,
                    reason_level=message["level"] if message["reason"] == "wrong_category" else None,
                ))
        elif message["action"] == "answer":
            if self.socket_id not in searchers or message["id"] not in prompters:
                self.write_message(json.dumps({
                    "action": "answer_error",
                    "error": "Sorry, either this prompt has already been taken or the prompter has disconnected.",
                }))
                return
            prompter = prompters[message["id"]]
            try:
                check_answer_limit(self.user.id)
                check_prompt_hash(self.user.id, prompter.hash)
            except AnswerDenied:
                self.write_message(json.dumps({
                    "action": "answer_error",
                    "error": "Sorry, you've answered too many prompts recently. Please try again later.",
                }))
                return
            with db_session() as db:
                new_chat_url = str(uuid4())
                new_chat = Chat(url=new_chat_url, source=ChatSource.front_page)
                db.add(new_chat)
                db.flush()
                db.add(ChatUser(
                    chat_id=new_chat.id,
                    user_id=prompter.user.id,
                    last_colour=prompter.colour,
                    symbol=0,
                ))
                # Only create one ChatUser if prompter and searcher are the same person.
                if self.user.id != prompter.user.id:
                    db.add(ChatUser(
                        chat_id=new_chat.id,
                        user_id=self.user.id,
                        symbol=1,
                    ))
                posted_date = datetime.now()
                new_message = Message(
                    chat_id=new_chat.id,
                    user_id=prompter.user.id,
                    colour=prompter.colour,
                    symbol=0,
                    posted=posted_date,
                    edited=posted_date,
                )
                new_message.text.update(prompter.format, prompter.prompt)
                db.add(new_message)
                response = json.dumps({"action": "chat", "url": new_chat_url})
                prompter.write_message(response)
                self.write_message(response)

    def on_close(self):
        self.reset_state()


def main():
    application = Application([(r"/", SearchHandler)])
    server = HTTPServer(application)
    socket = bind_unix_socket(config.get("app:main", "cherubplay.socket_search"), mode=0o777)
    server.add_socket(socket)
    IOLoop.instance().start()

