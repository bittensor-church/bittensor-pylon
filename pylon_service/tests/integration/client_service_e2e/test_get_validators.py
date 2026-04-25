import pytest
from pylon_client.artanis import BlockNumber, NetUid, PylonClient, PylonNotFound
from pylon_client.artanis.v1 import GetValidatorsResponse


def test_get_latest_validators(pylon_client: PylonClient):
    response = pylon_client.v1.open_access.get_latest_validators(netuid=NetUid(1))

    assert isinstance(response, GetValidatorsResponse)
    assert response.block.number > 0
    assert response.block.hash
    assert len(response.validators) > 1
    assert all(v.validator_permit for v in response.validators)
    totals = [v.stakes.total for v in response.validators]
    assert totals == sorted(totals, reverse=True)


def test_get_validators_nonexistent_block(pylon_client: PylonClient):
    with pytest.raises(PylonNotFound):
        pylon_client.v1.open_access.get_validators(netuid=NetUid(1), block_number=BlockNumber(999_999_999))
