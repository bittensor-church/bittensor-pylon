from pydantic import BaseModel

TIMEOUT_HEADER = "X-Pylon-Timeout"


class PylonTimeout(BaseModel):
    """
    Timeout configuration for Pylon clients.

    Args:
        connect: Timeout for establishing a connection.
        read: Timeout for receiving a response.
        write: Timeout for sending the request body.
        pool: Timeout for acquiring a connection from the pool.
    """

    connect: float = 5.0
    read: float = 60.0
    write: float = 5.0
    pool: float = 5.0

    def get_header(self) -> dict[str, str]:
        """
        Returns the timeout header for the server request.
        """
        return {TIMEOUT_HEADER: str(self.read)}
