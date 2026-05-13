from pact import match

from tests.pact.constants import (
    BLOCK_HASH,
    BLOCK_NUMBER,
    BLOCK_TIMESTAMP,
    COLDKEY,
    COMMITMENT_HEX,
    EVM_CONTRACT_ADDRESS,
    EVM_FROM_BLOCK,
    EVM_TO_BLOCK,
    EVM_TRANSACTION_HASH,
    EXTRINSIC_HASH,
    EXTRINSIC_INDEX,
    NETUID,
    NETUID_2,
    PRICE_VALUE_RAO,
    PRICE_VALUE_RAO_2,
    PUBLIC_KEY,
)


def block_matcher() -> dict:
    return {
        "number": match.int(BLOCK_NUMBER),
        "hash": match.str(BLOCK_HASH),
    }


def neuron_matcher(hotkey: str, uid: int) -> dict:
    return {
        "uid": match.int(uid),
        "coldkey": match.str(COLDKEY),
        "hotkey": match.str(hotkey),
        "active": match.bool(True),
        "axon_info": {
            "ip": match.str("192.168.1.100"),
            "port": match.int(9999),
            "protocol": match.int(4),
        },
        "stake": match.number(1.1),
        "rank": match.number(2.2),
        "emission": match.number(3.3),
        "incentive": match.number(4.4),
        "consensus": match.number(5.5),
        "trust": match.number(6.6),
        "validator_trust": match.number(7.7),
        "dividends": match.number(8.8),
        "last_update": match.int(1001),
        "validator_permit": match.bool(True),
        "pruning_score": match.int(99),
        "stakes": {
            "alpha": match.number(100.1),
            "tao": match.number(200.2),
            "total": match.number(300.3),
        },
    }


def neurons_response_matcher(hotkey_1: str, hotkey_2: str) -> dict:
    return {
        "block": block_matcher(),
        "neurons": match.each_value_matches(
            match.each_key_matches(  # type: ignore[reportArgumentType]
                {
                    hotkey_1: neuron_matcher(hotkey_1, uid=1),
                    hotkey_2: neuron_matcher(hotkey_2, uid=2),
                },
                rules=match.str(hotkey_1),
            ),
            rules=match.like(neuron_matcher(hotkey_1, uid=1)),
        ),
    }


def validators_response_matcher(hotkey_1: str, hotkey_2: str) -> dict:
    return {
        "block": block_matcher(),
        "validators": match.each_like(neuron_matcher(hotkey_1, uid=1)),
    }


def commitment_response_matcher(hotkey: str) -> dict:
    return {
        "block": block_matcher(),
        "commitment": {
            "commitment_block_number": match.int(BLOCK_NUMBER),
            "hotkey": match.str(hotkey),
            "commitment": match.str(COMMITMENT_HEX),
            "kind": "hex_data",
        },
    }


def v1_commitments_response_matcher(hotkey_1: str, hotkey_2: str) -> dict:
    return {
        "block": block_matcher(),
        "commitments": match.each_value_matches(
            match.each_key_matches(  # type: ignore[reportArgumentType]
                {
                    hotkey_1: match.str(COMMITMENT_HEX),
                    hotkey_2: match.str(COMMITMENT_HEX),
                },
                rules=match.str(hotkey_1),
            ),
            rules=match.str(COMMITMENT_HEX),
        ),
    }


def commitments_response_matcher(hotkey_1: str, hotkey_2: str) -> dict:
    commitment_matcher = {
        "commitment_block_number": match.int(BLOCK_NUMBER),
        "hotkey": match.str(hotkey_1),
        "commitment": match.str(COMMITMENT_HEX),
        "kind": "hex_data",
    }
    return {
        "block": block_matcher(),
        "commitments": match.each_value_matches(
            match.each_key_matches(  # type: ignore[reportArgumentType]
                {
                    hotkey_1: {
                        "commitment_block_number": match.int(BLOCK_NUMBER),
                        "hotkey": match.str(hotkey_1),
                        "commitment": match.str(COMMITMENT_HEX),
                        "kind": "hex_data",
                    },
                    hotkey_2: {
                        "commitment_block_number": match.int(BLOCK_NUMBER),
                        "hotkey": match.str(hotkey_2),
                        "commitment": match.str(COMMITMENT_HEX),
                        "kind": "hex_data",
                    },
                },
                rules=match.str(hotkey_1),
            ),
            rules=match.like(commitment_matcher),
        ),
    }


def extrinsic_response_matcher() -> dict:
    return {
        "block_number": match.int(BLOCK_NUMBER),
        "extrinsic_index": match.int(EXTRINSIC_INDEX),
        "extrinsic_hash": match.str(EXTRINSIC_HASH),
        "extrinsic_length": match.int(100),
        "address": match.str(COLDKEY),
        "call": {
            "call_module": match.str("SubtensorModule"),
            "call_function": match.str("set_weights"),
            "call_args": match.each_like(
                {
                    "name": match.str("netuid"),
                    "type": match.str("u16"),
                    # Value can actually be of any type.
                    "value": "",
                }
            ),
        },
    }


def set_weights_response_matcher() -> dict:
    return {}


def set_commitment_response_matcher() -> dict:
    return {}


def set_revealed_commitment_response_matcher() -> dict:
    return {
        "reveal_round": match.int(123456),
    }


def revealed_commitment_matcher(hotkey: str) -> dict:
    return {
        "reveal_block_number": match.int(BLOCK_NUMBER),
        "hotkey": match.str(hotkey),
        "commitment": match.str(COMMITMENT_HEX),
    }


def revealed_commitments_response_matcher(hotkey_1: str, hotkey_2: str) -> dict:
    return {
        "block": block_matcher(),
        "commitments": match.each_value_matches(
            match.each_key_matches(  # type: ignore[reportArgumentType]
                {
                    hotkey_1: match.each_like(revealed_commitment_matcher(hotkey_1)),
                    hotkey_2: match.each_like(revealed_commitment_matcher(hotkey_2)),
                },
                rules=match.str(hotkey_1),
            ),
            rules=match.each_like(revealed_commitment_matcher(hotkey_1)),
        ),
    }


def all_revealed_commitments_response_matcher(hotkey_1: str, hotkey_2: str) -> dict:
    return revealed_commitments_response_matcher(hotkey_1, hotkey_2)


def single_revealed_commitment_response_matcher(hotkey: str) -> dict:
    return {
        "block": block_matcher(),
        "commitments": match.each_like(revealed_commitment_matcher(hotkey)),
    }


def latest_block_info_response_matcher() -> dict:
    return {
        **block_matcher(),
        "timestamp": match.int(BLOCK_TIMESTAMP),
    }


def certificate_response_matcher() -> dict:
    return {
        "algorithm": match.int(1),
        "public_key": match.str(PUBLIC_KEY),
    }


def get_weights_status_response_matcher() -> dict:
    return {
        "weights_submitted": match.bool(False),
    }


def prices_response_matcher() -> dict:
    return {
        "block": block_matcher(),
        "prices": match.each_value_matches(
            match.each_key_matches(  # type: ignore[reportArgumentType]
                {
                    str(NETUID): {"value": match.int(PRICE_VALUE_RAO)},
                    str(NETUID_2): {"value": match.int(PRICE_VALUE_RAO_2)},
                },
                rules=match.str(str(NETUID)),
            ),
            rules=match.like({"value": match.int(PRICE_VALUE_RAO)}),
        ),
    }


def price_response_matcher() -> dict:
    return {
        "block": block_matcher(),
        "netuid": match.int(NETUID),
        "price": {"value": match.int(PRICE_VALUE_RAO)},
    }


def evm_log_matcher() -> dict:
    return {
        "event": match.str("Transfer"),
        "args": match.like({"from": "0xaaaa", "to": "0xbbbb", "value": 1000}),
        "address": match.str(EVM_CONTRACT_ADDRESS),
        "block_number": match.int(BLOCK_NUMBER),
        "transaction_hash": match.str(EVM_TRANSACTION_HASH),
        "transaction_index": match.int(0),
        "log_index": match.int(0),
    }


def evm_logs_response_matcher() -> dict:
    return {
        "logs": match.each_like(evm_log_matcher()),
        "from_block": match.int(EVM_FROM_BLOCK),
        "to_block": match.int(EVM_TO_BLOCK),
    }


def evm_empty_logs_response_matcher() -> dict:
    return {
        "logs": [],
        "from_block": match.int(EVM_FROM_BLOCK),
        "to_block": match.int(EVM_TO_BLOCK),
    }


def evm_associations_response_matcher(hotkey_1: str, hotkey_2: str) -> dict:
    association_matcher = {
        "hotkey": match.str(hotkey_1),
        "evm_address": match.str("0x" + "c" * 40),
        "last_block_where_ownership_was_proven": match.int(BLOCK_NUMBER),
    }
    return {
        "block": block_matcher(),
        "evm_associations": match.each_value_matches(
            match.each_key_matches(  # type: ignore[reportArgumentType]
                {
                    hotkey_1: {
                        "hotkey": match.str(hotkey_1),
                        "evm_address": match.str("0x" + "c" * 40),
                        "last_block_where_ownership_was_proven": match.int(BLOCK_NUMBER),
                    },
                    hotkey_2: {
                        "hotkey": match.str(hotkey_2),
                        "evm_address": match.str("0x" + "c" * 40),
                        "last_block_where_ownership_was_proven": match.int(BLOCK_NUMBER),
                    },
                },
                rules=match.str(hotkey_1),
            ),
            rules=match.like(association_matcher),
        ),
    }
