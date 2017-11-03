from schematics import Model
from schematics.types import UUIDType, StringType, ListType

from ingredients_db.models.authn import AuthNToken
from ingredients_http.schematics.types import ArrowType


class RequestScopeToken(Model):
    project_id = UUIDType(required=True)


class ParamsVerifyToken(Model):
    token_id = UUIDType(required=True)


class ResponseVerifyToken(Model):
    id = UUIDType(required=True)
    access_token = StringType(required=True)
    user_id = UUIDType(required=True)
    project_id = UUIDType()
    roles = ListType(StringType(), default=list)
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)
    expires_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, token: AuthNToken, roles):
        token_model = cls()
        token_model.id = token.id
        token_model.access_token = token.access_token
        token_model.user_id = token.user_id
        token_model.project_id = token.project_id
        token_model.created_at = token.created_at
        token_model.updated_at = token.updated_at
        token_model.expires_at = token.expires_at

        for role in roles:
            token_model.roles.append(role)

        return token_model


class ResponseOAuthToken(Model):
    access_token = StringType(required=True)
    expiry = ArrowType(required=True)

    @classmethod
    def from_database(cls, token: AuthNToken):
        token_model = cls()
        token_model.access_token = token.access_token
        token_model.expiry = token.expires_at

        return token_model
