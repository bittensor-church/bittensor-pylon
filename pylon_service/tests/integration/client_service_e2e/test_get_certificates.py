import pytest

pytestmark = pytest.mark.skip(reason="PylonClient does not expose certificate read methods yet")


def test_get_certificates_when_none_exist(pylon_client):
    pass


def test_get_certificate_for_nonexistent_hotkey(pylon_client):
    pass
