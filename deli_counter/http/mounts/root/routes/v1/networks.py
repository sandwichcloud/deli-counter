import uuid

import cherrypy
from sqlalchemy.orm import Query

from deli_counter.http.mounts.root.routes.v1.validation_models.networks import RequestCreateNetwork, ResponseNetwork, \
    ParamsNetwork, ParamsListNetwork
from ingredients_db.models.network import Network, NetworkState
from ingredients_db.models.network_port import NetworkPort
from ingredients_db.models.region import Region, RegionState
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router
from ingredients_tasks.tasks.network import create_network
from ingredients_tasks.tasks.tasks import create_task


class NetworkRouter(Router):
    def __init__(self):
        super().__init__(uri_base='networks')
        # TODO: default to admins only

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateNetwork)
    @cherrypy.tools.model_out(cls=ResponseNetwork)
    @cherrypy.tools.enforce_policy(policy_name="networks:create")
    def create(self):
        request: RequestCreateNetwork = cherrypy.request.model

        with cherrypy.request.db_session() as session:
            network = session.query(Network).filter(Network.name == request.name).first()

            if network is not None:
                raise cherrypy.HTTPError(409, "A network with the requested name already exists.")

            network = session.query(Network).filter(Network.port_group == request.port_group).first()

            if network is not None:
                raise cherrypy.HTTPError(409, "A network with the requested port group already exists.")

            region = session.query(Region).filter(Region.id == request.region_id).first()
            if region is None:
                raise cherrypy.HTTPError(404, "A region with the requested id does not exist.")

            if region.state != RegionState.CREATED:
                raise cherrypy.HTTPError(412,
                                         "The requested region is not in the following state: %s" %
                                         RegionState.CREATED.value)

            # TODO: make sure cidr doesn't overlap with another network

            network = Network()
            network.name = request.name
            network.port_group = request.port_group
            network.cidr = request.cidr
            network.gateway = request.gateway
            network.dns_servers = request.dns_servers
            network.pool_start = request.pool_start
            network.pool_end = request.pool_end
            network.region_id = region.id

            session.add(network)
            session.flush()

            create_task(session, network, create_network, network_id=network.id)

            session.commit()
            session.refresh(network)

        return ResponseNetwork.from_database(network)

    @Route(route='{network_id}')
    @cherrypy.tools.model_params(cls=ParamsNetwork)
    @cherrypy.tools.model_out(cls=ResponseNetwork)
    @cherrypy.tools.resource_object(id_param="network_id", cls=Network)
    @cherrypy.tools.enforce_policy(policy_name="networks:get")
    def get(self, network_id):
        return ResponseNetwork.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListNetwork)
    @cherrypy.tools.model_out_pagination(cls=ResponseNetwork)
    @cherrypy.tools.enforce_policy(policy_name="networks:list")
    def list(self, name, region_id, limit: int, marker: uuid.UUID):
        starting_query = Query(Network)
        if region_id is not None:
            with cherrypy.request.db_session() as session:
                region = session.query(Region).filter(Region.id == region_id).first()
                if region is None:
                    raise cherrypy.HTTPError(404, "A region with the requested id does not exist.")
            starting_query = starting_query.filter(Network.region_id == region.id)
        if name is not None:
            starting_query = starting_query.filter(Network.name == name)
        return self.paginate(Network, ResponseNetwork, limit, marker, starting_query=starting_query)

    @Route(route='{network_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsNetwork)
    @cherrypy.tools.resource_object(id_param="network_id", cls=Network)
    @cherrypy.tools.enforce_policy(policy_name="networks:delete")
    def delete(self, network_id):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']
        with cherrypy.request.db_session() as session:
            network: Network = session.merge(cherrypy.request.resource_object, load=False)

            if network.state not in [NetworkState.CREATED, NetworkState.ERROR]:
                raise cherrypy.HTTPError(409, "Can only delete a network while it is in the following states: %s" % (
                    [NetworkState.CREATED.value, NetworkState.ERROR.value]))

            ports = session.query(NetworkPort).filter(NetworkPort.network_id == network.id)

            if ports.count() > 0:
                raise cherrypy.HTTPError(412, "Cannot delete network when there are ports connected to it.")

            # Don't delete portgroup since it is manually managed

            network.state = NetworkState.DELETING
            session.delete(network)
            session.commit()
