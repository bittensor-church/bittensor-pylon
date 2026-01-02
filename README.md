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

### Setup

```bash
# Install dependencies
uv sync --extra dev

# Create test environment
cp pylon_client/service/envs/test_env.template .env
```

### Running Tests

```bash
nox -s test                    # Run all tests
nox -s test -- -k "test_name"  # Run specific test
```

### Code Quality

```bash
nox -s format                  # Format and lint code
```

### Local Development Server

```bash
uvicorn pylon_client.service.main:app --reload --host 127.0.0.1 --port 8000
```

### Release

These commands will create and push the appropriate git tags on master to trigger the deployment.

```bash
nox -s release-client
nox -s release-service
```
