import uuid
from unittest.mock import patch

from deli_counter.http.mounts.root.routes.v1.validation_models.images import ResponseImage
from deli_counter.test.base import DeliTestCase, fake
from ingredients_db.models.images import Image, ImageState


class TestImage(DeliTestCase):
    # TODO: check that routes have correct decorators
    # TODO: test model validations

    def test_create(self, wsgi, app):
        project = self.create_project(app)
        region = self.create_region(app)
        token = self.create_token(app, project=project)
        admin_token = self.create_token(app, roles=['admin'], project=project)

        image_data = {
            "name": fake.pystr(min_chars=3),
            "file_name": fake.pystr(min_chars=3),
            "visibility": "PRIVATE",
            "region_id": str(region.id)
        }

        # Test create normal
        with patch('ingredients_tasks.tasks.image.create_image.apply_async') as apply_async_mock:
            apply_async_mock.return_value = None
            resp = self.post(wsgi, "/v1/images", image_data, token=token)
        resp_model = ResponseImage(resp.json)
        # Check that the resp matches the model
        assert resp.json == resp_model.to_primitive()
        with app.database.session() as session:
            image = session.query(Image).filter(Image.id == resp_model.id).first()
            # Check that it was created
            assert image is not None
            # Check that it has a current task
            assert image.current_task_id is not None

        # Test create image same name
        resp = self.post(wsgi, "/v1/images", image_data, token=token, status=409)
        # Check the error message
        assert resp.json['message'] == 'An image with the requested name already exists.'

        # Test create image same file
        image_data['name'] = fake.pystr(min_chars=3)
        resp = self.post(wsgi, "/v1/images", image_data, token=token, status=409)
        # Check the error message
        assert resp.json['message'] == 'An image with the requested file already exists.'

        # Test create public (no perms)
        image_data = {
            "name": fake.pystr(min_chars=3),
            "file_name": fake.pystr(min_chars=3),
            "visibility": "PUBLIC",
            "region_id": str(region.id)
        }
        self.post(wsgi, "/v1/images", image_data, token=token, status=403)

        # Test create public
        with patch('ingredients_tasks.tasks.image.create_image.apply_async') as apply_async_mock:
            apply_async_mock.return_value = None
            self.post(wsgi, "/v1/images", image_data, token=admin_token)

    def test_get(self, wsgi, app):
        project = self.create_project(app)
        token = self.create_token(app, project=project)
        image = self.create_image(app, project)

        # Test invalid
        self.get(wsgi, '/v1/images/%s' % uuid.uuid4(), token=token, status=404)

        # Test ok
        resp = self.get(wsgi, '/v1/images/%s' % image.id, token=token)
        resp_model = ResponseImage(resp.json)
        assert resp.json == resp_model.to_primitive()
        assert resp.json == ResponseImage.from_database(image).to_primitive()

    def test_list(self, wsgi, app):
        project = self.create_project(app)
        token = self.create_token(app, project=project)

        # Test List
        resp = self.get(wsgi, "/v1/images", token=token)
        assert 'images' in resp.json
        for image_json in resp.json['images']:
            image_model = ResponseImage(image_json)
            assert image_json == image_model.to_primitive()

    def test_delete(self, wsgi, app):
        project = self.create_project(app)
        token = self.create_token(app, project=project)
        image = self.create_image(app, project)

        # Test invalid
        self.delete(wsgi, "/v1/images/%s" % uuid.uuid4(), token=token, status=404)

        # Test correct
        with patch('ingredients_tasks.tasks.image.delete_image.apply_async') as apply_async_mock:
            apply_async_mock.return_value = None
            self.delete(wsgi, "/v1/images/%s" % image.id, token=token, status=202)
        # Check to make sure it's in deleting state
        with app.database.session() as session:
            image = session.query(Image).filter(Image.id == image.id).first()
            assert image.state == ImageState.DELETING
