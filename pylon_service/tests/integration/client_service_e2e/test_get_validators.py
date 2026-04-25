import pytest
from pylon_client.artanis import BlockNumber, NetUid, PylonNotFound
from pylon_client.artanis.v1 import GetValidatorsResponse


def test_get_latest_validators(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        response = client.v1.open_access.get_latest_validators(netuid=NetUid(1))

        assert isinstance(response, GetValidatorsResponse)
        assert response.block.number > 0
        assert response.block.hash
        assert len(response.validators) > 1
        assert all(v.validator_permit for v in response.validators)
        totals = [v.stakes.total for v in response.validators]
        assert totals == sorted(totals, reverse=True)


def test_get_validators_nonexistent_block(pylon_client_factory):
    with pylon_client_factory("sn1") as client:
        with pytest.raises(PylonNotFound):
            client.v1.open_access.get_validators(netuid=NetUid(1), block_number=BlockNumber(999_999_999))
