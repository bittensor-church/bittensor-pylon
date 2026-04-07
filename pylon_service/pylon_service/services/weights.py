import logging

from pylon_commons.models import CommitReveal
from pylon_commons.types import Hotkey, NetUid, NeuronUid, Weight

from pylon_service.bittensor.contact import BittensorPort

from .errors import HyperparamsNotFoundError

logger = logging.getLogger(__name__)


class WeightsService:
    async def _translate_weights(
        self,
        router: BittensorPort,
        netuid: NetUid,
        weights: dict[Hotkey, Weight],
    ) -> dict[NeuronUid, Weight]:
        translated_weights: dict[NeuronUid, Weight] = {}
        missing: list[Hotkey] = []
        latest_block = await router.get_latest_block()
        neurons = await router.get_neurons_list(netuid, latest_block)
        hotkey_to_uid = {neuron.hotkey: neuron.uid for neuron in neurons}
        for hotkey, weight in weights.items():
            uid = hotkey_to_uid.get(hotkey)
            if uid is None:
                missing.append(hotkey)
                continue
            translated_weights[uid] = weight
        if missing:
            logger.warning(
                "Some of the hotkeys passed for weight commitment are missing. Weights will not be committed for: %s",
                missing,
            )
        return translated_weights

    async def apply_weights(self, router: BittensorPort, netuid: NetUid, weights: dict[Hotkey, Weight]) -> None:
        latest_block = await router.get_latest_block()
        hyperparams = await router.get_hyperparams(netuid, latest_block)
        if hyperparams is None:
            raise HyperparamsNotFoundError("Failed to fetch hyperparameters")

        translated_weights = await self._translate_weights(router, netuid, weights)
        commit_reveal_enabled = hyperparams.commit_reveal_weights_enabled
        if commit_reveal_enabled and commit_reveal_enabled != CommitReveal.DISABLED:
            await router.commit_weights(netuid, translated_weights)
        else:
            await router.set_weights(netuid, translated_weights)
