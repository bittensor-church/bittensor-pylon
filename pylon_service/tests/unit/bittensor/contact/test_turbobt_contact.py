import pytest
from pylon_commons.types import BittensorNetwork

from pylon_service.bittensor.contact import TurboBtContact


@pytest.mark.asyncio
async def test_turbobt_contact_requires_open_before_use():
    contact = TurboBtContact(wallet=None, uri=BittensorNetwork("mock://test"))

    with pytest.raises(AttributeError, match="not open"):
        await contact.get_latest_block()
