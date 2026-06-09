from __future__ import annotations

import pytest
from pylon_commons.types import evm as evm_types

from pylon_service.evm.contact import EvmContact
from pylon_service.evm.exceptions import EvmInvalidAddressError
from tests.integration.evm.conftest import TRANSFER_EVENT_ABI

# Well-known Ethereum burn address — no private key exists, guaranteed to have no contract or events.
_BURN_ADDRESS = evm_types.Address("0x000000000000000000000000000000000000dEaD")


@pytest.mark.asyncio
async def test_evm_contact_get_current_block_returns_block_number(evm_contact: EvmContact):
    """
    Test that get_current_block returns a non-negative integer.
    """
    block = await evm_contact.get_current_block()

    assert isinstance(block, int)
    assert block >= 0


@pytest.mark.asyncio
async def test_evm_contact_get_logs_returns_empty_for_address_with_no_events(evm_contact: EvmContact):
    """
    Test that get_logs returns an empty list when no matching events exist.
    """
    current = await evm_contact.get_current_block()
    logs = await evm_contact.get_logs(
        address=_BURN_ADDRESS,
        from_block=evm_types.BlockNumber(0),
        to_block=current,
        abi=TRANSFER_EVENT_ABI,
    )

    assert logs == []


@pytest.mark.asyncio
async def test_evm_contact_get_logs_returns_decoded_transfer_event(
    evm_contact: EvmContact, deployed_contract: str, transfer_log_block: int
):
    """
    Test that get_logs returns a correctly decoded Transfer event.
    """
    logs = await evm_contact.get_logs(
        address=evm_types.Address(deployed_contract),
        from_block=evm_types.BlockNumber(transfer_log_block),
        to_block=evm_types.BlockNumber(transfer_log_block),
        abi=TRANSFER_EVENT_ABI,
    )

    assert len(logs) == 1
    log = logs[0]
    assert log.event == "Transfer"
    assert log.block_number == transfer_log_block
    assert log.address == deployed_contract
    assert "from" in log.args
    assert "to" in log.args
    assert log.args["value"] == 1000


@pytest.mark.asyncio
async def test_evm_contact_get_logs_raises_invalid_address_error(evm_contact: EvmContact):
    """
    Test that get_logs raises EvmInvalidAddressError for a malformed contract address.
    """
    with pytest.raises(EvmInvalidAddressError):
        await evm_contact.get_logs(
            address=evm_types.Address("not_a_valid_address"),
            from_block=evm_types.BlockNumber(0),
            to_block=evm_types.BlockNumber(1),
            abi=TRANSFER_EVENT_ABI,
        )


@pytest.mark.asyncio
async def test_evm_contact_get_logs_returns_empty_for_non_event_abi(
    evm_contact: EvmContact, deployed_contract: str, transfer_log_block: int
):
    """
    Test that get_logs returns an empty list when the ABI contains no event entries.
    Logs are still fetched from the node but none match the (empty) event lookup.
    """
    logs = await evm_contact.get_logs(
        address=evm_types.Address(deployed_contract),
        from_block=evm_types.BlockNumber(transfer_log_block),
        to_block=evm_types.BlockNumber(transfer_log_block),
        abi=[{"type": "function", "name": "foo", "inputs": [], "outputs": []}],
    )

    assert logs == []
