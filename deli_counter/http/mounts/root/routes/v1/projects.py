import uuid

import cherrypy
from sqlalchemy.orm import Query

from deli_counter.http.mounts.root.routes.v1.validation_models.projects import ParamsProject, RequestCreateProject, \
    ResponseProject, ParamsListProject
from ingredients_db.models.authn import AuthNServiceAccount
from ingredients_db.models.authz import AuthZRole, AuthZPolicy, AuthZRolePolicy
from ingredients_db.models.images import Image
from ingredients_db.models.instance import Instance
from ingredients_db.models.project import Project, ProjectState, ProjectMembers
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
            session.flush()
            session.refresh(project)

            # Create the default member role
            member_role = AuthZRole()
            member_role.name = "default_member"
            member_role.description = "Default role for project members"
            member_role.project_id = project.id
            session.add(member_role)
            session.flush()
            session.refresh(member_role)
            member_policies = session.query(AuthZPolicy).filter(AuthZPolicy.tags.any("project_member"))
            for policy in member_policies:
                mr_policy = AuthZRolePolicy()
                mr_policy.role_id = member_role.id
                mr_policy.policy_id = policy.id
                session.add(mr_policy)

            # Create the default service account role
            sa_role = AuthZRole()
            sa_role.name = "default_service_account"
            sa_role.description = "Default role for project service accounts"
            sa_role.project_id = project.id
            session.add(sa_role)
            session.flush()
            session.refresh(sa_role)
            sa_policies = session.query(AuthZPolicy).filter(AuthZPolicy.tags.any("service_account"))
            for policy in sa_policies:
                sa_policy = AuthZRolePolicy()
                sa_policy.role_id = sa_role.id
                sa_policy.policy_id = policy.id
                session.add(sa_policy)

            # Create the default service account
            sa = AuthNServiceAccount()
            sa.name = "default"
            sa.project_id = project.id
            sa.role_id = sa_role.id
            session.add(sa)

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
    def list(self, all: bool, limit: int, marker: uuid.UUID):
        starting_query = Query(Project).join(ProjectMembers, Project.id == ProjectMembers.project_id).filter(
            ProjectMembers.user_id == cherrypy.request.user.id)
        if all:
            starting_query = None
        return self.paginate(Project, ResponseProject, limit, marker, starting_query=starting_query)

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

            instance_count = session.query(Instance).filter(Instance.project_id == project.id).count()
            if instance_count > 0:
                raise cherrypy.HTTPError(412, "Cannot delete a project with instances.")

            # Delete members
            session.query(ProjectMembers).filter(ProjectMembers.project_id == project.id).delete()

            # Delete service accounts
            session.query(AuthNServiceAccount).filter(AuthNServiceAccount.project_id == project.id).delete()

            # Everything else should CASCADE delete

            project.state = ProjectState.DELETED
            session.delete(project)
            session.commit()
