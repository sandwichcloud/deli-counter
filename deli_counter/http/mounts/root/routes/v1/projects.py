import uuid

import cherrypy

from deli_counter.http.mounts.root.routes.v1.validation_models.projects import ParamsProject, RequestCreateProject, \
    ResponseProject, ParamsListProject
from ingredients_db.models.images import Image
from ingredients_db.models.project import Project, ProjectState
from ingredients_http.route import Route, RequestMethods
from ingredients_http.router import Router


class ProjectRouter(Router):
    def __init__(self):
        super().__init__(uri_base='projects')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateProject)
    @cherrypy.tools.model_out(cls=ResponseProject)
    def create(self):
        # TODO: default to admins only
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
    def get(self, project_id: uuid.UUID):
        with cherrypy.request.db_session() as session:
            project = session.query(Project).filter(Project.id == project_id).first()

            if project is None:
                raise cherrypy.HTTPError(404, 'A project with the requested id does not exist.')

            return ResponseProject.from_database(project)

    @Route(route='{project_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsProject)
    def delete(self, project_id: uuid.UUID):
        cherrypy.response.status = 204

        with cherrypy.request.db_session() as session:
            project = session.query(Project).filter(Project.id == project_id).first()

            if project is None:
                raise cherrypy.HTTPError(404, 'A project with the requested id does not exist.')

            if project.state != ProjectState.CREATED:
                raise cherrypy.HTTPError(409, "Project with the requested id is not in the '%s' state" % (
                    ProjectState.CREATED.value))

            image_count = session.query(Image).filter(Image.project_id == project.id).count()
            if image_count > 0:
                raise cherrypy.HTTPError(412, 'Cannot delete a project with images.')
            # TODO: check instance count

            project.state = ProjectState.DELETED
            session.delete(project)
            session.commit()

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListProject)
    @cherrypy.tools.model_out_pagination(cls=ResponseProject)
    def list_projects(self, name: str, limit: int, marker: uuid.UUID):
        resp_projects = []

        with cherrypy.request.db_session() as session:
            projects = session.query(Project).order_by(Project.created_at.desc())

            if name is not None:
                projects = projects.filter(Project.name == name)

            if marker is not None:
                marker = session.query(Project).filter(Project.id == marker).first()
                if marker is None:
                    raise cherrypy.HTTPError(status=400, message="Unknown marker ID")
                projects = projects.filter(Project.created_at < marker.created_at)

            projects = projects.limit(limit + 1)

            for project in projects:
                resp_projects.append(ResponseProject.from_database(project))

        more_pages = False
        if len(resp_projects) > limit:
            more_pages = True
            del resp_projects[-1]  # Remove the last item to reset back to original limit

        return resp_projects, more_pages
