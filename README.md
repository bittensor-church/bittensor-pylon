# Pylon

Pylon is a high-performance HTTP service that provides fast, cached access to the Bittensor blockchain.
It is designed to be used by validators, miners, and other actors like indexers,
allowing them to interact with the Bittensor network without direct blockchain calls
or installing any blockchain-related libraries.

The benefits of using Pylon are:

- **Simplicity** - Complex subtensor operations like setting weights made easy via one API call
- **Safety** - Your hotkey is visible only to a small, easily verifiable software component
- **Durability** - Automatic handling of connection pooling, retries, and commit-reveal cycles
- **Convenience** - Easy to use Python client provided
- **Flexibility** - Query the HTTP API with any language you like

## Components

- **[Pylon](docs/SERVICE.md)** - The HTTP service itself, can be interacted with using any HTTP client
- **[Pylon Client](docs/CLIENT.md)** - An optional Python library for convenient programmatic access

## Quick Start

1. Create a `.env` file with basic configuration:

    ```bash
    # .env
    PYLON_OPEN_ACCESS_TOKEN=my_open_access_token
    ```

2. Run Pylon:

    ```bash
    docker run -d \
        --env-file .env \
        -v ~/.bittensor/wallets:/root/.bittensor/wallets \
        -p 8000:8000 \
        backenddevelopersltd/bittensor-pylon:latest
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
To perform write operations like setting weights, you need to configure an identity.

Since Pylon can support multiple neurons at once (possibly in multiple subnets), identities were introduced.
Think of identities as user credentials: they have names, passwords (tokens), and are attached to a single
wallet and netuid. Here's an example showing how to configure a single identity. Notice that `sn1` is an
arbitrary identity name and appears in several environment variable names (e.g. `PYLON_ID_SN1_WALLET_NAME`):

```bash
# .env
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

## Documentation

- **[Pylon Documentation](docs/SERVICE.md)** - Configuration, deployment, and observability
- **[Pylon Client Documentation](docs/CLIENT.md)** - Installation, usage, and API reference

## Development

### Monorepo Structure

This repository is organized as a monorepo with three packages:

| Package | PyPI Name | Description |
|---------|-----------|-------------|
| `pylon_commons` | - | Shared types, models, and utilities (vendored into client at build time) |
| `pylon_client` | `bittensor-pylon-client` | Python client library for the Pylon API |
| `pylon_service` | - | REST API service (distributed as Docker image) |

### pylon_commons Vendoring

The `pylon_commons` package is shared between client and service but is not published to PyPI.
Instead, it is vendored into `pylon_client` via a symlink at `pylon_client/_internal/pylon_commons`.

- **In development**: The symlink points to `pylon_commons`, so changes are reflected immediately
- **In release**: The symlink contents are copied into the wheel at build time

The client re-exports common objects through `pylon_client.v1`:
```python
from pylon_client.v1 import Hotkey, Block, Neuron
```

### Setup

```bash
# Install dependencies for a specific package
cd pylon_client && uv sync --extra dev

# Create test environment
cp pylon_service/envs/test_env.template .env
```

### Running Tests

Tests can be run separately for every project or collectively using root noxfile.

```bash
nox -s test                    # Run all tests
nox -s test -- -k "test_name"  # Run specific test
```

### Code Quality

Formatting can be run separately for every project or collectively using root noxfile.

```bash
nox -s format                  # Format and lint code
```

### Local Development Server

```bash
# Debug app, verbose logging, auto-reload
./pylon_service/debug-run.sh
```

or manually:

```bash
cd pylon_service

# Debug app, verbose logging, auto-reload
PYLON_DEBUG=true uv run python -m pylon_service.uvicorn_entrypoint
```



# Production-like server
uv run python -m pylon_service.uvicorn_entrypoint
```

### Release

These root-noxfile commands will create and push the appropriate git tags on master to trigger the deployment.
You may do it on any branch, but the release will always happen from the current state of origin/master.

```bash
nox -s release-client
nox -s release-service
```

You can also run this command from the project level:

```bash
nox -s release
```
