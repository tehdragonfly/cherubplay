import transaction
import uuid

from datetime import datetime, timedelta
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.view import view_config
from sqlalchemy import and_, func
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound

from ..lib import prompt_categories, prompt_levels
from ..models import (
    Session,
    Chat,
    ChatUser,
    PromptReport,
    Request,
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
    return {
        "PromptReport": PromptReport,
        "reports": reports,
        "report_count": report_count,
        "current_page": current_page,
        "prompt_categories": prompt_categories,
        "prompt_levels": prompt_levels,
    }


def _report_form(context, request, **kwargs):
    return dict(
        PromptReport=PromptReport,
        prompt_categories=prompt_categories,
        prompt_levels=prompt_levels,
        duplicates=(
            Session.query(PromptReport)
            .filter(PromptReport.duplicate_of_id == context.id)
            .order_by(PromptReport.id.desc()).all()
        ),
        chats=(
            Session.query(Chat, ChatUser)
            .outerjoin(ChatUser, and_(
                ChatUser.chat_id == Chat.id,
                ChatUser.user_id == request.user.id,
            ))
            .filter(and_(
                Chat.id.in_(context.chat_ids),
            ))
            .order_by(Chat.id.asc()).all()
        ) if context.chat_ids else [],
        **kwargs
    )


@view_config(route_name="admin_report", request_method="GET", permission="admin", renderer="layout2/admin/report.mako")
def report_get(context, request):
    return _report_form(context, request)


@view_config(route_name="admin_report_ext", request_method="GET", permission="admin", renderer="json")
def report_get_ext(context, request):
    return context


@view_config(route_name="admin_report", renderer="layout2/admin/report.mako", request_method="POST", permission="admin")
def report_post(context, request):

    for value in PromptReport.status.type.enums:
        if "status_" + value in request.POST:
            if value == "duplicate":
                try:
                    duplicate_of = Session.query(PromptReport).filter(PromptReport.id == int(request.POST["duplicate_of_id"])).one()
                    if duplicate_of.id == context.id:
                        raise ValueError("a report can't be a duplicate of itself")
                except (KeyError, ValueError, NoResultFound):
                    return _report_form(context, request, error="no_report")
                context.duplicate_of_id = duplicate_of.id
            else:
                context.duplicate_of_id = None
            context.status = value
            break

    if "notes" in request.POST:
        context.notes = request.POST["notes"]

    return _report_form(context, request)


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
        Session.query(Request).filter(Request.user_id == user.id).update({"status": "removed"})
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
    if "report_id" in request.POST:
        try:
            report = Session.query(PromptReport).filter(PromptReport.id == int(request.POST["report_id"])).one()
            report.chat_ids = report.chat_ids + [new_chat.id]
        except (ValueError, NoResultFound):
            pass
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


@view_config(route_name="api_users", request_method="GET", permission="admin", renderer="json")
def api_users(request):
    if not request.GET.get("email_address"):
        raise HTTPNotFound
    return {
        "users": [
            {"id": user.id, "username": user.username} for user in
            Session.query(User).filter(and_(
                func.lower(User.email) == request.GET["email_address"].strip().lower()[:100],
                User.email_verified == True,
            ))
        ]
    }

