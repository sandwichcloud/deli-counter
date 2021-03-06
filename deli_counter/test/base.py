import ipaddress
import json

import arrow
import webtest
from cryptography.fernet import Fernet
from faker import Faker

from deli_counter.http.app import Application
from deli_counter.http.mounts.root.mount import RootMount
from ingredients_db.models.authn import AuthNUser, AuthNServiceAccount
from ingredients_db.models.authz import AuthZPolicy, AuthZRole, AuthZRolePolicy
from ingredients_db.models.images import Image, ImageVisibility, ImageState
from ingredients_db.models.instance import Instance, InstanceState
from ingredients_db.models.network import Network, NetworkState
from ingredients_db.models.network_port import NetworkPort
from ingredients_db.models.project import Project, ProjectState
from ingredients_db.models.region import Region, RegionState
from ingredients_db.models.zones import Zone, ZoneState
from ingredients_http.test.base import APITestCase

fake = Faker()


class DeliTestCase(APITestCase):
    def settings_module(self) -> str:
        return 'deli_counter.test.settings.all'

    def app_cls(self):
        return Application

    def setup_mounts(self, app):
        app.register_mount(RootMount(app))

    def create_authn_user(self, app, username=None, driver='db') -> AuthNUser:
        with app.database.session() as session:
            user = AuthNUser()
            user.username = fake.pystr(min_chars=3) if username is None else username
            user.driver = driver

            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

        return user

    def create_token(self, app, roles=None, authn_user=None, project=None):
        if roles is None:
            roles = []
        if authn_user is None:
            authn_user = self.create_authn_user(app)

        with app.database.session() as session:
            global_role_ids = []
            for role_name in roles:
                role = session.query(AuthZRole).filter(AuthZRole.name == role_name).filter(
                    AuthZRole.project_id == None).first()  # noqa: E711
                if role is not None:
                    global_role_ids.append(role.id)

            from simple_settings import settings
            fernet = Fernet(settings.AUTH_FERNET_KEYS[0])

            token_data = {
                'expires_at': arrow.now().shift(days=+1),
                'user_id': authn_user.id,
                'roles': {
                    'global': global_role_ids,
                    'project': []
                }
            }

            if project is not None:
                token_data['project_id'] = project.id
                project_member_role = session.query(AuthZRole).filter(AuthZRole.name == "default_member").filter(
                    AuthZRole.project_id == project.id).first()
                token_data['roles']['project'] = [str(project_member_role.id)]

            return fernet.encrypt(json.dumps(token_data).encode()).decode()

    def create_policy(self, app, rule, name=None) -> AuthZPolicy:
        with app.database.session() as session:
            policy = AuthZPolicy()
            policy.name = fake.pystr(min_chars=3) if name is None else name
            policy.rule = rule

            session.add(policy)
            session.commit()
            session.refresh(policy)
            session.expunge(policy)

        return policy

    def create_role(self, app, name=None) -> AuthZRole:
        with app.database.session() as session:
            role = AuthZRole()
            role.name = fake.pystr(min_chars=3) if name is None else name

            session.add(role)
            session.commit()
            session.refresh(role)
            session.expunge(role)

        return role

    def create_project(self, app, name=None) -> Project:
        with app.database.session() as session:
            project = Project()
            project.name = fake.pystr(min_chars=3) if name is None else name
            project.state = ProjectState.CREATED

            session.add(project)
            session.flush()
            session.refresh(project)

            # Create the default member role
            member_role = AuthZRole()
            member_role.name = "default_member"
            member_role.description = "Default role for project members"
            member_role.project_id = project.id
            session.add(member_role)
            session.flush()
            session.refresh(member_role)
            member_policies = session.query(AuthZPolicy).filter(AuthZPolicy.tags.any("project_member"))
            for policy in member_policies:
                mr_policy = AuthZRolePolicy()
                mr_policy.role_id = member_role.id
                mr_policy.policy_id = policy.id
                session.add(mr_policy)

            # Create the default service account role
            sa_role = AuthZRole()
            sa_role.name = "default_service_account"
            sa_role.description = "Default role for project service accounts"
            sa_role.project_id = project.id
            session.add(sa_role)
            session.flush()
            session.refresh(sa_role)
            sa_policies = session.query(AuthZPolicy).filter(AuthZPolicy.tags.any("service_account"))
            for policy in sa_policies:
                sa_policy = AuthZRolePolicy()
                sa_policy.role_id = sa_role.id
                sa_policy.policy_id = policy.id
                session.add(sa_policy)

            # Create the default service account
            sa = AuthNServiceAccount()
            sa.name = "default"
            sa.project_id = project.id
            sa.role_id = sa_role.id
            session.add(sa)

            session.commit()
            session.refresh(project)
            session.expunge(project)

        return project

    def create_region(self, app, name=None) -> Region:
        with app.database.session() as session:
            region = Region()
            region.name = fake.pystr(min_chars=3) if name is None else name
            region.datacenter = fake.pystr(min_chars=3)
            region.image_datastore = fake.pystr(min_chars=3)
            region.schedulable = True
            region.image_folder = None
            region.state = RegionState.CREATED

            session.add(region)
            session.commit()
            session.refresh(region)
            session.expunge(region)

        return region

    def create_zone(self, app, region=None, name=None) -> Zone:
        if region is None:
            region = self.create_region(app)

        with app.database.session() as session:
            zone = Zone()
            zone.name = fake.pystr(min_chars=3) if name is None else name
            zone.region_id = region.id
            zone.vm_cluster = fake.pystr(min_chars=3)
            zone.vm_datastore = fake.pystr(min_chars=3)
            zone.core_provision_percent = 100
            zone.ram_provision_percent = 100
            zone.schedulable = True
            zone.vm_folder = None
            zone.state = ZoneState.CREATED

            session.add(zone)
            session.commit()
            session.refresh(zone)
            session.expunge(zone)

        return zone

    def create_network(self, app, name=None, region=None, port_group=None) -> Network:
        if region is None:
            region = self.create_region(app)

        with app.database.session() as session:
            network = Network()
            network.name = fake.pystr(min_chars=3) if name is None else name
            network.region_id = region.id
            network.port_group = fake.pystr(min_chars=3) if port_group is None else port_group

            # TODO: may need ability to specify these ips
            network.cidr = ipaddress.IPv4Network("192.168.1.0/24")
            network.gateway = ipaddress.IPv4Address("192.168.1.1")
            network.dns_servers = [ipaddress.IPv4Address("8.8.8.8"), ipaddress.IPv4Address("8.8.4.4")]
            network.pool_start = ipaddress.IPv4Address("192.168.1.1")
            network.pool_end = ipaddress.IPv4Address("192.168.1.254")
            network.state = NetworkState.CREATED

            session.add(network)
            session.commit()
            session.refresh(network)
            session.expunge(network)

        return network

    def create_image(self, app, project=None, region=None, name=None, file_name=None,
                     visibility=ImageVisibility.PRIVATE) -> Image:
        if project is None:
            project = self.create_project(app)
        if region is None:
            region = self.create_region(app)

        with app.database.session() as session:
            image = Image()
            image.name = fake.pystr(min_chars=3) if name is None else name
            image.project_id = project.id
            image.region_id = region.id
            image.visibility = visibility
            image.file_name = fake.pystr(min_chars=3) if file_name is None else file_name
            image.state = ImageState.CREATED

            session.add(image)
            session.commit()
            session.refresh(image)
            session.expunge(image)

        return image

    def create_instance(self, app, project=None, region=None, zone=None, image=None, network=None,
                        name=None) -> Instance:
        if project is None:
            project = self.create_project(app)
        if region is None:
            region = self.create_region(app)
        if zone is None:
            zone = self.create_zone(app, region=region)
        if network is None:
            network = self.create_network(app, region=region)
        if image is None:
            image = self.create_image(app, project=project, region=region)

        with app.database.session() as session:

            network_port = NetworkPort()
            network_port.network_id = network.id
            network_port.project_id = project.id
            network_port.ip_address = network.next_free_address(session)

            session.add(network_port)
            session.flush()

            instance = Instance()
            instance.name = fake.pystr(min_chars=3) if name is None else name
            instance.region_id = region.id
            instance.zone_id = zone.id
            instance.project_id = project.id
            instance.image_id = image.id
            instance.tags = {}  # TODO: allow specifying tags
            instance.network_port_id = network_port.id

            instance.state = InstanceState.ACTIVE

            service_account = session.query(AuthNServiceAccount).filter(
                AuthNServiceAccount.project_id == project.id).filter(
                AuthNServiceAccount.name == "default").first()

            instance.service_account_id = service_account.id

            session.add(instance)
            session.commit()
            session.refresh(instance)
            session.expunge(instance)

        return instance

    def get(self, wsgi: webtest.TestApp, uri, token=None, headers=None, **kwargs):
        if headers is None:
            headers = {}
        if token is not None:
            headers['Authorization'] = 'Bearer ' + token

        return wsgi.get(url=uri, headers=headers, **kwargs)

    def post(self, wsgi: webtest.TestApp, uri, body, token=None, headers=None, **kwargs):
        if headers is None:
            headers = {}
        if token is not None:
            headers['Authorization'] = 'Bearer ' + token

        return wsgi.post_json(url=uri, headers=headers, params=body, **kwargs)

    def put(self, wsgi: webtest.TestApp, uri, body, token=None, headers=None, **kwargs):
        if headers is None:
            headers = {}
        if token is not None:
            headers['Authorization'] = 'Bearer ' + token

        return wsgi.put_json(url=uri, headers=headers, params=body, **kwargs)

    def delete(self, wsgi: webtest.TestApp, uri, token=None, headers=None, **kwargs):
        if headers is None:
            headers = {}
        if token is not None:
            headers['Authorization'] = 'Bearer ' + token

        return wsgi.delete(url=uri, headers=headers, **kwargs)
