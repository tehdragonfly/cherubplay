import transaction
import uuid

from datetime import datetime, timedelta
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


status_filters = {
    "admin_report_list": "open",
    "admin_report_list_closed": "closed",
    "admin_report_list_invalid": "invalid",
}


@view_config(route_name="admin_report_list", renderer="layout2/admin/report_list.mako", request_method="GET", permission="admin")
@view_config(route_name="admin_report_list_closed", renderer="layout2/admin/report_list.mako", request_method="GET", permission="admin")
@view_config(route_name="admin_report_list_invalid", renderer="layout2/admin/report_list.mako", request_method="GET", permission="admin")
def report_list(request):
    current_status = status_filters[request.matched_route.name]
    current_page = int(request.GET.get("page", 1))
    reports = Session.query(PromptReport).order_by(
        PromptReport.created.desc(),
    ).filter(PromptReport.status == current_status).options(
        joinedload(PromptReport.reporting_user),
        joinedload(PromptReport.reported_user),
    ).limit(25).offset((current_page-1)*25).all()
    # 404 on empty pages.
    if current_page!=1 and len(reports)==0:
        raise HTTPNotFound
    report_count = Session.query(func.count('*')).select_from(PromptReport).filter(PromptReport.status == current_status).scalar()
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
        "PromptReport": PromptReport,
        "reports": reports,
        "paginator": paginator,
        "prompt_categories": prompt_categories,
        "prompt_levels": prompt_levels,
    }


@view_config(route_name="admin_report", renderer="layout2/admin/report.mako", request_method="GET", permission="admin")
def report_get(request):
    try:
        report = Session.query(PromptReport).filter(PromptReport.id==int(request.matchdict["id"])).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound
    return {
        "PromptReport": PromptReport,
        "report": report,
        "prompt_categories": prompt_categories,
        "prompt_levels": prompt_levels,
    }


@view_config(route_name="admin_report", renderer="layout2/admin/report.mako", request_method="POST", permission="admin")
def report_post(request):
    try:
        report = Session.query(PromptReport).filter(PromptReport.id==int(request.matchdict["id"])).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound
    if request.POST["status"] in PromptReport.status.type.enums:
        report.status = request.POST["status"]
    report.notes = request.POST["notes"]
    return {
        "PromptReport": PromptReport,
        "report": report,
        "prompt_categories": prompt_categories,
        "prompt_levels": prompt_levels,
    }


def _get_user(request):
    try:
        return Session.query(User).filter(User.username==request.matchdict["username"]).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound


@view_config(route_name="admin_user", renderer="layout2/admin/user.mako", request_method="GET", permission="admin")
def user(request):
    user = _get_user(request)
    return {
        "user": user,
    }


@view_config(route_name="admin_user_status", request_method="POST", permission="admin")
def user_status(request):
    user = _get_user(request)
    if user.status != "banned" and request.POST["status"] == "banned":
        user.unban_date = None
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


@view_config(route_name="admin_user_ban", request_method="POST", permission="admin")
def user_ban(request):
    user = _get_user(request)
    user.status = "banned"
    try:
        days = int(request.POST["days"])
    except KeyError, ValueError:
        days = 1
    user.unban_date = datetime.now() + timedelta(days)
    return HTTPFound(request.route_path("admin_user", username=request.matchdict["username"], _query={ "saved": "status" }))


