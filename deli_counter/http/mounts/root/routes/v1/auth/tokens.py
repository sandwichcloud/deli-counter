import arrow
import cherrypy

from deli_counter.http.mounts.root.routes.v1.auth.validation_models.tokens import ResponseVerifyToken, \
    RequestScopeToken, \
    ResponseOAuthToken
from ingredients_db.models.authn import AuthNServiceAccount
from ingredients_db.models.authz import AuthZRole
from ingredients_db.models.project import Project, ProjectMembers
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router


class AuthNTokenRouter(Router):
    def __init__(self):
        super().__init__('tokens')

    @Route()
    @cherrypy.tools.model_out(cls=ResponseVerifyToken)
    def get(self):
        global_role_names = []
        project_role_names = []
        with cherrypy.request.db_session() as session:
            for role_id in cherrypy.request.token['roles']['global']:
                role = session.query(AuthZRole).filter(AuthZRole.id == role_id).first()
                if role is not None:
                    global_role_names.append(role.name)
            if cherrypy.request.project is not None:
                for role_id in cherrypy.request.token['roles']['project']:
                    role = session.query(AuthZRole).filter(AuthZRole.id == role_id).first()
                    if role is not None:
                        project_role_names.append(role.name)

        response = ResponseVerifyToken()

        if isinstance(cherrypy.request.user, AuthNServiceAccount):
            response.service_account_id = cherrypy.request.user.id
            response.service_account_name = cherrypy.request.user.name
        else:
            response.user_id = cherrypy.request.user.id
            response.username = cherrypy.request.user.username
            response.driver = cherrypy.request.user.driver
        if cherrypy.request.project is not None:
            response.project_id = cherrypy.request.project.id
            response.project_roles = project_role_names
        response.global_roles = global_role_names
        return response

    @Route(methods=[RequestMethods.HEAD])
    def head(self):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']

    # Generate a new token scoped for the requested project
    @Route(route='scope', methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestScopeToken)
    @cherrypy.tools.model_out(cls=ResponseOAuthToken)
    def scope_token(self):

        if isinstance(cherrypy.request.user, AuthNServiceAccount):
            raise cherrypy.HTTPError(403, "Service Accounts cannot scope tokens.")

        if cherrypy.request.project is not None:
            raise cherrypy.HTTPError(403, "Cannot scope an already scoped token.")

        request: RequestScopeToken = cherrypy.request.model

        with cherrypy.request.db_session() as session:
            project = session.query(Project).filter(Project.id == request.project_id).first()

            if project is None:
                raise cherrypy.HTTPError(404, 'A project with the requested id does not exist.')

            driver = self.mount.auth_manager.drivers.get(cherrypy.request.user.driver)

            if driver is None:
                raise cherrypy.HTTPError(500, "Previous auth driver '%s' is not loaded. Cannot scope token."
                                         % cherrypy.request.token.driver)

            # Do we want to ask the driver for roles again or do we just copy them over?

            global_role_names = []
            for role_id in cherrypy.request.token['roles']['global']:
                print(role_id)
                role = session.query(AuthZRole).filter(AuthZRole.id == role_id).first()
                if role is not None:
                    global_role_names.append(role.name)

            project_role_ids = []
            project_roles = session.query(AuthZRole).join(ProjectMembers,
                                                          AuthZRole.id == ProjectMembers.role_id).filter(
                ProjectMembers.project_id == project.id).filter(ProjectMembers.user_id == cherrypy.request.user.id)
            for role in project_roles:
                project_role_ids.append(role.id)

            expiry = arrow.now().shift(days=+1)
            token = driver.generate_user_token(session, expiry, cherrypy.request.user.username, global_role_names,
                                               project_id=project.id, project_role_ids=project_role_ids)
            session.commit()

            response = ResponseOAuthToken()
            response.access_token = token
            response.expiry = expiry
            return response
