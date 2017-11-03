import logging
import secrets
from abc import ABCMeta, abstractmethod
from typing import Dict

from ingredients_db.models.authn import AuthNUser, AuthNToken, AuthNTokenRole
from ingredients_db.models.authz import AuthZRole
from ingredients_http.router import Router


class AuthDriver(object):
    __metaclass__ = ABCMeta

    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))

    @abstractmethod
    def discover_options(self) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def auth_router(self) -> Router:
        raise NotImplementedError

    def generate_user_token(self, session, username, roles):
        user = session.query(AuthNUser).filter(AuthNUser.username == username).filter(
            AuthNUser.driver == self.name).first()
        if user is None:
            user = AuthNUser()
            user.username = username
            user.driver = self.name
            session.add(user)
            session.flush()

        token = AuthNToken()
        token.user_id = user.id
        token.access_token = secrets.token_urlsafe()
        session.add(token)
        session.flush()

        for role in roles:
            db_role = session.query(AuthZRole).filter(AuthZRole.name == role).first()
            if db_role is not None:
                token_role = AuthNTokenRole()
                token_role.token_id = token.id
                token_role.role_id = db_role.id
                session.add(token_role)

        return token
