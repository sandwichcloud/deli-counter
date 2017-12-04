import json
import logging
from abc import ABCMeta, abstractmethod
from typing import Dict

from cryptography.fernet import Fernet
from simple_settings import settings

from ingredients_db.models.authn import AuthNUser
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

    def generate_user_token(self, session, expires_at, username, global_role_names, project_id=None,
                            project_role_ids=None):
        user = session.query(AuthNUser).filter(AuthNUser.username == username).filter(
            AuthNUser.driver == self.name).first()
        if user is None:
            user = AuthNUser()
            user.username = username
            user.driver = self.name
            session.add(user)
            session.flush()
            session.refresh(user)

        global_role_ids = []

        for role_name in global_role_names:
            role = session.query(AuthZRole).filter(AuthZRole.name == role_name).filter(
                AuthZRole.project_id == None).first()  # noqa: E711
            if role is not None:
                global_role_ids.append(role.id)

        fernet = Fernet(settings.AUTH_FERNET_KEYS[0])

        token_data = {
            'expires_at': expires_at,
            'user_id': user.id,
            'roles': {
                'global': global_role_ids,
                'project': []
            }
        }

        if project_id is not None:
            token_data['project_id'] = project_id
            if project_role_ids is None:
                project_role_ids = []
            token_data['roles']['project'] = project_role_ids

        return fernet.encrypt(json.dumps(token_data).encode())
