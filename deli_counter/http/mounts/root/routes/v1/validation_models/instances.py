from schematics import Model
from schematics.types import StringType, UUIDType, IntType, DictType, ListType, BooleanType

from ingredients_db.models.images import ImageVisibility
from ingredients_db.models.instance import Instance, InstanceState
from ingredients_http.schematics.types import ArrowType, EnumType


class RequestCreateInstance(Model):
    name = StringType(required=True, min_length=3)
    image_id = UUIDType(required=True)
    service_account_id = UUIDType()
    network_id = UUIDType(required=True)
    region_id = UUIDType(required=True)
    zone_id = UUIDType()
    keypair_ids = ListType(UUIDType, default=list)
    tags = DictType(StringType)


class ResponseInstance(Model):
    id = UUIDType(required=True)
    name = StringType(required=True, min_length=3)
    image_id = UUIDType(required=True)
    network_port_id = UUIDType(required=True)
    region_id = UUIDType(required=True)
    zone_id = UUIDType()
    service_account_id = UUIDType()
    keypair_ids = ListType(UUIDType, default=list)
    state = EnumType(InstanceState, required=True)
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
        instance_model.state = instance.state
        instance_model.tags = instance.tags
        instance_model.service_account_id = instance.service_account_id

        instance_model.region_id = instance.region_id
        if instance.zone_id is not None:
            instance_model.zone_id = instance.zone_id

        for keypair in instance.keypairs:
            instance_model.keypair_ids.append(keypair.id)

        instance_model.created_at = instance.created_at
        instance_model.updated_at = instance.updated_at

        return instance_model


class ParamsInstance(Model):
    instance_id = UUIDType(required=True)


class ParamsListInstance(Model):
    image_id = UUIDType()
    zone_id = UUIDType()
    region_id = UUIDType()
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestInstanceImage(Model):
    name = StringType(required=True)
    visibility = EnumType(ImageVisibility, required=True)


class RequestInstancePowerOffRestart(Model):
    hard = BooleanType(default=False)
    timeout = IntType(default=60, min_value=60, max_value=300)


class RequestInstanceResetState(Model):
    active = BooleanType(default=False)
