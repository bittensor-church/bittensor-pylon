# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bittensor Pylon is a high-performance, asynchronous proxy for a Bittensor subnet. It is a single unified package `pylon_client` with the following sub-packages:

- **`pylon_client.service`**: Core REST API service that connects to Bittensor network and exposes API endpoints
- **`pylon_client._internal.client`**: Lightweight Python client library for interacting with the pylon service API
- **`pylon_client._internal.common`**: Shared utilities, settings, and request/response models

## Development Commands

### Package Management
- Install dependencies: `uv sync --extra dev`
- Uses `uv` as the package manager (faster than pip)
- Build package: `uv build` (uses hatchling backend with dynamic versioning)
  - **Important**: The wheel build **excludes** `pylon_client/service/` (only client library and common code are packaged)
  - Version is dynamically read from `pylon_client/__init__.py`

### Running python commands

- Run python command: `uv run python`

### Testing
- Run all tests: `nox -s test`
- Run specific test: `nox -s test -- -k "test_name"`

### Code Quality
- Format and lint: `nox -s format`
- Uses `ruff` for formatting and linting, `pyright` for type checking
- Line length: 120 characters


### Running the Service
- Local development: `uvicorn pylon_client.service.main:app --host 0.0.0.0 --port 8000`
- Docker: `PYLON_DOCKER_IMAGE_NAME="bittensor_pylon" ./docker-run.sh`

## Architecture

The application follows a clear separation of concerns with these core components:

### Core Components
- **`pylon_client/service/bittensor/client.py`**: Manages all interactions with the Bittensor network using the `turbobt` library, including wallet operations. Provides `AbstractBittensorClient` base class and `TurboBtClient` implementation
- **`pylon_client/service/bittensor/pool.py`**: Manages `BittensorClientPool` for acquiring and sharing client instances per wallet
- **`pylon_client/service/identities.py`**: Identity system for multi-subnet/multi-wallet support with per-identity authentication
- **`pylon_client/service/api.py`**: The Litestar-based API layer that defines all external endpoints using two controllers:
  - `OpenAccessController`: Endpoints under `/subnet/{netuid}/` (requires `open_access_token`)
  - `IdentityController`: Endpoints under `/identity/{identity_name}/subnet/{netuid}` (requires per-identity token)
- **`pylon_client/service/main.py`**: The main entry point. It wires up the application, manages the startup/shutdown lifecycle
- **`pylon_client/service/tasks.py`**: Contains `ApplyWeights` task for applying weights to the subnet on-demand
- **`pylon_client/_internal/common/models.py`**: Bittensor-specific models (Block, Neuron, Certificate, SubnetHyperparams, etc.)
- **`pylon_client/_internal/common/endpoints.py`**: Endpoint path definitions using the `Endpoint` enum
- **`pylon_client/_internal/common/settings.py`**: Manages application configuration using `pydantic-settings`, loading from a `.env` file
- **`pylon_client/_internal/common/requests.py`**: Pydantic request models for API validation
- **`pylon_client/_internal/common/responses.py`**: Pydantic response models for API serialization
- **`pylon_client/_internal/client/`**: Client library implementation with both sync and async clients

### Key Dependencies
- **Web Framework**: Litestar (not FastAPI)
- **Bittensor**: `turbobt` library for blockchain interaction, `bittensor_wallet` for wallet operations
- **Config**: `pydantic-settings` with `.env` file support
- **HTTP Client**: `httpx` for async HTTP requests
- **Containerization**: Docker

### Background Tasks
- **`ApplyWeights`** (`pylon_client/service/tasks.py`): Applies weights to the subnet on-demand (triggered by PUT /subnet/weights endpoint)
  - Uses retry logic with exponential backoff (configurable: default 200 attempts, 1-second delay)
  - Handles both commit-reveal and direct weight setting based on subnet hyperparameters

## API Endpoints

All endpoints are prefixed with `/api/v1`. The API supports two access patterns:

### Access Patterns

1. **Open Access** (`/api/v1/subnet/{netuid}/...`): Read-only endpoints requiring `open_access_token` authentication
2. **Identity Access** (`/api/v1/identity/{identity_name}/subnet/{netuid}/...`): Full access requiring per-identity token authentication

### Authentication & Identities

The service supports multi-subnet/multi-wallet operations through an identity system (`pylon_client/service/identities.py`):
- Each identity has its own wallet (coldkey/hotkey pair), subnet, and authentication token
- Identities are configured via environment variables: `PYLON_ID_{IDENTITY_NAME}_*`
- Required per-identity settings: `wallet_name`, `hotkey_name`, `netuid`, `token`
- List of active identities: `PYLON_IDENTITIES` (comma-separated)
- Example: For identity "sn1", set `PYLON_ID_SN1_WALLET_NAME`, `PYLON_ID_SN1_HOTKEY_NAME`, `PYLON_ID_SN1_NETUID`, `PYLON_ID_SN1_TOKEN`

### Endpoint List

#### Authentication
- **POST `/api/v1/login/identity/{identity_name}`**: Login with identity credentials
  - Returns: `{"netuid": 1, "identity_name": "sn1"}`

#### Neuron Data (Open Access & Identity)
- **GET `/api/v1/subnet/{netuid}/neurons/{block_number}`**: Get neurons at specific block
- **GET `/api/v1/subnet/{netuid}/neurons/latest`**: Get neurons at latest block
- **GET `/api/v1/identity/{identity_name}/subnet/{netuid}/neurons/{block_number}`**: Identity version
- **GET `/api/v1/identity/{identity_name}/subnet/{netuid}/neurons/latest`**: Identity version

#### Certificates (Open Access & Identity)
- **GET `/api/v1/subnet/{netuid}/certificates`**: Get all certificates for the subnet
- **GET `/api/v1/subnet/{netuid}/certificates/{hotkey}`**: Get certificate for specific hotkey
- **GET `/api/v1/identity/{identity_name}/subnet/{netuid}/certificates`**: Identity version
- **GET `/api/v1/identity/{identity_name}/subnet/{netuid}/certificates/{hotkey}`**: Identity version
- **GET `/api/v1/identity/{identity_name}/subnet/{netuid}/certificates/self`**: Get certificate for identity's wallet
- **POST `/api/v1/identity/{identity_name}/subnet/{netuid}/certificates/self`**: Generate certificate keypair for identity's wallet
  - Request body: `{"algorithm": 1}` (1 = ED25519, currently the only supported algorithm)

#### Weight Management (Identity Only)
- **PUT `/api/v1/identity/{identity_name}/subnet/{netuid}/weights`**: Set weights for the subnet (triggers background ApplyWeights task)
  - Request body: `{"weights": {"hotkey1": 0.5, "hotkey2": 0.3, ...}}`
  - Automatically handles commit-reveal or direct weight setting based on subnet configuration


## turbobt Integration

`turbobt` is a Python library providing core functionalities for interacting with the Bittensor blockchain. The application uses it through the `TurboBtClient` implementation in `pylon_client/service/bittensor/client.py`:

### Client Architecture
- **`AbstractBittensorClient`**: Abstract base class defining the interface for Bittensor operations
- **`TurboBtClient`**: Production implementation using the turbobt library
- **`BittensorClientPool`**: Connection pool that maintains one client instance per wallet, managed via `BittensorClientPool.acquire(wallet)` context manager

### Key turbobt Features Used
- **Blockchain Interaction**:
  - `Bittensor.head.get()`: Fetches the latest block from the blockchain
  - `Bittensor.block(block).get()`: Retrieves a specific block by its number
  - `Bittensor.subnet(netuid)`: Accesses a specific subnet
    - `Subnet.list_neurons(block_hash)`: Lists all neurons within a subnet for a given block
    - `Subnet.get_hyperparameters()`: Fetches the hyperparameters for a subnet
    - `Subnet.get_certificates()`: Fetches all certificates for a subnet
    - `Subnet.generate_certificate_keypair()`: Generates a new certificate keypair
- **Wallet Integration**: Using a `bittensor_wallet.Wallet` instance: `Bittensor(wallet=...)`
- **Weight Operations**: On-chain weight setting and commit-reveal weights
- **Asynchronous Design**: All network and blockchain operations within `turbobt` are inherently asynchronous

## Configuration

Configuration is managed in `pylon_client/_internal/common/settings.py` using `pydantic-settings`. Environment variables are loaded from a `.env` file (template at `pylon_client/service/envs/test_env.template`).

All settings use the `PYLON_` prefix. Example: `PYLON_BITTENSOR_NETWORK=finney`

### Core Settings
- **Bittensor networks**:
  - `bittensor_network`: Main network URI (default: "finney")
  - `bittensor_archive_network`: Archive network URI for historical data (default: "archive")
  - `bittensor_archive_blocks_cutoff`: Block number threshold for switching to archive network (default: 300)
  - `bittensor_wallet_path`: Path to wallet directory (required)

- **Access Control**:
  - `identities`: List of identity names for multi-subnet support (e.g., `["sn1", "sn2"]`)
  - `open_access_token`: Token for open access endpoints
  - `metrics_token`: Token for metrics endpoint access

- **Subnet Configuration**:
  - `tempo`: Subnet epoch length in blocks (default: 360)
  - `commit_cycle_length`: Number of tempos between weight commitments (default: 3)
  - `commit_window_start_offset`: Offset from interval start to begin commit window (default: 180)
  - `commit_window_end_buffer`: Buffer at end of commit window before interval ends (default: 10)

- **Weight Submission**:
  - `weights_retry_attempts`: Max retry attempts for weight submission (default: 200)
  - `weights_retry_delay_seconds`: Delay between retries (default: 1)

- **Monitoring**:
  - `sentry_dsn`: Sentry DSN for error tracking (optional)
  - `sentry_environment`: Environment name for Sentry (default: "development")

- **Development**:
  - `docker_image_name`: Docker image name (default: "bittensor_pylon")
  - `debug`: Enable debug mode (default: false)

### Identity Configuration

Per-identity settings use the pattern `PYLON_ID_{IDENTITY_NAME}_*` (uppercase):
- `PYLON_ID_{NAME}_WALLET_NAME`: Wallet name (coldkey)
- `PYLON_ID_{NAME}_HOTKEY_NAME`: Hotkey name
- `PYLON_ID_{NAME}_NETUID`: Subnet UID
- `PYLON_ID_{NAME}_TOKEN`: Authentication token for this identity

Example for identity "sn1":
```bash
PYLON_ID_SN1_WALLET_NAME=my_wallet
PYLON_ID_SN1_HOTKEY_NAME=my_hotkey
PYLON_ID_SN1_NETUID=1
PYLON_ID_SN1_TOKEN=secret_token_here
```

## Testing Notes

- Uses `pytest` with `pytest-asyncio` for async test support
- Test environment: Set `PYLON_ENV_FILE=tests/.test-env` (nox does this automatically)
- Both sync (`PylonClient`) and async (`AsyncPylonClient`) clients exist and support testing mode

### Service API Testing

The service endpoints are tested using `MockBittensorClient` (`tests/mock_bittensor_client.py`), which provides a mock implementation of `AbstractBittensorClient` for testing without blockchain interactions.

#### MockBittensorClient Features
- **All methods are async**: Including `mock_behavior()` context manager and `reset_call_tracking()`
- **Async Behavior Queue System**: Configure method behaviors using async context manager
  ```python
  async with mock_client.mock_behavior(
      get_latest_block=[Block(number=100, hash=BlockHash("0x123"))],
      _get_certificates=[{hotkey: certificate}],
  ):
      # Test code here
  ```
- **Call Tracking**: All method calls are tracked in `mock_client.calls` dict (using `defaultdict(list)`):
  ```python
  # Check entire call arguments in one assert
  assert mock_client.calls["commit_weights"] == [
      (settings.bittensor_netuid, weights),
  ]
  ```
- **Flexible Behaviors**: Each behavior can be:
  - A value to return directly
  - A callable that receives method arguments
  - An exception instance to raise

#### Test Structure
- **One file per endpoint**: Each endpoint has its own test file (e.g., `test_put_weights_endpoint.py`)
- **Test organization**: Tests are organized in subdirectories:
  - `tests/service/open_access_endpoints/`: Tests for open access endpoints
  - `tests/service/identity_endpoints/`: Tests for identity-scoped endpoints
- **Shared fixtures**: Common fixtures in `tests/service/conftest.py`:
  - `mock_bt_client_pool`: Shared `BittensorClientPool` with `MockBittensorClient` instances (session-scoped)
  - `open_access_mock_bt_client`: Mock client for open access endpoints (no wallet)
  - `sn1_mock_bt_client`: Mock client for "sn1" identity (with wallet)
  - `sn2_mock_bt_client`: Mock client for "sn2" identity (with wallet)
  - `test_app`: Returns configured Litestar app with mocked client pool (session-scoped)
  - `test_client`: Returns `AsyncTestClient` (session-scoped async fixture using `@pytest_asyncio.fixture`)
- **Test helpers** (`tests/helpers.py`):
  - `wait_for_background_tasks(tasks_to_wait: Iterable[asyncio.Task], timeout: float)`: Wait for specific background tasks to complete
    - Takes actual task objects (e.g., `ApplyWeights.tasks_running`), not task names
    - Uses `asyncio.wait()` for native async task synchronization
    - Example: `await wait_for_background_tasks(ApplyWeights.tasks_running)`
  - `wait_until(func: Callable, timeout: float, sleep_interval: float)`: Wait until a condition becomes true
- **Comprehensive coverage**: Tests cover success cases, error cases, and validation errors

#### Testing Best Practices (REMEMBER FOR ETERNITY)

1. **Response Validation**: ALWAYS check the whole `response.json()` in one assert comparing a complete dict
   ```python
   # ✅ CORRECT
   assert response.json() == {
       "detail": "weights update scheduled",
       "count": 3,
   }

   # ❌ WRONG - multiple asserts
   assert response.json()["detail"] == "weights update scheduled"
   assert response.json()["count"] == 3
   ```

2. **Parametrized Tests**: Use `pytest.mark.parametrize` with `pytest.param` and snake_case IDs
   ```python
   @pytest.mark.parametrize(
       "algorithm",
       [
           pytest.param(0, id="algorithm_zero"),
           pytest.param(2, id="algorithm_two"),
           pytest.param("invalid", id="invalid_type"),
       ],
   )
   ```

3. **URL Hardcoding**: Hard code URLs in tests (don't use constants or variables)
   ```python
   # ✅ CORRECT
   response = await client.get("/api/v1/certificates/self")

   # ❌ WRONG
   response = await client.get(f"{API_PREFIX}/certificates/self")
   ```

4. **Docstring Style**: ALWAYS break line after `"""` even for one-line docstrings
   ```python
   # ✅ CORRECT
   def test_example():
       """
       Test that example works correctly.
       """
       pass

   # ❌ WRONG
   def test_example():
       """Test that example works correctly."""
       pass
   ```

5. **Background Task Synchronization**: Use `wait_for_background_tasks()` helper instead of `asyncio.sleep()`
   ```python
   # ✅ CORRECT - wait for specific tasks (pass the task set/list)
   await wait_for_background_tasks(ApplyWeights.tasks_running)

   # ❌ WRONG - unreliable timing
   await asyncio.sleep(0.5)
   ```

6. **Mock Behavior Setup**: Account for ALL method calls including those from background tasks
   ```python
   # Background tasks may call get_latest_block multiple times
   async with mock_client.mock_behavior(
       get_latest_block=[
           Block(number=1000, hash=BlockHash("0xabc123")),  # First call
           Block(number=1001, hash=BlockHash("0xabc124")),  # Second call from background task
       ],
   ):
   ```

7. **Call Tracking Validation**: Check entire call arguments in one assert (like response.json())
   ```python
   # ✅ CORRECT - check entire call tuple
   assert mock_client.calls["commit_weights"] == [
       (settings.bittensor_netuid, weights),
   ]

   # ❌ WRONG - separate asserts
   assert len(mock_client.calls["commit_weights"]) == 1
   assert mock_client.calls["commit_weights"][0][0] == settings.bittensor_netuid
   ```

### Client Library Structure

The client library (`pylon_client/_internal/client/`) provides both synchronous and asynchronous clients:

#### Sync Client (`pylon_client/_internal/client/sync/`)
- **`PylonClient`**: Main synchronous client class
- **`OpenAccessApi`**: Methods for open access endpoints
- **`IdentityApi`**: Methods for identity-scoped endpoints
- **`HttpCommunicator`**: HTTP client for making requests
- Usage: `with PylonClient(config) as client: ...`

#### Async Client (`pylon_client/_internal/client/asynchronous/`)
- **`AsyncPylonClient`**: Main asynchronous client class
- **`AsyncOpenAccessApi`**: Async methods for open access endpoints
- **`AsyncIdentityApi`**: Async methods for identity-scoped endpoints
- **`AsyncHttpCommunicator`**: Async HTTP client for making requests
- Usage: `async with AsyncPylonClient(config) as client: ...`

Both clients follow the Communicator pattern, allowing for different transport implementations (HTTP for production, mock for testing).

## Development Workflow

1. Create `.env` from template: `cp pylon_client/service/envs/test_env.template .env`
2. Install dependencies: `uv sync --extra dev`
3. Run tests: `nox -s test`
4. Format code: `nox -s format`
5. Run service: `uvicorn pylon_client.service.main:app --reload --host 127.0.0.1 --port 8000`

### Release Process

The project has two independent products with separate release workflows:

#### Client Release (PyPI)

The client library is published to PyPI when a `client-v*` tag is pushed:

```bash
# 1. Update version in pylon_client/__init__.py
#    __version__ = "0.2.0"

# 2. Commit and push
git commit -am "chore: bump client version to 0.2.0"
git push origin master

# 3. Create and push tag
git tag client-v0.2.0
git push origin client-v0.2.0

# 4. CI runs, then CD publishes to PyPI
```

#### Service Release (Docker Hub)

The service is published to Docker Hub when a `service-v*` tag is pushed:

```bash
# 1. Update version in pylon_client/service/__init__.py
#    __version__ = "1.0.0"

# 2. Commit and push
git commit -am "chore: bump service version to 1.0.0"
git push origin master

# 3. Create and push tag
git tag service-v1.0.0
git push origin service-v1.0.0

# 4. CI runs, then CD publishes to Docker Hub
```

#### Version Files

| Product | Version File | Tag Pattern |
|---------|--------------|-------------|
| Client (PyPI) | `pylon_client/__init__.py` | `client-v<semver>` |
| Service (Docker) | `pylon_client/service/__init__.py` | `service-v<semver>` |

**Important**: The CD workflow validates that the tag version matches the version in the code. If they don't match, the build will fail.

## Common Gotchas and Important Notes

### Package Structure
- **Service is not packaged**: The `pylon_client/service/` directory is excluded from wheel builds. Only `pylon_client._internal.client` and `pylon_client._internal.common` are distributed as a library
- **Service runs standalone**: The service is meant to be run directly via uvicorn, not imported as a library

### Testing
- **Session-scoped fixtures**: Many test fixtures (`test_app`, `test_client`, `mock_bt_client_pool`) are session-scoped for performance
- **Client pool sharing**: All tests in a session share the same `BittensorClientPool`, but each test gets fresh mock clients via `reset_call_tracking()`
- **Background tasks**: Always use `wait_for_background_tasks()` instead of `asyncio.sleep()` for reliability

### API Access Patterns
- **Open Access**: Read-only, requires `open_access_token`, uses `/api/v1/subnet/{netuid}/...` paths
- **Identity Access**: Full access including writes, requires per-identity token, uses `/api/v1/identity/{name}/subnet/{netuid}/...` paths
- **No mixing**: An identity cannot use open access endpoints and vice versa (different authentication mechanisms)

## Important Implementation Details

- **No active database usage**: While database packages (`sqlalchemy`, `aiosqlite`, `alembic`) are in dependencies, they are not currently used in the codebase. All operations are direct blockchain interactions. Consider removing these dependencies in a future cleanup.
- **Weight management**: Weights are submitted directly to the blockchain via the `ApplyWeights` background task with configurable retry logic
- **Client library**: Both `PylonClient` (sync) and `AsyncPylonClient` (async) are provided
- **Bittensor client abstraction**:
  - `AbstractBittensorClient`: Base interface for all Bittensor operations
  - `TurboBtClient`: Production implementation using turbobt library
  - `BittensorClientPool`: Manages client instances per wallet with connection pooling
  - `MockBittensorClient`: Testing implementation without blockchain interactions
- **Multi-identity support**: Service can operate multiple wallets/subnets simultaneously through the identity system
- **Async-first**: All operations are asynchronous using `asyncio`
- **Architecture patterns**:
  - Communicator pattern in client library (HTTP, Mock communicators)
  - Connection pooling for Bittensor clients
  - Two-tier API access (open access vs identity access)
- **Testing**: Use `nox -s test` to run all tests with proper environment configuration
