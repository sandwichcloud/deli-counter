import uuid

import cherrypy
from sqlalchemy.orm import Query

from deli_counter.http.mounts.root.routes.v1.validation_models.images import ResponseImage
from deli_counter.http.mounts.root.routes.v1.validation_models.instances import RequestCreateInstance, \
    ResponseInstance, ParamsInstance, ParamsListInstance, RequestInstanceImage, RequestInstancePowerOffRestart, \
    RequestInstanceResetState
from ingredients_db.models.images import Image, ImageVisibility, ImageState
from ingredients_db.models.instance import Instance, InstanceState
from ingredients_db.models.network import Network, NetworkState
from ingredients_db.models.network_port import NetworkPort
from ingredients_db.models.public_key import PublicKey
from ingredients_db.models.task import Task
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router
from ingredients_tasks.tasks.image import convert_vm
from ingredients_tasks.tasks.instance import create_instance, delete_instance, start_instance, stop_instance, \
    restart_instance
from ingredients_tasks.tasks.tasks import create_task


class InstanceRouter(Router):
    def __init__(self):
        super().__init__(uri_base='instances')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_in(cls=RequestCreateInstance)
    @cherrypy.tools.model_out(cls=ResponseInstance)
    @cherrypy.tools.enforce_policy(policy_name="instances:create")
    def create(self):
        request: RequestCreateInstance = cherrypy.request.model

        # TODO: allow multiple instances to be created at once add -# to the name

        with cherrypy.request.db_session() as session:
            project = cherrypy.request.project

            instance = session.query(Instance).filter(Instance.project_id == project.id).filter(
                Instance.name == request.name).first()

            if instance is not None:
                raise cherrypy.HTTPError(409, 'An instance already exists with the requested name.')

            image = session.query(Image).filter(Image.id == request.image_id).first()

            if image is None:
                raise cherrypy.HTTPError(404, "An image with the requested id does not exist.")

            if image.state != ImageState.CREATED:
                raise cherrypy.HTTPError(412, "The requested image is not in the '%s' state" % (
                    ImageState.CREATED.value))

            if image.project_id != project.id:
                if image.visibility == ImageVisibility.PRIVATE:
                    raise cherrypy.HTTPError(400, "The requested image does not belong to the scoped project.")
                elif image.visibility == ImageVisibility.SHARED:
                    if project not in image.members:
                        raise cherrypy.HTTPError(400, "The requested image is not shared with the scoped project.")
                elif image.visibility == ImageVisibility.PUBLIC:
                    # Image is public so don't error
                    pass

            network = session.query(Network).filter(Network.id == request.network_id).first()

            if network is None:
                raise cherrypy.HTTPError(404, "A network with the requested id does not exist.")

            if network.state != NetworkState.CREATED:
                raise cherrypy.HTTPError(412, "The requested network is not in the '%s' state" % (
                    NetworkState.CREATED.value))

            network_port = NetworkPort()
            network_port.network_id = network.id
            session.add(network_port)
            session.flush()

            instance = Instance()
            instance.name = request.name
            instance.image_id = image.id
            instance.project_id = project.id
            instance.network_port_id = network_port.id
            instance.tags = request.tags
            session.add(instance)
            session.flush()

            for public_key_id in request.public_keys:
                public_key = session.query(PublicKey).filter(PublicKey.id == public_key_id).filter(
                    PublicKey.project_id == project.id).first()

                if public_key is None:
                    raise cherrypy.HTTPError(404,
                                             "Could not find a public key within the scoped project with the id %s" %
                                             public_key_id)

                instance.public_keys.append(public_key)

            print("TASK")
            create_task(session, instance, create_instance, instance_id=instance.id)

            response = ResponseInstance.from_database(instance)
            session.commit()

            return response

    @Route(route='{instance_id}')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.model_out(cls=ResponseInstance)
    @cherrypy.tools.resource_object(id_param="instance_id", cls=Instance)
    @cherrypy.tools.enforce_policy(policy_name="instances:get")
    def get(self, instance_id: uuid.UUID):
        return ResponseInstance.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListInstance)
    @cherrypy.tools.model_out_pagination(cls=ResponseInstance)
    @cherrypy.tools.enforce_policy(policy_name="instances:list")
    def list(self, image_id: uuid.UUID, limit: int, marker: uuid.UUID):
        # TODO: allow filtering by tags
        project = cherrypy.request.project
        starting_query = Query(Instance).filter(Instance.project_id == project.id)
        return self.mount.paginate(Instance, ResponseInstance, limit, marker, starting_query=starting_query)

    @Route(route='{instance_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.resource_object(id_param="instance_id", cls=Instance)
    @cherrypy.tools.enforce_policy(policy_name="instances:delete")
    def delete(self, instance_id: uuid.UUID):
        cherrypy.response.status = 202
        with cherrypy.request.db_session() as session:
            instance: Instance = session.merge(cherrypy.request.resource_object, load=False)

            if instance.state not in [InstanceState.STOPPED, InstanceState.ACTIVE, InstanceState.ERROR]:
                raise cherrypy.HTTPError(409, "Can only delete an instance in the following states: %s" % [
                    InstanceState.STOPPED.value, InstanceState.ACTIVE.value, InstanceState.ERROR.value])

            instance.state = InstanceState.DELETING

            create_task(session, instance, delete_instance, instance_id=instance.id, delete_backing=True)

            session.commit()

    @Route(route='{instance_id}/action/stop', methods=[RequestMethods.PUT])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.model_in(cls=RequestInstancePowerOffRestart)
    @cherrypy.tools.resource_object(id_param="instance_id", cls=Instance)
    @cherrypy.tools.enforce_policy(policy_name="instances:action:stop")
    def action_stop(self, instance_id: uuid.UUID):
        request: RequestInstancePowerOffRestart = cherrypy.request.model
        cherrypy.response.status = 202
        with cherrypy.request.db_session() as session:
            instance: Instance = session.merge(cherrypy.request.resource_object, load=False)

            if instance.state != InstanceState.ACTIVE:
                raise cherrypy.HTTPError(409,
                                         "Can only stop an instance in the following state: %s" %
                                         InstanceState.ACTIVE.value)

            instance.state = InstanceState.STOPPING

            create_task(session, instance, stop_instance, instance_id=instance.id, hard=request.hard,
                        timeout=request.timeout)

            session.commit()

    @Route(route='{instance_id}/action/start', methods=[RequestMethods.PUT])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.resource_object(id_param="instance_id", cls=Instance)
    @cherrypy.tools.enforce_policy(policy_name="instances:action:start")
    def action_start(self, instance_id: uuid.UUID):
        cherrypy.response.status = 202
        with cherrypy.request.db_session() as session:
            instance: Instance = session.merge(cherrypy.request.resource_object, load=False)

            if instance.state != InstanceState.STOPPED:
                raise cherrypy.HTTPError(400,
                                         "Can only start an instance in the following state: %s" %
                                         InstanceState.STOPPED.value)

            if instance.state != InstanceState.STOPPED:
                raise cherrypy.HTTPError(409,
                                         "Can only start an instance in the following state: %s" %
                                         InstanceState.STOPPED.value)

            instance.state = InstanceState.STARTING

            create_task(session, instance, start_instance, instance_id=instance.id)

            session.commit()

    @Route(route='{instance_id}/action/restart', methods=[RequestMethods.PUT])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.model_in(cls=RequestInstancePowerOffRestart)
    @cherrypy.tools.resource_object(id_param="instance_id", cls=Instance)
    @cherrypy.tools.enforce_policy(policy_name="instances:action:restart")
    def action_restart(self, instance_id: uuid.UUID):
        request: RequestInstancePowerOffRestart = cherrypy.request.model
        cherrypy.response.status = 202
        with cherrypy.request.db_session() as session:
            instance: Instance = session.merge(cherrypy.request.resource_object, load=False)

            if instance.state != InstanceState.ACTIVE:
                raise cherrypy.HTTPError(409,
                                         "Can only restart an instance in the following state: %s" %
                                         InstanceState.ACTIVE.value)

            instance.state = InstanceState.RESTARTING

            create_task(session, instance, restart_instance, instance_id=instance.id, hard=request.hard,
                        timeout=request.timeout)

            session.commit()

    @Route(route='{instance_id}/action/image', methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.model_in(cls=RequestInstanceImage)
    @cherrypy.tools.model_out(cls=ResponseImage)
    @cherrypy.tools.resource_object(id_param="instance_id", cls=Instance)
    @cherrypy.tools.enforce_policy(policy_name="instances:action:image")
    def action_image(self, instance_id: uuid.UUID):
        request: RequestInstanceImage = cherrypy.request.model

        if request.visibility == ImageVisibility.PUBLIC:
            self.mount.enforce_policy("instances:action:image:public")

        with cherrypy.request.db_session() as session:
            instance: Instance = session.merge(cherrypy.request.resource_object, load=False)

            if instance.state != InstanceState.STOPPED:
                raise cherrypy.HTTPError(409, "Can only image an instance in the following state: %s" %
                                         InstanceState.STOPPED.value)

            instance.state = InstanceState.IMAGING

            image = Image()
            image.name = request.name
            image.file_name = str(instance.id)
            image.visibility = request.visibility
            image.project_id = instance.project_id

            session.add(image)
            session.flush()

            # Delete vm without actually deleting the backing
            create_task(session, instance, delete_instance, instance_id=instance.id, delete_backing=False)

            # Convert the vm to a template
            create_task(session, image, convert_vm, image_id=image.id, from_instance=True)

            session.commit()

            return ResponseImage.from_database(image)

    @Route(route='{instance_id}/action/reset_state', methods=[RequestMethods.PUT])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.model_in(cls=RequestInstanceResetState)
    @cherrypy.tools.resource_object(id_param="instance_id", cls=Instance)
    @cherrypy.tools.enforce_policy(policy_name="instances:action:reset_state")
    def action_reset_state(self, instance_id: uuid.UUID):
        cherrypy.response.status = 204
        request: RequestInstanceResetState = cherrypy.request.model
        with cherrypy.request.db_session() as session:
            instance: Instance = session.merge(cherrypy.request.resource_object, load=False)

            task = session.query(Task).filter(Task.id == instance.current_task_id).one()

            if task.stopped_at is None:
                # TODO: how to take care of a task that is broken and will never be stopped?
                raise cherrypy.HTTPError(409, "Current task for the instance has not finished, "
                                              "please wait for it to finish.")

            if request.active:
                self.mount.enforce_policy("instances:action:reset_state:active")
                instance.state = InstanceState.ACTIVE
            else:
                instance.state = InstanceState.ERROR

            session.commit()
