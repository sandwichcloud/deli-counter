import uuid

import cherrypy
from sqlalchemy.orm import Query

from deli_counter.http.mounts.root.routes.v1.auth.z.validation_models.roles import ResponseRole, RequestCreateRole, \
    ParamsRole, ParamsListRole, RoleType
from ingredients_db.models.authz import AuthZRole
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router

# TODO: add ability to add policies to a role
# Add ability to list policies in a role

# These roles cannot be added, deleted or modified
protected_roles = [
    "admin",
    "viewer",
    "default_member",
    "default_service_account"
]


class AuthZRoleRouter(Router):
    def __init__(self):
        super().__init__('roles')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateRole)
    @cherrypy.tools.model_out(cls=ResponseRole)
    def create(self):
        request: RequestCreateRole = cherrypy.request.model

        project = None
        if request.type == RoleType.PROJECT:
            self.mount.validate_project_scope()
            self.mount.enforce_policy("roles:create:project")
            project = cherrypy.request.project
        else:
            self.mount.enforce_policy("roles:create:global")

        with cherrypy.request.db_session() as session:
            role = session.query(AuthZRole).filter(AuthZRole.name == request.name).first()
            if role is not None:
                raise cherrypy.HTTPError(409, 'A role with the requested name already exists.')

            if request.name.lower() in protected_roles:
                raise cherrypy.HTTPError(400, "Cannot create a protected role with the name of " + request.name)

            role = AuthZRole()
            role.name = request.name
            role.description = request.description

            if project is not None:
                role.project_id = project.id

            session.add(role)
            session.commit()
            session.refresh(role)

        return ResponseRole.from_database(role)

    @Route('{role_id}')
    @cherrypy.tools.model_params(cls=ParamsRole)
    @cherrypy.tools.model_out(cls=ResponseRole)
    @cherrypy.tools.resource_object(id_param="role_id", cls=AuthZRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:get")
    def get(self, role_id):
        return ResponseRole.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListRole)
    @cherrypy.tools.model_out_pagination(cls=ResponseRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:list")
    def list(self, type: RoleType, limit: int, marker: uuid.UUID):
        if type == RoleType.GLOBAL:
            starting_query = Query(AuthZRole).filter(AuthZRole.project_id == None)  # noqa: E711
        else:
            self.mount.validate_project_scope()
            starting_query = Query(AuthZRole).filter(AuthZRole.project_id == cherrypy.request.project.id)
        return self.paginate(AuthZRole, ResponseRole, limit, marker, starting_query=starting_query)

    @Route('{role_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsRole)
    @cherrypy.tools.resource_object(id_param="role_id", cls=AuthZRole)
    def delete(self, role_id):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']
        with cherrypy.request.db_session() as session:
            role: AuthZRole = session.merge(cherrypy.request.resource_object, load=False)

            if role.project_id is not None:
                self.mount.validate_project_scope()
                self.mount.enforce_policy("roles:delete:project")
                if role.project_id != cherrypy.request.project.id:
                    raise cherrypy.HTTPError(401, "Cannot delete a role in another project.")
            else:
                self.mount.enforce_policy("roles:delete:global")

            if role.name in protected_roles:
                raise cherrypy.HTTPError(400, "Cannot delete a protected role with the name of " + role.name)

            # TODO: check if role is in use

            session.delete(role)
            session.commit()
