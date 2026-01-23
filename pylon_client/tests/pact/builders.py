from ipaddress import IPv4Address

from pylon_client._internal.pylon_commons.currency import Currency, Token
from pylon_client._internal.pylon_commons.models import (
    AxonInfo,
    AxonProtocol,
    Block,
    Extrinsic,
    ExtrinsicCall,
    ExtrinsicCallArg,
    Neuron,
    Stakes,
)
from pylon_client._internal.pylon_commons.types import (
    AlphaStake,
    BlockHash,
    BlockNumber,
    Coldkey,
    Consensus,
    Dividends,
    Emission,
    ExtrinsicHash,
    ExtrinsicIndex,
    ExtrinsicLength,
    Hotkey,
    Incentive,
    NeuronActive,
    NeuronUid,
    Port,
    PruningScore,
    Rank,
    Stake,
    TaoStake,
    Timestamp,
    TotalStake,
    Trust,
    ValidatorPermit,
    ValidatorTrust,
)
from tests.pact.constants import BLOCK_HASH, BLOCK_NUMBER, COLDKEY, EXTRINSIC_HASH, EXTRINSIC_INDEX


def build_block() -> Block:
    return Block(number=BlockNumber(BLOCK_NUMBER), hash=BlockHash(BLOCK_HASH))


def build_neuron(hotkey: str, uid: int) -> Neuron:
    return Neuron(
        uid=NeuronUid(uid),
        coldkey=Coldkey(COLDKEY),
        hotkey=Hotkey(hotkey),
        active=NeuronActive(True),
        axon_info=AxonInfo(ip=IPv4Address("192.168.1.100"), port=Port(9999), protocol=AxonProtocol.HTTP),
        stake=Stake(1.1),
        rank=Rank(2.2),
        emission=Emission(Currency[Token.ALPHA](3.3)),
        incentive=Incentive(4.4),
        consensus=Consensus(5.5),
        trust=Trust(6.6),
        validator_trust=ValidatorTrust(7.7),
        dividends=Dividends(8.8),
        last_update=Timestamp(1001),
        validator_permit=ValidatorPermit(True),
        pruning_score=PruningScore(99),
        stakes=Stakes(
            alpha=AlphaStake(Currency[Token.ALPHA](100.1)),
            tao=TaoStake(Currency[Token.TAO](200.2)),
            total=TotalStake(Currency[Token.ALPHA](300.3)),
        ),
    )


def build_extrinsic() -> Extrinsic:
    return Extrinsic(
        block_number=BlockNumber(BLOCK_NUMBER),
        extrinsic_index=ExtrinsicIndex(EXTRINSIC_INDEX),
        extrinsic_hash=ExtrinsicHash(EXTRINSIC_HASH),
        extrinsic_length=ExtrinsicLength(100),
        address=COLDKEY,
        call=ExtrinsicCall(
            call_module="SubtensorModule",
            call_function="set_weights",
            call_args=[
                ExtrinsicCallArg(
                    name="netuid",
                    type="u16",
                    value="",
                )
            ],
        ),
    )
