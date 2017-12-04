import uuid

import arrow
import cherrypy

from deli_counter.auth.validation_models.builtin import RequestBuiltInLogin, RequestBuiltInCreateUser, \
    ResponseBuiltInUser, RequestBuiltInChangePassword, RequestBuiltInUserRole, ParamsBuiltInUser, ParamsListBuiltInUser
from deli_counter.http.mounts.root.routes.v1.auth.validation_models.tokens import ResponseOAuthToken
from ingredients_db.models.builtin import BuiltInUser
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router


class DatabaseAuthRouter(Router):
    def __init__(self, driver):
        super().__init__(uri_base='builtin')
        self.driver = driver

    @Route(route='login', methods=[RequestMethods.POST])
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.model_in(cls=RequestBuiltInLogin)
    @cherrypy.tools.model_out(cls=ResponseOAuthToken)
    def login(self):
        request: RequestBuiltInLogin = cherrypy.request.model
        with cherrypy.request.db_session() as session:
            user: BuiltInUser = session.query(BuiltInUser).filter(BuiltInUser.username == request.username).first()
            if user is None or user.password != request.password:
                raise cherrypy.HTTPError(403, "Invalid username or password")

            expiry = arrow.now().shift(days=+1)
            token = self.driver.generate_user_token(session, expiry, user.username, user.roles)
            session.commit()

            response = ResponseOAuthToken()
            response.access_token = token
            response.expiry = expiry
            return response

    @Route(route='users', methods=[RequestMethods.POST])
    @cherrypy.tools.enforce_policy(policy_name="builtin:users:create")
    @cherrypy.tools.model_in(cls=RequestBuiltInCreateUser)
    @cherrypy.tools.model_out(cls=ResponseBuiltInUser)
    def create_user(self):
        request: RequestBuiltInCreateUser = cherrypy.request.model
        with cherrypy.request.db_session() as session:
            user = BuiltInUser()
            user.username = request.username
            user.password = request.password

            session.add(user)
            session.commit(user)
            session.refresh(user)

        return ResponseBuiltInUser.from_database(user)

    @Route(route='users/{user_id}')
    @cherrypy.tools.model_params(cls=ParamsBuiltInUser)
    @cherrypy.tools.enforce_policy(policy_name="builtin:users:get")
    @cherrypy.tools.model_out(cls=ResponseBuiltInUser)
    @cherrypy.tools.resource_object(id_param="user_id", cls=BuiltInUser)
    def get_user(self, user_id):
        return ResponseBuiltInUser.from_database(cherrypy.request.resource_object)

    @Route(route='users')
    @cherrypy.tools.model_params(cls=ParamsListBuiltInUser)
    @cherrypy.tools.enforce_policy(policy_name="builtin:users:list")
    @cherrypy.tools.model_out_pagination(cls=ResponseBuiltInUser)
    def list_users(self, limit: int, marker: uuid.UUID):
        return self.paginate(BuiltInUser, ResponseBuiltInUser, limit, marker)

    @Route(route='users/{user_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsBuiltInUser)
    @cherrypy.tools.enforce_policy(policy_name="builtin:users:delete")
    @cherrypy.tools.resource_object(id_param="user_id", cls=BuiltInUser)
    def delete_user(self, user_id):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']
        with cherrypy.request.db_session() as session:
            user: BuiltInUser = session.merge(cherrypy.request.resource_object, load=False)

            if user.username == "admin":
                raise cherrypy.HTTPError(400, "Cannot delete admin user.")

            session.delete(user)
            session.commit()

    @Route(route='users', methods=[RequestMethods.PATCH])
    @cherrypy.tools.model_in(cls=RequestBuiltInChangePassword)
    def change_password_self(self):
        request: RequestBuiltInChangePassword = cherrypy.request.model
        with cherrypy.request.db_session() as session:
            if cherrypy.request.user.driver != self.driver.name:
                raise cherrypy.HTTPError(400, "Token is not using 'builtin' authentication.")

            user: BuiltInUser = session.query(BuiltInUser).filter(
                BuiltInUser.username == cherrypy.request.user.username).first()
            user.password = request.password
            session.commit()

        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']

    @Route(route='users/{user_id}', methods=[RequestMethods.PATCH])
    @cherrypy.tools.model_params(cls=ParamsBuiltInUser)
    @cherrypy.tools.enforce_policy(policy_name="builtin:users:password")
    @cherrypy.tools.model_in(cls=RequestBuiltInChangePassword)
    @cherrypy.tools.resource_object(id_param="user_id", cls=BuiltInUser)
    def change_password_other(self, user_id):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']
        request: RequestBuiltInChangePassword = cherrypy.request.model
        with cherrypy.request.db_session() as session:
            user: BuiltInUser = session.merge(cherrypy.request.resource_object, load=False)

            if user.username == "admin":
                raise cherrypy.HTTPError(400, "Only the admin user can change it's password.")

            user.password = request.password
            session.commit()

    @Route(route='users/{user_id}/role/add', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsBuiltInUser)
    @cherrypy.tools.enforce_policy(policy_name="builtin:users:role:add")
    @cherrypy.tools.model_in(cls=RequestBuiltInUserRole)
    @cherrypy.tools.resource_object(id_param="user_id", cls=BuiltInUser)
    def add_user_role(self, user_id):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']
        request: RequestBuiltInUserRole = cherrypy.request.model
        with cherrypy.request.db_session() as session:
            user: BuiltInUser = session.merge(cherrypy.request.resource_object, load=False)

            if user.username == "admin":
                raise cherrypy.HTTPError(400, "Cannot change roles for the admin user.")

            user.roles.append(request.role)
            session.commit()

    @Route(route='users/{user_id}/role/remove', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsBuiltInUser)
    @cherrypy.tools.enforce_policy(policy_name="builtin:users:role:remove")
    @cherrypy.tools.model_in(cls=RequestBuiltInUserRole)
    @cherrypy.tools.resource_object(id_param="user_id", cls=BuiltInUser)
    def remove_user_role(self, user_id):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']
        request: RequestBuiltInUserRole = cherrypy.request.model
        with cherrypy.request.db_session() as session:
            user: BuiltInUser = session.merge(cherrypy.request.resource_object, load=False)

            if user.username == "admin":
                raise cherrypy.HTTPError(400, "Cannot change roles for the admin user.")

            if request.role not in user.roles:
                raise cherrypy.HTTPError(400, "User does not have the requested role.")
            user.roles.remove(request.role)
            session.commit()
