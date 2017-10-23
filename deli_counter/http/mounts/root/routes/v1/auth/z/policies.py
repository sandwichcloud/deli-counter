import uuid

from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router


class AuthZPolicyRouter(Router):
    def __init__(self):
        super().__init__('policies')

    @Route('{policy_id}')
    def get(self, policy_id: uuid.UUID):
        pass

    @Route(methods=[RequestMethods.POST])
    def create(self):
        # TODO: create a new enforcer, load all the rules into it and run checks before applying to main enforcer
        pass

    @Route()
    def list(self):
        pass
