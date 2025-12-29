# Pylon

Pylon provides a convenient way to access and manipulate the state of the Bittensor chain.
It is aimed at validators and miners to make their interaction with the chain and themselves
easy and robust.

Pylon consists of two distinct parts:

- **[Pylon Service](docs/SERVICE.md)** - The core HTTP service providing chain operations via a REST API
- **[Pylon Client](docs/CLIENT.md)** - A Python library that wraps the service under a user-friendly, pythonic API

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

## Documentation

- **[Pylon Service Documentation](docs/SERVICE.md)** - Configuration, deployment, and observability
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
