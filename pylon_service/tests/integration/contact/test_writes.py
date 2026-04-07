from __future__ import annotations

import asyncio

import pytest
from pylon_commons.types import CommitmentDataBytes, Weight
from turbobt.substrate.exceptions import SubstrateException
from turbobt.subtensor.exceptions import CommitRevealDisabled

from pylon_service.bittensor.models import CertificateAlgorithm, CommitReveal
from tests.integration.localchain.dev_accounts import DevAccount


@pytest.mark.asyncio
async def test_write_chain_subnets_have_expected_commit_reveal_modes(write_contact, direct_netuid, commit_netuid):
    block = await write_contact.get_latest_block()
    direct_hyperparams = await write_contact.get_hyperparams(direct_netuid, block)
    commit_hyperparams = await write_contact.get_hyperparams(commit_netuid, block)

    assert direct_hyperparams is not None
    assert commit_hyperparams is not None
    assert direct_hyperparams.commit_reveal_weights_enabled == CommitReveal.DISABLED
    assert commit_hyperparams.commit_reveal_weights_enabled == CommitReveal.V4


@pytest.mark.asyncio
async def test_set_commitment_writes_readable_commitment(write_contact, direct_netuid):
    expected_commitment = CommitmentDataBytes(b"contact-write-commitment")

    await write_contact.set_commitment(direct_netuid, expected_commitment)

    commitment = None
    for _ in range(8):
        latest_block = await write_contact.get_latest_block()
        commitment = await write_contact.get_commitment(direct_netuid, latest_block)
        if commitment is not None:
            break
        await asyncio.sleep(1)

    assert commitment is not None
    assert commitment.hotkey == DevAccount.ALICE.hotkey_ss58
    assert commitment.commitment == expected_commitment.hex()


@pytest.mark.asyncio
async def test_set_weights_succeeds_on_direct_subnet(write_contact, direct_netuid):
    latest_block = await write_contact.get_latest_block()
    bob_uid = next(
        neuron.uid
        for neuron in await write_contact.get_neurons_list(direct_netuid, latest_block)
        if neuron.hotkey == DevAccount.BOB.hotkey_ss58
    )

    await write_contact.set_weights(direct_netuid, {bob_uid: Weight(1.0)})


@pytest.mark.asyncio
async def test_set_weights_raises_on_commit_reveal_subnet(write_contact, commit_netuid):
    latest_block = await write_contact.get_latest_block()
    bob_uid = next(
        neuron.uid
        for neuron in await write_contact.get_neurons_list(commit_netuid, latest_block)
        if neuron.hotkey == DevAccount.BOB.hotkey_ss58
    )

    with pytest.raises(SubstrateException) as exc_info:
        await write_contact.set_weights(commit_netuid, {bob_uid: Weight(1.0)})

    assert exc_info.value.args[0]["name"] == "CommitRevealEnabled"


@pytest.mark.asyncio
async def test_commit_weights_succeeds_on_commit_reveal_subnet(write_contact, commit_netuid):
    latest_block = await write_contact.get_latest_block()
    bob_uid = next(
        neuron.uid
        for neuron in await write_contact.get_neurons_list(commit_netuid, latest_block)
        if neuron.hotkey == DevAccount.BOB.hotkey_ss58
    )

    reveal_round = await write_contact.commit_weights(commit_netuid, {bob_uid: Weight(1.0)})

    assert reveal_round > 0


@pytest.mark.asyncio
async def test_commit_weights_raises_on_direct_subnet(write_contact, direct_netuid):
    latest_block = await write_contact.get_latest_block()
    bob_uid = next(
        neuron.uid
        for neuron in await write_contact.get_neurons_list(direct_netuid, latest_block)
        if neuron.hotkey == DevAccount.BOB.hotkey_ss58
    )

    with pytest.raises(CommitRevealDisabled):
        await write_contact.commit_weights(direct_netuid, {bob_uid: Weight(1.0)})


@pytest.mark.asyncio
async def test_generate_certificate_keypair_can_be_read_back(write_contact, direct_netuid):
    keypair = await write_contact.generate_certificate_keypair(direct_netuid, CertificateAlgorithm.ED25519)

    assert keypair is not None
    assert keypair.algorithm == CertificateAlgorithm.ED25519

    latest_block = await write_contact.get_latest_block()
    certificate = await write_contact.get_certificate(direct_netuid, latest_block)

    assert certificate is not None
    assert certificate.algorithm == keypair.algorithm
    assert certificate.public_key == keypair.public_key
