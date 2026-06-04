from __future__ import annotations

from typing import Any

import pytest_asyncio
from eth_typing import HexStr
from pylon_commons.types import evm as evm_types
from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider
from web3.types import TxParams

from pylon_service.evm.contact import EvmContact
from tests.integration.containers import AnvilContainer

# Pre-compiled bytecode for a minimal Transfer event emitter.
#
# Solidity equivalent:
#   event Transfer(address indexed from, address indexed to, uint256 value);
#   function emitTransfer(address from, address to, uint256 value) external {
#       emit Transfer(from, to, value);
#   }
#
# The runtime bytecode reads 3 ABI-encoded args from calldata (offset 4, 36, 68)
# and emits a Transfer LOG3 with the standard ERC-20 topic layout.
_DEPLOYER_BYTECODE = (
    "6034600c60003960346000f3"  # constructor: copy runtime to mem and return it
    "600435602435604435600052"  # CALLDATALOAD(4,36,68); MSTORE value at mem[0]
    "907fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"  # SWAP1; PUSH32 Transfer sig
    "60206000a300"  # PUSH1 0x20; PUSH1 0x00; LOG3; STOP
)

_EMIT_TRANSFER_ABI: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "emitTransfer",
        "inputs": [
            {"name": "from_", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    }
]

TRANSFER_EVENT_ABI: list[dict[str, Any]] = [
    {
        "type": "event",
        "name": "Transfer",
        "anonymous": False,
        "inputs": [
            {"name": "from", "type": "address", "indexed": True},
            {"name": "to", "type": "address", "indexed": True},
            {"name": "value", "type": "uint256", "indexed": False},
        ],
    }
]


@pytest_asyncio.fixture(scope="module")
async def anvil():
    """
    Start a local Anvil EVM node and yield it for the test module.
    """
    with AnvilContainer() as container:
        yield container


@pytest_asyncio.fixture(scope="module")
async def evm_contact(anvil: AnvilContainer):
    """
    Open an EvmContact connected to the Anvil node.
    """
    async with EvmContact(evm_types.RpcUrl(anvil.http_url)) as contact:
        yield contact


@pytest_asyncio.fixture(scope="module")
async def deployed_contract(anvil: AnvilContainer) -> str:
    """
    Deploy the minimal Transfer event emitter contract and return its address.
    """
    provider = AsyncHTTPProvider(anvil.http_url)
    w3 = AsyncWeb3(provider)
    accounts = await w3.eth.accounts
    deployer = accounts[0]
    tx: TxParams = {"from": deployer, "data": HexStr("0x" + _DEPLOYER_BYTECODE), "gas": 200_000}
    tx_hash = await w3.eth.send_transaction(tx)
    receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)
    assert receipt["contractAddress"] is not None
    return receipt["contractAddress"]


@pytest_asyncio.fixture(scope="module")
async def transfer_log_block(anvil: AnvilContainer, deployed_contract: str) -> int:
    """
    Emit one Transfer event and return the block number it landed in.
    """
    provider = AsyncHTTPProvider(anvil.http_url)
    w3 = AsyncWeb3(provider)
    accounts = list(await w3.eth.accounts)
    caller = accounts[0]
    from_ = accounts[1]
    to = accounts[2]
    value = 1000

    contract = w3.eth.contract(address=AsyncWeb3.to_checksum_address(deployed_contract), abi=_EMIT_TRANSFER_ABI)
    tx_hash = await contract.functions.emitTransfer(from_, to, value).transact({"from": caller})
    receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt["blockNumber"]
