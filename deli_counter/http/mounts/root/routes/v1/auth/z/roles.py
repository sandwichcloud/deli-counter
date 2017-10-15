import uuid

from ingredients_http.route import Route
from ingredients_http.router import Router


class AuthZRoleRouter(Router):
    def __init__(self):
        super().__init__('roles')

    @Route('{role_id}')
    def get(self, role_id: uuid.UUID):
        pass
