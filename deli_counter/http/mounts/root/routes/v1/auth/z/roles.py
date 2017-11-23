import uuid

import cherrypy

from deli_counter.http.mounts.root.routes.v1.auth.z.validation_models.roles import ResponseRole, RequestCreateRole, \
    ParamsRole, ParamsListRole
from ingredients_db.models.authz import AuthZRole
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router


class AuthZRoleRouter(Router):
    def __init__(self):
        super().__init__('roles')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateRole)
    @cherrypy.tools.model_out(cls=ResponseRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:create")
    def create(self):
        request: RequestCreateRole = cherrypy.request.model

        with cherrypy.request.db_session() as session:
            role = session.query(AuthZRole).filter(AuthZRole.name == request.name).first()

            if role is not None:
                raise cherrypy.HTTPError(409, 'A role with the requested name already exists.')

            role = AuthZRole()
            role.name = request.name
            role.description = request.description

            session.add(role)
            session.commit()
            session.refresh(role)

        return ResponseRole.from_database(role)

    @Route('{role_id}')
    @cherrypy.tools.model_params(cls=ParamsRole)
    @cherrypy.tools.model_out(cls=ResponseRole)
    @cherrypy.tools.resource_object(id_param="role_id", cls=AuthZRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:get")
    def get(self, role_id: uuid.UUID):
        return ResponseRole.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListRole)
    @cherrypy.tools.model_out_pagination(cls=ResponseRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:list")
    def list(self, limit: int, marker: uuid.UUID):
        return self.paginate(AuthZRole, ResponseRole, limit, marker)

    @Route('{role_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsRole)
    @cherrypy.tools.resource_object(id_param="role_id", cls=AuthZRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:delete")
    def delete(self, role_id: uuid.UUID):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']
        with cherrypy.request.db_session() as session:
            policy: AuthZRole = session.merge(cherrypy.request.resource_object, load=False)
            session.delete(policy)
            session.commit()
