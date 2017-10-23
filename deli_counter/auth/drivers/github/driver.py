from typing import Dict

from simple_settings import settings

from deli_counter.auth.driver import AuthDriver
from deli_counter.auth.drivers.github.router import GithubAuthRouter


class GithubAuthDriver(AuthDriver):
    def __init__(self):
        super().__init__('github')

    def auth_router(self) -> GithubAuthRouter:
        return GithubAuthRouter(self)

    def discover_options(self) -> Dict:
        return {}

    def check_in_org(self, github_user) -> bool:
        for org in github_user.get_orgs():
            if org.login == settings.GITHUB_ORG:
                return True

        return False

    def has_role(self, username, role) -> bool:
        return True
