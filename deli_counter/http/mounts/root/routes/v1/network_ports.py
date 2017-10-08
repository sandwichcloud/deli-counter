from ingredients_http.router import Router


class NetworkPortRouter(Router):
    def __init__(self):
        super().__init__(uri_base='network_ports')

        # TODO: do this
