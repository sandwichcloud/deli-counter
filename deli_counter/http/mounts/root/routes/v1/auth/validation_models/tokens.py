from schematics import Model
from schematics.types import UUIDType, StringType, ListType

from ingredients_http.schematics.types import ArrowType


class RequestScopeToken(Model):
    project_id = UUIDType(required=True)


class ResponseVerifyToken(Model):
    user_id = UUIDType()
    username = StringType()
    driver = StringType()
    service_account_id = UUIDType()
    service_account_name = StringType()
    project_id = UUIDType()
    global_roles = ListType(StringType(), default=list)
    project_roles = ListType(StringType(), default=list)


class ResponseOAuthToken(Model):
    access_token = StringType(required=True)
    expiry = ArrowType(required=True)
