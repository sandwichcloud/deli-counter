from schematics import Model
from schematics.types import IntType, UUIDType, StringType, BooleanType

from ingredients_db.models.zones import Zone, ZoneState
from ingredients_http.schematics.types import ArrowType, EnumType


class RequestCreateZone(Model):
    name = StringType(required=True, min_length=3)
    region_id = UUIDType(required=True)
    vm_cluster = StringType(required=True)
    vm_datastore = StringType(required=True)
    vm_folder = StringType()
    core_provision_percent = IntType(min_value=0, required=True)
    ram_provision_percent = IntType(min_value=0, required=True)


class ParamsZone(Model):
    zone_id = UUIDType(required=True)


class ParamsListZone(Model):
    region_id = UUIDType()
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestZoneSchedule(Model):
    schedulable = BooleanType(required=True)


class ResponseZone(Model):
    id = UUIDType(required=True)
    name = StringType(required=True, min_length=3)
    region_id = UUIDType(required=True)
    vm_cluster = StringType(required=True)
    vm_datastore = StringType(required=True)
    vm_folder = StringType()
    core_provision_percent = IntType(required=True)
    ram_provision_percent = IntType(required=True)
    schedulable = BooleanType(required=True)
    state = EnumType(ZoneState, required=True)
    current_task_id = UUIDType()
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, zone: Zone):
        zone_model = cls()
        zone_model.id = zone.id
        zone_model.name = zone.name
        zone_model.region_id = zone.region_id
        zone_model.vm_cluster = zone.vm_cluster
        zone_model.vm_datastore = zone.vm_datastore
        zone_model.vm_folder = zone.vm_folder
        zone_model.core_provision_percent = zone.core_provision_percent
        zone_model.ram_provision_percent = zone.ram_provision_percent
        zone_model.schedulable = zone.schedulable

        zone_model.state = zone.state
        zone_model.current_task_id = zone.current_task_id

        zone_model.created_at = zone.created_at
        zone_model.updated_at = zone.updated_at

        return zone_model
