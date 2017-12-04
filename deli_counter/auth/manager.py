import importlib
import logging

import cherrypy
from simple_settings import settings

from deli_counter.auth.driver import AuthDriver
from ingredients_db.models.authz import AuthZPolicy, AuthZRolePolicy
from ingredients_db.models.project import Project


class AuthManager(object):
    def __init__(self):
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))
        self.drivers = {}

    def load_drivers(self):
        for driver_string in settings.AUTH_DRIVERS:
            if ':' not in driver_string:
                raise ValueError("AUTH_DRIVER does not contain a module and class. "
                                 "Must be in the following format: 'my.module:MyClass'")

            auth_module, auth_class, *_ = driver_string.split(":")
            try:
                auth_module = importlib.import_module(auth_module)
            except ImportError:
                self.logger.exception("Could not import auth driver's module: " + auth_module)
                raise
            try:
                driver_klass = getattr(auth_module, auth_class)
            except AttributeError:
                self.logger.exception("Could not get driver's module class: " + auth_class)
                raise

            if not issubclass(driver_klass, AuthDriver):
                raise ValueError("AUTH_DRIVER class is not a subclass of '" + AuthDriver.__module__ + ".AuthDriver'")

            driver: AuthDriver = driver_klass()
            self.drivers[driver.name] = driver

        if len(self.drivers) == 0:
            raise ValueError("No auth drivers loaded")

    def enforce_policy(self, policy_name, session, token: dict, project: Project):

        policy_query = session.query(AuthZPolicy). \
            join(AuthZRolePolicy, AuthZPolicy.id == AuthZRolePolicy.policy_id).filter(AuthZPolicy.name == policy_name)

        role_ids = token['roles']['global']
        if project is not None:
            role_ids = token['roles']['project'] + role_ids

        for role_id in role_ids:
            policy = policy_query.filter(AuthZRolePolicy.role_id == role_id).first()
            if policy is not None:
                return

        raise cherrypy.HTTPError(403, "Insufficient permissions to perform the requested action.")
