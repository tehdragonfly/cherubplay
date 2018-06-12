import uuid

from bcrypt import gensalt, hashpw
from datetime import datetime, timedelta
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.view import view_config
from sqlalchemy import and_, func
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound

from cherubplay.lib import prompt_categories, prompt_starters, prompt_levels
from cherubplay.models import Chat, ChatUser, PromptReport, Request, RequestSlot, User
from cherubplay.models.enums import ChatSource
from cherubplay.services.redis import INewsStore

status_filters = {
    "admin_report_list": "open",
    "admin_report_list_closed": "closed",
    "admin_report_list_invalid": "invalid",
}


@view_config(route_name="admin_report_list", renderer="layout2/admin/report_list.mako", request_method="GET", permission="admin")
@view_config(route_name="admin_report_list_closed", renderer="layout2/admin/report_list.mako", request_method="GET", permission="admin")
@view_config(route_name="admin_report_list_invalid", renderer="layout2/admin/report_list.mako", request_method="GET", permission="admin")
def report_list(request):

    try:
        current_status = status_filters[request.matched_route.name]
    except KeyError:
        raise HTTPNotFound
    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        raise HTTPNotFound

    db = request.find_service(name="db")
    reports = db.query(PromptReport).order_by(
        PromptReport.created.desc(),
    ).filter(PromptReport.status == current_status).options(
        joinedload(PromptReport.reporting_user),
        joinedload(PromptReport.reported_user),
    ).limit(25).offset((current_page-1)*25).all()

    # 404 on empty pages.
    if current_page != 1 and len(reports) == 0:
        raise HTTPNotFound

    report_count = (
        db.query(func.count('*')).select_from(PromptReport)
        .filter(PromptReport.status == current_status).scalar()
    )

    return {
        "PromptReport": PromptReport,
        "reports": reports,
        "report_count": report_count,
        "current_page": current_page,
        "prompt_categories": prompt_categories,
        "prompt_starters": prompt_starters,
        "prompt_levels": prompt_levels,
    }


def _report_form(context: PromptReport, request, **kwargs):
    db = request.find_service(name="db")
    return dict(
        PromptReport=PromptReport,
        prompt_categories=prompt_categories,
        prompt_starters=prompt_starters,
        prompt_levels=prompt_levels,
        duplicates=(
            db.query(PromptReport)
            .filter(PromptReport.duplicate_of_id == context.id)
            .order_by(PromptReport.id.desc()).all()
        ),
        chats=(
            db.query(Chat, ChatUser)
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
def report_get(context: PromptReport, request):
    return _report_form(context, request)


@view_config(route_name="admin_report_ext", request_method="GET", permission="admin", renderer="json")
def report_get_ext(context: PromptReport, request):
    return context


@view_config(route_name="admin_report", renderer="layout2/admin/report.mako", request_method="POST", permission="admin")
def report_post(context: PromptReport, request):

    for value in PromptReport.status.type.enums:
        if "status_" + value in request.POST:
            if value == "duplicate":
                try:
                    db = request.find_service(name="db")
                    duplicate_of = db.query(PromptReport).filter(PromptReport.id == int(request.POST["duplicate_of_id"])).one()
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


@view_config(route_name="admin_user", renderer="layout2/admin/user.mako", request_method="GET", permission="admin")
def user(context: User, request):
    return {}


def _remove_requests(db, user_id):
    db.query(Request).filter(and_(
        Request.user_id == user_id,
        Request.status == "posted",
    )).update({"status": "draft"})
    db.query(RequestSlot).filter(and_(
        RequestSlot.user_id == user_id,
        RequestSlot.order != 1,
    )).update({"user_id": None, "user_name": None}, synchronize_session=False)


@view_config(route_name="admin_user_status", request_method="POST", permission="admin")
def user_status(context: User, request):
    if context.status != "banned" and request.POST["status"] == "banned":
        context.unban_date = None
        _remove_requests(request.find_service(name="db"), context.id)
    context.status = request.POST["status"]
    return HTTPFound(request.route_path("admin_user", username=context.username, _query={"saved": "status"}))


@view_config(route_name="admin_user_chat", request_method="POST", permission="admin")
def user_chat(context: User, request):
    if context.status == "banned" or context.id == request.user.id:
        raise HTTPNotFound
    new_chat = Chat(url=str(uuid.uuid4()), source=ChatSource.admin)
    db = request.find_service(name="db")
    db.add(new_chat)
    db.flush()
    if "report_id" in request.POST:
        try:
            report = db.query(PromptReport).filter(PromptReport.id == int(request.POST["report_id"])).one()
            report.chat_ids = report.chat_ids + [new_chat.id]
        except (ValueError, NoResultFound):
            pass
    db.add(ChatUser(
        chat_id=new_chat.id,
        user_id=request.user.id,
        symbol=0,
        title="Chat with %s" % context.username,
    ))
    db.add(ChatUser(
        chat_id=new_chat.id,
        user_id=context.id,
        symbol=1,
        title="Admin chat"
    ))
    return HTTPFound(request.route_path("chat", url=new_chat.url))


@view_config(route_name="admin_user_ban", request_method="POST", permission="admin")
def user_ban(context: User, request):
    context.status = "banned"
    try:
        days = int(request.POST["days"])
    except (KeyError, ValueError):
        days = 1
    context.unban_date = datetime.now() + timedelta(days)
    _remove_requests(request.find_service(name="db"), context.id)
    return HTTPFound(request.route_path("admin_user", username=context.username, _query={"saved": "status"}))


@view_config(route_name="admin_user_reset_password", request_method="POST", permission="admin", renderer="layout2/admin/reset_password.mako")
def user_reset_password(context: User, request):
    new_password = str(uuid.uuid4())
    context.password = hashpw(new_password.encode("utf-8"), gensalt()).decode()
    return {"new_password": new_password}


@view_config(route_name="admin_news", request_method="GET", permission="admin", renderer="layout2/admin/news.mako")
def admin_news_get(request):
    return {"current_news": request.find_service(INewsStore).get_news()}


@view_config(route_name="admin_news", request_method="POST", permission="admin", renderer="layout2/admin/news.mako")
def admin_news_post(request):
    request.find_service(INewsStore).set_news(request.POST.get("news", ""))
    return HTTPFound(request.route_path("admin_news"))
