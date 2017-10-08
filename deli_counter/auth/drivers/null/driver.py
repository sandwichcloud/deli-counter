from typing import Dict

from deli_counter.auth.driver import AuthDriver


class NullAuthDriver(AuthDriver):
    def __init__(self):
        super().__init__('null')

    def discover_options(self) -> Dict:
        return {}

    def auth_router(self) -> None:
        return None
