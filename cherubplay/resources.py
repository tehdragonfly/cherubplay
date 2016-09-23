from pyramid.httpexceptions import HTTPNotFound
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound

from .models import Session, Prompt, PromptReport, Request, RequestTag


def prompt_factory(request):
    try:
        return Session.query(Prompt).filter(and_(
            Prompt.user_id == request.user.id,
            Prompt.id == int(request.matchdict["id"]),
        )).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound


def report_factory(request):
    try:
        return Session.query(PromptReport).filter(
            PromptReport.id == int(request.matchdict["id"])
        ).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound


def request_factory(request):
    if not request.user:
        raise HTTPNotFound

    try:
        return Session.query(Request).filter(and_(
            Request.id == int(request.matchdict["id"]),
            or_(
                request.user.tag_status_filter,
                Request.user_id == request.user.id,
            ),
        )).options(
            joinedload(Request.tags)
        ).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound

