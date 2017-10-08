from schematics import Model
from schematics.types import UUIDType, StringType

from ingredients_db.models.task import TaskState, Task
from ingredients_http.schematics.types import EnumType, ArrowType


class TaskModel(Model):
    id = UUIDType(required=True)
    name = StringType(required=True)
    state = EnumType(TaskState)
    error_message = StringType()
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)
    stopped_at = ArrowType()

    @classmethod
    def from_database(cls, task: Task):
        task_model = cls()
        task_model.id = task.id
        task_model.name = task.name
        task_model.state = task.state
        task_model.error_message = task.error_message
        task_model.created_at = task.created_at
        task_model.updated_at = task.updated_at
        task_model.stopped_at = task.stopped_at

        return task_model
