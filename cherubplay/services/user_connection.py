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

    def create(self, from_: User, to_username: str) -> Optional[BaseUserConnection]:
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
            return self._get_user_connection(from_, to)
        return self._get_virtual_user_connection(from_, to_username)

    def _get_user_connection(self, from_: User, to: User) -> Optional[UserConnection]:
        return (
            self._db.query(UserConnection).filter(and_(
                UserConnection.from_id == from_.id,
                UserConnection.to_id == to.id,
            ))
            .join(User, UserConnection.to_id == User.id)
                .options(
                contains_eager(UserConnection.to),
                joinedload(UserConnection.reverse),
            ).scalar()
        )

    def _get_virtual_user_connection(self, from_, to_username) -> Optional[VirtualUserConnection]:
        return (
            self._db.query(VirtualUserConnection).filter(and_(
                VirtualUserConnection.from_id == from_.id,
                VirtualUserConnection.to_username == to_username,
            )).scalar()
        )

    def create(self, from_: User, to_username: str) -> Optional[BaseUserConnection]:
        if username_validator.match(to_username) is None:
            return None

        to = self._db.query(User).filter(User.username == to_username).scalar()

        if to is not None:
            existing_connection = self._get_user_connection(from_, to)
            if existing_connection:
                return existing_connection

            new_connection = UserConnection(from_=from_, to=to)
            self._db.add(new_connection)
            self._db.flush()
            return new_connection

        existing_connection = self._get_virtual_user_connection(from_, to_username)
        if existing_connection:
            return existing_connection

        new_connection = VirtualUserConnection(from_=from_, to_username=to_username)
        self._db.add(new_connection)
        self._db.flush()
        return new_connection


def includeme(config):
    config.register_service_factory(lambda context, request: UserConnectionService(request), iface=IUserConnectionService)
