from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import contains_eager, joinedload
from zope.interface import Interface, implementer

from cherubplay.lib import username_validator
from cherubplay.models import BaseUserConnection, User, UserConnection, VirtualUserConnection


class IUserConnectionService(Interface):
    def __init__(self, request):
        pass

    def search(self, from_: User) -> List[BaseUserConnection]:
        pass

    def get(self, from_: User, to: str) -> Optional[BaseUserConnection]:
        pass


@implementer(IUserConnectionService)
class UserConnectionService(object):
    def __init__(self, request):
        self._db = request.find_service(name="db")

    def search(self, from_: User) -> List[BaseUserConnection]:
        # TODO VirtualUserConnection
        return (
            self._db.query(UserConnection)
            .filter(UserConnection.from_id == from_.id)
            .join(User, UserConnection.to_id == User.id)
            .options(
                contains_eager(UserConnection.to),
                joinedload(UserConnection.reverse),
            )
            .order_by(User.username).all()
        )

    def get(self, from_: User, to_username: str) -> Optional[BaseUserConnection]:
        if username_validator.match(to_username) is None:
            return None

        to = self._db.query(User).filter(User.username == to_username).scalar()

        if to is not None:
            return (
                self._db.query(UserConnection).filter(and_(
                    UserConnection.from_id == from_.id,
                    UserConnection.to_id   == to.id,
                ))
                .join(User, UserConnection.to_id == User.id)
                .options(
                    contains_eager(UserConnection.to),
                    joinedload(UserConnection.reverse),
                ).scalar()
            )

        return (
            self._db.query(VirtualUserConnection).filter(and_(
                VirtualUserConnection.from_id     == from_.id,
                VirtualUserConnection.to_username == to_username,
            )).scalar()
        )


def includeme(config):
    config.register_service_factory(lambda context, request: UserConnectionService(request), iface=IUserConnectionService)
