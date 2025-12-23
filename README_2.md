# Pylon

Pylon provides a convenient way to access and manipulate the state of the Bittensor chain.
It is aimed at validators and miners to make their interaction with the chain and themselves
easy and robust.

Pylon consists of two distinct parts:

- **Pylon Service** - The core HTTP service providing chain operations via a REST API
- **Pylon Client** - A Python library that wraps the service under a user-friendly, pythonic API

## Quick Start

1. Create a `.env` file with basic configuration:

    ```bash
    # .env
    PYLON_BITTENSOR_NETWORK=finney
    PYLON_BITTENSOR_WALLET_PATH=/root/.bittensor/wallets
    PYLON_OPEN_ACCESS_TOKEN=my_open_access_token
    ```

2. Run the Pylon service:

    ```bash
    docker pull backenddevelopersltd/bittensor-pylon:latest
    docker run -d --env-file .env -p 8000:8000 backenddevelopersltd/bittensor-pylon:latest
    ```

3. Query the Subtensor via Pylon using the Python client:

    ```python
    import asyncio
    from pylon_client.v1 import AsyncPylonClient, AsyncConfig, NetUid

    async def main():
        config = AsyncConfig(
            address="http://localhost:8000",
            open_access_token="my_open_access_token",
        )
        async with AsyncPylonClient(config) as client:
            response = await client.open_access.get_latest_neurons(netuid=NetUid(1))
            print(f"Block: {response.block.number}, Neurons: {len(response.neurons)}")

    asyncio.run(main())
    ```

4. ...or use any HTTP client:

    ```bash
    curl -X GET "http://localhost:8000/api/v1/subnet/1/block/latest/neurons" \
         -H "Authorization: Bearer my_open_access_token"
    ```

The above basic configuration allows you to perform read operations.
To perform write operations like setting weights, you need to configure an identity:

```bash
# .env
PYLON_BITTENSOR_NETWORK=finney
PYLON_BITTENSOR_WALLET_PATH=/root/.bittensor/wallets
PYLON_IDENTITIES=["sn1"]
PYLON_ID_SN1_WALLET_NAME=my_wallet
PYLON_ID_SN1_HOTKEY_NAME=my_hotkey
PYLON_ID_SN1_NETUID=1
PYLON_ID_SN1_TOKEN=my_secret_token
```

After that, operations like setting weights are just one method call away:

```python
import asyncio
from pylon_client.v1 import AsyncPylonClient, AsyncConfig, Hotkey, Weight

async def main():
    config = AsyncConfig(
        address="http://localhost:8000",
        identity_name="sn1",
        identity_token="my_secret_token",
    )
    async with AsyncPylonClient(config) as client:
        weights = {Hotkey("5C..."): Weight(0.5), Hotkey("5D..."): Weight(0.3)}
        await client.identity.put_weights(weights=weights)

asyncio.run(main())
```

---

# Pylon Service

Pylon service provides an HTTP API that simplifies communication with subtensor.
It makes subtensor queries and operations on behalf of a neuron.
The benefits of using Pylon service are:

- **Simplicity** - Complex subtensor operations like setting weights made easy via one API call
- **Safety** - Your hotkey is visible only to a small, easily verifiable software component
- **Durability** - Automatic handling of connection pooling, retries, and commit-reveal cycles
- **Convenience** - Easy to use Python client provided
- **Flexibility** - Query the HTTP API with any language you like

## Access Modes

Pylon Service supports two access patterns:

### Open Access

Open access mode can be used to query the subtensor without presenting any hotkey.
It gives access to subtensor data like neurons or hyperparams,
but does not allow write operations.

Open access endpoints may require authentication via `open_access_token`,
depending on service configuration.

Open access endpoints follow the pattern `/api/v1/subnet/{netuid}/...` and do not require
an identity. See the full list at `/schema/swagger` when the service is running.

### Identity Access

Identity is a combination of a Bittensor wallet and a subnet.
Identities are named and defined in the Pylon Service configuration.
Each identity is protected by its own secret token.

When authenticated with an identity token, Pylon uses the wallet defined in the identity
to perform all operations on the associated subnet.

Identity endpoints follow the pattern `/api/v1/identity/{identity_name}/subnet/{netuid}/...`.
See the full list at `/schema/swagger` when the service is running.

> **Note:** Output of respective open-access and identity endpoints may differ slightly,
> as data can depend on the hotkey presented. Axon info is a good example of this.

## Configuration

All configuration is done via environment variables with the `PYLON_` prefix.
Create a `.env` file and pass it to the Docker container using `--env-file .env`.

### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `PYLON_BITTENSOR_NETWORK` | Bittensor network (e.g., `finney` or `ws://127.0.0.1:9944`) | `finney` |
| `PYLON_BITTENSOR_ARCHIVE_NETWORK` | Archive network for historical data | `archive` |
| `PYLON_BITTENSOR_ARCHIVE_BLOCKS_CUTOFF` | Blocks threshold for switching to archive network | `300` |
| `PYLON_BITTENSOR_WALLET_PATH` | Path to wallet directory | **required** |

### Access Control

| Variable | Description | Default |
|----------|-------------|---------|
| `PYLON_OPEN_ACCESS_TOKEN` | Token for open access endpoints (empty = no auth required) | `""` |
| `PYLON_IDENTITIES` | JSON list of identity names to configure | `[]` |

### Identity Configuration

For each identity listed in `PYLON_IDENTITIES`, configure these variables
(replace `{NAME}` with uppercase identity name):

| Variable | Description |
|----------|-------------|
| `PYLON_ID_{NAME}_WALLET_NAME` | Wallet name (coldkey) |
| `PYLON_ID_{NAME}_HOTKEY_NAME` | Hotkey name |
| `PYLON_ID_{NAME}_NETUID` | Subnet UID |
| `PYLON_ID_{NAME}_TOKEN` | Authentication token for this identity |

**Example:**

```bash
# .env
PYLON_IDENTITIES=["sn12", "sn89"]
PYLON_BITTENSOR_WALLET_PATH=~/.bittensor/wallets

# Identity: sn12
PYLON_ID_SN12_WALLET_NAME=sn12_wallet
PYLON_ID_SN12_HOTKEY_NAME=sn12_hotkey
PYLON_ID_SN12_NETUID=12
PYLON_ID_SN12_TOKEN=8GOqUEjyTuYXER790bm8LpSmOIDuPvbr

# Identity: sn89
PYLON_ID_SN89_WALLET_NAME=sn89_wallet
PYLON_ID_SN89_HOTKEY_NAME=sn89_hotkey
PYLON_ID_SN89_NETUID=89
PYLON_ID_SN89_TOKEN=IEYAWl9rPQAMTV0hqAKAaQtEYqqKws5z
```

### Retry Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `PYLON_WEIGHTS_RETRY_ATTEMPTS` | Max retry attempts for weight submission | `200` |
| `PYLON_WEIGHTS_RETRY_DELAY_SECONDS` | Delay between retries in seconds | `1` |
| `PYLON_COMMITMENT_RETRY_ATTEMPTS` | Max retry attempts for commitment submission | `10` |
| `PYLON_COMMITMENT_RETRY_DELAY_SECONDS` | Delay between commitment retries in seconds | `1` |

### Monitoring

| Variable | Description | Default |
|----------|-------------|---------|
| `PYLON_METRICS_TOKEN` | Token for `/metrics` endpoint (empty = 403 Forbidden) | `""` |
| `PYLON_SENTRY_DSN` | Sentry DSN for error tracking | `""` |
| `PYLON_SENTRY_ENVIRONMENT` | Sentry environment name | `development` |

## Deployment

The recommended way to run Pylon service is via Docker.
Make sure your `.env` file and wallet directory are accessible to the container.

### Docker

```bash
docker pull backenddevelopersltd/bittensor-pylon:latest
docker run -d \
    --env-file .env \
    -v ~/.bittensor/wallets/:/root/.bittensor/wallets \
    backenddevelopersltd/bittensor-pylon:latest
```

### Docker Compose

Create a `docker-compose.yaml` file:

```yaml
services:
  pylon:
    image: backenddevelopersltd/bittensor-pylon:latest
    restart: unless-stopped
    env_file: ./.env
    volumes:
      - ~/.bittensor/wallets/:/root/.bittensor/wallets
```

Run with:

```bash
docker compose up -d
```

## Observability

### Prometheus Metrics

The service exposes Prometheus metrics at `/metrics` endpoint,
protected with Bearer token authentication.

**Configuration:**

```bash
PYLON_METRICS_TOKEN=your-secure-metrics-token
```

**Access:**

```bash
curl http://localhost:8000/metrics -H "Authorization: Bearer your-secure-metrics-token"
```

**Available Metrics:**

*HTTP API Metrics:*

| Metric | Type | Description |
|--------|------|-------------|
| `pylon_requests_total` | Counter | Total number of HTTP requests |
| `pylon_request_duration_seconds` | Histogram | HTTP request duration |
| `pylon_requests_in_progress` | Gauge | HTTP requests currently being processed |

All HTTP metrics include labels: `method`, `path`, `status_code`, `app_name`.

*Bittensor Operations Metrics:*

| Metric | Type | Description |
|--------|------|-------------|
| `pylon_bittensor_operation_duration_seconds` | Histogram | Duration of Bittensor operations |
| `pylon_bittensor_fallback_total` | Counter | Archive client fallback events |

Labels: `operation`, `status`, `uri`, `netuid`, `hotkey`, `reason`.

*ApplyWeights Job Metrics:*

| Metric | Type | Description |
|--------|------|-------------|
| `pylon_apply_weights_job_duration_seconds` | Histogram | Duration of entire ApplyWeights job |
| `pylon_apply_weights_attempt_duration_seconds` | Histogram | Duration of individual weight attempts |

Labels: `operation`, `status`, `netuid`, `hotkey`.

*Python Runtime Metrics:*
Standard Python process metrics are also exposed: memory usage, CPU time,
garbage collection stats, and file descriptors.

> **Tip:** Set `PROMETHEUS_DISABLE_CREATED_SERIES=True` to disable automatic `*_created`
> gauge metrics and reduce metrics output.

---

# Pylon Client

Pylon client is a Python library for interacting with Pylon service.
All API endpoints are wrapped into easy-to-use Python methods with features like
authentication, retries, and connection pools built in.

## Installation

```bash
pip install pylon-client
```

## Basic Usage

The client is designed to be used as a context manager. This ensures proper resource
management - the HTTP connection pool is opened when entering the context and closed
when exiting. Always use the client within a `with` (sync) or `async with` (async) block.
Using the client outside a context manager will raise `PylonClosed` exception.

Alternatively, you can call `open()` and `close()` methods directly, but then you are
responsible for closing the client yourself.

### Synchronous Client

```python
from pylon_client.v1 import PylonClient, Config, NetUid

with PylonClient(
    Config(
       address="http://localhost:8000",
       open_access_token="my_token",
    )
) as client:
    response = client.open_access.get_latest_neurons(netuid=NetUid(1))
    for hotkey, neuron in response.neurons.items():
        print(f"{hotkey}: rank={neuron.rank}, stake={neuron.stake}")
 # Client is automatically closed here
```

### Asynchronous Client

```python
import asyncio
from pylon_client.v1 import AsyncPylonClient, AsyncConfig, NetUid

async def main():
    async with AsyncPylonClient(AsyncConfig(
        address="http://localhost:8000",
        open_access_token="my_token",
    )) as client:
        response = await client.open_access.get_latest_neurons(netuid=NetUid(1))
        print(f"Found {len(response.neurons)} neurons")
    # Client is automatically closed here

asyncio.run(main())
```

## Configuration

The client instance is configured by the passed `Config` (or `AsyncConfig`) object.

### Config Parameters

| Parameter | Description                                                | Required |
|-----------|------------------------------------------------------------|----------|
| `address` | Pylon service URL (e.g., `http://localhost:8000`)          | Yes |
| `open_access_token` | Token for open access endpoints                            | No |
| `identity_name` | Identity name for authenticated operations                 | No* |
| `identity_token` | Token for the specified identity                           | No* |
| `retry` | Retry configuration (tenacity object, see Retries chapter) | No |

*`identity_name` and `identity_token` must both be provided together or not at all.

### Example Configurations

**Open access only:**
```python
config = AsyncConfig(
    address="http://localhost:8000",
    open_access_token="my_token",
)
```

**Identity access only:**
```python
config = AsyncConfig(
    address="http://localhost:8000",
    identity_name="sn1",
    identity_token="my_secret_token",
)
```

**Both access modes:**
```python
config = AsyncConfig(
    address="http://localhost:8000",
    open_access_token="my_open_token",
    identity_name="sn1",
    identity_token="my_identity_token",
)
```

## Available Methods

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

The operations will be performed on the subnet associated with the identity for which the client is configured.

| Method | Description |
|--------|-------------|
| `get_latest_neurons()` | Get neurons at latest block |
| `get_neurons(block_number)` | Get neurons at specific block |
| `put_weights(weights)` | Submit weights to subnet |
| `get_commitments()` | Get all commitments for the subnet |
| `get_commitment(hotkey)` | Get commitment for specific hotkey |
| `set_commitment(commitment)` | Set commitment on-chain |

## Retries

The client automatically retries failed requests. Default behavior:
- 3 attempts maximum
- Exponential backoff with jitter (0.1s base, 0.2s jitter)

### Custom Retry Configuration

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

## Data Types

The client provides strongly-typed [pydantic](https://docs.pydantic.dev/latest/) models for all Bittensor data:

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

# Development

## Setup

```bash
# Install dependencies
uv sync --extra dev

# Create test environment
cp pylon_client/service/envs/test_env.template .env
```

## Running Tests

```bash
nox -s test                    # Run all tests
nox -s test -- -k "test_name"  # Run specific test
```

## Code Quality

```bash
nox -s format                  # Format and lint code
```

## Local Development Server

```bash
uvicorn pylon_client.service.main:app --reload --host 127.0.0.1 --port 8000
```
