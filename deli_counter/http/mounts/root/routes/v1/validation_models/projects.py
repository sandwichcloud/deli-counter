from schematics import Model
from schematics.types import UUIDType, StringType, IntType

from ingredients_db.models.project import Project, ProjectState
from ingredients_http.schematics.types import ArrowType, EnumType


class RequestCreateProject(Model):
    name = StringType(required=True, min_length=3)


class ParamsProject(Model):
    project_id = UUIDType(required=True)


class ParamsListProject(Model):
    name = StringType(min_length=3)
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class ResponseProject(Model):
    id = UUIDType(required=True)
    name = StringType(required=True, min_length=3)
    state = EnumType(ProjectState, required=True)
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, project: Project):
        project_model = cls()
        project_model.id = project.id
        project_model.name = project.name
        project_model.state = project.state

        project_model.created_at = project.created_at
        project_model.updated_at = project.updated_at

        return project_model
