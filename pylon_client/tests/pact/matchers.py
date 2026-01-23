from pact import match

from tests.pact.constants import BLOCK_HASH, BLOCK_NUMBER, COLDKEY, COMMITMENT_HEX, EXTRINSIC_HASH, EXTRINSIC_INDEX


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
        "hotkey": match.str(hotkey),
        "commitment": match.str(COMMITMENT_HEX),
    }


def commitments_response_matcher(hotkey_1: str, hotkey_2: str) -> dict:
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
