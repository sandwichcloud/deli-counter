from schematics import Model
from schematics.types import IntType, UUIDType, StringType, BooleanType

from ingredients_db.models.region import RegionState, Region
from ingredients_http.schematics.types import ArrowType, EnumType


class RequestCreateRegion(Model):
    name = StringType(required=True, min_length=3)
    datacenter = StringType(required=True)
    image_datastore = StringType(required=True)
    image_folder = StringType()


class ParamsRegion(Model):
    region_id = UUIDType(required=True)


class ParamsListRegion(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestRegionSchedule(Model):
    schedulable = BooleanType(required=True)


class ResponseRegion(Model):
    id = UUIDType(required=True)
    name = StringType(required=True, min_length=3)
    datacenter = StringType(required=True, )
    image_datastore = StringType(required=True)
    image_folder = StringType()
    schedulable = BooleanType(required=True)
    state = EnumType(RegionState, required=True)
    current_task_id = UUIDType()
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, region: Region):
        region_model = cls()
        region_model.id = region.id
        region_model.name = region.name
        region_model.datacenter = region.datacenter
        region_model.image_datastore = region.image_datastore
        region_model.image_folder = region.image_folder
        region_model.schedulable = region.schedulable

        region_model.state = region.state
        region_model.current_task_id = region.current_task_id

        region_model.created_at = region.created_at
        region_model.updated_at = region.updated_at

        return region_model
