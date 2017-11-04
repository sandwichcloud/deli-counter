import uuid
from unittest.mock import patch

from deli_counter.http.mounts.root.routes.v1.validation_models.networks import ResponseNetwork
from deli_counter.test.base import DeliTestCase, fake
from ingredients_db.models.network import Network


class TestNetwork(DeliTestCase):
    # TODO: check that routes have correct decorators
    # TODO: test model validations

    def test_create(self, wsgi, app):
        admin_token = self.create_token(app, roles=["admin"])

        network_data = {
            "name": fake.pystr(min_chars=3),
            "port_group": fake.pystr(min_chars=3),
            "cidr": "10.0.0.0/24",
            "gateway": "10.0.0.1",
            "dns_servers": ["8.8.8.8", "8.8.4.4"],
            "pool_start": "10.0.0.10",
            "pool_end": "10.0.0.254"
        }

        # Test create
        with patch('ingredients_tasks.tasks.network.create_network.apply_async') as apply_async_mock:
            apply_async_mock.return_value = None
            resp = self.post(wsgi, "/v1/networks", network_data, token=admin_token)
        resp_model = ResponseNetwork(resp.json)
        # Check that the resp matches the model
        assert resp.json == resp_model.to_primitive()
        with app.database.session() as session:
            network = session.query(Network).filter(Network.id == resp_model.id).first()
            # Check that the network was created
            assert network is not None
            # Check that the network has a current task
            assert network.current_task_id is not None

        # Test duplicate name
        resp = self.post(wsgi, "/v1/networks", network_data, token=admin_token, status=409)
        # Check the error message
        assert resp.json['message'] == 'A network with the requested name already exists.'

        # Test duplicate port group
        network_data['name'] = fake.pystr(min_chars=3)
        resp = self.post(wsgi, "/v1/networks", network_data, token=admin_token, status=409)
        # Check the error message
        assert resp.json['message'] == 'A network with the requested port group already exists.'

    def test_get(self, wsgi, app):
        token = self.create_token(app)
        network = self.create_network(app)

        # Test invalid
        self.get(wsgi, '/v1/networks/%s' % uuid.uuid4(), token=token, status=404)

        # Test ok
        resp = self.get(wsgi, '/v1/networks/%s' % network.id, token=token)
        resp_model = ResponseNetwork(resp.json)
        assert resp.json == resp_model.to_primitive()
        assert resp.json == ResponseNetwork.from_database(network).to_primitive()

    def test_list(self, wsgi, app):
        token = self.create_token(app)

        # Test List
        resp = self.get(wsgi, "/v1/networks", token=token)
        assert 'networks' in resp.json
        for network_json in resp.json['networks']:
            network_model = ResponseNetwork(network_json)
            assert network_json == network_model.to_primitive()

    def test_delete(self, wsgi, app):
        admin_token = self.create_token(app, roles=["admin"])
        network = self.create_network(app)

        # Test invalid
        self.delete(wsgi, "/v1/networks/%s" % uuid.uuid4(), token=admin_token, status=404)

        # Test correct
        self.delete(wsgi, "/v1/networks/%s" % network.id, token=admin_token, status=204)

        # Check to make sure it's gone
        with app.database.session() as session:
            network = session.query(Network).filter(Network.id == network.id).first()
            assert network is None
