from enum import StrEnum


class ApiVersion(StrEnum):
    V1 = "v1"
    V2 = "v2"

    @property
    def prefix(self) -> str:
        return f"/api/{self}"
