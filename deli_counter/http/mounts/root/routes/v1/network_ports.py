import uuid

import cherrypy
from sqlalchemy.orm import Query

from deli_counter.http.mounts.root.routes.v1.validation_models.network_ports import ParamsNetworkPort, \
    ParamsListNetworkPort, ResponseNetworkPort
from ingredients_db.models.instance import Instance
from ingredients_db.models.network_port import NetworkPort
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router


class NetworkPortRouter(Router):
    def __init__(self):
        super().__init__(uri_base='network-ports')

    # Do we want to allow creation? It's kinda pointless since they are auto created

    @Route(route='{network_port_id}')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsNetworkPort)
    @cherrypy.tools.model_out(cls=ResponseNetworkPort)
    @cherrypy.tools.resource_object(id_param="network_port_id", cls=NetworkPort)
    @cherrypy.tools.enforce_policy(policy_name="network_ports:get")
    def get(self, network_port_id):
        return ResponseNetworkPort.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListNetworkPort)
    @cherrypy.tools.model_out_pagination(cls=ResponseNetworkPort)
    @cherrypy.tools.enforce_policy(policy_name="network_ports:list")
    def list(self, limit: int, marker: uuid.UUID):
        project = cherrypy.request.project
        starting_query = Query(NetworkPort).filter(NetworkPort.project_id == project.id)
        return self.paginate(NetworkPort, ResponseNetworkPort, limit, marker, starting_query=starting_query)

    @Route(route='{network_port_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsNetworkPort)
    @cherrypy.tools.resource_object(id_param="network_port_id", cls=NetworkPort)
    @cherrypy.tools.enforce_policy(policy_name="network_ports:delete")
    def delete(self, network_port_id):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']

        with cherrypy.request.db_session() as session:
            network_port: NetworkPort = session.merge(cherrypy.request.resource_object, load=False)

            instance_count = session.query(Instance).filter(Instance.network_port_id == network_port.id).count()
            if instance_count > 0:
                raise cherrypy.HTTPError(400, "Cannot delete a network port while it is in use.")

            session.delete(network_port)
            session.commit()
