"""
Domain models layered on top of raw recorded WebSocket frames.

These models recognize Substrate JSON-RPC payloads carrying SCALE-encoded
extrinsics, expose decoded contents as typed Pydantic models, and offer
typed accessors for specific extrinsic call functions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict

from tests.integration.mitmproxy.ws_recorder_client import WSDirection, WSFrame

type ExtrinsicDecoder = Callable[[str], dict[str, Any]]


_SUBMIT_AND_WATCH_METHOD = "author_submitAndWatchExtrinsic"


class DecodedCallArg(BaseModel):
    """
    A single argument of a decoded Substrate runtime call.
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    type: str | None = None
    value: Any


class DecodedCall(BaseModel):
    """
    The runtime call portion of a decoded SCALE extrinsic.
    """

    model_config = ConfigDict(extra="ignore")

    call_function: str
    call_module: str
    call_args: list[DecodedCallArg]


class DecodedExtrinsic(BaseModel):
    """
    A SCALE-decoded extrinsic, as produced by `scalecodec`'s Extrinsic decoder.

    Only the fields relevant to test assertions are typed; the rest are dropped.
    """

    model_config = ConfigDict(extra="ignore")

    address: str | None = None
    call: DecodedCall


class SubmitAndWatchExtrinsicFrame(WSFrame):
    """
    A client-to-server WS frame carrying an `author_submitAndWatchExtrinsic` JSON-RPC call.

    The decoded extrinsic is parsed into a `DecodedExtrinsic` model. Use
    `from_ws_frame` to attempt construction from a raw frame.
    """

    decoded_extrinsic: DecodedExtrinsic

    @classmethod
    def from_ws_frame(cls, frame: WSFrame, decoder: ExtrinsicDecoder) -> Self | None:
        """
        Build an instance from a raw `WSFrame`, or return `None` if the frame
        is not an `author_submitAndWatchExtrinsic` call.

        Returns:
            An instance of `cls` (so subclasses can call this and get back
            their own type) or `None` if the frame does not match.
        """
        if frame.direction != WSDirection.CLIENT_TO_SERVER or not frame.is_text:
            return None
        try:
            payload = frame.content_json
        except ValueError:
            return None
        if not isinstance(payload, dict) or payload.get("method") != _SUBMIT_AND_WATCH_METHOD:
            return None
        params = payload.get("params")
        if not isinstance(params, dict):
            return None
        extrinsic_bytes = params.get("bytes")
        if not isinstance(extrinsic_bytes, str):
            return None
        decoded = DecodedExtrinsic.model_validate(decoder(extrinsic_bytes))
        return cls(**frame.model_dump(), decoded_extrinsic=decoded)


class CommitTimelockedMechanismWeightsCallArgs(BaseModel):
    """
    Strongly-typed arguments of the `commit_timelocked_mechanism_weights` extrinsic.

    Mirrors the SubtensorModule call signature (netuid, commit hex, mecid,
    reveal_round, commit_reveal_version).
    """

    netuid: int
    commit: str
    mecid: int
    reveal_round: int
    commit_reveal_version: int


class CommitTimelockedMechanismWeightsFrame(SubmitAndWatchExtrinsicFrame):
    """
    A `SubmitAndWatchExtrinsicFrame` whose inner call is `commit_timelocked_mechanism_weights`.

    Exposes the call arguments as typed fields populated at construction time.
    """

    CALL_FUNCTION: ClassVar[str] = "commit_timelocked_mechanism_weights"

    address: str
    call_args: CommitTimelockedMechanismWeightsCallArgs

    @classmethod
    def from_ws_frame(cls, frame: WSFrame, decoder: ExtrinsicDecoder) -> Self | None:
        """
        Build an instance from a raw `WSFrame`, or return `None` if the frame
        is not a `commit_timelocked_mechanism_weights` extrinsic submission.
        """
        base = SubmitAndWatchExtrinsicFrame.from_ws_frame(frame, decoder)
        if base is None or base.decoded_extrinsic.call.call_function != cls.CALL_FUNCTION:
            return None
        if base.decoded_extrinsic.address is None:
            return None
        call_args = CommitTimelockedMechanismWeightsCallArgs.model_validate(
            {arg.name: arg.value for arg in base.decoded_extrinsic.call.call_args},
        )
        return cls(
            **base.model_dump(exclude={"decoded_extrinsic"}),
            decoded_extrinsic=base.decoded_extrinsic,
            address=base.decoded_extrinsic.address,
            call_args=call_args,
        )
