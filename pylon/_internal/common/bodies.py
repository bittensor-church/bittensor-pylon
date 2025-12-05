from pydantic import BaseModel, field_validator

from pylon._internal.common.types import Hotkey, PylonAuthToken, Weight


class PylonBody(BaseModel):
    """
    Base class for all Pylon requests' bodies.
    PylonBody is used in the service to parse the incoming data.
    It is also used in the client as a base for the requests made to the endpoints that require that pylon body.
    """


class LoginBody(PylonBody):
    """
    Class used to log in to the API.
    """

    token: PylonAuthToken


class SetWeightsBody(PylonBody):
    """
    Class used to perform setting weights via the API.
    """

    weights: dict[Hotkey, Weight]

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, v):
        if not v:
            raise ValueError("No weights provided")

        for hotkey, weight in v.items():
            if not hotkey or not isinstance(hotkey, str):
                raise ValueError(f"Invalid hotkey: '{hotkey}' must be a non-empty string")
            if not isinstance(weight, int | float):
                raise ValueError(f"Invalid weight for hotkey '{hotkey}': '{weight}' must be a number")

        return v
