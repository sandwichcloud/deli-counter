import uuid

from deli_counter.http.mounts.root.routes.v1.auth.z.validation_models.policies import ResponsePolicy
from deli_counter.http.mounts.root.routes.v1.auth.z.validation_models.roles import ResponseRole
from deli_counter.test.base import DeliTestCase, fake
from ingredients_db.models.authz import AuthZPolicy, AuthZRole


class TestAuthZ(DeliTestCase):
    # TODO: check that routes have correct decorators
    # TODO: test model validations

    def test_create_policy(self, wsgi, app):
        admin_token = self.create_token(app, roles=["admin"])

        policy_data = {
            "name": fake.pystr(min_chars=3),
            "rule": "role:test"
        }

        # Test create
        resp = self.post(wsgi, "/v1/auth/z/policies", policy_data, token=admin_token)
        resp_model = ResponsePolicy(resp.json)
        # Check that the resp matches the model
        assert resp.json == resp_model.to_primitive()
        with app.database.session() as session:
            policy = session.query(AuthZPolicy).filter(AuthZPolicy.id == resp_model.id).first()
            assert policy is not None

        # Test duplicate
        resp = self.post(wsgi, "/v1/auth/z/policies", policy_data, token=admin_token, status=409)
        # Check the error message
        assert resp.json['message'] == 'A policy with the requested name already exists.'

        # Test cyclic policy
        policy_data = {
            "name": fake.pystr(min_chars=3),
        }
        policy_data['rule'] = 'rule:' + policy_data['name']
        resp = self.post(wsgi, "/v1/auth/z/policies", policy_data, token=admin_token, status=400)
        # Check the error message
        assert resp.json['message'] == "Policies ['" + policy_data[
            'name'] + "'] are not well defined. Check logs for more details."

        # TODO: figure out how to test an invalid policy.
        # Like 'rule:is_admin or', oslo.policy doesn't seem to have a way to check for this?

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

    def test_update_policy(self, wsgi, app):
        policy = self.create_policy(app, "role:test")
        admin_token = self.create_token(app, roles=["admin"])

        update_policy = {
            "rule": "role:updated"
        }

        # Test invalid policy
        self.put(wsgi, "/v1/auth/z/policies/%s" % uuid.uuid4(), update_policy, token=admin_token, status=404)

        # Test correct policy
        resp = self.put(wsgi, "/v1/auth/z/policies/%s" % policy.id, update_policy, token=admin_token)
        # Pull updated policy from database
        with app.database.session() as session:
            policy = session.query(AuthZPolicy).filter(AuthZPolicy.id == policy.id).first()
            # Check that the resp matches the model
            resp_model = ResponsePolicy(resp.json)
            assert resp.json == resp_model.to_primitive()
            assert resp.json == ResponsePolicy.from_database(policy).to_primitive()
            # Check that rule has been applied
            assert policy.rule == update_policy['rule']

    def test_delete_policy(self, wsgi, app):
        admin_token = self.create_token(app, roles=["admin"])
        policy = self.create_policy(app, "rule:test")

        # Test invalid policy
        self.delete(wsgi, "/v1/auth/z/policies/%s" % uuid.uuid4(), token=admin_token, status=404)

        # Test correct policy
        self.delete(wsgi, "/v1/auth/z/policies/%s" % policy.id, token=admin_token, status=204)

        # Check to make sure it's gone
        with app.database.session() as session:
            policy = session.query(AuthZPolicy).filter(AuthZPolicy.id == policy.id).first()
            assert policy is None

    def test_create_role(self, wsgi, app):
        admin_token = self.create_token(app, roles=["admin"])

        role_data = {
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
        resp = self.get(wsgi, "/v1/auth/z/roles", token=admin_token)
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
