import uuid

from ingredients_http.route import Route
from ingredients_http.router import Router


class AuthZPolicyRouter(Router):
    def __init__(self):
        super().__init__('policies')

    @Route('{policy_id}')
    def get(self, policy_id: uuid.UUID):
        pass
