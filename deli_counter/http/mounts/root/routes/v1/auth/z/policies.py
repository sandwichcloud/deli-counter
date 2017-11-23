import uuid

import cherrypy
from oslo_policy.policy import InvalidDefinitionError

from deli_counter.http.mounts.root.routes.v1.auth.z.validation_models.policies import RequestCreatePolicy, \
    ResponsePolicy, ParamsPolicy, ParamsListPolicy, RequestUpdatePolicy
from ingredients_db.models.authz import AuthZPolicy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router


class AuthZPolicyRouter(Router):
    def __init__(self):
        super().__init__('policies')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreatePolicy)
    @cherrypy.tools.model_out(cls=ResponsePolicy)
    @cherrypy.tools.enforce_policy(policy_name="policies:create")
    def create(self):
        request: RequestCreatePolicy = cherrypy.request.model

        with cherrypy.request.db_session() as session:
            policy = session.query(AuthZPolicy).filter(AuthZPolicy.name == request.name).first()

            if policy is not None:
                raise cherrypy.HTTPError(409, 'A policy with the requested name already exists.')

            policy = AuthZPolicy()
            policy.name = request.name
            policy.rule = request.rule
            policy.description = request.description

            session.add(policy)
            session.flush()

            try:
                # Load dry and raise on exception
                self.mount.auth_manager.load_policies(session, dry=True)
            except InvalidDefinitionError as e:
                raise cherrypy.HTTPError(400, str(e))

            session.commit()
            session.refresh(policy)

        # If no exception actually load them
        self.mount.auth_manager.load_policies(session)

        return ResponsePolicy.from_database(policy)

    @Route('{policy_id}')
    @cherrypy.tools.model_params(cls=ParamsPolicy)
    @cherrypy.tools.model_out(cls=ResponsePolicy)
    @cherrypy.tools.resource_object(id_param="policy_id", cls=AuthZPolicy)
    @cherrypy.tools.enforce_policy(policy_name="policies:get")
    def get(self, policy_id: uuid.UUID):
        return ResponsePolicy.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListPolicy)
    @cherrypy.tools.model_out_pagination(cls=ResponsePolicy)
    @cherrypy.tools.enforce_policy(policy_name="policies:list")
    def list(self, limit: int, marker: uuid.UUID):
        return self.paginate(AuthZPolicy, ResponsePolicy, limit, marker)

    @Route('{policy_id}', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsPolicy)
    @cherrypy.tools.model_in(cls=RequestUpdatePolicy)
    @cherrypy.tools.model_out(cls=ResponsePolicy)
    @cherrypy.tools.resource_object(id_param="policy_id", cls=AuthZPolicy)
    @cherrypy.tools.enforce_policy(policy_name="policies:update")
    def update(self, policy_id: uuid.UUID):
        request: RequestUpdatePolicy = cherrypy.request.model
        with cherrypy.request.db_session() as session:
            policy: AuthZPolicy = session.merge(cherrypy.request.resource_object, load=False)
            policy.rule = request.rule
            session.commit()
            session.refresh(policy)

        return ResponsePolicy.from_database(policy)

    @Route('{policy_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsPolicy)
    @cherrypy.tools.resource_object(id_param="policy_id", cls=AuthZPolicy)
    @cherrypy.tools.enforce_policy(policy_name="policies:delete")
    def delete(self, policy_id: uuid.UUID):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']
        with cherrypy.request.db_session() as session:
            policy: AuthZPolicy = session.merge(cherrypy.request.resource_object, load=False)
            session.delete(policy)
            session.commit()
