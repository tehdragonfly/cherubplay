import transaction
import uuid

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from sqlalchemy.orm.exc import NoResultFound

from ..models import (
    Session,
    Chat,
    ChatUser,
    User,
)

@view_config(route_name="admin_ban", renderer="admin/ban.mako", request_method="GET", permission="admin")
def ban_get(request):
    return { "feedback": None }

@view_config(route_name="admin_ban", renderer="admin/ban.mako", request_method="POST", permission="admin")
def ban_post(request):
    try:
        user = Session.query(User).filter(User.username==request.POST["username"]).one()
    except NoResultFound:
        return { "feedback": "User %s not found." % request.POST["username"] }
    if user.status=="banned":
        return { "feedback": "User %s is already banned." % request.POST["username"] }
    user.status = "banned"
    return { "feedback": "User %s has now been banned." % request.POST["username"] }

@view_config(route_name="admin_chat", renderer="admin/chat.mako", request_method="GET", permission="admin")
def chat_get(request):
    return { "feedback": None }

@view_config(route_name="admin_chat", renderer="admin/chat.mako", request_method="POST", permission="admin")
def chat_post(request):
    if request.POST["username"]==request.user.username:
        return { "feedback": "You can't chat with yourself." }
    try:
        user = Session.query(User).filter(User.username==request.POST["username"]).one()
    except NoResultFound:
        return { "feedback": "User %s not found." % request.POST["username"] }
    if user.status=="banned":
        return { "feedback": "User %s is banned." % request.POST["username"] }
    new_chat = Chat(url=str(uuid.uuid4()))
    Session.add(new_chat)
    Session.flush()
    Session.add(ChatUser(
        chat_id=new_chat.id,
        user_id=request.user.id,
        symbol=0,
        title="Chat with %s" % user.username,
    ))
    Session.add(ChatUser(
        chat_id=new_chat.id,
        user_id=user.id,
        symbol=1,
        title="Admin chat"
    ))
    return HTTPFound(request.route_path("chat", url=new_chat.url))

