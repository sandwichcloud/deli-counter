import uuid

from ingredients_http.route import Route
from ingredients_http.router import Router


class AuthNUserRouter(Router):
    def __init__(self):
        super().__init__('users')

    @Route('{user_id}')
    def get(self, user_id: uuid.UUID):
        pass
