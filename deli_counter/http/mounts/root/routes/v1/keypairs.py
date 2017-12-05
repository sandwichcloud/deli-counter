import uuid

import cherrypy
from sqlalchemy.orm import Query

from deli_counter.http.mounts.root.routes.v1.validation_models.keypairs import RequestCreateKeypair, ParamsListKeypair, \
    ParamsKeypair, ResponseKeypair
from ingredients_db.models.keypair import Keypair
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router


class KeypairsRouter(Router):
    def __init__(self):
        super().__init__(uri_base='keypairs')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_in(cls=RequestCreateKeypair)
    @cherrypy.tools.model_out(cls=ResponseKeypair)
    @cherrypy.tools.enforce_policy(policy_name="keypairs:create")
    def create(self):
        request: RequestCreateKeypair = cherrypy.request.model
        project = cherrypy.request.project

        with cherrypy.request.db_session() as session:
            keypair = session.query(Keypair).filter(Keypair.name == request.name).first()

            if keypair is not None:
                raise cherrypy.HTTPError(409, "A keypair with the requested name already exists.")

            keypair = Keypair()
            keypair.name = request.name
            keypair.public_key = request.public_key
            keypair.project_id = project.id
            session.add(keypair)
            session.commit()
            session.refresh(keypair)
            return ResponseKeypair.from_database(keypair)

    @Route(route='{keypair_id}')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsKeypair)
    @cherrypy.tools.model_out(cls=ResponseKeypair)
    @cherrypy.tools.resource_object(id_param="keypair_id", cls=Keypair)
    @cherrypy.tools.enforce_policy(policy_name="keypairs:get")
    def get(self, keypair_id: uuid.UUID):
        return ResponseKeypair.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListKeypair)
    @cherrypy.tools.model_out_pagination(cls=ResponseKeypair)
    @cherrypy.tools.enforce_policy(policy_name="keypairs:list")
    def list(self, limit: int, marker: uuid.UUID):
        project = cherrypy.request.project
        starting_query = Query(Keypair).filter(Keypair.project_id == project.id)
        return self.paginate(Keypair, ResponseKeypair, limit, marker, starting_query=starting_query)

    @Route(route='{keypair_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsKeypair)
    @cherrypy.tools.resource_object(id_param="keypair_id", cls=Keypair)
    @cherrypy.tools.enforce_policy(policy_name="keypairs:delete")
    def delete(self, keypair_id: uuid.UUID):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']

        with cherrypy.request.db_session() as session:
            keypair: Keypair = session.merge(cherrypy.request.resource_object, load=False)
            session.delete(keypair)
            session.commit()
