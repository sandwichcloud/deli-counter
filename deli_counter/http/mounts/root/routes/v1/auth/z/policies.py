import uuid

import cherrypy

from deli_counter.http.mounts.root.routes.v1.auth.z.validation_models.policies import ResponsePolicy, ParamsPolicy, \
    ParamsListPolicy
from ingredients_db.models.authz import AuthZPolicy
from ingredients_http.route import Route
from ingredients_http.router import Router


class AuthZPolicyRouter(Router):
    def __init__(self):
        super().__init__('policies')

    @Route('{policy_id}')
    @cherrypy.tools.model_params(cls=ParamsPolicy)
    @cherrypy.tools.model_out(cls=ResponsePolicy)
    @cherrypy.tools.resource_object(id_param="policy_id", cls=AuthZPolicy)
    @cherrypy.tools.enforce_policy(policy_name="policies:get")
    def get(self, policy_id):
        return ResponsePolicy.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListPolicy)
    @cherrypy.tools.model_out_pagination(cls=ResponsePolicy)
    @cherrypy.tools.enforce_policy(policy_name="policies:list")
    def list(self, limit: int, marker: uuid.UUID):
        return self.paginate(AuthZPolicy, ResponsePolicy, limit, marker)
