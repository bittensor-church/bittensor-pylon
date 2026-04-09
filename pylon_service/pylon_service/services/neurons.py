from pylon_commons.models import SubnetNeurons, SubnetValidators
from pylon_commons.types import NetUid

from pylon_service.bittensor.contact import BittensorPort
from pylon_service.bittensor.models import Block
from pylon_service.bittensor.recent import RecentObjectMissing, RecentObjectProvider, RecentObjectStale

from .errors import RecentObjectMissingError, RecentObjectStaleError


class NeuronService:
    async def get_neurons(self, contact_router: BittensorPort, netuid: NetUid, block: Block) -> SubnetNeurons:
        return await contact_router.get_neurons(netuid, block)

    async def get_latest_neurons(self, contact_router: BittensorPort, netuid: NetUid) -> SubnetNeurons:
        block = await contact_router.get_latest_block()
        return await contact_router.get_neurons(netuid, block)

    async def get_recent_neurons(self, recent_object_provider: RecentObjectProvider) -> SubnetNeurons:
        try:
            return await recent_object_provider.get(SubnetNeurons)
        except RecentObjectMissing as exc:
            raise RecentObjectMissingError(
                "Recent neurons data is not available. Cache update may not have finished "
                "yet or subnet may not be configured for caching recent objects."
            ) from exc
        except RecentObjectStale as exc:
            raise RecentObjectStaleError("Recent neurons data is stale. Cache update may be failing.") from exc

    async def get_validators(self, contact_router: BittensorPort, netuid: NetUid, block: Block) -> SubnetValidators:
        subnet_neurons = await contact_router.get_neurons(netuid, block)
        validators = [neuron for neuron in subnet_neurons.neurons.values() if neuron.validator_permit]
        validators.sort(key=lambda neuron: neuron.stakes.total, reverse=True)
        return SubnetValidators(block=block, validators=validators)

    async def get_latest_validators(self, contact_router: BittensorPort, netuid: NetUid) -> SubnetValidators:
        block = await contact_router.get_latest_block()
        return await self.get_validators(contact_router, netuid, block)
