from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_ssh_public_key
from schematics import Model
from schematics.exceptions import ValidationError
from schematics.types import UUIDType, IntType, StringType

from ingredients_db.models.keypair import Keypair


class ParamsKeypair(Model):
    keypair_id = UUIDType(required=True)


class ParamsListKeypair(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestCreateKeypair(Model):
    name = StringType(required=True, min_length=3)
    public_key = StringType(required=True)

    def validate_public_key(self, data, value):
        try:
            load_ssh_public_key(value.encode(), default_backend())
        except ValueError:
            raise ValidationError("public_key could not be decoded or is not in the proper format")
        except UnsupportedAlgorithm:
            raise ValidationError("public_key serialization type is not supported")

        return value


class ResponseKeypair(Model):
    id = UUIDType(required=True)
    name = StringType(required=True, min_length=3)
    public_key = StringType(required=True)

    @classmethod
    def from_database(cls, keypair: Keypair):
        model = cls()
        model.id = keypair.id
        model.name = keypair.name
        model.public_key = keypair.public_key

        return model
