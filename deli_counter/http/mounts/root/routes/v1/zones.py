import cherrypy
from sqlalchemy.orm import Query

from deli_counter.http.mounts.root.routes.v1.validation_models.zones import RequestCreateZone, ResponseZone, \
    ParamsZone, ParamsListZone, RequestZoneSchedule
from ingredients_db.models.region import Region, RegionState
from ingredients_db.models.zones import Zone, ZoneState
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from ingredients_http.router import Router
from ingredients_tasks.tasks.tasks import create_task
from ingredients_tasks.tasks.zone import create_zone


class ZoneRouter(Router):
    def __init__(self):
        super().__init__(uri_base='zones')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateZone)
    @cherrypy.tools.model_out(cls=ResponseZone)
    @cherrypy.tools.enforce_policy(policy_name="zones:create")
    def create(self):
        request: RequestCreateZone = cherrypy.request.model

        with cherrypy.request.db_session() as session:
            zone = session.query(Zone).filter(Zone.name == request.name).first()
            if zone is not None:
                raise cherrypy.HTTPError(409, 'A zone with the requested name already exists.')

            region = session.query(Region).filter(Region.id == request.region_id).first()
            if region is None:
                raise cherrypy.HTTPError(404, "A region with the requested id does not exist.")

            if region.state != RegionState.CREATED:
                raise cherrypy.HTTPError(412,
                                         "The requested region is not in the following state: %s" %
                                         RegionState.CREATED.value)

            zone = Zone()
            zone.name = request.name
            zone.region_id = region.id
            zone.vm_cluster = request.vm_cluster
            zone.vm_datastore = request.vm_datastore
            zone.core_provision_percent = request.core_provision_percent
            zone.ram_provision_percent = request.ram_provision_percent
            zone.schedulable = False

            if request.vm_folder is not None:
                zone.vm_folder = request.vm_folder

            session.add(zone)
            session.flush()

            create_task(session, zone, create_zone, zone_id=zone.id)

            session.commit()
            session.refresh(zone)

        return ResponseZone.from_database(zone)

    @Route(route='{zone_id}')
    @cherrypy.tools.model_params(cls=ParamsZone)
    @cherrypy.tools.model_out(cls=ResponseZone)
    @cherrypy.tools.resource_object(id_param="zone_id", cls=Zone)
    @cherrypy.tools.enforce_policy(policy_name="zones:get")
    def get(self, zone_id):
        return ResponseZone.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListZone)
    @cherrypy.tools.model_out_pagination(cls=ResponseZone)
    @cherrypy.tools.enforce_policy(policy_name="zones:list")
    def list(self, region_id, limit, marker):
        starting_query = Query(Zone)
        if region_id is not None:
            with cherrypy.request.db_session() as session:
                region = session.query(Region).filter(Region.id == region_id).first()
                if region is None:
                    raise cherrypy.HTTPError(404, "A region with the requested id does not exist.")
            starting_query = starting_query.filter(Zone.region_id == region.id)
        return self.paginate(Zone, ResponseZone, limit, marker, starting_query=starting_query)

    @Route(route='{zone_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsZone)
    @cherrypy.tools.resource_object(id_param="zone_id", cls=Zone)
    @cherrypy.tools.enforce_policy(policy_name="zones:delete")
    def delete(self, zone_id):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']

        with cherrypy.request.db_session() as session:
            zone: Zone = session.merge(cherrypy.request.resource_object, load=False)

            if zone.state not in [ZoneState.CREATED, ZoneState.ERROR]:
                raise cherrypy.HTTPError(409, "Can only delete a zone in the following states: %s" % [
                    ZoneState.CREATED.value, ZoneState.ERROR.value])

            # TODO: check things in zone are deleted

            zone.state = ZoneState.DELETED
            session.delete(zone)
            session.commit()

    @Route(route='{zone_id}/action/schedule', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsZone)
    @cherrypy.tools.model_in(cls=RequestZoneSchedule)
    @cherrypy.tools.resource_object(id_param="zone_id", cls=Zone)
    @cherrypy.tools.enforce_policy(policy_name="zones:action:schedule")
    def action_schedule(self, zone_id):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']

        request: RequestZoneSchedule = cherrypy.request.model

        with cherrypy.request.db_session() as session:
            zone: Zone = session.merge(cherrypy.request.resource_object, load=False)

            if zone.state != ZoneState.CREATED:
                raise cherrypy.HTTPError(409,
                                         "Can only set schedulable on a zone in the following state: %s" %
                                         ZoneState.CREATED.value)

            zone.schedulable = request.schedulable
            session.commit()
