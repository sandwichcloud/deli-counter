import uuid

from deli_counter.http.mounts.root.routes.v1.auth.z.validation_models.policies import ResponsePolicy
from deli_counter.http.mounts.root.routes.v1.auth.z.validation_models.roles import ResponseRole
from deli_counter.test.base import DeliTestCase, fake
from ingredients_db.models.authz import AuthZRole


class TestAuthZ(DeliTestCase):
    # TODO: check that routes have correct decorators
    # TODO: test model validations

    def test_get_policy(self, wsgi, app):
        policy = self.create_policy(app, "role:test")
        admin_token = self.create_token(app, roles=["admin"])

        # Test invalid policy
        self.get(wsgi, "/v1/auth/z/policies/%s" % uuid.uuid4(), token=admin_token, status=404)

        # Test correct policy
        resp = self.get(wsgi, "/v1/auth/z/policies/%s" % policy.id, token=admin_token)
        resp_model = ResponsePolicy(resp.json)
        assert resp.json == resp_model.to_primitive()
        # Check that the resp matches the model
        assert resp.json == ResponsePolicy.from_database(policy).to_primitive()

    def test_list_policies(self, wsgi, app):
        admin_token = self.create_token(app, roles=["admin"])

        # Test List
        resp = self.get(wsgi, "/v1/auth/z/policies", token=admin_token)
        assert 'policies' in resp.json
        for policy_json in resp.json['policies']:
            policy_model = ResponsePolicy(policy_json)
            assert policy_json == policy_model.to_primitive()

    def test_create_role(self, wsgi, app):
        admin_token = self.create_token(app, roles=["admin"])

        role_data = {
            "type": "global",
            "name": fake.pystr(min_chars=3)
        }

        # Test create
        resp = self.post(wsgi, "/v1/auth/z/roles", role_data, token=admin_token)
        with app.database.session() as session:
            resp_model = ResponseRole(resp.json)
            # Check that the resp matches the model
            assert resp.json == resp_model.to_primitive()
            role = session.query(AuthZRole).filter(AuthZRole.id == resp_model.id).first()
            # Check that role is in the database
            assert role is not None

        # Test duplicate
        resp = self.post(wsgi, "/v1/auth/z/roles", role_data, token=admin_token, status=409)
        # Check the error message
        assert resp.json['message'] == 'A role with the requested name already exists.'

    def test_get_role(self, wsgi, app):
        role = self.create_role(app)
        admin_token = self.create_token(app, roles=["admin"])

        # Test invalid role
        self.get(wsgi, "/v1/auth/z/roles/%s" % uuid.uuid4(), token=admin_token, status=404)

        # Test correct role
        resp = self.get(wsgi, "/v1/auth/z/roles/%s" % role.id, token=admin_token)
        # Check that the resp matches the model
        resp_model = ResponseRole(resp.json)
        assert resp.json == resp_model.to_primitive()
        assert resp.json == ResponseRole.from_database(role).to_primitive()

    def test_list_roles(self, wsgi, app):
        admin_token = self.create_token(app, roles=["admin"])

        # Test List
        resp = self.get(wsgi, "/v1/auth/z/roles", token=admin_token, params={"type": "global"})
        assert 'roles' in resp.json
        for role_json in resp.json['roles']:
            role_model = ResponseRole(role_json)
            assert role_json == role_model.to_primitive()

    def test_delete_role(self, wsgi, app):
        admin_token = self.create_token(app, roles=["admin"])
        role = self.create_role(app)

        # Test invalid role
        self.delete(wsgi, "/v1/auth/z/roles/%s" % uuid.uuid4(), token=admin_token, status=404)

        # Test correct role
        self.delete(wsgi, "/v1/auth/z/roles/%s" % role.id, token=admin_token, status=204)

        # Check to make sure it's gone
        with app.database.session() as session:
            role = session.query(AuthZRole).filter(AuthZRole.id == role.id).first()
            assert role is None
