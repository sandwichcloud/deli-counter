from clify.app import Application
from pbr.version import VersionInfo

from ingredients_http.conf.loader import SETTINGS


class DeliApplication(Application):
    def __init__(self):
        super().__init__('deli_counter', 'CLI for Deli Counter')

    @property
    def version(self):
        return VersionInfo('deli-counter').semantic_version().release_string()

    def logging_config(self, log_level: int) -> dict:
        return SETTINGS.LOGGING_CONFIG
