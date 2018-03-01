import re

from sqlalchemy import and_, func
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound
from zope.interface import Interface, implementer

from cherubplay.models import Tag
from cherubplay.models.enums import TagType


class CreateNotAllowed(Exception): pass


class ITagService(Interface):
    def get_or_create(
        self,
        tag_type: TagType,
        name: str,
        allow_maturity_and_type_creation: bool=True,
        create_opposite_tag: bool=True,
    ) -> Tag:
        pass


@implementer(ITagService)
class TagService(object):
    def __init__(self, db):
        self._db = db

    def get_or_create(
        self,
        tag_type: TagType,
        name: str,
        allow_maturity_and_type_creation: bool=True,
        create_opposite_tag: bool=True,
    ) -> Tag:
        name = re.sub("\s+", " ", name)
        try:
            tag = (
                self._db.query(Tag)
                .filter(and_(
                    Tag.type == tag_type,
                    func.lower(Tag.name) == name.lower()
                ))
                .options(joinedload(Tag.synonym_of))
                .one()
            )
        except NoResultFound:
            if not allow_maturity_and_type_creation and tag_type in (TagType.maturity, TagType.type):
                raise CreateNotAllowed
            tag = Tag(type=tag_type, name=name)
            self._db.add(tag)
            self._db.flush()
            if create_opposite_tag:
                if tag_type in TagType.playing_types:
                    self.get_or_create(tag_type.wanted, name, create_opposite_tag=False)
                elif tag_type in TagType.wanted_types:
                    self.get_or_create(tag_type.playing, name, create_opposite_tag=False)
        return tag


def includeme(config):
    config.register_service_factory(lambda context, request: TagService(
        request.find_service(name="db"),
    ), iface=ITagService)
