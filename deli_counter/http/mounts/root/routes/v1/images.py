import uuid

import cherrypy
from sqlalchemy import or_

from deli_counter.http.mounts.root.routes.v1.validation_models.images import ParamsImage, RequestCreateImage, \
    ResponseImage, ParamsListImage
from ingredients_db.models.images import Image, ImageVisibility, ImageState
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router
from ingredients_tasks.tasks.image import create_image, delete_image
from ingredients_tasks.tasks.tasks import create_task


class ImageRouter(Router):
    def __init__(self):
        super().__init__(uri_base='images')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateImage)
    @cherrypy.tools.model_out(cls=ResponseImage)
    def create(self):
        request: RequestCreateImage = cherrypy.request.model

        with cherrypy.request.db_session() as session:
            project = self.mount.get_token_project(session)

            image = session.query(Image).filter(Image.project_id == project.id).filter(
                Image.name == request.name).first()

            if image is not None:
                raise cherrypy.HTTPError(409, 'An image already exists with the requested name.')

            image = session.query(Image).filter(Image.project_id == project.id).filter(
                Image.file_name == request.file_name).first()

            if image is not None:
                raise cherrypy.HTTPError(409, 'An image already exists with the requested file name.')

            image = Image()
            image.name = request.name
            image.file_name = request.file_name
            image.visibility = request.visibility
            image.project_id = project.id

            session.add(image)
            session.flush()

            create_task(session, image, create_image, image_id=image.id)

            session.commit()
            session.refresh(image)

        return ResponseImage.from_database(image)

    @Route(route='{image_id}')
    @cherrypy.tools.model_params(cls=ParamsImage)
    @cherrypy.tools.model_out(cls=ResponseImage)
    def inspect(self, image_id):
        with cherrypy.request.db_session() as session:
            project = self.mount.get_token_project(session)
            image = session.query(Image).filter(Image.id == image_id).filter(Image.project_id == project.id).first()

            if image is None:
                raise cherrypy.HTTPError(404, "An image with the requested id does not exist in the scoped project.")

        return ResponseImage.from_database(image)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListImage)
    @cherrypy.tools.model_out_pagination(cls=ResponseImage)
    def list(self, limit: int, marker: uuid.UUID):
        resp_images = []
        with cherrypy.request.db_session() as session:
            project = self.mount.get_token_project(session)

            images = session.query(Image).filter(
                or_(Image.project_id == project.id,
                    Image.visibility == ImageVisibility.PUBLIC,
                    Image.members.any(id=project.id))).order_by(Image.created_at.desc())

            if marker is not None:
                marker = session.query(Image).filter(Image.id == marker).first()
                if marker is None:
                    raise cherrypy.HTTPError(status=400, message="Unknown marker ID")
                images = images.filter(Image.created_at < marker.created_at)

            images = images.limit(limit + 1)

            for image in images:
                resp_images.append(ResponseImage.from_database(image))

        more_pages = False
        if len(resp_images) > limit:
            more_pages = True
            del resp_images[-1]  # Remove the last item to reset back to original limit

        return resp_images, more_pages

    @Route(route='{image_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsImage)
    def delete(self, image_id):
        cherrypy.response.status = 202
        with cherrypy.request.db_session() as session:
            project = self.mount.get_token_project(session)
            image = session.query(Image).filter(Image.id == image_id).filter(
                Image.project_id == project.id).with_for_update().first()

            if image is None:
                raise cherrypy.HTTPError(404, "An image with the requested id does not exist in the scoped project.")

            if image.state not in [ImageState.CREATED, ImageState.ERROR]:
                raise cherrypy.HTTPError(412, "Can only delete an image while it is in the following states: %s" % (
                    [ImageState.CREATED.value, ImageState.ERROR.value]))

            if image.locked:
                raise cherrypy.HTTPError(412, "Cannot delete an image while it is locked.")

            image.state = ImageState.DELETING
            create_task(session, image, delete_image, image_id=image.id)

            session.commit()

            # TODO: add/remove members

    @Route(route='{image_id}/action/lock', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsImage)
    def action_lock(self, image_id):
        cherrypy.response.status = 204
        with cherrypy.request.db_session() as session:
            project = self.mount.get_token_project(session)
            image = session.query(Image).filter(Image.id == image_id).filter(
                Image.project_id == project.id).with_for_update().first()

            if image is None:
                raise cherrypy.HTTPError(404, "An image with the requested id does not exist in the scoped project.")

            if image.locked:
                raise cherrypy.HTTPError(412, "Can only lock unlocked images.")

            image.locked = True
            session.commit()

    @Route(route='{image_id}/action/unlock', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsImage)
    def action_unlock(self, image_id):
        cherrypy.response.status = 204
        with cherrypy.request.db_session() as session:
            project = self.mount.get_token_project(session)
            image = session.query(Image).filter(Image.id == image_id).filter(
                Image.project_id == project.id).with_for_update().first()

            if image is None:
                raise cherrypy.HTTPError(404, "An image with the requested id does not exist in the scoped project.")

            if image.locked is False:
                raise cherrypy.HTTPError(412, "Can only unlock locked images.")

            image.locked = False
            session.commit()
