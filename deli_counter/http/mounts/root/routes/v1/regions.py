import cherrypy
from sqlalchemy.orm import Query

from deli_counter.http.mounts.root.routes.v1.validation_models.regions import ResponseRegion, RequestCreateRegion, \
    ParamsRegion, ParamsListRegion, RequestRegionSchedule
from ingredients_db.models.region import Region, RegionState
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router
from ingredients_tasks.tasks.region import create_region
from ingredients_tasks.tasks.tasks import create_task


class RegionsRouter(Router):
    def __init__(self):
        super().__init__(uri_base='regions')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateRegion)
    @cherrypy.tools.model_out(cls=ResponseRegion)
    @cherrypy.tools.enforce_policy(policy_name="regions:create")
    def create(self):
        request: RequestCreateRegion = cherrypy.request.model

        with cherrypy.request.db_session() as session:
            region = session.query(Region).filter(Region.name == request.name).first()

            if region is not None:
                raise cherrypy.HTTPError(409, 'A region with the requested name already exists.')

            region = Region()
            region.name = request.name
            region.datacenter = request.datacenter
            region.image_datastore = request.image_datastore
            region.schedulable = False

            if request.image_folder is not None:
                region.image_folder = request.image_folder

            session.add(region)
            session.flush()

            create_task(session, region, create_region, region_id=region.id)

            session.commit()
            session.refresh(region)

        return ResponseRegion.from_database(region)

    @Route(route='{region_id}')
    @cherrypy.tools.model_params(cls=ParamsRegion)
    @cherrypy.tools.model_out(cls=ResponseRegion)
    @cherrypy.tools.resource_object(id_param="region_id", cls=Region)
    @cherrypy.tools.enforce_policy(policy_name="regions:get")
    def get(self, region_id):
        return ResponseRegion.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListRegion)
    @cherrypy.tools.model_out_pagination(cls=ResponseRegion)
    @cherrypy.tools.enforce_policy(policy_name="regions:list")
    def list(self, name, limit, marker):
        starting_query = None
        if name is not None:
            starting_query = Query(Region).filter(Region.name == name)
        return self.paginate(Region, ResponseRegion, limit, marker, starting_query=starting_query)

    @Route(route='{region_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsRegion)
    @cherrypy.tools.resource_object(id_param="region_id", cls=Region)
    @cherrypy.tools.enforce_policy(policy_name="regions:delete")
    def delete(self, region_id):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']

        with cherrypy.request.db_session() as session:
            region: Region = session.merge(cherrypy.request.resource_object, load=False)

            if region.state not in [RegionState.CREATED, RegionState.ERROR]:
                raise cherrypy.HTTPError(409, "Can only delete a region in the following states: %s" % [
                    RegionState.CREATED.value, RegionState.ERROR.value])

            # TODO: check things in region are deleted

            region.state = RegionState.DELETED
            session.delete(region)
            session.commit()

    @Route(route='{region_id}/action/schedule', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsRegion)
    @cherrypy.tools.model_in(cls=RequestRegionSchedule)
    @cherrypy.tools.resource_object(id_param="region_id", cls=Region)
    @cherrypy.tools.enforce_policy(policy_name="regions:action:schedule")
    def action_schedule(self, region_id):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']

        request: RequestRegionSchedule = cherrypy.request.model

        with cherrypy.request.db_session() as session:
            region: Region = session.merge(cherrypy.request.resource_object, load=False)

            if region.state != RegionState.CREATED:
                raise cherrypy.HTTPError(409,
                                         "Can only set schedulable on a region in the following state: %s" %
                                         RegionState.CREATED.value)

            region.schedulable = request.schedulable
            session.commit()
