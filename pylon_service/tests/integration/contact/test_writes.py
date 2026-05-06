from __future__ import annotations

import asyncio

import pytest
from pylon_commons.models import CommitmentKind
from pylon_commons.types import CommitmentDataBytes, MechanismId, RevealedCommitmentData, Weight
from turbobt.substrate.exceptions import SubstrateException
from turbobt.subtensor.exceptions import CommitRevealDisabled

from pylon_service.bittensor.models import CertificateAlgorithm
from tests.integration.localchain.common import MAX_WEIGHT_REVEAL_WAIT_TIME
from tests.integration.localchain.dev_accounts import DevAccount


@pytest.mark.asyncio
async def test_set_commitment_writes_readable_commitment(write_contact, direct_netuid, snapshot):
    expected_commitment = CommitmentDataBytes(b"contact-write-commitment")

    await write_contact.set_commitment(direct_netuid, expected_commitment)

    latest_block = await write_contact.get_latest_block()
    commitment = await write_contact.get_commitment(direct_netuid, latest_block)

    assert commitment is not None
    assert commitment.model_dump(exclude={"commitment_block_number"}) == snapshot


@pytest.mark.asyncio
async def test_set_revealed_commitment_writes_readable_commitment(
    write_contact, direct_netuid, snapshot, turbobt_client
):
    expected_commitment = RevealedCommitmentData("contact-write-commitment")

    reveal_round = await write_contact.set_revealed_commitment(direct_netuid, expected_commitment, block_to_reveal=10)
    assert reveal_round > 0

    commitments = None
    for _ in range(8):
        latest_block = await write_contact.get_latest_block()
        commitments = await write_contact.get_revealed_commitments(direct_netuid, latest_block)
        if commitments and any(commitment.commitment == expected_commitment for commitment in commitments):
            break
        await asyncio.sleep(1)

    assert commitments is not None
    assert [item.model_dump(exclude={"reveal_block_number"}) for item in commitments] == snapshot


async def test_set_revealed_commitment_writes_readable_timelock_encrypted_commitment(write_contact, direct_netuid):
    expected_commitment = RevealedCommitmentData("contact-write-commitment")

    reveal_round = await write_contact.set_revealed_commitment(direct_netuid, expected_commitment, block_to_reveal=1000)
    assert reveal_round > 0

    latest_block = await write_contact.get_latest_block()
    commitment = await write_contact.get_commitment(direct_netuid, latest_block)

    assert commitment is not None
    assert commitment.kind == CommitmentKind.TIMELOCK_ENCRYPTED
    assert commitment.reveal_round == reveal_round


@pytest.mark.asyncio
async def test_set_weights_succeeds_on_direct_subnet(
    participant_uids_factory, write_contact, direct_netuid, turbobt_client, snapshot
):
    participant_uids = await participant_uids_factory(write_contact, direct_netuid)

    await write_contact.set_weights(
        direct_netuid,
        MechanismId(0),
        {
            participant_uids[DevAccount.CHARLIE]: Weight(0.6),
            participant_uids[DevAccount.DAVE]: Weight(0.4),
        },
    )

    weights = await turbobt_client.subnet(direct_netuid).weights.get(participant_uids[DevAccount.ALICE])
    assert weights == snapshot


@pytest.mark.asyncio
async def test_mechanism_set_weights_succeeds_on_direct_subnet(
    participant_uids_factory, write_contact, mechanism_direct_netuid, turbobt_client, snapshot
):
    participant_uids = await participant_uids_factory(write_contact, mechanism_direct_netuid)

    await write_contact.set_weights(
        mechanism_direct_netuid,
        MechanismId(1),
        {
            participant_uids[DevAccount.CHARLIE]: Weight(0.6),
            participant_uids[DevAccount.DAVE]: Weight(0.4),
        },
    )

    weights = await turbobt_client.subnet(mechanism_direct_netuid).weights.get(
        participant_uids[DevAccount.ALICE], mechanism_id=MechanismId(1)
    )
    assert weights == snapshot


@pytest.mark.asyncio
async def test_set_weights_raises_on_commit_reveal_subnet(participant_uids_factory, write_contact, commit_netuid):
    participant_uids = await participant_uids_factory(write_contact, commit_netuid)

    with pytest.raises(SubstrateException) as exc_info:
        await write_contact.set_weights(
            commit_netuid, MechanismId(0), {participant_uids[DevAccount.CHARLIE]: Weight(1.0)}
        )

    assert exc_info.value.args[0]["name"] == "CommitRevealEnabled"


@pytest.mark.asyncio
async def test_commit_weights_succeeds_on_commit_reveal_subnet(
    participant_uids_factory, write_contact, commit_netuid, turbobt_client, snapshot
):
    participant_uids = await participant_uids_factory(write_contact, commit_netuid)

    reveal_round = await write_contact.commit_weights(
        commit_netuid,
        MechanismId(0),
        {
            participant_uids[DevAccount.CHARLIE]: Weight(0.6),
            participant_uids[DevAccount.DAVE]: Weight(0.4),
        },
    )

    assert reveal_round > 0

    weights = None
    for _ in range(MAX_WEIGHT_REVEAL_WAIT_TIME):
        weights = await turbobt_client.subnet(commit_netuid).weights.get(participant_uids[DevAccount.ALICE])
        if weights:
            break
        await asyncio.sleep(1)

    assert weights is not None
    assert weights == snapshot


@pytest.mark.asyncio
async def test_mechanism_commit_weights_succeeds_on_commit_reveal_subnet(
    participant_uids_factory, write_contact, mechanism_commit_netuid, turbobt_client, snapshot
):
    participant_uids = await participant_uids_factory(write_contact, mechanism_commit_netuid)

    reveal_round = await write_contact.commit_weights(
        mechanism_commit_netuid,
        MechanismId(1),
        {
            participant_uids[DevAccount.CHARLIE]: Weight(0.6),
            participant_uids[DevAccount.DAVE]: Weight(0.4),
        },
    )

    assert reveal_round > 0

    weights = None
    for _ in range(MAX_WEIGHT_REVEAL_WAIT_TIME):
        weights = await turbobt_client.subnet(mechanism_commit_netuid).weights.get(
            participant_uids[DevAccount.ALICE], mechanism_id=MechanismId(1)
        )
        if weights:
            break
        await asyncio.sleep(1)

    assert weights is not None
    assert weights == snapshot


@pytest.mark.asyncio
async def test_commit_weights_raises_on_direct_subnet(write_contact, direct_netuid):
    latest_block = await write_contact.get_latest_block()
    bob_uid = next(
        neuron.uid
        for neuron in await write_contact.get_neurons_list(direct_netuid, latest_block)
        if neuron.hotkey == DevAccount.BOB.hotkey_ss58
    )

    with pytest.raises(CommitRevealDisabled):
        await write_contact.commit_weights(direct_netuid, MechanismId(0), {bob_uid: Weight(1.0)})


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
