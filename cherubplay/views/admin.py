import transaction
import uuid

from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.view import view_config
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound
from webhelpers import paginate

from ..lib import prompt_categories
from ..models import (
    Session,
    Chat,
    ChatUser,
    PromptReport,
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


@view_config(route_name="admin_report_list", renderer="admin/report_list.mako", request_method="GET", permission="admin")
def report_list(request):
    current_page = int(request.GET.get("page", 1))
    reports = Session.query(PromptReport).order_by(
        PromptReport.created.desc()
    ).options(
        joinedload(PromptReport.reporting_user),
        joinedload(PromptReport.reported_user),
    ).limit(25).offset((current_page-1)*25).all()
    # 404 on empty pages.
    if current_page!=1 and len(reports)==0:
        raise HTTPNotFound
    report_count = Session.query(func.count('*')).select_from(PromptReport).scalar()
    paginator = paginate.Page(
        [],
        page=current_page,
        items_per_page=25,
        item_count=report_count,
        url=paginate.PageURL(
            request.route_path("admin_report_list"),
            { "page": current_page }
        ),
    )
    return {
        "reports": reports,
        "paginator": paginator,
        "prompt_categories": prompt_categories,
    }


@view_config(route_name="admin_report", renderer="admin/report.mako", request_method="GET", permission="admin")
def report_get(request):
    try:
        report = Session.query(PromptReport).filter(PromptReport.id==int(request.matchdict["id"])).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound
    return {
        "report": report,
        "prompt_categories": prompt_categories,
    }


@view_config(route_name="admin_report", renderer="admin/report.mako", request_method="POST", permission="admin")
def report_post(request):
    try:
        report = Session.query(PromptReport).filter(PromptReport.id==int(request.matchdict["id"])).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound
    report.notes = request.POST["notes"]
    return {
        "report": report,
        "prompt_categories": prompt_categories,
    }


@view_config(route_name="admin_user", renderer="admin/user.mako", request_method="GET", permission="admin")
def user(request):
    try:
        user = Session.query(User).filter(User.username==request.matchdict["username"]).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound
    return {
        "user": user,
    }


