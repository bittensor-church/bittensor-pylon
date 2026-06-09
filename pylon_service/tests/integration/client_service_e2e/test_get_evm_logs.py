from eth_typing import HexStr
from pylon_commons.types import evm as evm_types
from web3 import Web3

from tests.integration.evm.conftest import _DEPLOYER_BYTECODE, _EMIT_TRANSFER_ABI, TRANSFER_EVENT_ABI

_BURN_ADDRESS = evm_types.Address("0x000000000000000000000000000000000000dEaD")


def test_get_evm_logs_open_access_returns_empty_for_address_with_no_events(pylon_client_factory, anvil):
    with pylon_client_factory("sn1") as client:
        response = client.unstable.open_access.get_evm_logs(
            contract_address=_BURN_ADDRESS,
            from_block=evm_types.BlockNumber(0),
            to_block=evm_types.BlockNumber(0),
            abi=TRANSFER_EVENT_ABI,
        )

    assert response is not None
    assert response.logs == []
    assert response.from_block == 0
    assert response.to_block == 0


def test_get_evm_logs_open_access_returns_decoded_transfer_event(pylon_client_factory, anvil):
    w3 = Web3(Web3.HTTPProvider(anvil.http_url))
    accounts = list(w3.eth.accounts)

    # Deploy the Transfer event emitter contract.
    tx_hash = w3.eth.send_transaction({"from": accounts[0], "data": HexStr("0x" + _DEPLOYER_BYTECODE), "gas": 200_000})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = receipt["contractAddress"]
    assert contract_address is not None

    # Emit one Transfer event.
    contract = w3.eth.contract(address=contract_address, abi=_EMIT_TRANSFER_ABI)
    tx_hash = contract.functions.emitTransfer(accounts[1], accounts[2], 1000).transact({"from": accounts[0]})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    log_block = receipt["blockNumber"]

    with pylon_client_factory("sn1") as client:
        response = client.unstable.open_access.get_evm_logs(
            contract_address=evm_types.Address(contract_address),
            from_block=evm_types.BlockNumber(log_block),
            to_block=evm_types.BlockNumber(log_block),
            abi=TRANSFER_EVENT_ABI,
        )

    assert response is not None
    assert len(response.logs) == 1
    log = response.logs[0]
    assert log.event == "Transfer"
    assert log.block_number == log_block
    assert log.address.lower() == contract_address.lower()
    assert log.args["value"] == 1000
