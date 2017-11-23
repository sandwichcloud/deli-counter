import uuid

import cherrypy

from deli_counter.http.mounts.root.routes.v1.validation_models.projects import ParamsProject, RequestCreateProject, \
    ResponseProject, ParamsListProject
from ingredients_db.models.images import Image
from ingredients_db.models.instance import Instance
from ingredients_db.models.project import Project, ProjectState
from ingredients_http.route import Route, RequestMethods
from ingredients_http.router import Router


# TODO: restrict project to certain networks


class ProjectRouter(Router):
    def __init__(self):
        super().__init__(uri_base='projects')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateProject)
    @cherrypy.tools.model_out(cls=ResponseProject)
    @cherrypy.tools.enforce_policy(policy_name="projects:create")
    def create(self):
        request: RequestCreateProject = cherrypy.request.model

        with cherrypy.request.db_session() as session:
            project = session.query(Project).filter(Project.name == request.name).first()

            if project is not None:
                raise cherrypy.HTTPError(409, 'A project with the requested name already exists.')

            project = Project()
            project.name = request.name

            session.add(project)
            session.commit()
            session.refresh(project)

        return ResponseProject.from_database(project)

    @Route(route='{project_id}')
    @cherrypy.tools.model_params(cls=ParamsProject)
    @cherrypy.tools.model_out(cls=ResponseProject)
    @cherrypy.tools.resource_object(id_param="project_id", cls=Project)
    @cherrypy.tools.enforce_policy(policy_name="projects:get")
    def get(self, project_id):
        return ResponseProject.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListProject)
    @cherrypy.tools.model_out_pagination(cls=ResponseProject)
    @cherrypy.tools.enforce_policy(policy_name="projects:list")
    def list(self, name: str, limit: int, marker: uuid.UUID):
        # TODO: only list projects that we are a member of
        # optional param to list all
        return self.paginate(Project, ResponseProject, limit, marker)

    @Route(route='{project_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsProject)
    @cherrypy.tools.resource_object(id_param="project_id", cls=Project)
    @cherrypy.tools.enforce_policy(policy_name="projects:delete")
    def delete(self, project_id):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']

        with cherrypy.request.db_session() as session:
            project: Project = session.merge(cherrypy.request.resource_object, load=False)

            if project.state != ProjectState.CREATED:
                raise cherrypy.HTTPError(409, "Project with the requested id is not in the '%s' state" % (
                    ProjectState.CREATED.value))

            image_count = session.query(Image).filter(Image.project_id == project.id).count()
            if image_count > 0:
                raise cherrypy.HTTPError(412, 'Cannot delete a project with images.')
            # TODO: check instance count

            instance_count = session.query(Instance).filter(Instance.project_id == project.id).count()
            if instance_count > 0:
                raise cherrypy.HTTPError(412, "Cannot delete a project with instances.")

            project.state = ProjectState.DELETED
            session.delete(project)
            session.commit()
