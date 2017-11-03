from schematics import Model
from schematics.types import UUIDType, StringType, IntType, BooleanType

from ingredients_db.models.images import ImageVisibility, ImageState, Image
from ingredients_http.schematics.types import EnumType, ArrowType


class ParamsImage(Model):
    image_id = UUIDType(required=True)


class ParamsListImage(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestCreateImage(Model):
    name = StringType(required=True, min_length=3)
    file_name = StringType(required=True)
    visibility = EnumType(ImageVisibility, required=True)


class ResponseImage(Model):
    id = UUIDType(required=True)
    name = StringType(required=True, min_length=3)
    file_name = StringType(required=True)
    locked = BooleanType(required=True)
    visibility = EnumType(ImageVisibility, required=True)
    state = EnumType(ImageState, required=True)
    current_task_id = UUIDType()
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, image: Image):
        image_model = cls()
        image_model.id = image.id
        image_model.name = image.name

        image_model.file_name = image.file_name
        image_model.visibility = image.visibility
        image_model.locked = image.locked
        image_model.state = image.state
        image_model.current_task_id = image.current_task_id

        image_model.created_at = image.created_at
        image_model.updated_at = image.updated_at

        return image_model
