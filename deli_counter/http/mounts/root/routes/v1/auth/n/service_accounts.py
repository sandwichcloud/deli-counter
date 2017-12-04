import uuid

import cherrypy
from sqlalchemy.orm import Query

from deli_counter.http.mounts.root.routes.v1.auth.n.validation_models.service_accounts import \
    RequestCreateServiceAccount, ResponseServiceAccount, ParamsServiceAccount, ParamsListServiceAccount
from ingredients_db.models.authn import AuthNServiceAccount
from ingredients_db.models.authz import AuthZRole
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router


class AuthNUserRouter(Router):
    def __init__(self):
        super().__init__('service-accounts')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_in(cls=RequestCreateServiceAccount)
    @cherrypy.tools.model_out(cls=ResponseServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:create")
    def create(self):
        project = cherrypy.request.project
        request: RequestCreateServiceAccount = cherrypy.request.model

        with cherrypy.request.db_session() as session:
            service_account = session.query(AuthNServiceAccount).filter(AuthNServiceAccount.project_id == project.id). \
                filter(AuthNServiceAccount.name == request.name).first()

            if service_account is not None:
                raise cherrypy.HTTPError(409, 'A service account with the requested name already exists.')

            role = session.query(AuthZRole).filter(AuthZRole.project_id == project.id). \
                filter(AuthZRole.id == request.role_id).first()

            if role is None:
                raise cherrypy.HTTPError(404, "A role with the requested ID does not exist in the project.")

            service_account = AuthNServiceAccount()
            service_account.name = request.name
            service_account.role_id = role.id

            session.add(service_account)
            session.commit()
            session.refresh(service_account)

        return ResponseServiceAccount.from_database(service_account)

    @Route('{service_account_id}')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.model_out(cls=ResponseServiceAccount)
    @cherrypy.tools.resource_object(id_param="service_account_id", cls=AuthNServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:get")
    def get(self, service_account_id):
        return ResponseServiceAccount.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListServiceAccount)
    @cherrypy.tools.model_out_pagination(cls=ResponseServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_account:list")
    def list(self, limit: int, marker: uuid.UUID):
        project = cherrypy.request.project
        starting_query = Query(AuthNServiceAccount).filter(AuthNServiceAccount.project_id == project.id)
        return self.paginate(AuthNServiceAccount, ResponseServiceAccount, limit, marker, starting_query=starting_query)

    @Route('{service_account}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.resource_object(id_param="service_account_id", cls=AuthNServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_account:delete")
    def delete(self, service_account_id):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']
        with cherrypy.request.db_session() as session:
            service_account: AuthNServiceAccount = session.merge(cherrypy.request.resource_object, load=False)

            if service_account.name == "default_service_account":
                raise cherrypy.HTTPError(401, "Cannot delete the default service account.")

            # TODO: check if sa is in use

            session.delete(service_account)
            session.commit()
