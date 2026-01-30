from enum import StrEnum


class ApiVersion(StrEnum):
    V1 = "v1"
    UNSTABLE = "_unstable"

    @property
    def prefix(self) -> str:
        return f"/api/{self}"
