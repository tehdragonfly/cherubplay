import transaction
import uuid

from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.view import view_config
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound
from webhelpers import paginate

from ..lib import prompt_categories, prompt_levels
from ..models import (
    Session,
    Chat,
    ChatUser,
    PromptReport,
    User,
)


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
        "prompt_levels": prompt_levels,
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
        "prompt_levels": prompt_levels,
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
        "prompt_levels": prompt_levels,
    }


def _get_user(request):
    try:
        return Session.query(User).filter(User.username==request.matchdict["username"]).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound


@view_config(route_name="admin_user", renderer="admin/user.mako", request_method="GET", permission="admin")
def user(request):
    user = _get_user(request)
    return {
        "user": user,
    }


@view_config(route_name="admin_user_status", request_method="POST", permission="admin")
def user_status(request):
    user = _get_user(request)
    user.status = request.POST["status"]
    return HTTPFound(request.route_path("admin_user", username=request.matchdict["username"], _query={ "saved": "status" }))


@view_config(route_name="admin_user_chat", request_method="POST", permission="admin")
def user_chat(request):
    user = _get_user(request)
    if user.status == "banned" or user.id == request.user.id:
        raise HTTPNotFound
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


