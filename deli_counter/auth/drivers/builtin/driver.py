from typing import Dict

from deli_counter.auth.driver import AuthDriver
from deli_counter.auth.drivers.builtin.router import DatabaseAuthRouter
from ingredients_http.router import Router


class BuiltInAuthDriver(AuthDriver):
    def __init__(self):
        super().__init__('builtin')

    def discover_options(self) -> Dict:
        return {}

    def auth_router(self) -> Router:
        return DatabaseAuthRouter(self)
