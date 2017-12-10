import uuid

import cherrypy
from sqlalchemy import or_
from sqlalchemy.orm import Query

from deli_counter.http.mounts.root.routes.v1.validation_models.images import ParamsImage, RequestCreateImage, \
    ResponseImage, ParamsListImage
from ingredients_db.models.images import Image, ImageVisibility, ImageState
from ingredients_db.models.region import Region, RegionState
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router
from ingredients_tasks.tasks.image import create_image, delete_image
from ingredients_tasks.tasks.tasks import create_task


class ImageRouter(Router):
    def __init__(self):
        super().__init__(uri_base='images')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_in(cls=RequestCreateImage)
    @cherrypy.tools.model_out(cls=ResponseImage)
    @cherrypy.tools.enforce_policy(policy_name="images:create")
    def create(self):
        request: RequestCreateImage = cherrypy.request.model

        if request.visibility == ImageVisibility.PUBLIC:
            self.mount.enforce_policy("images:create:public")

        with cherrypy.request.db_session() as session:
            project = cherrypy.request.project

            region = session.query(Region).filter(Region.id == request.region_id).first()
            if region is None:
                raise cherrypy.HTTPError(404, "A region with the requested id does not exist.")

            if region.state != RegionState.CREATED:
                raise cherrypy.HTTPError(412,
                                         "The requested region is not in the following state: %s" %
                                         RegionState.CREATED.value)

            image = session.query(Image).filter(Image.project_id == project.id).filter(
                Image.name == request.name).filter(Image.region_id == region.id).first()

            if image is not None:
                raise cherrypy.HTTPError(409, 'An image with the requested name already exists.')

            image = session.query(Image).filter(Image.project_id == project.id).filter(
                Image.file_name == request.file_name).first()

            if image is not None:
                raise cherrypy.HTTPError(409, 'An image with the requested file already exists.')

            image = Image()
            image.name = request.name
            image.file_name = request.file_name
            image.visibility = request.visibility
            image.project_id = project.id
            image.region_id = region.id

            session.add(image)
            session.flush()

            create_task(session, image, create_image, image_id=image.id)

            session.commit()
            session.refresh(image)

        return ResponseImage.from_database(image)

    @Route(route='{image_id}')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsImage)
    @cherrypy.tools.model_out(cls=ResponseImage)
    @cherrypy.tools.resource_object(id_param="image_id", cls=Image)
    @cherrypy.tools.enforce_policy(policy_name="images:get")
    def get(self, image_id):
        return ResponseImage.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListImage)
    @cherrypy.tools.model_out_pagination(cls=ResponseImage)
    @cherrypy.tools.enforce_policy(policy_name="images:list")
    def list(self, region_id, limit: int, marker: uuid.UUID):
        project = cherrypy.request.project
        starting_query = Query(Image).filter(
            or_(Image.project_id == project.id,
                Image.visibility == ImageVisibility.PUBLIC,
                Image.members.any(id=project.id)))
        if region_id is not None:
            with cherrypy.request.db_session() as session:
                region = session.query(Region).filter(Region.id == region_id).first()
                if region is None:
                    raise cherrypy.HTTPError(404, "A region with the requested id does not exist.")
            starting_query = starting_query.filter(Image.region_id == region.id)
        return self.paginate(Image, ResponseImage, limit, marker, starting_query=starting_query)

    @Route(route='{image_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsImage)
    @cherrypy.tools.resource_object(id_param="image_id", cls=Image)
    @cherrypy.tools.enforce_policy(policy_name="images:delete")
    def delete(self, image_id):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']
        with cherrypy.request.db_session() as session:
            image: Image = session.merge(cherrypy.request.resource_object, load=False)

            if image.state not in [ImageState.CREATED, ImageState.ERROR]:
                raise cherrypy.HTTPError(409, "Can only delete an image while it is in the following states: %s" % (
                    [ImageState.CREATED.value, ImageState.ERROR.value]))

            if image.locked:
                raise cherrypy.HTTPError(409, "Cannot delete an image while it is locked.")

            image.state = ImageState.DELETING
            # TODO: do we allow not deleting image backing?
            create_task(session, image, delete_image, image_id=image.id, delete_backing=True)

            session.commit()

    @Route(route='{image_id}/action/lock', methods=[RequestMethods.PUT])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsImage)
    @cherrypy.tools.resource_object(id_param="image_id", cls=Image)
    @cherrypy.tools.enforce_policy(policy_name="images:action:lock")
    def action_lock(self, image_id):
        cherrypy.response.status = 204
        with cherrypy.request.db_session() as session:
            image: Image = session.merge(cherrypy.request.resource_object, load=False)

            if image.locked:
                raise cherrypy.HTTPError(409, "Can only lock unlocked images.")

            image.locked = True
            session.commit()

    @Route(route='{image_id}/action/unlock', methods=[RequestMethods.PUT])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsImage)
    @cherrypy.tools.resource_object(id_param="image_id", cls=Image)
    @cherrypy.tools.enforce_policy(policy_name="images:action:unlock")
    def action_unlock(self, image_id):
        cherrypy.response.status = 204
        with cherrypy.request.db_session() as session:
            image: Image = session.merge(cherrypy.request.resource_object, load=False)

            if image.locked is False:
                raise cherrypy.HTTPError(409, "Can only unlock locked images.")

            image.locked = False
            session.commit()

            # TODO: add/remove members
