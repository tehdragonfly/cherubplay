from pyramid.httpexceptions import HTTPNotFound
from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound

from .models import Session, Prompt


def prompt_factory(request):
    try:
        return Session.query(Prompt).filter(and_(
            Prompt.user_id == request.user.id,
            Prompt.id == int(request.matchdict["id"]),
        )).one()
    except (ValueError, NoResultFound):
        raise HTTPNotFound

