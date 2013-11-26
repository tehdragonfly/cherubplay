from sqlalchemy.orm.exc import NoResultFound
from tornado.gen import engine, Task
from tornado.ioloop import IOLoop
from tornado.web import Application, HTTPError
from tornado.websocket import WebSocketHandler

from db import get_user

class SearchHandler(WebSocketHandler):
    def open(self):
        self.user = get_user(self.cookies)
        if self.user is None:
            self.close()
            return
        self.state = "idle"

def main():
    application = Application([(r"/search/", SearchHandler)])
    application.listen(8000)
    IOLoop.instance().start()

