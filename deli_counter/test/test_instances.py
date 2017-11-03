import uuid
from unittest.mock import patch

from deli_counter.http.mounts.root.routes.v1.validation_models.instances import ResponseInstance
from deli_counter.test.base import DeliTestCase, fake
from ingredients_db.models.instance import Instance, InstanceState


class TestInstance(DeliTestCase):
    # TODO: check that routes have correct decorators
    # TODO: test model validations

    def test_create(self, wsgi, app):
        project = self.create_project(app)
        token = self.create_token(app, project=project)
        network = self.create_network(app)
        image = self.create_image(app, project=project)

        instance_data = {
            "name": fake.pystr(min_chars=3),
            "image_id": str(image.id),
            "network_id": str(network.id)
        }

        # Test create normal
        with patch('ingredients_tasks.tasks.instance.create_instance.apply_async') as apply_async_mock:
            apply_async_mock.return_value = None
            resp = self.post(wsgi, "/v1/instances", instance_data, token=token)
        resp_model = ResponseInstance(resp.json)
        # Check that the resp matches the model
        assert resp.json == resp_model.to_primitive()
        with app.database.session() as session:
            image = session.query(Instance).filter(Instance.id == resp_model.id).first()
            # Check that it was created
            assert image is not None
            # Check that it has a current task
            assert image.current_task_id is not None

    def test_get(self, wsgi, app):
        project = self.create_project(app)
        token = self.create_token(app, project=project)
        network = self.create_network(app)
        image = self.create_image(app, project)
        instance = self.create_instance(app, project, image, network)

        # Test invalid
        self.get(wsgi, '/v1/instances/%s' % uuid.uuid4(), token=token, status=404)

        # Test ok
        resp = self.get(wsgi, '/v1/instances/%s' % instance.id, token=token)
        resp_model = ResponseInstance(resp.json)
        assert resp.json == resp_model.to_primitive()
        assert resp.json == ResponseInstance.from_database(instance).to_primitive()

    def test_list(self, wsgi, app):
        project = self.create_project(app)
        token = self.create_token(app, project=project)

        # Test List
        resp = self.get(wsgi, "/v1/instances", token=token)
        assert 'instances' in resp.json
        for instane_json in resp.json['instances']:
            instance_model = ResponseInstance(instane_json)
            assert instane_json == instance_model.to_primitive()

    def test_delete(self, wsgi, app):
        project = self.create_project(app)
        token = self.create_token(app, project=project)
        network = self.create_network(app)
        image = self.create_image(app, project)
        instance = self.create_instance(app, project, image, network)

        # Test invalid
        self.delete(wsgi, "/v1/instances/%s" % uuid.uuid4(), token=token, status=404)

        # Test correct
        with patch('ingredients_tasks.tasks.instance.delete_instance.apply_async') as apply_async_mock:
            apply_async_mock.return_value = None
            self.delete(wsgi, "/v1/instances/%s" % instance.id, token=token, status=202)
        # Check to make sure it's in deleting state
        with app.database.session() as session:
            image = session.query(Instance).filter(Instance.id == instance.id).first()
            assert image.state == InstanceState.DELETING
