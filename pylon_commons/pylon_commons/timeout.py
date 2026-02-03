from pydantic import BaseModel

TIMEOUT_HEADER = "X-Pylon-Timeout"
MIN_SERVER_TIMEOUT = 0.5


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

    def get_header(self, buffer: float = 0.5) -> dict[str, str]:
        """
        Returns the timeout header for the server request.

        The server timeout is reduced by `buffer` so the server responds before the client times out.
        The server timeout is capped at a minimum of MIN_SERVER_TIMEOUT.
        """
        server_timeout = max(self.read - buffer, MIN_SERVER_TIMEOUT)
        return {TIMEOUT_HEADER: str(server_timeout)}
