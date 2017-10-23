import cherrypy

from deli_counter.http.mounts.root.routes.v1.validation_models.auth import ResponseVerifyToken, RequestScopeToken, \
    ResponseOAuthToken
from ingredients_db.models.project import Project
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router


class AuthNTokenRouter(Router):
    def __init__(self):
        super().__init__('tokens')

    @Route()
    @cherrypy.tools.model_out(cls=ResponseVerifyToken)
    def get(self):
        # TODO: allow getting another token with X-Subject-Token-ID header
        return ResponseVerifyToken.from_database(cherrypy.request.token)

    @Route(methods=[RequestMethods.HEAD])
    def head(self):
        pass

    # Generate a new token scoped for the requested project
    @Route(route='scope', methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestScopeToken)
    @cherrypy.tools.model_out(cls=ResponseOAuthToken)
    def scope_token(self):
        request: RequestScopeToken = cherrypy.request.model

        with cherrypy.request.db_session() as session:
            project = session.query(Project).filter(Project.id == request.project_id).first()

            if project is None:
                raise cherrypy.HTTPError(404, 'A project with the requested id does not exist.')

            # TODO: check project membership

            driver = self.mount.auth_manager.drivers.get(cherrypy.request.user.driver)

            if driver is None:
                raise cherrypy.HTTPError(500, "Previous auth driver '%s' is not loaded. Cannot scope token."
                                         % cherrypy.request.token.driver)

            token = driver.generate_user_token(session, cherrypy.request.user.username)
            # Should project tokens last the same amount of time?
            token.project_id = project.id
            session.commit()
            session.refresh(token)

            return ResponseOAuthToken.from_database(token)
