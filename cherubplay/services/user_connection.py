from typing import List, Optional

from sqlalchemy import and_, text
from sqlalchemy.orm import contains_eager, joinedload
from zope.interface import Interface, implementer

from cherubplay.lib import username_validator
from cherubplay.models import BaseUserConnection, User, UserConnection, VirtualUserConnection


CONVERT_QUERY = text("""
    INSERT INTO user_connections (from_id, to_id)
    SELECT from_id, :to_id FROM virtual_user_connections
    WHERE to_username = :to_username
    AND from_id NOT IN (
        SELECT from_id FROM user_connections
        WHERE to_id = :to_id
    )
""")


class IUserConnectionService(Interface):
    def search(self, from_: User) -> List[BaseUserConnection]:
        pass

    def get(self, from_: User, to: str) -> Optional[BaseUserConnection]:
        pass

    def create(self, from_: User, to_username: str) -> Optional[BaseUserConnection]:
        pass

    def convert_virtual_connections(self, to: User):
        pass

    def revert_non_mutual_connections(self, to: User):
        pass


@implementer(IUserConnectionService)
class UserConnectionService(object):
    def __init__(self, db):
        self._db = db

    def search(self, from_: User) -> List[BaseUserConnection]:

        user_connections = (
            self._db.query(UserConnection)
            .filter(UserConnection.from_id == from_.id)
            .join(User, UserConnection.to_id == User.id)
            .options(
                contains_eager(UserConnection.to),
                joinedload(UserConnection.reverse),
            ).all()
        ) + (
            self._db.query(VirtualUserConnection)
            .filter(VirtualUserConnection.from_id == from_.id).all()
        )
        user_connections.sort(key=lambda _: _.to_username)
        return user_connections

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
        if to_username == from_.username:
            raise ValueError("can't connect to self")
        if username_validator.match(to_username) is None:
            raise ValueError("not a valid username")

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

    def convert_virtual_connections(self, to: User):
        """
        Turns virtual connections to a user into real connections.
        """
        self._db.execute(CONVERT_QUERY, {"to_id": to.id, "to_username": to.username})
        self._db.query(VirtualUserConnection).filter(VirtualUserConnection.to_username == to.username).delete()

    def revert_non_mutual_connections(self, to: User):
        """
        Turns non-mutual user connections into virtual connections, allowing the user to leave them behind when they
        change their username.
        """
        user_connections = (
            self._db.query(UserConnection)
            .filter(and_(
                UserConnection.to_id == to.id,
                UserConnection.from_id.notin_(
                    self._db.query(UserConnection.to_id)
                    .filter(UserConnection.from_id == to.id).subquery()
                ),
            )).all()
        )
        for user_connection in user_connections:
            self._db.add(VirtualUserConnection(from_id=user_connection.from_id, to_username=to.username))
            self._db.delete(user_connection)


def includeme(config):
    config.register_service_factory(
        lambda context, request: UserConnectionService(request.find_service(name="db")),
        iface=IUserConnectionService,
    )
