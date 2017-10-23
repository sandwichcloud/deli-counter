import arrow
import cherrypy
from simple_settings import settings

from deli_counter.auth.manager import AuthManager
from ingredients_db.models.authn import AuthNToken, AuthNUser
from ingredients_db.models.project import Project
from ingredients_http.app import HTTPApplication
from ingredients_http.app_mount import ApplicationMount
from ingredients_http.route import Route
from ingredients_http.router import Router
from ingredients_tasks.celary import Messaging


class RootMount(ApplicationMount):
    def __init__(self, app: HTTPApplication):
        super().__init__(app=app, mount_point='/')
        self.auth_manager: AuthManager = None
        self.messaging = None

    def validate_token(self):
        authorization_header = cherrypy.request.headers.get('Authorization', None)
        if authorization_header is None:
            raise cherrypy.HTTPError(400, 'Missing Authorization header.')

        method, token, *_ = authorization_header.split(" ")

        if method != 'Bearer':
            raise cherrypy.HTTPError(400, 'Only Bearer tokens are allowed.')

        with cherrypy.request.db_session() as session:
            token: AuthNToken = session.query(AuthNToken).filter(AuthNToken.access_token == token).first()

            # Token DNE
            if token is None:
                raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')

            # Token is expired so delete the token
            if token.expires_at < arrow.now():
                session.delete(token)
                session.commit()
                raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')

            project = session.query(Project).filter(Project.id == token.project_id).first()

            user = session.query(AuthNUser).filter(AuthNUser.id == token.user_id).first()

            session.expunge(token)
            session.expunge(user)
            if project is not None:
                session.expunge(project)
            cherrypy.request.token = token
            cherrypy.request.user = user
            cherrypy.request.project = project

    def validate_project_scope(self):
        if cherrypy.request.project is None:
            raise cherrypy.HTTPError(403, "Token not scoped for a project")

    def enforce_policy(self, policy_name, resource_object=None):
        resource_object = getattr(cherrypy.request, "resource_object", resource_object)
        self.auth_manager.enforce_policy(policy_name, cherrypy.request.token, cherrypy.request.user,
                                         cherrypy.request.project, resource_object)

    def resource_object(self, id_param, cls):
        resource_id = cherrypy.request.params[id_param]
        with cherrypy.request.db_session() as session:
            resource = session.query(cls).filter(cls.id == resource_id).first()
            if resource is None:
                raise cherrypy.HTTPError(404, "The resource could not be found.")

            session.expunge(resource)
            cherrypy.request.resource_object = resource

    def __setup_tools(self):
        cherrypy.tools.authentication = cherrypy.Tool('on_start_resource', self.validate_token, priority=20)
        cherrypy.tools.project_scope = cherrypy.Tool('on_start_resource', self.validate_project_scope, priority=30)

        cherrypy.tools.resource_object = cherrypy.Tool('before_request_body', self.resource_object, priority=30)
        cherrypy.tools.enforce_policy = cherrypy.Tool('before_request_body', self.enforce_policy, priority=40)

    def __setup_auth(self):
        self.auth_manager = AuthManager(self.app.database)
        self.auth_manager.load_drivers()
        self.auth_manager.load_policies()

    def __setup_messaging(self):
        self.messaging = Messaging(settings.RABBITMQ_HOST, settings.RABBITMQ_PORT, settings.RABBITMQ_USERNAME,
                                   settings.RABBITMQ_PASSWORD, settings.RABBITMQ_VHOST)
        self.messaging.connect()

    def setup(self):
        self.__setup_tools()
        self.__setup_auth()
        self.__setup_messaging()
        super().setup()

    def mount_config(self):
        config = super().mount_config()
        config['tools.authentication.on'] = True
        return config


class AuthDiscoverRouter(Router):
    def __init__(self, mount):
        super().__init__('auth')
        self.mount = mount

    @Route()
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.json_out()
    def auth_driver_discovery_route(self):
        return {
            "drivers": self.mount.auth_driver.name
        }
