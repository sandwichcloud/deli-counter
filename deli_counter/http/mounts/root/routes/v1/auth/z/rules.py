import uuid

from ingredients_http.route import Route
from ingredients_http.router import Router


class AuthZRuleRouter(Router):
    def __init__(self):
        super().__init__('rules')

    @Route('{rule_id}')
    def get(self, rule_id: uuid.UUID):
        pass
