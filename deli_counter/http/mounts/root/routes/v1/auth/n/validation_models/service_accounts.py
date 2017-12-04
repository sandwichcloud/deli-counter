from schematics import Model
from schematics.types import UUIDType, IntType, StringType

from ingredients_db.models.authn import AuthNServiceAccount
from ingredients_http.schematics.types import ArrowType


class ParamsServiceAccount(Model):
    service_account_id = UUIDType(required=True)


class ParamsListServiceAccount(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestCreateServiceAccount(Model):
    name = StringType(required=True)
    role_id = UUIDType(required=True)


class ResponseServiceAccount(Model):
    service_account_id = UUIDType(required=True)
    name = StringType(required=True)
    project_id = UUIDType(required=True)
    role_id = UUIDType(required=True)
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, service_account: AuthNServiceAccount):
        model = cls()
        model.service_account_id = service_account.id
        model.name = service_account.name
        model.project_id = service_account.project_id
        model.role_id = service_account.role_id
        model.created_at = service_account.created_at
        model.updated_at = service_account.updated_at

        return model
