from schematics import Model
from schematics.types import StringType, UUIDType, IntType, DictType, ListType

from ingredients_db.models.instance import Instance
from ingredients_http.schematics.types import ArrowType


class RequestCreateInstance(Model):
    name = StringType(required=True, min_length=3)
    image_id = UUIDType(required=True)
    network_id = UUIDType(required=True)
    public_keys = ListType(UUIDType, default=list, required=True)
    tags = DictType(StringType)


class ResponseInstance(Model):
    id = UUIDType(required=True)
    name = StringType(required=True, min_length=3)
    image_id = UUIDType(required=True)
    network_port_id = UUIDType(required=True)
    public_keys = ListType(UUIDType, default=list)
    tags = DictType(StringType, default=dict)

    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, instance: Instance):
        instance_model = cls()
        instance_model.id = instance.id
        instance_model.name = instance.name
        instance_model.image_id = instance.image_id
        instance_model.network_port_id = instance.network_port_id
        instance_model.tags = instance.tags

        for public_key in instance.public_keys:
            instance_model.public_keys.append(public_key.id)

        instance_model.created_at = instance.created_at
        instance_model.updated_at = instance.updated_at

        return instance_model


class ParamsInstance(Model):
    instance_id = UUIDType(required=True)


class ParamsListInstance(Model):
    image_id = UUIDType()
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()
