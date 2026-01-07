from ipaddress import IPv4Address, IPv6Address

import pytest

from pylon_client._internal.common.models import AxonInfo, AxonProtocol
from pylon_client._internal.common.types import Port


@pytest.mark.parametrize(
    ("ip", "expected"),
    [
        pytest.param(IPv4Address("0.0.0.0"), False, id="ipv4_zero"),
        pytest.param(IPv4Address("192.168.1.1"), True, id="ipv4_serving"),
        pytest.param(IPv6Address("::"), False, id="ipv6_zero"),
        pytest.param(IPv6Address("2001:db8::1"), True, id="ipv6_serving"),
    ],
)
def test_axon_info_is_serving(ip: IPv4Address | IPv6Address, expected: bool):
    axon_info = AxonInfo(ip=ip, port=Port(8080), protocol=AxonProtocol.HTTP)

    assert axon_info.is_serving is expected
