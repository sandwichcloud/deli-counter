import inspect
import types

import cherrypy

from deli_counter.auth import utils
from deli_counter.auth.driver import AuthDriver  # noqa: F401
from deli_counter.http.mounts.root.routes.v1.validation_models.auth import ResponseVerifyToken, ResponseOAuthToken, \
    ParamsVerifyToken, RequestScopeToken
from ingredients_db.models.project import Project
from ingredients_db.models.user import UserToken, User
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router


class AuthRouter(Router):
    def __init__(self):
        super().__init__('auth')
        self.driver: AuthDriver = None

    def setup_routes(self, dispatcher: cherrypy.dispatch.RoutesDispatcher, uri_prefix: str):
        self.driver = self.mount.auth_driver

        for name, method in inspect.getmembers(self.driver.auth_router(), predicate=inspect.isfunction):
            setattr(self, name, types.MethodType(method, self))

        super().setup_routes(dispatcher, uri_prefix)

    @Route(route='discover')
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.json_out()
    def discover(self):
        return {
            "driver": self.driver.name,
            "options": self.driver.discover_options()
        }

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

            user = session.query(User).filter(User.id == cherrypy.request.user_id).first()

            token = utils.generate_oauth_token(session, user.username)
            # Should project tokens last the same amount of time?
            token.project_id = project.id
            session.commit()
            session.refresh(token)

        return ResponseOAuthToken.from_database(token)

    # HEAD only verify that we can auth
    @Route(route='verify', methods=[RequestMethods.HEAD])
    def verify_head(self):
        pass

    # GET show information about current auth token
    @Route(route='verify', methods=[RequestMethods.GET])
    @cherrypy.tools.model_out(cls=ResponseVerifyToken)
    def verify_self(self):
        with cherrypy.request.db_session() as session:
            token = session.query(UserToken).filter(UserToken.id == cherrypy.request.token_id).first()

        return ResponseVerifyToken.from_database(token)

    # GET show information about the requested auth token
    @Route(route='verify/{token_id}', methods=[RequestMethods.HEAD])
    @cherrypy.tools.model_params(cls=ParamsVerifyToken)
    @cherrypy.tools.model_out(cls=ResponseVerifyToken)
    def verify_other(self, token_id):
        with cherrypy.request.db_session() as session:
            token = session.query(UserToken).filter(UserToken.id == token_id).first()

            if token is None:
                raise cherrypy.HTTPError(404, 'A token with the requested id does not exist.')

        return ResponseVerifyToken.from_database(token)
