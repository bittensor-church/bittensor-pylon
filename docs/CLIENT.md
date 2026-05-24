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
| `timeout` | Timeout configuration (see [Timeouts](#timeouts) section) | No |

*`identity_name` and `identity_token` must both be provided together or not at all.

Most parameters can also be set via a `PYLON_CLIENT_<FIELD>` environment variable (read from the
process environment), e.g. `PYLON_CLIENT_NEURONS_FILE` or `PYLON_CLIENT_OPEN_ACCESS_TOKEN`. Values
passed explicitly to the config take precedence over the environment.

Nested fields inside `timeout` use `__` as a delimiter:

```bash
PYLON_CLIENT_TIMEOUT__READ=120.0
PYLON_CLIENT_TIMEOUT__CONNECT=10.0
PYLON_CLIENT_TIMEOUT__WRITE=10.0
PYLON_CLIENT_TIMEOUT__POOL=10.0
```

> **Note:** `retry` cannot be set via environment variable — it is a tenacity object that must be
> configured in code. See the [Retries](#retries) section.


**Open access configuration:**
```python
from pylon_client.artanis import AsyncConfig

config = AsyncConfig(
    address="http://localhost:8000",
    open_access_token="my_token",
)
```

**Identity access configuration:**
```python
from pylon_client.artanis import AsyncConfig

config = AsyncConfig(
    address="http://localhost:8000",
    identity_name="sn1",
    identity_token="my_secret_token",
)
```

**Both access modes:**
```python
from pylon_client.artanis import AsyncConfig

config = AsyncConfig(
    address="http://localhost:8000",
    open_access_token="my_open_token",
    identity_name="sn1",
    identity_token="my_identity_token",
)
```

### Authentication Flow

Authentication depends on which API you use — `client.v1.open_access` or
`client.v1.identity`. Here is how a request flows through the client:

```
 You call an API method
 e.g. client.v1.identity.get_latest_neurons()
          │
          ▼
 API layer creates an AuthenticatedPylonRequest
 with netuid and identity_name (or None for open access)
          │
          ▼
 HttpTranslator receives the request and checks identity_name
          │
          ├─ identity_name is set ──────────────────────────┐
          │  • URL: /api/v1/identity/{name}/subnet/{netuid}/...
          │  • Header: Authorization: Bearer {identity_token}
          │                                                 │
          ├─ identity_name is None ─────────────────────────┤
          │  • URL: /api/v1/subnet/{netuid}/...             │
          │  • Header: Authorization: Bearer {open_access_token}
          │                                                 │
          ▼                                                 ▼
                      HTTP request is sent
```

So the `identity_name` field on the request object is what drives the difference —
the translator sees it and picks the matching token from the config and the
matching URL structure.

When using `client.v1.open_access`, the API layer sets `identity_name=None` and
you pass `netuid` explicitly to each method. When using `client.v1.identity`, the
API layer sets `identity_name` from the config and resolves `netuid` automatically
from the server (cached after the first request).

### Creating the Client

The client is available in two variants:
- `PylonClient` with `Config` - synchronous client
- `AsyncPylonClient` with `AsyncConfig` - asynchronous client

The client should be used as a context manager to ensure proper resource management.
The connection pool is opened when entering the context and closed when exiting.

```python
from pylon_client.artanis import AsyncPylonClient, AsyncConfig

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
from pylon_client.artanis import AsyncPylonClient, AsyncConfig, NetUid

config = AsyncConfig(address="http://localhost:8000", open_access_token="my_token")

async with AsyncPylonClient(config) as client:
    response = await client.v1.open_access.get_latest_neurons(netuid=NetUid(1))
    print(f"Found {len(response.neurons)} neurons")
```

**Identity API** - for operations on the subnet associated with the configured identity:

```python
from pylon_client.artanis import AsyncPylonClient, AsyncConfig, Hotkey, Weight

config = AsyncConfig(
    address="http://localhost:8000",
    identity_name="sn1",
    identity_token="my_secret_token",
)

async with AsyncPylonClient(config) as client:
    # Read neurons for the identity's subnet
    response = await client.v1.identity.get_latest_neurons()

    # Set weights
    weights = {Hotkey("5C..."): Weight(0.5), Hotkey("5D..."): Weight(0.3)}
    await client.v1.identity.put_weights(weights=weights)
```

### Synchronous Client

For synchronous code, use `PylonClient` with `Config`:

```python
from pylon_client.artanis import PylonClient, Config, NetUid

config = Config(address="http://localhost:8000", open_access_token="my_token")

with PylonClient(config) as client:
    response = client.v1.open_access.get_latest_neurons(netuid=NetUid(1))
    print(f"Found {len(response.neurons)} neurons")
```

## Versioning

See the [Versioning documentation](VERSIONS.md) for details on package versioning,
client interface versioning, and API version namespaces.

## Using Different API Versions

By default, the client communicates with the latest stable API version (v1).
To use the unstable API, access methods through the `client.unstable` namespace:

```python
from pylon_client.artanis import AsyncPylonClient, AsyncConfig, NetUid

async with AsyncPylonClient(config) as client:
    # V1 API (default)
    response = await client.v1.open_access.get_latest_neurons(netuid=NetUid(1))
    response = await client.v1.identity.get_commitments()

    # Unstable API
    response = await client.unstable.open_access.get_latest_neurons(netuid=NetUid(1))
    response = await client.unstable.identity.get_commitments()
```

> **Note:** The unstable API may change with breaking modifications in any release.
> See the [Versioning documentation](VERSIONS.md#unstable-api) for details.

## API Reference

### Open Access API (`client.v1.open_access`)

To use these methods you might need to provide open access token via client config,
depending on the service configuration.

Target subnet is chosen based on the netuid passed to the method via the argument.

| Method                                     | Description                                              |
|--------------------------------------------|----------------------------------------------------------|
| `get_latest_neurons(netuid)`               | Get neurons at latest block                              |
| `get_neurons(netuid, block_number)`        | Get neurons at specific block                            |
| `get_recent_neurons(netuid)`               | Get cached neurons (fast, may be slightly behind latest) |
| `get_latest_validators(netuid)`            | Get validators at latest block                           |
| `get_validators(netuid, block_number)`     | Get validators at specific block                         |
| `get_commitments(netuid)`                  | Get all commitments for the subnet                       |
| `get_commitment(netuid, hotkey)`           | Get commitment for specific hotkey                       |
| `get_all_revealed_commitments(netuid)`     | Get all revealed commitments for the subnet              |
| `get_revealed_commitments(netuid, hotkey)` | Get revealed commitments for specific hotkey             |

### Identity API (`client.v1.identity`)

To use these methods you must provide the identity name and token via client config.

The operations will be performed on the subnet associated with the identity
for which the client is configured.

| Method                                                     | Description                                                          |
|------------------------------------------------------------|----------------------------------------------------------------------|
| `get_latest_neurons()`                                     | Get neurons at latest block                                          |
| `get_neurons(block_number)`                                | Get neurons at specific block                                        |
| `get_recent_neurons()`                                     | Get cached neurons (fast, may be slightly behind latest)             |
| `get_latest_validators()`                                  | Get validators at latest block                                       |
| `get_validators(block_number)`                             | Get validators at specific block                                     |
| `put_weights(weights, mechanism_id)`                       | Submit weights to subnet (with automatic retries until end of epoch) |
| `get_commitments()`                                        | Get all commitments for the subnet                                   |
| `get_commitment(hotkey)`                                   | Get commitment for specific hotkey                                   |
| `get_own_commitment()`                                     | Get commitment for identity's own wallet                             |
| `set_commitment(commitment)`                               | Set commitment on-chain                                              |
| `get_all_revealed_commitments()`                           | Get all revealed commitments for the subnet                          |
| `get_revealed_commitments(hotkey)`                         | Get revealed commitments for specific hotkey                         |
| `get_own_revealed_commitments()`                           | Get revealed commitments for identity's own wallet                   |
| `set_revealed_commitment(commitment, blocks_until_reveal)` | Set revealed commitment on-chain                                     |

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
from pylon_client.artanis import AsyncConfig, ASYNC_DEFAULT_RETRIES
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
from pylon_client.artanis import AsyncConfig, ASYNC_DEFAULT_RETRIES
from tenacity import stop_after_attempt

config = AsyncConfig(
    address="http://localhost:8000",
    open_access_token="token",
    retry=ASYNC_DEFAULT_RETRIES.copy(stop=stop_after_attempt(1))
)
```

## Timeouts

The client enforces timeouts on all requests. The default timeout configuration is:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `connect` | Timeout for establishing a connection | `5.0s` |
| `read` | Timeout for receiving a response | `60.0s` |
| `write` | Timeout for sending the request body | `5.0s` |
| `pool` | Timeout for acquiring a connection from the pool | `5.0s` |

The `read` timeout is the most relevant for API calls -- it controls how long the client
waits for the server to respond. When a request times out, a `PylonTimeoutException` is raised.

The client automatically sends an `X-Pylon-Timeout` header derived from the `read` timeout
(reduced by a small buffer) so that the server can abort processing before the client times out,
returning a `504 Gateway Timeout` response instead. Both client-side timeouts and server 504
responses raise `PylonTimeoutException` and are retried automatically.

### Custom Timeout Configuration

```python
from pylon_client.artanis import AsyncConfig, PylonTimeout

config = AsyncConfig(
    address="http://localhost:8000",
    open_access_token="token",
    timeout=PylonTimeout(read=120.0),
)
```

You only need to specify the fields you want to override; the rest will use defaults.

## Exception Handling

Pylon client may throw the following exceptions:

```
BasePylonException
├── PylonRequestException      # Network/connection errors
│   └── PylonTimeoutException  # Request timed out (client-side or 504 gateway timeout)
├── PylonResponseException     # Server response errors
│   ├── PylonUnauthorized      # Trying to access the server with no credentials passed.
│   └── PylonForbidden         # Trying to access the resource with no permissions.
├── PylonClosed                # Trying to use closed client instance.
└── PylonMisconfigured         # Invalid client configuration
```

**Example:**

```python
from pylon_client.artanis import AsyncPylonClient, AsyncConfig, NetUid, PylonRequestException

config = AsyncConfig(address="http://localhost:8000", open_access_token="my_token")

async with AsyncPylonClient(config) as client:
    try:
        response = await client.v1.open_access.get_latest_neurons(netuid=NetUid(1))
    except PylonRequestException:
        print("Network or connection error")
```

## Data Types

The client provides strongly-typed [pydantic](https://docs.pydantic.dev/latest/) models
for all Bittensor data:

```python
from pylon_client.artanis import (
    # Core types
    Hotkey, Coldkey, BlockNumber, NetUid, Weight,
)
from pylon_client.artanis.v1 import (
    # Models
    Block, Neuron, AxonInfo, Stakes,

    # Responses
    GetNeuronsResponse,
)
```
