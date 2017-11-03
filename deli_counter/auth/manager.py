import importlib
import json
import logging

import cherrypy
from oslo_config import cfg
from oslo_policy.policy import Enforcer, RuleDefault, Rules
from simple_settings import settings

from deli_counter.auth.driver import AuthDriver
from ingredients_db.models.authn import AuthNTokenRole, AuthNUser, AuthNToken
from ingredients_db.models.authz import AuthZPolicy, AuthZRole
from ingredients_db.models.project import Project


class AuthManager(object):
    def __init__(self):
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))
        self.enforcer = Enforcer(cfg.CONF, use_conf=False)
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

    def load_policies(self, session, dry=False):

        if dry:
            enforcer = Enforcer(cfg.CONF, use_conf=False)
        else:
            enforcer = self.enforcer
        enforcer.clear()

        rules = {}
        policies = session.query(AuthZPolicy)
        for policy in policies:
            rules[policy.name] = policy.rule
            enforcer.register_default(RuleDefault(policy.name, policy.rule, policy.description))

        enforcer.set_rules(Rules.from_dict(rules), overwrite=True, use_conf=False)
        enforcer.check_rules(raise_on_violation=True)

    def enforce_policy(self, policy_name, session, token: AuthNToken, user: AuthNUser, project: Project,
                       resource_object):
        creds = {
            "roles": [],
            "user_id": str(user.id)
        }

        if project is not None:
            if True:  # TODO: check if member of project before injecting project into creds
                creds['project_id'] = str(project.id)

        target = {}

        # If the resource object is not none set as target
        if resource_object is not None:
            # Copy the __dict__ and remove _sa_instance_state
            resource_dict = resource_object.__dict__.copy()
            resource_dict.pop('_sa_instance_state')

            # Dump to json then load back in to convert all values to str
            target = json.loads(json.dumps(resource_dict))

        # else If project is not None insert project id into target
        elif project is not None:
            target['project_id'] = project.id

        # Find all roles that the token has and add it to the creds
        token_roles = session.query(AuthZRole).join(AuthNTokenRole, AuthZRole.id == AuthNTokenRole.role_id).filter(
            AuthNTokenRole.token_id == token.id)

        for role in token_roles:
            creds['roles'].append(role.name)

        self.enforcer.authorize(policy_name, target, creds, do_raise=True, exc=cherrypy.HTTPError, status=403,
                                message="Insufficient permissions to perform the requested action.")
