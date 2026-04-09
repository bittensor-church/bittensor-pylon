from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

import pytest
from dirty_equals import IsInt, IsStr
from pylon_commons.types import BlockNumber, ExtrinsicIndex

from tests.integration.localchain.dev_accounts import DevAccount

SNAPSHOT_BLOCK = {
    "number": 238,
    "hash": IsStr(regex=r"^0x[0-9a-fA-F]{64}$"),
}

EXPECTED_NEURONS_LIST = [
    {
        "active": True,
        "axon_info": {"ip": "0.0.0.0", "port": 0, "protocol": 0},
        "coldkey": "5C4hrfjw9DjXZTzV3MwzrrAr9P1MJhSrvWGWqi1eSuyUpnhM",
        "consensus": 0.0,
        "dividends": 0.0,
        "emission": 0.0,
        "hotkey": "5C4hrfjw9DjXZTzV3MwzrrAr9P1MJhSrvWGWqi1eSuyUpnhM",
        "incentive": 0.0,
        "last_update": 0,
        "pruning_score": 0,
        "rank": 0.0,
        "stake": 1.0,
        "stakes": {"alpha": 1.0, "tao": 0.0, "total": 1.0},
        "trust": 0.0,
        "uid": 0,
        "validator_permit": True,
        "validator_trust": 0.0,
    },
    {
        "active": True,
        "axon_info": {"ip": "0.0.0.0", "port": 0, "protocol": 0},
        "coldkey": DevAccount.ALICE.coldkey_ss58,
        "consensus": 0.0,
        "dividends": 0.0,
        "emission": 0.0,
        "hotkey": DevAccount.ALICE.hotkey_ss58,
        "incentive": 0.0,
        "last_update": 55,
        "pruning_score": 65535,
        "rank": 0.0,
        "stake": 9.6055762,
        "stakes": {"alpha": 9.6055762, "tao": 0.0, "total": 9.6055762},
        "trust": 0.0,
        "uid": 1,
        "validator_permit": True,
        "validator_trust": 0.0,
    },
    {
        "active": True,
        "axon_info": {"ip": "0.0.0.0", "port": 0, "protocol": 0},
        "coldkey": DevAccount.BOB.coldkey_ss58,
        "consensus": 0.0,
        "dividends": 0.0,
        "emission": 0.0,
        "hotkey": DevAccount.BOB.hotkey_ss58,
        "incentive": 0.0,
        "last_update": 65,
        "pruning_score": 65535,
        "rank": 0.0,
        "stake": 0.00499472,
        "stakes": {"alpha": 0.00499472, "tao": 0.0, "total": 0.00499472},
        "trust": 0.0,
        "uid": 2,
        "validator_permit": True,
        "validator_trust": 0.0,
    },
    {
        "active": True,
        "axon_info": {"ip": "0.0.0.0", "port": 0, "protocol": 0},
        "coldkey": DevAccount.CHARLIE.coldkey_ss58,
        "consensus": 0.0,
        "dividends": 0.0,
        "emission": 0.0,
        "hotkey": DevAccount.CHARLIE.hotkey_ss58,
        "incentive": 0.0,
        "last_update": 74,
        "pruning_score": 65535,
        "rank": 0.0,
        "stake": 0.0,
        "stakes": {"alpha": 0.0, "tao": 0.0, "total": 0.0},
        "trust": 0.0,
        "uid": 3,
        "validator_permit": False,
        "validator_trust": 0.0,
    },
    {
        "active": True,
        "axon_info": {"ip": "0.0.0.0", "port": 0, "protocol": 0},
        "coldkey": DevAccount.DAVE.coldkey_ss58,
        "consensus": 0.0,
        "dividends": 0.0,
        "emission": 0.0,
        "hotkey": DevAccount.DAVE.hotkey_ss58,
        "incentive": 0.0,
        "last_update": 81,
        "pruning_score": 65535,
        "rank": 0.0,
        "stake": 0.0,
        "stakes": {"alpha": 0.0, "tao": 0.0, "total": 0.0},
        "trust": 0.0,
        "uid": 4,
        "validator_permit": False,
        "validator_trust": 0.0,
    },
]

EXPECTED_NEURONS = {
    "block": SNAPSHOT_BLOCK,
    "neurons": {neuron["hotkey"]: neuron for neuron in EXPECTED_NEURONS_LIST},
}

EXPECTED_HYPERPARAMS = {
    "commit_reveal_weights_enabled": "v4",
    "max_weights_limit": 65535,
}

EXPECTED_SUBNET_STATE = {
    "active": [True, True, True, True, True],
    "alpha_stake": [1000000000, 9605576200, 4994720, 0, 0],
    "block_at_registration": [0, 55, 65, 74, 81],
    "coldkeys": [
        "5C4hrfjw9DjXZTzV3MwzrrAr9P1MJhSrvWGWqi1eSuyUpnhM",
        DevAccount.ALICE.coldkey_ss58,
        DevAccount.BOB.coldkey_ss58,
        DevAccount.CHARLIE.coldkey_ss58,
        DevAccount.DAVE.coldkey_ss58,
    ],
    "consensus": [0.0, 0.0, 0.0, 0.0, 0.0],
    "dividends": [0.0, 0.0, 0.0, 0.0, 0.0],
    "emission": [0, 0, 0, 0, 0],
    "emission_history": [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]],
    "hotkeys": [
        "5C4hrfjw9DjXZTzV3MwzrrAr9P1MJhSrvWGWqi1eSuyUpnhM",
        DevAccount.ALICE.hotkey_ss58,
        DevAccount.BOB.hotkey_ss58,
        DevAccount.CHARLIE.hotkey_ss58,
        DevAccount.DAVE.hotkey_ss58,
    ],
    "incentives": [0.0, 0.0, 0.0, 0.0, 0.0],
    "last_update": [0, 55, 65, 74, 81],
    "netuid": 1,
    "pruning_score": [0],
    "rank": [0.0],
    "tao_stake": [0, 0, 0, 0, 0],
    "total_stake": [1000000000, 9605576200, 4994720, 0, 0],
    "trust": [0.0],
    "validator_permit": [True, True, True, False, False],
}

EXPECTED_COMMITMENTS = {
    "block": SNAPSHOT_BLOCK,
    "commitments": {
        DevAccount.CHARLIE.hotkey_ss58: {
            "commitment": "0x636f6d6d69746d656e742d636861726c6965",
            "commitment_block_number": 191,
            "hotkey": DevAccount.CHARLIE.hotkey_ss58,
        },
        DevAccount.DAVE.hotkey_ss58: {
            "commitment": "0x636f6d6d69746d656e742d64617665",
            "commitment_block_number": 198,
            "hotkey": DevAccount.DAVE.hotkey_ss58,
        },
    },
}

EXPECTED_TIMESTAMP_EXTRINSIC = {
    "address": None,
    "block_number": 238,
    "call": {
        "call_args": [{"name": "now", "type": "Moment", "value": IsInt(ge=0)}],
        "call_function": "set",
        "call_hash": IsStr(regex=r"^0x[0-9a-fA-F]{64}$"),
        "call_index": "0x0200",
        "call_module": "Timestamp",
    },
    "extrinsic_hash": IsStr(regex=r"^0x[0-9a-fA-F]{64}$"),
    "extrinsic_index": 0,
    "extrinsic_length": 10,
}

EXPECTED_MEV_SHIELD_EXTRINSIC = {
    "address": None,
    "block_number": 238,
    "call": {
        "call_args": [
            {
                "name": "enc_key",
                "type": "Option<ShieldEncKey>",
                "value": IsStr(regex=r"^0x[0-9a-fA-F]+$"),
            }
        ],
        "call_function": "announce_next_key",
        "call_hash": IsStr(regex=r"^0x[0-9a-fA-F]{64}$"),
        "call_index": "0x1e00",
        "call_module": "MevShield",
    },
    "extrinsic_hash": IsStr(regex=r"^0x[0-9a-fA-F]{64}$"),
    "extrinsic_index": 1,
    "extrinsic_length": 1190,
}


def dump_model(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {key: dump_model(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [dump_model(item) for item in value]
    return value


async def get_snapshot_block(open_contact):
    block = await open_contact.get_block(BlockNumber(SNAPSHOT_BLOCK["number"]))
    assert block is not None
    return block


@pytest.mark.asyncio
async def test_get_block_returns_prepared_snapshot_block(open_contact):
    block = await get_snapshot_block(open_contact)

    assert SNAPSHOT_BLOCK == dump_model(block)


@pytest.mark.asyncio
async def test_get_latest_block_returns_a_resolvable_block(open_contact):
    latest_block = await open_contact.get_latest_block()
    resolved_block = await open_contact.get_block(latest_block.number)

    assert latest_block.number >= SNAPSHOT_BLOCK["number"]
    assert dump_model(resolved_block) == dump_model(latest_block)


@pytest.mark.asyncio
async def test_get_block_timestamp_matches_timestamp_extrinsic(open_contact):
    block = await get_snapshot_block(open_contact)

    timestamp = await open_contact.get_block_timestamp(block)
    timestamp_extrinsic = await open_contact.get_extrinsic(block, ExtrinsicIndex(0))

    assert timestamp_extrinsic is not None
    extrinsic_dump = cast(dict[str, Any], dump_model(timestamp_extrinsic))
    call_dump = cast(dict[str, Any], extrinsic_dump["call"])
    call_args = cast(list[dict[str, Any]], call_dump["call_args"])
    timestamp_millis = call_args[0]["value"]

    assert isinstance(timestamp_millis, int)
    assert timestamp_millis // 1000 == timestamp


@pytest.mark.asyncio
async def test_get_neurons_list_returns_full_prepared_snapshot(open_contact, prepared_netuid):
    block = await get_snapshot_block(open_contact)
    neurons = await open_contact.get_neurons_list(prepared_netuid, block)

    assert dump_model(neurons) == EXPECTED_NEURONS_LIST


@pytest.mark.asyncio
async def test_get_neurons_returns_full_snapshot_mapping(open_contact, prepared_netuid):
    block = await get_snapshot_block(open_contact)
    neurons = await open_contact.get_neurons(prepared_netuid, block)

    assert EXPECTED_NEURONS == dump_model(neurons)


@pytest.mark.asyncio
async def test_get_hyperparams_returns_prepared_snapshot(open_contact, prepared_netuid):
    block = await get_snapshot_block(open_contact)
    hyperparams = await open_contact.get_hyperparams(prepared_netuid, block)

    assert dump_model(hyperparams) == EXPECTED_HYPERPARAMS


@pytest.mark.asyncio
async def test_get_subnet_state_returns_prepared_snapshot(open_contact, prepared_netuid):
    block = await get_snapshot_block(open_contact)
    state = await open_contact.get_subnet_state(prepared_netuid, block)

    assert dump_model(state) == EXPECTED_SUBNET_STATE


@pytest.mark.asyncio
async def test_get_commitment_and_commitments_return_prepared_snapshot(open_contact, prepared_netuid):
    block = await get_snapshot_block(open_contact)

    commitment = await open_contact.get_commitment(prepared_netuid, block, DevAccount.CHARLIE.hotkey_ss58)
    commitments = await open_contact.get_commitments(prepared_netuid, block)

    assert EXPECTED_COMMITMENTS["commitments"][DevAccount.CHARLIE.hotkey_ss58] == dump_model(commitment)
    assert EXPECTED_COMMITMENTS == dump_model(commitments)


@pytest.mark.asyncio
async def test_get_certificates_and_certificate_return_prepared_snapshot(open_contact, prepared_netuid):
    block = await get_snapshot_block(open_contact)

    certificates = await open_contact.get_certificates(prepared_netuid, block)
    certificate = await open_contact.get_certificate(prepared_netuid, block, DevAccount.ALICE.hotkey_ss58)

    assert dump_model(certificates) == {}
    assert certificate is None


@pytest.mark.asyncio
async def test_get_signed_block_returns_snapshot_block(open_contact):
    block = await get_snapshot_block(open_contact)
    signed_block = await open_contact.get_signed_block(block)

    assert signed_block is not None
    assert signed_block["block"]["header"]["number"] == SNAPSHOT_BLOCK["number"]
    assert len(signed_block["block"]["extrinsics"]) == 2


@pytest.mark.asyncio
async def test_get_extrinsic_returns_expected_snapshot_extrinsics(open_contact):
    block = await get_snapshot_block(open_contact)

    timestamp_extrinsic = await open_contact.get_extrinsic(block, ExtrinsicIndex(0))
    mev_shield_extrinsic = await open_contact.get_extrinsic(block, ExtrinsicIndex(1))
    missing_extrinsic = await open_contact.get_extrinsic(block, ExtrinsicIndex(2))

    assert EXPECTED_TIMESTAMP_EXTRINSIC == dump_model(timestamp_extrinsic)
    assert EXPECTED_MEV_SHIELD_EXTRINSIC == dump_model(mev_shield_extrinsic)
    assert missing_extrinsic is None
