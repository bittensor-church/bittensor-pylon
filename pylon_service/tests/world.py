from __future__ import annotations

from dataclasses import dataclass

from pylon_commons.currency import Currency, CurrencyRao, Token
from pylon_commons.models import (
    Block,
    CommitmentVariant,
    CommitReveal,
    HexDataCommitment,
    Neuron,
    RevealedCommitment,
    Stakes,
    SubnetCommitments,
    SubnetHyperparams,
    SubnetNeurons,
    SubnetRevealedCommitments,
    SubnetState,
    TimelockEncryptedCommitment,
)
from pylon_commons.types import (
    AlphaStake,
    AlphaStakeRao,
    BlockHash,
    BlockNumber,
    Coldkey,
    CommitmentDataHex,
    Consensus,
    Dividends,
    EmissionRao,
    Hotkey,
    IdentityName,
    Incentive,
    NetUid,
    NeuronUid,
    PruningScore,
    Rank,
    RevealedCommitmentData,
    SubnetActive,
    TaoStake,
    TaoStakeRao,
    Tempo,
    Timestamp,
    TotalStake,
    TotalStakeRao,
    Trust,
    ValidatorPermit,
)

from pylon_service.bittensor.mock_contact import MockBittensorContact
from tests.factories import NeuronFactory

VALIDATORS_NETUID = NetUid(11)
COMMITMENTS_ALL_NETUID = NetUid(21)
COMMITMENTS_FILTERED_NETUID = NetUid(22)
COMMITMENTS_EMPTY_NETUID = NetUid(23)
OWN_COMMITMENT_NETUID = NetUid(24)
COMMITMENTS_MIXED_NETUID = NetUid(25)
COMMITMENTS_TIMELOCK_ONLY_NETUID = NetUid(26)
OWN_TIMELOCK_COMMITMENT_NETUID = NetUid(27)
REVEALED_COMMITMENTS_NETUID = NetUid(28)


@dataclass(frozen=True)
class IdentityContacts:
    main: MockBittensorContact
    archive: MockBittensorContact


@dataclass(frozen=True)
class SharedWorld:
    open_access: IdentityContacts
    identity_contacts: dict[IdentityName, IdentityContacts]
    default_latest_block: Block
    default_neurons: dict[NetUid, list[Neuron]]
    default_subnet_states: dict[NetUid, SubnetState]
    default_commitments: dict[NetUid, dict[Hotkey, CommitmentVariant]]
    default_revealed_commitments: dict[NetUid, dict[Hotkey, list[RevealedCommitment]]]

    @property
    def contacts(self) -> tuple[MockBittensorContact, ...]:
        seen: set[int] = set()
        result: list[MockBittensorContact] = []
        for contact in (self.open_access.main, self.open_access.archive):
            if id(contact) not in seen:
                seen.add(id(contact))
                result.append(contact)
        for ic in self.identity_contacts.values():
            for contact in (ic.main, ic.archive):
                if id(contact) not in seen:
                    seen.add(id(contact))
                    result.append(contact)
        return tuple(result)

    def reset(self) -> None:
        for contact in self.contacts:
            contact.reset()

    def seed_defaults(self) -> None:
        for contact in self.contacts:
            contact.set_default("get_latest_block", self.default_latest_block)
            contact.set_default("get_block", lambda number: build_block(number))
            contact.set_default("get_neurons_list", lambda netuid, block, neurons=self.default_neurons: neurons[netuid])
            contact.set_default(
                "get_neurons",
                lambda netuid, block, neurons=self.default_neurons: SubnetNeurons(
                    block=block,
                    neurons={neuron.hotkey: neuron for neuron in neurons[netuid]},
                ),
            )
            contact.set_default(
                "get_subnet_state", lambda netuid, block, states=self.default_subnet_states: states[netuid]
            )
            contact.set_default(
                "get_commitments",
                lambda netuid, block, commitments=self.default_commitments: SubnetCommitments(
                    block=block,
                    commitments=commitments.get(netuid, {}),
                ),
            )
            contact.set_default(
                "get_commitment",
                lambda netuid,
                block,
                hotkey=None,
                commitments=self.default_commitments,
                wallet_hotkey=contact.hotkey: _resolve_commitment(
                    netuid,
                    hotkey or wallet_hotkey,
                    commitments,
                ),
            )
            contact.set_default(
                "get_revealed_commitments",
                lambda netuid,
                block,
                hotkey=None,
                revealed_commitments=self.default_revealed_commitments,
                wallet_hotkey=contact.hotkey: _resolve_revealed_commitments(
                    netuid,
                    hotkey or wallet_hotkey,
                    revealed_commitments,
                ),
            )
            contact.set_default(
                "get_all_revealed_commitments",
                lambda netuid, block, revealed_commitments=self.default_revealed_commitments: SubnetRevealedCommitments(
                    block=block,
                    commitments=revealed_commitments.get(netuid, {}),
                ),
            )
            contact.set_default(
                "get_hyperparams",
                lambda netuid, block: SubnetHyperparams(
                    commit_reveal_weights_enabled=CommitReveal.DISABLED,
                    tempo=Tempo(50),
                ),
            )
            contact.set_default("set_weights", lambda netuid, mechanism_id, weights: None)


def default_latest_block() -> Block:
    return Block(number=BlockNumber(1000), hash=BlockHash("0xshared-latest-block"))


def build_block(number: BlockNumber) -> Block:
    return Block(number=number, hash=BlockHash(f"0xblock{number}"))


def default_neurons(*, own_commitment_hotkey: str) -> dict[NetUid, list[Neuron]]:
    NeuronFactory.seed_random(1)

    def build_neuron(netuid: int, uid: int, hotkey: str) -> Neuron:
        return NeuronFactory.build(
            uid=NeuronUid(uid),
            hotkey=Hotkey(hotkey),
        )

    subnet_one = [
        build_neuron(1, 1, "hotkey1"),
        build_neuron(1, 2, "hotkey2"),
        build_neuron(1, 3, "hotkey3"),
    ]
    subnet_two = [
        build_neuron(2, 1, "hotkey1"),
        build_neuron(2, 2, "hotkey2"),
        build_neuron(2, 3, "hotkey3"),
    ]
    validator_high = NeuronFactory.build(
        hotkey=Hotkey("validator-high"),
        validator_permit=ValidatorPermit(True),
        stakes=Stakes(
            alpha=AlphaStake(Currency[Token.ALPHA](1)),
            tao=TaoStake(Currency[Token.TAO](1)),
            total=TotalStake(Currency[Token.ALPHA](9)),
        ),
    )
    validator_low = NeuronFactory.build(
        hotkey=Hotkey("validator-low"),
        validator_permit=ValidatorPermit(True),
        stakes=Stakes(
            alpha=AlphaStake(Currency[Token.ALPHA](1)),
            tao=TaoStake(Currency[Token.TAO](1)),
            total=TotalStake(Currency[Token.ALPHA](3)),
        ),
    )
    validator_hidden = NeuronFactory.build(
        hotkey=Hotkey("non-validator"),
        validator_permit=ValidatorPermit(False),
        stakes=Stakes(
            alpha=AlphaStake(Currency[Token.ALPHA](1)),
            tao=TaoStake(Currency[Token.TAO](1)),
            total=TotalStake(Currency[Token.ALPHA](99)),
        ),
    )

    return {
        NetUid(1): subnet_one,
        NetUid(2): subnet_two,
        VALIDATORS_NETUID: [
            validator_low,
            validator_hidden,
            validator_high,
        ],
        COMMITMENTS_ALL_NETUID: [
            build_neuron(21, 1, "hotkey1"),
            build_neuron(21, 2, "hotkey2"),
        ],
        COMMITMENTS_FILTERED_NETUID: [
            build_neuron(22, 1, "hotkey1"),
        ],
        COMMITMENTS_EMPTY_NETUID: [],
        OWN_COMMITMENT_NETUID: [
            build_neuron(24, 1, own_commitment_hotkey),
        ],
        COMMITMENTS_MIXED_NETUID: [
            build_neuron(25, 1, "hotkey1"),
            build_neuron(25, 2, "hotkey2"),
        ],
        COMMITMENTS_TIMELOCK_ONLY_NETUID: [
            build_neuron(26, 1, "hotkey2"),
        ],
        REVEALED_COMMITMENTS_NETUID: [
            build_neuron(28, 1, "hotkey1"),
            build_neuron(28, 2, own_commitment_hotkey),
        ],
        OWN_TIMELOCK_COMMITMENT_NETUID: [
            build_neuron(27, 1, own_commitment_hotkey),
        ],
    }


def _build_subnet_state(
    netuid: NetUid, registered_hotkeys: list[str], *, validator_permits: list[bool] | None = None
) -> SubnetState:
    count = len(registered_hotkeys)
    if validator_permits is None:
        validator_permits = [True] * count
    if len(validator_permits) != count:
        raise ValueError("validator_permits must match registered_hotkeys length")
    return SubnetState(
        netuid=netuid,
        hotkeys=[Hotkey(hotkey) for hotkey in registered_hotkeys],
        coldkeys=[Coldkey(f"coldkey-{i}") for i in range(count)],
        active=[SubnetActive(True)] * count,
        validator_permit=[ValidatorPermit(value) for value in validator_permits],
        pruning_score=[PruningScore(0)] * count,
        last_update=[Timestamp(0)] * count,
        emission=[EmissionRao(CurrencyRao[Token.ALPHA](0))] * count,
        dividends=[Dividends(0)] * count,
        incentives=[Incentive(0)] * count,
        consensus=[Consensus(0)] * count,
        trust=[Trust(0)] * count,
        rank=[Rank(0)] * count,
        block_at_registration=[BlockNumber(1)] * count,
        alpha_stake=[AlphaStakeRao(CurrencyRao[Token.ALPHA](0))] * count,
        tao_stake=[TaoStakeRao(CurrencyRao[Token.TAO](0))] * count,
        total_stake=[TotalStakeRao(CurrencyRao[Token.ALPHA](0))] * count,
        emission_history=[[EmissionRao(CurrencyRao[Token.ALPHA](0))] for _ in range(count)],
    )


def default_subnet_states(*, own_commitment_hotkey: str) -> dict[NetUid, SubnetState]:
    return {
        NetUid(1): _build_subnet_state(NetUid(1), ["hotkey1", "hotkey2", "hotkey3"]),
        NetUid(2): _build_subnet_state(NetUid(2), ["hotkey1", "hotkey2", "hotkey3"]),
        VALIDATORS_NETUID: _build_subnet_state(
            VALIDATORS_NETUID,
            ["validator-low", "non-validator", "validator-high"],
            validator_permits=[True, False, True],
        ),
        COMMITMENTS_ALL_NETUID: _build_subnet_state(COMMITMENTS_ALL_NETUID, ["hotkey1", "hotkey2"]),
        COMMITMENTS_FILTERED_NETUID: _build_subnet_state(COMMITMENTS_FILTERED_NETUID, ["hotkey1"]),
        COMMITMENTS_EMPTY_NETUID: _build_subnet_state(COMMITMENTS_EMPTY_NETUID, []),
        OWN_COMMITMENT_NETUID: _build_subnet_state(OWN_COMMITMENT_NETUID, [own_commitment_hotkey]),
        COMMITMENTS_MIXED_NETUID: _build_subnet_state(COMMITMENTS_MIXED_NETUID, ["hotkey1", "hotkey2"]),
        COMMITMENTS_TIMELOCK_ONLY_NETUID: _build_subnet_state(COMMITMENTS_TIMELOCK_ONLY_NETUID, ["hotkey2"]),
        REVEALED_COMMITMENTS_NETUID: _build_subnet_state(
            REVEALED_COMMITMENTS_NETUID, ["hotkey1", own_commitment_hotkey]
        ),
        OWN_TIMELOCK_COMMITMENT_NETUID: _build_subnet_state(OWN_TIMELOCK_COMMITMENT_NETUID, [own_commitment_hotkey]),
    }


def default_commitments() -> dict[NetUid, dict[Hotkey, CommitmentVariant]]:
    return {
        COMMITMENTS_ALL_NETUID: {
            Hotkey("hotkey1"): HexDataCommitment(
                commitment_block_number=BlockNumber(699),
                hotkey=Hotkey("hotkey1"),
                commitment=CommitmentDataHex("0xaaaa"),
            ),
            Hotkey("hotkey2"): HexDataCommitment(
                commitment_block_number=BlockNumber(699),
                hotkey=Hotkey("hotkey2"),
                commitment=CommitmentDataHex("0xbbbb"),
            ),
        },
        COMMITMENTS_FILTERED_NETUID: {
            Hotkey("hotkey1"): HexDataCommitment(
                commitment_block_number=BlockNumber(700),
                hotkey=Hotkey("hotkey1"),
                commitment=CommitmentDataHex("0xaaaa"),
            ),
            Hotkey("foreign-hotkey"): HexDataCommitment(
                commitment_block_number=BlockNumber(700),
                hotkey=Hotkey("foreign-hotkey"),
                commitment=CommitmentDataHex("0xffff"),
            ),
        },
        COMMITMENTS_EMPTY_NETUID: {},
        OWN_COMMITMENT_NETUID: {},
        COMMITMENTS_MIXED_NETUID: {
            Hotkey("hotkey1"): HexDataCommitment(
                commitment_block_number=BlockNumber(701),
                hotkey=Hotkey("hotkey1"),
                commitment=CommitmentDataHex("0xcafe"),
            ),
            Hotkey("hotkey2"): TimelockEncryptedCommitment(
                commitment_block_number=BlockNumber(702),
                hotkey=Hotkey("hotkey2"),
                commitment=CommitmentDataHex("0xbeef"),
                reveal_round=321,
            ),
        },
        COMMITMENTS_TIMELOCK_ONLY_NETUID: {
            Hotkey("hotkey2"): TimelockEncryptedCommitment(
                commitment_block_number=BlockNumber(703),
                hotkey=Hotkey("hotkey2"),
                commitment=CommitmentDataHex("0xcccc"),
                reveal_round=123,
            ),
        },
        REVEALED_COMMITMENTS_NETUID: {},
        OWN_TIMELOCK_COMMITMENT_NETUID: {},
    }


def _resolve_commitment(
    netuid: NetUid,
    hotkey: Hotkey,
    commitments: dict[NetUid, dict[Hotkey, CommitmentVariant]],
) -> CommitmentVariant | None:
    if netuid == OWN_COMMITMENT_NETUID:
        return HexDataCommitment(
            commitment_block_number=BlockNumber(999),
            hotkey=hotkey,
            commitment=CommitmentDataHex("0x0f0e0d0c"),
        )
    if netuid == OWN_TIMELOCK_COMMITMENT_NETUID:
        return TimelockEncryptedCommitment(
            commitment_block_number=BlockNumber(998),
            hotkey=hotkey,
            commitment=CommitmentDataHex("0x10203040"),
            reveal_round=654,
        )
    return commitments.get(netuid, {}).get(hotkey)


def default_revealed_commitments(*, own_commitment_hotkey: str) -> dict[NetUid, dict[Hotkey, list[RevealedCommitment]]]:
    return {
        REVEALED_COMMITMENTS_NETUID: {
            Hotkey("hotkey1"): [
                RevealedCommitment(
                    reveal_block_number=BlockNumber(703),
                    hotkey=Hotkey("hotkey1"),
                    commitment=RevealedCommitmentData("model-a"),
                ),
                RevealedCommitment(
                    reveal_block_number=BlockNumber(704),
                    hotkey=Hotkey("hotkey1"),
                    commitment=RevealedCommitmentData("model-b"),
                ),
            ],
            Hotkey(own_commitment_hotkey): [
                RevealedCommitment(
                    reveal_block_number=BlockNumber(705),
                    hotkey=Hotkey(own_commitment_hotkey),
                    commitment=RevealedCommitmentData("self-model"),
                ),
            ],
        }
    }


def _resolve_revealed_commitments(
    netuid: NetUid,
    hotkey: Hotkey,
    revealed_commitments: dict[NetUid, dict[Hotkey, list[RevealedCommitment]]],
) -> list[RevealedCommitment] | None:
    return revealed_commitments.get(netuid, {}).get(hotkey)
