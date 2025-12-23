import pytest

from pylon_client._internal.common.types import CommitmentDataBytes


@pytest.fixture
def subnet_spec(subnet_spec):
    subnet_spec.commitments.set.return_value = None
    return subnet_spec


@pytest.mark.asyncio
async def test_turbobt_client_set_commitment(turbobt_client, subnet_spec):
    """
    Test that set_commitment sets commitment data on chain.
    """
    commitment_data = CommitmentDataBytes(b"\xde\xad\xbe\xef")
    await turbobt_client.set_commitment(netuid=1, data=commitment_data)
    subnet_spec.commitments.set.assert_called_once_with(commitment_data)
