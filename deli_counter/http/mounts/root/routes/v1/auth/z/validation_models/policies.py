from schematics import Model
from schematics.types import UUIDType, IntType, StringType

from ingredients_db.models.authz import AuthZPolicy
from ingredients_http.schematics.types import ArrowType


class ParamsPolicy(Model):
    policy_id = UUIDType(required=True)


class ParamsListPolicy(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestUpdatePolicy(Model):
    rule = StringType(required=True)


class ResponsePolicy(Model):
    id = UUIDType(required=True)
    name = StringType(required=True)
    description = StringType()
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, policy: AuthZPolicy):
        policy_model = cls()
        policy_model.id = policy.id
        policy_model.name = policy.name
        policy_model.description = policy.description
        if policy_model.description is None:
            policy_model.description = ""

        policy_model.created_at = policy.created_at
        policy_model.updated_at = policy.updated_at

        return policy_model
