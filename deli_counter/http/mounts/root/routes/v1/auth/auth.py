import cherrypy

from ingredients_http.route import Route
from ingredients_http.router import Router


class AuthRouter(Router):
    def __init__(self):
        super().__init__()
        self.drivers = []

    def setup_routes(self, dispatcher: cherrypy.dispatch.RoutesDispatcher, uri_prefix: str):
        self.drivers = self.mount.auth_drivers

        for driver in self.drivers:
            driver_router: Router = driver.auth_router()
            driver_router.setup_routes(dispatcher, uri_prefix)

        super().setup_routes(dispatcher, uri_prefix)

    @Route(route='discover')
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.json_out()
    def discover(self):
        data = {}

        for driver in self.drivers:
            data[driver.name] = driver.discover_options()

        return data
