from ipaddress import IPv4Address

from pylon_client._internal.pylon_commons.currency import CurrencyRao
from pylon_client._internal.pylon_commons.types import AlphaPriceRao
from pylon_client._internal.pylon_commons.types import evm as evm_types
from pylon_client.artanis import (
    AlphaStake,
    BlockHash,
    BlockNumber,
    Coldkey,
    Consensus,
    Currency,
    Dividends,
    Emission,
    EvmAddress,
    ExtrinsicHash,
    ExtrinsicIndex,
    ExtrinsicLength,
    Hotkey,
    Incentive,
    NetUid,
    NeuronActive,
    NeuronUid,
    Port,
    PruningScore,
    Rank,
    Stake,
    TaoStake,
    Timestamp,
    Token,
    TotalStake,
    Trust,
    ValidatorPermit,
    ValidatorTrust,
)
from pylon_client.artanis.unstable import (
    AxonInfo,
    AxonProtocol,
    Block,
    BlockInfoBag,
    EvmAssociation,
    EvmLog,
    Extrinsic,
    ExtrinsicCall,
    ExtrinsicCallArg,
    GetEvmLogsResponse,
    GetPriceResponse,
    GetPricesResponse,
    Neuron,
    Stakes,
    SubnetPriceEntry,
)
from tests.pact.constants import (
    BLOCK_HASH,
    BLOCK_NUMBER,
    BLOCK_TIMESTAMP,
    COLDKEY,
    EVM_CONTRACT_ADDRESS,
    EVM_FROM_BLOCK,
    EVM_TO_BLOCK,
    EVM_TRANSACTION_HASH,
    EXTRINSIC_HASH,
    EXTRINSIC_INDEX,
    NETUID,
    NETUID_2,
    PRICE_VALUE_RAO,
    PRICE_VALUE_RAO_2,
)


def build_block() -> Block:
    return Block(number=BlockNumber(BLOCK_NUMBER), hash=BlockHash(BLOCK_HASH))


def build_block_info_bag() -> BlockInfoBag:
    return BlockInfoBag(
        number=BlockNumber(BLOCK_NUMBER),
        hash=BlockHash(BLOCK_HASH),
        timestamp=Timestamp(BLOCK_TIMESTAMP),
    )


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


def build_prices() -> GetPricesResponse:
    return GetPricesResponse(
        block=build_block(),
        prices={
            NetUid(NETUID): SubnetPriceEntry(value=AlphaPriceRao(CurrencyRao[Token.TAO](PRICE_VALUE_RAO))),
            NetUid(NETUID_2): SubnetPriceEntry(value=AlphaPriceRao(CurrencyRao[Token.TAO](PRICE_VALUE_RAO_2))),
        },
    )


def build_price(netuid: int = NETUID) -> GetPriceResponse:
    return GetPriceResponse(
        block=build_block(),
        netuid=NetUid(netuid),
        price=SubnetPriceEntry(value=AlphaPriceRao(CurrencyRao[Token.TAO](PRICE_VALUE_RAO))),
    )


def build_evm_association(hotkey: Hotkey) -> EvmAssociation:
    return EvmAssociation(
        hotkey=hotkey,
        evm_address=EvmAddress("0x" + "c" * 40),
        last_block_where_ownership_was_proven=BlockNumber(BLOCK_NUMBER),
    )


def build_evm_log() -> EvmLog:
    return EvmLog(
        event="Transfer",
        args={"from": "0xaaaa", "to": "0xbbbb", "value": 1000},
        address=evm_types.Address(EVM_CONTRACT_ADDRESS),
        block_number=evm_types.BlockNumber(BLOCK_NUMBER),
        transaction_hash=evm_types.TransactionHash(EVM_TRANSACTION_HASH),
        transaction_index=evm_types.TransactionIndex(0),
        log_index=evm_types.LogIndex(0),
    )


def build_evm_logs_response() -> GetEvmLogsResponse:
    return GetEvmLogsResponse(
        logs=[build_evm_log()],
        from_block=evm_types.BlockNumber(EVM_FROM_BLOCK),
        to_block=evm_types.BlockNumber(EVM_TO_BLOCK),
    )


def build_empty_evm_logs_response() -> GetEvmLogsResponse:
    return GetEvmLogsResponse(
        logs=[],
        from_block=evm_types.BlockNumber(EVM_FROM_BLOCK),
        to_block=evm_types.BlockNumber(EVM_TO_BLOCK),
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
