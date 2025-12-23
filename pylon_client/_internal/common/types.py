from typing import NewType

from pylon_client._internal.common.currency import Currency, CurrencyRao, Token

# When adding new type, remember to also include it in extend-immutable-calls in pyproject.toml so that ruff does not
# raise B008 on new type wrapping the function's default value.

Hotkey = NewType("Hotkey", str)
Coldkey = NewType("Coldkey", str)
Weight = NewType("Weight", float)
BlockHash = NewType("BlockHash", str)
BlockNumber = NewType("BlockNumber", int)
RevealRound = NewType("RevealRound", int)
PublicKey = NewType("PublicKey", str)
PrivateKey = NewType("PrivateKey", str)
NeuronUid = NewType("NeuronUid", int)
Port = NewType("Port", int)
Stake = NewType("Stake", float)
Rank = NewType("Rank", float)
Emission = NewType("Emission", Currency[Token.ALPHA])
EmissionRao = NewType("EmissionRao", CurrencyRao[Token.ALPHA])
Incentive = NewType("Incentive", float)
Consensus = NewType("Consensus", float)
Trust = NewType("Trust", float)
ValidatorTrust = NewType("ValidatorTrust", float)
Dividends = NewType("Dividends", float)
Timestamp = NewType("Timestamp", int)
PruningScore = NewType("PruningScore", int)
MaxWeightsLimit = NewType("MaxWeightsLimit", int)
Tempo = NewType("Tempo", int)
NetUid = NewType("NetUid", int)
BittensorNetwork = NewType("BittensorNetwork", str)
ArchiveBlocksCutoff = NewType("ArchiveBlocksCutoff", int)
NeuronActive = NewType("NeuronActive", bool)
ValidatorPermit = NewType("ValidatorPermit", bool)
SubnetActive = NewType("SubnetActive", bool)
AlphaStakeRao = NewType("AlphaStakeRao", CurrencyRao[Token.ALPHA])
TaoStakeRao = NewType("TaoStakeRao", CurrencyRao[Token.TAO])
TotalStakeRao = NewType("TotalStakeRao", CurrencyRao[Token.ALPHA])
AlphaStake = NewType("AlphaStake", Currency[Token.ALPHA])
TaoStake = NewType("TaoStake", Currency[Token.TAO])
TotalStake = NewType("TotalStake", Currency[Token.ALPHA])
WalletName = NewType("WalletName", str)
HotkeyName = NewType("HotkeyName", str)
PylonAuthToken = NewType("PylonAuthToken", str)
IdentityName = NewType("IdentityName", str)


class CommitmentDataHex(str):
    def __new__(cls, value: str) -> "CommitmentDataHex":
        if not value.startswith("0x"):
            value = "0x" + value
        return super().__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema

        return core_schema.no_info_after_validator_function(cls, handler(str))


class CommitmentDataBytes(bytes):
    def hex(self, *args, **kwargs) -> CommitmentDataHex:
        return CommitmentDataHex(super().hex(*args, **kwargs))

    @classmethod
    def fromhex(cls, value: str | CommitmentDataHex) -> "CommitmentDataBytes":
        if value.startswith("0x"):
            value = value[2:]
        return cls(super().fromhex(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema

        return core_schema.no_info_after_validator_function(cls, core_schema.bytes_schema(min_length=1))
