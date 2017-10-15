import importlib

import cherrypy

from deli_counter.auth.driver import AuthDriver
from ingredients_db.models.project import Project
from ingredients_db.models.user import UserToken, User
from ingredients_http.app import HTTPApplication
from ingredients_http.app_mount import ApplicationMount
from ingredients_http.conf.loader import SETTINGS
from ingredients_http.route import Route
from ingredients_http.router import Router
from ingredients_tasks.celary import Messaging


class RootMount(ApplicationMount):
    def __init__(self, app: HTTPApplication):
        super().__init__(app=app, mount_point='/')
        self.auth_drivers = []
        self.messaging = None

    def validate_token(self):
        authorization_header = cherrypy.request.headers.get('Authorization', None)
        if authorization_header is None:
            raise cherrypy.HTTPError(400, 'Missing Authorization header.')

        method, token, *_ = authorization_header.split(" ")

        if method != 'Bearer':
            raise cherrypy.HTTPError(400, 'Only Bearer tokens are allowed.')

        with cherrypy.request.db_session() as session:
            token = session.query(UserToken).filter(UserToken.access_token == token).first()

            if token is None:
                raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')

            # TODO: check project membership because they may no longer be a member since scoping
            user = session.query(User).filter(User.id == token.user_id).first()
            project = session.query(Project).filter(Project.id == token.project_id).first()

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

    def __setup_tools(self):
        cherrypy.tools.authentication = cherrypy.Tool('on_start_resource', self.validate_token, priority=10)
        cherrypy.tools.project_scope = cherrypy.Tool('on_start_resource', self.validate_project_scope, priority=20)

    def __setup_auth(self):

        for driver_string in SETTINGS.AUTH_DRIVERS:
            if ':' not in driver_string:
                raise ValueError("AUTH_DRIVER does not contain a module and class. "
                                 "Must be in the following format: 'my.module:MyClass'")

            auth_module, auth_class, *_ = driver_string.split(":")
            try:
                auth_module = importlib.import_module(auth_module)
            except ImportError:
                self.logger.exception("Could not import auth driver's module: " + auth_module)
                raise
            try:
                driver_klass = getattr(auth_module, auth_class)
            except AttributeError:
                self.logger.exception("Could not get driver's module class: " + auth_class)
                raise

            if not issubclass(driver_klass, AuthDriver):
                raise ValueError("AUTH_DRIVER class is not a subclass of '" + AuthDriver.__module__ + ".AuthDriver'")

            self.auth_drivers.append(driver_klass())

        if len(self.auth_drivers) == 0:
            raise ValueError("No auth drivers loaded")

    def __setup_messaging(self):
        self.messaging = Messaging(SETTINGS.RABBITMQ_HOST, SETTINGS.RABBITMQ_PORT, SETTINGS.RABBITMQ_USERNAME,
                                   SETTINGS.RABBITMQ_PASSWORD, SETTINGS.RABBITMQ_VHOST)
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
