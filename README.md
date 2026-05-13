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
    from pylon_client.artanis import AsyncPylonClient, AsyncConfig, NetUid

    async def main():
        config = AsyncConfig(
            address="http://localhost:8000",
            open_access_token="my_open_access_token",
        )
        async with AsyncPylonClient(config) as client:
            response = await client.v1.open_access.get_latest_neurons(netuid=NetUid(1))
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
from pylon_client.artanis import AsyncPylonClient, AsyncConfig, Hotkey, Weight

async def main():
    config = AsyncConfig(
        address="http://localhost:8000",
        identity_name="sn1",
        identity_token="my_secret_token",
    )
    async with AsyncPylonClient(config) as client:
        weights = {Hotkey("5C..."): Weight(0.5), Hotkey("5D..."): Weight(0.3)}
        await client.v1.identity.put_weights(weights=weights)

asyncio.run(main())
```

## Documentation

- **[Pylon Documentation](docs/SERVICE.md)** - Configuration, deployment, and observability
- **[Pylon Client Documentation](docs/CLIENT.md)** - Installation, usage, and API reference
- **[Versioning](docs/VERSIONS.md)** - Package versioning, API versioning, and migration guide

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

The client re-exports common objects through `pylon_client.artanis`:
```python
from pylon_client.artanis import Hotkey
from pylon_client.artanis.v1 import Block, Neuron
```

### Setup

```bash
# Install dependencies for a specific package
cd pylon_client && uv sync --group dev

# Create test environment
cp pylon_service/envs/test_env.template .env
```

### Running Tests

Tests can be run separately for every project or collectively using root noxfile.

```bash
nox -s test                    # Run all tests
nox -s test -- -k "test_name"  # Run specific test
```

### Pact Tests

Pact tests verify the contract between the client and service. The client tests generate pact files
that are then verified by the service tests.

```bash
# Step 1: Run client pact tests (generates pact files)
cd pylon_client && nox -s test-pact

# Step 2: Run service pact tests (verifies pact files)
cd pylon_service && nox -s test-pact
```

The client pact tests must be run first to generate the pact files in `pylon_client/tests/pact/pacts/`.
The service pact tests will fail if the pact files do not exist.

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
```
uv run python -m pylon_service.uvicorn_entrypoint
```

### Release

Releases are managed with [`release-toolkit`](https://github.com/reef-technologies/release-toolkit)
(a [commitizen](https://commitizen-tools.github.io/commitizen/) plugin with `impacts_cz` rule).
The two products — `pylon_client` and `pylon_service` — release independently, each with its own
git tag prefix, `CHANGELOG.md`, and CI workflow. Versions are derived from git tags using `hatch-vcs`,
so there are no version files in the code.

#### Conventional commits with impacts

Every commit on `master` must follow the [Conventional Commits](https://www.conventionalcommits.org/)
specification, with an `impacts:` trailer declaring which products it affects:

```
feat: add neuron caching

impacts: client, service
```

Allowed impacts are `client`, `service`, and `commons`. The trailer drives which `CHANGELOG.md`
(under `pylon_client/` or `pylon_service/`) the entry lands in when bumping. Commits without an
`impacts:` trailer are ignored by the changelog generator.

The `commons` impact is special: since `pylon_commons` is shared between client and service
(vendored into the client, used as an editable dependency by the service), commits with
`impacts: commons` land in **both** changelogs and contribute to the version increment of both
products. This is implemented by listing `commons` alongside the package's own tag in each
package's `[tool.commitizen] impacts` setting (`["client", "commons"]` for the client and
`["service", "commons"]` for the service). A commit can mix tags freely, e.g.
`impacts: client, commons` or `impacts: service, commons, client`.

#### Cutting a release

Run `rt release` from the package directory you want to release. The command:

1. Syncs the environment with `uv sync`.
2. Runs the project's checks.
3. Computes the changelog-filtered version increment from commits whose `impacts:` trailer
   matches the package, then invokes `cz bump` to update `CHANGELOG.md`, create a `bump:`
   commit and an annotated tag (`client-v<version>` or `service-v<version>`).
4. Pushes the bump commit and the new tag to `origin/master`.

It aborts if the working tree is dirty or there are no releasable commits, and prompts for
confirmation when run from a branch other than `master`.

```bash
# Release the client
cd pylon_client && rt release

# Release the service
cd pylon_service && rt release

# Dry-run (forwards --dry-run to cz bump):
rt release -- --dry-run
```

Pushing the tag triggers the matching GitHub Actions workflow:

| Tag pattern    | Workflow                              | Publishes to                                            |
|----------------|---------------------------------------|---------------------------------------------------------|
| `client-v*`    | `.github/workflows/release-client.yml`  | PyPI (`bittensor-pylon-client`)                          |
| `service-v*`   | `.github/workflows/release-service.yml` | Docker Hub (`backenddevelopersltd/bittensor-pylon`)      |

After publishing, both workflows call `release-toolkit`'s `release-notify` reusable workflow, which
creates a GitHub Release with the changelog section for the new version and posts a notification to
Slack.
