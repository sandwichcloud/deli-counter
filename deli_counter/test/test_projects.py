import uuid

from deli_counter.http.mounts.root.routes.v1.validation_models.projects import ResponseProject
from deli_counter.test.base import DeliTestCase, fake
from ingredients_db.models.project import Project


class TestProject(DeliTestCase):
    # TODO: check that routes have correct decorators
    # TODO: test model validations

    def test_create(self, wsgi, app):
        admin_token = self.create_token(app, roles=["admin"])

        project_data = {
            "name": fake.pystr(min_chars=3)
        }

        # Test create
        resp = self.post(wsgi, "/v1/projects", project_data, token=admin_token)
        resp_model = ResponseProject(resp.json)
        # Check that the resp matches the model
        assert resp.json == resp_model.to_primitive()
        with app.database.session() as session:
            project = session.query(Project).filter(Project.id == resp_model.id).first()
            assert project is not None

        # Test duplicate
        resp = self.post(wsgi, "/v1/projects", project_data, token=admin_token, status=409)
        # Check the error message
        assert resp.json['message'] == 'A project with the requested name already exists.'

    def test_get(self, wsgi, app):
        token = self.create_token(app, roles=["viewer"])
        project = self.create_project(app)

        # Test invalid
        self.get(wsgi, "/v1/projects/%s" % uuid.uuid4(), token=token, status=404)

        # Test good
        resp = self.get(wsgi, "/v1/projects/%s" % project.id, token=token)
        resp_model = ResponseProject(resp.json)
        assert resp.json == resp_model.to_primitive()
        assert resp.json == ResponseProject.from_database(project).to_primitive()

    def test_list(self, wsgi, app):
        token = self.create_token(app, roles=["viewer"])

        # Test List
        resp = self.get(wsgi, "/v1/projects", token=token)
        assert 'projects' in resp.json
        for project_json in resp.json['projects']:
            project_model = ResponseProject(project_json)
            assert project_json == project_model.to_primitive()

    def test_delete(self, wsgi, app):
        admin_token = self.create_token(app, roles=["admin"])
        project = self.create_project(app)

        # Test invalid
        self.delete(wsgi, "/v1/projects/%s" % uuid.uuid4(), token=admin_token, status=404)

        # Test correct
        self.delete(wsgi, "/v1/projects/%s" % project.id, token=admin_token, status=204)

        # Check to make sure it's gone
        with app.database.session() as session:
            project = session.query(Project).filter(Project.id == project.id).first()
            assert project is None
