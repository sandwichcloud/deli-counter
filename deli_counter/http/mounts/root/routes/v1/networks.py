import uuid

import cherrypy

from deli_counter.http.mounts.root.routes.v1.validation_models.networks import RequestCreateNetwork, ResponseNetwork, \
    ParamsNetwork, ParamsListNetwork
from ingredients_db.models.network import Network, NetworkState
from ingredients_db.models.network_port import NetworkPort
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router
from ingredients_tasks.tasks.network import create_network
from ingredients_tasks.tasks.tasks import create_task


class NetworkRouter(Router):
    def __init__(self):
        super().__init__(uri_base='networks')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateNetwork)
    @cherrypy.tools.model_out(cls=ResponseNetwork)
    def create(self):
        request: RequestCreateNetwork = cherrypy.request.model

        with cherrypy.request.db_session() as session:
            network = session.query(Network).filter(Network.name == request.name).first()

            if network is not None:
                raise cherrypy.HTTPError(409, "A network already exists with the requested name.")

            network = session.query(Network).filter(Network.port_group == request.port_group).first()

            if network is not None:
                raise cherrypy.HTTPError(409, "A network already exists with the requested port group.")

            # TODO: make sure cidr doesn't overlap with another network

            network = Network()
            network.name = request.name
            network.port_group = request.port_group
            network.cidr = request.cidr
            network.pool_start = request.pool_start
            network.pool_end = request.pool_end

            session.add(network)
            session.flush()

            create_task(session, network, create_network, network_id=network.id)

            session.commit()
            session.refresh(network)

        return ResponseNetwork.from_database(network)

    @Route(route='{network_id}')
    @cherrypy.tools.model_params(cls=ParamsNetwork)
    @cherrypy.tools.model_out(cls=ResponseNetwork)
    def inspect(self, network_id):
        with cherrypy.request.db_session() as session:
            network = session.query(Network).filter(Network.id == network_id).with_for_update().first()

            if network is None:
                raise cherrypy.HTTPError(400, "A network with the requested id does not exist.")

        return ResponseNetwork.from_database(network)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListNetwork)
    @cherrypy.tools.model_out_pagination(cls=ResponseNetwork)
    def list(self, limit: int, marker: uuid.UUID):
        resp_networks = []
        with cherrypy.request.db_session() as session:
            networks = session.query(Network).order_by(Network.created_at.desc())

            if marker is not None:
                marker = session.query(Network).filter(Network.id == marker).first()
                if marker is None:
                    raise cherrypy.HTTPError(status=400, message="Unknown marker ID")
                networks = networks.filter(Network.created_at < marker.created_at)

            networks = networks.limit(limit + 1)

            for network in networks:
                resp_networks.append(ResponseNetwork.from_database(network))

        more_pages = False
        if len(resp_networks) > limit:
            more_pages = True
            del resp_networks[-1]  # Remove the last item to reset back to original limit

        return resp_networks, more_pages

    @Route(route='{network_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsNetwork)
    def delete(self, network_id):
        cherrypy.response.status = 204
        with cherrypy.request.db_session() as session:
            network = session.query(Network).filter(Network.id == network_id).with_for_update().first()

            if network is None:
                raise cherrypy.HTTPError(400, "A network with the requested id does not exist.")

            if network.state not in [NetworkState.CREATED, NetworkState.ERROR]:
                raise cherrypy.HTTPError(412, "Can only delete a network while it is in the following states: %s" % (
                    [NetworkState.CREATED.value, NetworkState.ERROR.value]))

            ports = session.query(NetworkPort).filter(NetworkPort.network_id == network.id).with_for_update
            port_count = len(ports)

            if port_count > 0:
                raise cherrypy.HTTPError(412, "Cannot delete network when there are ports connected to it.")

            # Don't delete portgroup since it is manually managed

            network.state = NetworkState.DELETING
            session.delete(network)
            session.commit()
