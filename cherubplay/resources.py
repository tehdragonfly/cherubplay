from pyramid.httpexceptions import HTTPNotFound
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload_all
from sqlalchemy.orm.exc import NoResultFound

from .models import Session, Prompt, Request, RequestTag


def prompt_factory(request):
    try:
        return Session.query(Prompt).filter(and_(
            Prompt.user_id == request.user.id,
            Prompt.id == int(request.matchdict["id"]),
        )).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound


def request_factory(request):
    try:
        return Session.query(Request).filter(and_(
            Request.id == int(request.matchdict["id"]),
            or_(
                Request.status == "posted",
                Request.user_id == request.user.id,
            ),
        )).options(
            joinedload_all(Request.tags, RequestTag.tag)
        ).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound

