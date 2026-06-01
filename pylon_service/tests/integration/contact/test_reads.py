from __future__ import annotations

import pytest
from dirty_equals import IsInt, IsStr
from pylon_commons.models import CommitmentKind
from pylon_commons.types import ExtrinsicIndex

from tests.integration.localchain.dev_accounts import DevAccount
from tests.integration.localchain.dev_evm_wallets import DevEvmWallet
from tests.matchers import HASH_REGEX, SNAPSHOT_BLOCK, dict_model_dump

EXPECTED_TIMESTAMP_EXTRINSIC = {
    "address": None,
    "block_number": IsInt(ge=0),
    "call": {
        "call_args": [{"name": "now", "type": "Moment", "value": IsInt(ge=0)}],
        "call_function": "set",
        "call_hash": IsStr(regex=HASH_REGEX),
        "call_index": "0x0200",
        "call_module": "Timestamp",
    },
    "extrinsic_hash": IsStr(regex=HASH_REGEX),
    "extrinsic_index": 0,
    "extrinsic_length": 10,
}

EXPECTED_MEV_SHIELD_EXTRINSIC = {
    "address": None,
    "block_number": IsInt(ge=0),
    "call": {
        "call_args": [
            {
                "name": "enc_key",
                "type": "Option<ShieldEncKey>",
                "value": IsStr(regex=r"^0x[0-9a-fA-F]+$"),
            }
        ],
        "call_function": "announce_next_key",
        "call_hash": IsStr(regex=HASH_REGEX),
        "call_index": "0x1e00",
        "call_module": "MevShield",
    },
    "extrinsic_hash": IsStr(regex=HASH_REGEX),
    "extrinsic_index": 1,
    "extrinsic_length": 1190,
}

EXPECTED_COMMITMENTS = {
    "block": SNAPSHOT_BLOCK,
    "commitments": {
        DevAccount.BOB.hotkey_ss58: {
            "commitment": "0x636f6d6d69746d656e742d626f62",
            "commitment_block_number": IsInt(ge=0),
            "hotkey": DevAccount.BOB.hotkey_ss58,
            "kind": CommitmentKind.HEX_DATA,
        },
        DevAccount.DAVE.hotkey_ss58: {
            "commitment": "0x636f6d6d69746d656e742d64617665",
            "commitment_block_number": IsInt(ge=0),
            "hotkey": DevAccount.DAVE.hotkey_ss58,
            "kind": CommitmentKind.HEX_DATA,
        },
    },
}

EXPECTED_REVEALED_COMMITMENTS = {
    "block": SNAPSHOT_BLOCK,
    "commitments": {
        DevAccount.ALICE.hotkey_ss58: [
            {
                "commitment": "revealed-commitment-alice",
                "reveal_block_number": IsInt(ge=0),
                "hotkey": DevAccount.ALICE.hotkey_ss58,
            }
        ],
        DevAccount.CHARLIE.hotkey_ss58: [
            {
                "commitment": "revealed-commitment-charlie",
                "reveal_block_number": IsInt(ge=0),
                "hotkey": DevAccount.CHARLIE.hotkey_ss58,
            }
        ],
    },
}

EXPECTED_EVM_ASSOCIATIONS = {
    0: {
        "evm_address": DevEvmWallet.ALICE.evm_address,
        "last_block_where_ownership_was_proven": IsInt(ge=0),
    },
    2: {
        "evm_address": DevEvmWallet.CHARLIE.evm_address,
        "last_block_where_ownership_was_proven": IsInt(ge=0),
    },
}


@pytest.mark.asyncio
async def test_get_block_returns_block(open_contact):
    latest_block = await open_contact.get_latest_block()
    block_number = latest_block.number - 10
    block = await open_contact.get_block(block_number)

    assert block.model_dump() == {"number": block_number, "hash": IsStr(regex=HASH_REGEX)}


@pytest.mark.asyncio
async def test_get_latest_block_returns_a_resolvable_block(open_contact):
    latest_block = await open_contact.get_latest_block()
    resolved_block = await open_contact.get_block(latest_block.number)

    assert resolved_block.model_dump() == latest_block.model_dump()


@pytest.mark.asyncio
async def test_get_block_timestamp_matches_timestamp_extrinsic(open_contact):
    latest_block = await open_contact.get_latest_block()

    timestamp = await open_contact.get_block_timestamp(latest_block)
    timestamp_extrinsic = await open_contact.get_extrinsic(latest_block, ExtrinsicIndex(0))

    assert timestamp_extrinsic is not None

    timestamp_millis = timestamp_extrinsic.call.call_args[0].value
    assert isinstance(timestamp_millis, int)
    assert timestamp_millis // 1000 == timestamp


@pytest.mark.asyncio
async def test_get_neurons_list_returns_prepared_neurons(open_contact, prepared_netuid, snapshot):
    latest_block = await open_contact.get_latest_block()
    neurons = await open_contact.get_neurons_list(prepared_netuid, latest_block)

    assert type(neurons) is list
    assert [
        neuron.model_dump(include={"active", "coldkey", "hotkey", "validator_permit"}) for neuron in neurons
    ] == snapshot


@pytest.mark.asyncio
async def test_get_neurons_returns_full_prepared_neurons(open_contact, prepared_netuid, snapshot):
    latest_block = await open_contact.get_latest_block()
    neurons = await open_contact.get_neurons(prepared_netuid, latest_block)

    assert neurons is not None
    assert neurons.block.model_dump() == SNAPSHOT_BLOCK
    assert (
        neurons.model_dump(include={"neurons": {"__all__": {"active", "coldkey", "hotkey", "validator_permit"}}})
        == snapshot
    )


@pytest.mark.asyncio
async def test_get_hyperparams_returns_prepared_hyperparams(open_contact, prepared_netuid, snapshot):
    latest_block = await open_contact.get_latest_block()
    hyperparams = await open_contact.get_hyperparams(prepared_netuid, latest_block)

    assert hyperparams is not None
    assert hyperparams.model_dump() == snapshot


@pytest.mark.asyncio
async def test_get_subnet_state_returns_prepared_state(open_contact, prepared_netuid, snapshot):
    latest_block = await open_contact.get_latest_block()
    state = await open_contact.get_subnet_state(prepared_netuid, latest_block)

    assert state is not None
    assert state.model_dump(include={"active", "coldkeys", "hotkeys", "netuid", "validator_permit"}) == snapshot


# get_commitment is covered in tests_writes.py
@pytest.mark.asyncio
async def test_get_commitments_return_prepared_commitments(open_contact, prepared_netuid):
    latest_block = await open_contact.get_latest_block()
    commitments = await open_contact.get_commitments(prepared_netuid, latest_block)

    assert commitments is not None
    assert commitments.model_dump() == EXPECTED_COMMITMENTS


# get_revealed_commitments is covered in tests_writes.py
@pytest.mark.asyncio
async def test_get_revealed_commitments_return_prepared_revelaed_commitments(open_contact, prepared_netuid):
    latest_block = await open_contact.get_latest_block()
    commitments = await open_contact.get_all_revealed_commitments(prepared_netuid, latest_block)

    assert commitments.model_dump() == EXPECTED_REVEALED_COMMITMENTS


@pytest.mark.asyncio
async def test_get_certificates_and_certificate_return_no_certificates(open_contact, prepared_netuid):
    latest_block = await open_contact.get_latest_block()

    certificates = await open_contact.get_certificates(prepared_netuid, latest_block)
    certificate = await open_contact.get_certificate(prepared_netuid, latest_block, DevAccount.ALICE.hotkey_ss58)

    assert certificates == dict()
    assert certificate is None


@pytest.mark.asyncio
async def test_get_extrinsic_returns_expected_snapshot_extrinsics(open_contact):
    latest_block = await open_contact.get_latest_block()

    timestamp_extrinsic = await open_contact.get_extrinsic(latest_block, ExtrinsicIndex(0))
    mev_shield_extrinsic = await open_contact.get_extrinsic(latest_block, ExtrinsicIndex(1))
    missing_extrinsic = await open_contact.get_extrinsic(latest_block, ExtrinsicIndex(9999))

    assert timestamp_extrinsic.model_dump() == EXPECTED_TIMESTAMP_EXTRINSIC
    assert mev_shield_extrinsic.model_dump() == EXPECTED_MEV_SHIELD_EXTRINSIC
    assert missing_extrinsic is None


@pytest.mark.asyncio
async def test_get_drand_last_stored_round_returns_round(open_contact):
    latest_block = await open_contact.get_latest_block()
    drand_last_stored_round = await open_contact.get_drand_last_stored_round(latest_block)
    assert drand_last_stored_round == IsInt(ge=0)


@pytest.mark.asyncio
async def test_get_evm_key_associations_returns_data(open_contact, prepared_netuid):
    associations = await open_contact.get_evm_key_associations(prepared_netuid)
    assert associations is not None
    assert dict_model_dump(associations) == EXPECTED_EVM_ASSOCIATIONS


@pytest.mark.asyncio
async def test_get_evm_key_associations_returns_empty_map(open_contact):
    associations = await open_contact.get_evm_key_associations(3)
    assert associations is not None
    assert associations == dict()
