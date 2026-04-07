from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest
from pylon_commons.types import BlockNumber, ExtrinsicIndex

from tests.integration.localchain.dev_accounts import DevAccount

SNAPSHOT_BLOCK = {
    "number": 238,
    "hash": "0x70494790e450cc89f92001d32da9ecab781761b066b5393f942689bb4d188889",
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
        "call_args": [{"name": "now", "type": "Moment", "value": 1775571311250}],
        "call_function": "set",
        "call_hash": "0xa2f737782c4f63ae1772e6385ebdf522cb47d1afc092970a12834a9f5d5a1ebf",
        "call_index": "0x0200",
        "call_module": "Timestamp",
    },
    "extrinsic_hash": "0xfaa40da551ee3b2ce1bee1d4ee6cc9384e5501dfb51b81105b864fcbd07b9ffa",
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
                "value": "0xe6c0a00b5c2e56e0b7fb6b4895859059a48fa5c754744454b845b230f34783f58f008da3ac76c134dc9262d5840e9052624093a483391836a86ca58b038c8d62629e0db1261b88aebc328b45a275538babfe2ca8c31bbd9866a3d9a314b87a030c15b799617ac4b1236be77d7a7027cbd1cd9e1cb515da12d1c660564c27e50a3c90769abe210273f00907e1aaea0b372a3c8fba77126fd29e4d6004afcccdcc9cbaca154778006ab134ce8cd349b5915e6f38c880207ffc499fd81c37f58c99d5f49ce75c27567a58f653636b2720b50c7df5e8723a949adc783faea6a416e05521449a27fa6c3efa5b0a527b386b2b9e15036fc4ad02ca634e8b770a8950e9ecb013a0b88c416c8eaa1cb4b755139c50664908cc5541b9e722a757034237008fd91ea92b36605bac97c7865fb42b0ea592b10a7f871068ec45a063492cc7d99bb5acac5eaa79ad79c291cc05607667c26c1b33d4a23663054d941f7391b6b43c7deb40b6211445d4f76d8b1aaeb8684cfe1ab27d140c18568bed3a025d520e97175b8019a243046082b389fa3bbd336b12d54980ca4c4a1de87b6cb0877f66c9176b230344152db4426dd73648467ea8d90fd0b3be0a87ae92a6159654548dccb0e0f7bace7498b1229879828ecafbb2c0d5cc873a85746c2a64e63cbf742161f01365f396a955060b8cb1d25b2549c698b18736f98aa3b93753dc9b45fb403f4cd6a4cc3a5319924d131386d3e607de667159d5a75992b218569fd29482a2c2a0046bb7577454bb905d7b28575ba3a3c456af54325d7b677d592105220aab2d309b4f07cd41c20ee0cb9ab1609f922065818bce96333136025c01662580279b580a29ebe83fd8648a7236503fa3ac465c2c9087932394b9d0fa88310429fe68c9921342650175c8abb967830eb3484cfcd7a07b4abc4d35c36b949357a51525120444121f8f898886454849105a249a2cbc5062f53cc358219f2be152145202583974d3b9084f5a41729c182d4494d2f6be62aa138337a6c2549014707f89fbc67de51bec03c7723c031ae43ae52c8f3f1626790b2116d4af8196a1183094effc9ded5900ed34782d23a88a7c4aaffa0e30abbd45bb32184aa5977538db9c486caa7a09cb0b988c434bc563b425a02ec35b678a701f0627dda47c7a4698643c2f95da82098726b75561f8f67f1ec50f5f6236b88366c62773a472a03768376df0305aea1257e892b4f7767f4262f9cb9d02948b77d4b7b439573840083f39c3aeb17a1c7777828167a534218e17432dfc7708419fdf377b9a06962646a42afa6587d98fecf121c302313888488725416b92c5c3105fb46b1cab2b95c8606217fa9834d92fb097733a2b04e7a4c2e68073096705fd812ecf4425d2d56b835a038416459977a388ca433420660f2a3c9bd7b9447cbdc6e68d0ddbc584d3cd542c7a2799afdc2c6fd6b4bf7b445ffaa7404db316faf44828640f6c5abcc01c05290b5b106b3cf57b9cba81c7ceaa74f9ba6e89e4cdaed309a4d63a6d3a5c3996446aa813afe121d2cc89e8060c3578c065d09a3fda38ae409852f805e7485e1e66a079d11ca30c2d2d7853c509ccaf9c643eb4ae18926043791e846a58fbd147bb3dc967b0d38ef370d0b139a29a3633c8a0d27af8546c8afa54c512ee5290e7",
            }
        ],
        "call_function": "announce_next_key",
        "call_hash": "0x74166f237e358a34c79e95e84449b37101fbed7991f3297e9a1ac952d506fdd3",
        "call_index": "0x1e00",
        "call_module": "MevShield",
    },
    "extrinsic_hash": "0xd95c7dacc2662c3e20b4360d842cfcf70582bf52be7ed257978266fad4bf723b",
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

    assert dump_model(block) == SNAPSHOT_BLOCK


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
    assert dump_model(timestamp_extrinsic)["call"]["call_args"][0]["value"] // 1000 == timestamp


@pytest.mark.asyncio
async def test_get_neurons_list_returns_full_prepared_snapshot(open_contact, prepared_netuid):
    block = await get_snapshot_block(open_contact)
    neurons = await open_contact.get_neurons_list(prepared_netuid, block)

    assert dump_model(neurons) == EXPECTED_NEURONS_LIST


@pytest.mark.asyncio
async def test_get_neurons_returns_full_snapshot_mapping(open_contact, prepared_netuid):
    block = await get_snapshot_block(open_contact)
    neurons = await open_contact.get_neurons(prepared_netuid, block)

    assert dump_model(neurons) == EXPECTED_NEURONS


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

    assert dump_model(commitment) == EXPECTED_COMMITMENTS["commitments"][DevAccount.CHARLIE.hotkey_ss58]
    assert dump_model(commitments) == EXPECTED_COMMITMENTS


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

    assert dump_model(timestamp_extrinsic) == EXPECTED_TIMESTAMP_EXTRINSIC
    assert dump_model(mev_shield_extrinsic) == EXPECTED_MEV_SHIELD_EXTRINSIC
    assert missing_extrinsic is None
