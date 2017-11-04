import ipaddress  # noqa: F401

from schematics import Model
from schematics.exceptions import ValidationError
from schematics.types import UUIDType, IntType, StringType, ListType

from ingredients_db.models.network import Network, NetworkState
from ingredients_http.schematics.types import IPv4NetworkType, IPv4AddressType, EnumType, ArrowType


class RequestCreateNetwork(Model):
    name = StringType(required=True, min_length=3)
    port_group = StringType(required=True)
    cidr = IPv4NetworkType(required=True)
    gateway = IPv4AddressType(required=True)
    dns_servers = ListType(IPv4AddressType, min_size=1, required=True)
    pool_start = IPv4AddressType(required=True)
    pool_end = IPv4AddressType(required=True)

    def validate_gateway(self, data, value):
        cidr: ipaddress.IPv4Network = data['cidr']

        if value not in cidr:
            raise ValidationError('gateway is not an address within ' + str(cidr))

        return value

    def validate_pool_start(self, data, value):
        cidr: ipaddress.IPv4Network = data['cidr']

        if value not in cidr:
            raise ValidationError('pool_start is not an address within ' + str(cidr))

        return value

    def validate_pool_end(self, data, value):
        cidr: ipaddress.IPv4Network = data['cidr']

        if value not in cidr:
            raise ValidationError('pool_end is not an address within ' + str(cidr))

        if value < self.pool_start:
            raise ValidationError('pool_end needs to be larger than pool_start')

        return value


class ResponseNetwork(Model):
    id = UUIDType(required=True)
    name = StringType(required=True, min_length=3)
    port_group = StringType(required=True)
    cidr = IPv4NetworkType(required=True)
    gateway = IPv4AddressType(required=True)
    dns_servers = ListType(IPv4AddressType, min_size=1, required=True)
    pool_start = IPv4AddressType(required=True)
    pool_end = IPv4AddressType(required=True)
    state = EnumType(NetworkState, required=True)
    current_task_id = UUIDType()
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    # Do we need the custom validations? This isn't user input so maybe not?

    @classmethod
    def from_database(cls, network: Network):
        network_model = cls()
        network_model.id = network.id
        network_model.name = network.name

        network_model.port_group = network.port_group
        network_model.cidr = network.cidr
        network_model.gateway = network.gateway
        network_model.dns_servers = network.dns_servers
        network_model.pool_start = network.pool_start
        network_model.pool_end = network.pool_end

        network_model.state = network.state
        network_model.current_task_id = network.current_task_id

        network_model.created_at = network.created_at
        network_model.updated_at = network.updated_at

        return network_model


class ParamsNetwork(Model):
    network_id = UUIDType(required=True)


class ParamsListNetwork(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()
