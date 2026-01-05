"""
Mock Bittensor client for testing API endpoints.

This module provides a mock implementation of AbstractBittensorClient that can be configured
to return specific values or raise exceptions, enabling comprehensive testing of API endpoints
without requiring actual blockchain interactions.
"""

from contextlib import asynccontextmanager
from typing import Any

from pylon_client._internal.common.models import (
    Block,
    CertificateAlgorithm,
    Commitment,
    Neuron,
    NeuronCertificate,
    NeuronCertificateKeypair,
    SubnetCommitments,
    SubnetHyperparams,
    SubnetNeurons,
    SubnetState,
    SubnetValidators,
)
from pylon_client._internal.common.types import (
    BittensorNetwork,
    BlockNumber,
    CommitmentDataBytes,
    Hotkey,
    NetUid,
    RevealRound,
    Timestamp,
    Weight,
)
from pylon_client.service.bittensor.client import AbstractBittensorClient
from tests.behave import Behave, Behavior


class MockBittensorClient(AbstractBittensorClient):
    """
    Mock implementation of AbstractBittensorClient for testing.

    This client uses the Behave to configure method behaviors and track calls.
    Each method maintains a queue of behaviors that are consumed in order.

    Example usage:
        mock_client = MockBittensorClient()
        async with mock_client.mock_behavior(
            get_certificates=[
                {"5FHneW46...": NeuronCertificate(...)},
                {"5GHneW47...": NeuronCertificate(...)},
            ],
            get_latest_block=[Block(number=100, hash=BlockHash("0x123"))]
        ):
            # First call returns first item, second call returns second item, etc.
            result1 = await mock_client.get_certificates(1)
            result2 = await mock_client.get_certificates(1)
    """

    def __init__(
        self,
        wallet: Any | None = None,
        uri: BittensorNetwork = BittensorNetwork("mock://test"),
    ):
        super().__init__(wallet=wallet, uri=uri)
        self._behave = Behave()
        self._is_open = False

    async def open(self) -> None:
        self._is_open = True

    async def close(self) -> None:
        self._is_open = False

    @asynccontextmanager
    async def mock_behavior(self, **behaviors: list[Behavior] | Behavior):
        """
        Configure mock behavior for methods.

        Delegates to the internal Behave instance.

        Args:
            **behaviors: Method names as keys, and either:
                - A list of behaviors (each can be a callable, value, or exception)
                - A single behavior (callable, value, or exception)

        Example:
            async with mock_client.mock_behavior(
                get_latest_block=[Block(number=100, hash=BlockHash("0x123"))],
                get_certificates=[
                    lambda netuid, block: {...},
                    {"hotkey": NeuronCertificate(...)},
                ],
                get_certificate=[None, Exception("Network error")]
            ):
                # Test code here
        """
        async with self._behave.mock(**behaviors):
            yield

    async def _execute_behavior(self, method_name: str, *args, **kwargs) -> Any:
        return await self._behave.execute(method_name, *args, **kwargs)

    @property
    def calls(self):
        """Access call tracking from the behavior engine."""
        return self._behave.calls

    async def get_block(self, number: BlockNumber) -> Block | None:
        """
        Get a block by number.
        """
        self.calls["get_block"].append((number,))
        return await self._execute_behavior("get_block", number)

    async def get_latest_block(self) -> Block:
        """
        Get the latest block.
        """
        self.calls["get_latest_block"].append(())
        return await self._execute_behavior("get_latest_block")

    async def get_block_timestamp(self, block: Block) -> Timestamp:
        self.calls["get_block_timestamp"].append((block,))
        return await self._execute_behavior("get_block_timestamp", block)

    async def get_neurons_list(self, netuid: NetUid, block: Block) -> list[Neuron]:
        """
        Get neurons for a subnet.
        """
        self.calls["get_neurons_list"].append((netuid, block))
        return await self._execute_behavior("get_neurons_list", netuid, block)

    async def get_neurons(self, netuid: NetUid, block: Block) -> SubnetNeurons:
        """
        Get metagraph for a subnet.
        """
        self.calls["get_neurons"].append((netuid, block))
        return await self._execute_behavior("get_neurons", netuid, block)

    async def get_hyperparams(self, netuid: NetUid, block: Block) -> SubnetHyperparams | None:
        """
        Get hyperparameters for a subnet.
        """
        self.calls["get_hyperparams"].append((netuid, block))
        return await self._execute_behavior("get_hyperparams", netuid, block)

    async def get_certificates(self, netuid: NetUid, block: Block) -> dict[Hotkey, NeuronCertificate]:
        """
        Get all certificates for a subnet.
        """
        self.calls["get_certificates"].append((netuid, block))
        return await self._execute_behavior("get_certificates", netuid, block)

    async def get_certificate(
        self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None
    ) -> NeuronCertificate | None:
        """
        Get a certificate for a specific hotkey.
        """
        self.calls["get_certificate"].append((netuid, block, hotkey))
        return await self._execute_behavior("get_certificate", netuid, block, hotkey)

    async def generate_certificate_keypair(
        self, netuid: NetUid, algorithm: CertificateAlgorithm
    ) -> NeuronCertificateKeypair | None:
        """
        Generate a certificate keypair.
        """
        self.calls["generate_certificate_keypair"].append((netuid, algorithm))
        return await self._execute_behavior("generate_certificate_keypair", netuid, algorithm)

    async def commit_weights(self, netuid: NetUid, weights: dict[Hotkey, Weight]) -> RevealRound:
        """
        Commit weights for a subnet.
        """
        self.calls["commit_weights"].append((netuid, weights))
        return await self._execute_behavior("commit_weights", netuid, weights)

    async def set_weights(self, netuid: NetUid, weights: dict[Hotkey, Weight]) -> None:
        """
        Set weights for a subnet.
        """
        self.calls["set_weights"].append((netuid, weights))
        return await self._execute_behavior("set_weights", netuid, weights)

    async def get_subnet_state(self, netuid: NetUid, block: Block) -> SubnetState:
        """
        Get subnet state.
        """
        self.calls["get_subnet_state"].append((netuid, block))
        return await self._execute_behavior("get_subnet_state", netuid, block)

    async def get_commitment(self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None) -> Commitment | None:
        self.calls["get_commitment"].append((netuid, block, hotkey))
        return await self._execute_behavior("get_commitment", netuid, block, hotkey)

    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments:
        """
        Get all commitments for a subnet.
        """
        self.calls["get_commitments"].append((netuid, block))
        return await self._execute_behavior("get_commitments", netuid, block)

    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None:
        """
        Set commitment data on chain.
        """
        self.calls["set_commitment"].append((netuid, data))
        return await self._execute_behavior("set_commitment", netuid, data)

    async def get_validators(self, netuid: NetUid, block: Block) -> SubnetValidators:
        """
        Get validators for a subnet.
        """
        self.calls["get_validators"].append((netuid, block))
        return await self._execute_behavior("get_validators", netuid, block)

    async def reset_call_tracking(self) -> None:
        """
        Reset all call tracking.
        """
        self.calls.clear()
