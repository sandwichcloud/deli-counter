from schematics import Model
from schematics.types import UUIDType, IntType, StringType

from ingredients_db.models.authz import AuthZRole
from ingredients_http.schematics.types import ArrowType


class ParamsRole(Model):
    role_id = UUIDType(required=True)


class ParamsListRole(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestCreateRole(Model):
    name = StringType(required=True, min_length=3)
    description = StringType()


class ResponseRole(Model):
    id = UUIDType(required=True)
    name = StringType(required=True)
    description = StringType()
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, role: AuthZRole):
        role_model = cls()
        role_model.id = role.id
        role_model.name = role.name
        role_model.description = role.description
        if role_model.description is None:
            role_model.description = ''

        role_model.created_at = role.created_at
        role_model.updated_at = role.updated_at

        return role_model
