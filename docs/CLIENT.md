# Pylon Client

Pylon client is a Python library for interacting with Pylon.
All API endpoints are wrapped into easy-to-use Python methods with features like
authentication, retries, and connection pools built in.

> **Note:** Before using the client, it is recommended to familiarize yourself with
> the concepts from [Pylon documentation](SERVICE.md), such as open access,
> identity access, and configuration.

## Installation

```bash
pip install bittensor-pylon-client
```

## Getting Started

### Configuring the Client

The client requires a configuration object that specifies the Pylon service address
and authentication credentials.

| Parameter | Description | Required |
|-----------|-------------|----------|
| `address` | Pylon service URL (e.g., `http://localhost:8000`) | Yes |
| `open_access_token` | Token for open access endpoints | No |
| `identity_name` | Identity name for authenticated operations | No* |
| `identity_token` | Token for the specified identity | No* |
| `retry` | Retry configuration (see [Retries](#retries) section) | No |

*`identity_name` and `identity_token` must both be provided together or not at all.

**Open access configuration:**
```python
from pylon_client.v1 import AsyncConfig

config = AsyncConfig(
    address="http://localhost:8000",
    open_access_token="my_token",
)
```

**Identity access configuration:**
```python
from pylon_client.v1 import AsyncConfig

config = AsyncConfig(
    address="http://localhost:8000",
    identity_name="sn1",
    identity_token="my_secret_token",
)
```

**Both access modes:**
```python
from pylon_client.v1 import AsyncConfig

config = AsyncConfig(
    address="http://localhost:8000",
    open_access_token="my_open_token",
    identity_name="sn1",
    identity_token="my_identity_token",
)
```

### Creating the Client

The client is available in two variants:
- `PylonClient` with `Config` - synchronous client
- `AsyncPylonClient` with `AsyncConfig` - asynchronous client

The client should be used as a context manager to ensure proper resource management.
The connection pool is opened when entering the context and closed when exiting.

```python
from pylon_client.v1 import AsyncPylonClient, AsyncConfig

config = AsyncConfig(address="http://localhost:8000", open_access_token="my_token")

async with AsyncPylonClient(config) as client:
    # Client is open and ready to use
    ...
# Client is automatically closed here
```

Using the client outside a context manager will raise `PylonClosed` exception.

Alternatively, you can call `open()` and `close()` methods directly, but then you are
responsible for closing the client yourself.

### Making Requests

Once the client is open, you can make requests using the
[Open Access API](#open-access-api-clientopen_access) and
[Identity API](#identity-api-clientidentity).

**Open Access API** - for read-only operations on any subnet:

```python
from pylon_client.v1 import AsyncPylonClient, AsyncConfig, NetUid

config = AsyncConfig(address="http://localhost:8000", open_access_token="my_token")

async with AsyncPylonClient(config) as client:
    response = await client.open_access.get_latest_neurons(netuid=NetUid(1))
    print(f"Found {len(response.neurons)} neurons")
```

**Identity API** - for operations on the subnet associated with the configured identity:

```python
from pylon_client.v1 import AsyncPylonClient, AsyncConfig, Hotkey, Weight

config = AsyncConfig(
    address="http://localhost:8000",
    identity_name="sn1",
    identity_token="my_secret_token",
)

async with AsyncPylonClient(config) as client:
    # Read neurons for the identity's subnet
    response = await client.identity.get_latest_neurons()

    # Set weights
    weights = {Hotkey("5C..."): Weight(0.5), Hotkey("5D..."): Weight(0.3)}
    await client.identity.put_weights(weights=weights)
```

### Synchronous Client

For synchronous code, use `PylonClient` with `Config`:

```python
from pylon_client.v1 import PylonClient, Config, NetUid

config = Config(address="http://localhost:8000", open_access_token="my_token")

with PylonClient(config) as client:
    response = client.open_access.get_latest_neurons(netuid=NetUid(1))
    print(f"Found {len(response.neurons)} neurons")
```

## Versioning

The client library uses versioned packages to ensure backward compatibility. All objects
are exported under versioned modules (e.g., `pylon_client.v1`). If breaking changes need
to be introduced, they will be exported under a new version (e.g., `v2`, `v3`), while the
previous version remains unchanged. This allows us to deploy seemingly breaking changes without
bumping up the package major version and therefore not breaking existing clients. The aim of this
is to support older clients, providing them fixes and improvements, without maintaining separate branches.

Current newest version: `v1` (import from `pylon_client.v1`)

## API Reference

### Open Access API (`client.open_access`)

To use these methods you might need to provide open access token via client config,
depending on the service configuration.

Target subnet is chosen based on the netuid passed to the method via the argument.

| Method | Description |
|--------|-------------|
| `get_latest_neurons(netuid)` | Get neurons at latest block |
| `get_neurons(netuid, block_number)` | Get neurons at specific block |
| `get_commitments(netuid)` | Get all commitments for the subnet |
| `get_commitment(netuid, hotkey)` | Get commitment for specific hotkey |

### Identity API (`client.identity`)

To use these methods you must provide the identity name and token via client config.

The operations will be performed on the subnet associated with the identity
for which the client is configured.

| Method | Description |
|--------|-------------|
| `get_latest_neurons()` | Get neurons at latest block |
| `get_neurons(block_number)` | Get neurons at specific block |
| `put_weights(weights)` | Submit weights to subnet (with automatic retries until end of epoch) |
| `get_commitments()` | Get all commitments for the subnet |
| `get_commitment(hotkey)` | Get commitment for specific hotkey |
| `set_commitment(commitment)` | Set commitment on-chain |

## Retries

The client automatically retries failed requests. Default behavior:
- 3 attempts maximum
- Exponential backoff with jitter (0.1s base, 0.2s jitter)

### Custom Retry Configuration

Pylon client uses [tenacity](https://tenacity.readthedocs.io/en/latest/) as its retry backend.
You can customize the retry behavior by passing a `retry` parameter to the config.

The `retry` parameter accepts a `tenacity.Retrying` (sync) or `tenacity.AsyncRetrying` (async)
instance. For convenience, use the provided `DEFAULT_RETRIES` or `ASYNC_DEFAULT_RETRIES` objects
and call `.copy()` to create a modified version.

Common tenacity options:
- `stop` - When to stop retrying (e.g., `stop_after_attempt(5)`, `stop_after_delay(30)`)
- `wait` - How long to wait between retries (e.g., `wait_fixed(1)`, `wait_random(0.1, 0.5)`,
  `wait_exponential()`)

> **Note:** It is discouraged to change the `retry` parameter of `tenacity.Retrying` object
> (which controls which exceptions to retry on). The default configuration ensures retries only
> happen in appropriate circumstances. Modifying this may cause retries on non-retryable errors
> or skip retries when they are needed.

See the [tenacity documentation](https://tenacity.readthedocs.io/en/latest/) for the full list
of available options.

**Example: Retry up to 5 times with random wait:**

```python
from pylon_client.v1 import AsyncConfig, ASYNC_DEFAULT_RETRIES
from tenacity import stop_after_attempt, wait_random

config = AsyncConfig(
    address="http://localhost:8000",
    open_access_token="token",
    retry=ASYNC_DEFAULT_RETRIES.copy(
        wait=wait_random(min=0.1, max=0.3),
        stop=stop_after_attempt(5),
    )
)
```

### Disable Retries (for testing)

```python
from pylon_client.v1 import AsyncConfig, ASYNC_DEFAULT_RETRIES
from tenacity import stop_after_attempt

config = AsyncConfig(
    address="http://localhost:8000",
    open_access_token="token",
    retry=ASYNC_DEFAULT_RETRIES.copy(stop=stop_after_attempt(1))
)
```

## Exception Handling

Pylon client may throw the following exceptions:

```
BasePylonException
├── PylonRequestException      # Network/connection errors
├── PylonResponseException     # Server response errors
│   ├── PylonUnauthorized      # Trying to access the server with no credentials passed.
│   └── PylonForbidden         # Trying to access the resource with no permissions.
├── PylonClosed                # Trying to use closed client instance.
└── PylonMisconfigured         # Invalid client configuration
```

**Example:**

```python
from pylon_client.v1 import AsyncPylonClient, AsyncConfig, NetUid, PylonRequestException

config = AsyncConfig(address="http://localhost:8000", open_access_token="my_token")

async with AsyncPylonClient(config) as client:
    try:
        response = await client.open_access.get_latest_neurons(netuid=NetUid(1))
    except PylonRequestException:
        print("Network or connection error")
```

## Data Types

The client provides strongly-typed [pydantic](https://docs.pydantic.dev/latest/) models
for all Bittensor data:

```python
from pylon_client.v1 import (
    # Core types
    Hotkey, Coldkey, BlockNumber, NetUid, Weight,

    # Models
    Block, Neuron, AxonInfo, Stakes,

    # Responses
    GetNeuronsResponse,
)
```
