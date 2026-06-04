# Versioning

Pylon consists of two independently versioned products: the **service** (Docker image)
and the **client** (Python library). Each has its own release cycle and versioning scheme.

## Service

### Docker Image Version

The Pylon service is distributed as a Docker image on
[Docker Hub](https://hub.docker.com/r/backenddevelopersltd/bittensor-pylon).
It follows [semantic versioning](https://semver.org/):

- **Major** version bump indicates breaking changes (does not happen often because of [api versioning](#api-versioning))
- **Minor** version bump adds new features in a backward-compatible manner
- **Patch** version bump contains backward-compatible bug fixes

### API Versioning

API endpoints are versioned independently of the Docker image version. Endpoints live
under a versioned prefix (e.g., `/api/v1/...`). When breaking changes need to be introduced
to an endpoint, 'unstable' version of that endpoint is modified while the old version remains
unchanged. This allows deploying breaking API changes without bumping the image major
version and without breaking existing clients.

Current stable API version: **v1** (endpoints under `/api/v1/...`)

### Unstable API

Endpoint breaking changes and new endpoints are published under the `/api/_unstable/...` prefix before
being promoted to a stable version. The unstable API:

- **May change with breaking modifications** in any release, including minor and patch versions
- Once stabilized, endpoints are promoted to a new numbered version (e.g., v2)

## Client

### Package Version

The client library is published on PyPI as
[`bittensor-pylon-client`](https://pypi.org/project/bittensor-pylon-client/).
It follows [semantic versioning](https://semver.org/):

- **Major** version bump indicates breaking changes in the public API (does not happen often because of [client interface versioning](#client-interface-versioning))
- **Minor** version bump adds new features in a backward-compatible manner
- **Patch** version bump contains backward-compatible bug fixes

### Client interface versioning

The client's public interface is exported under named version packages, e.g. `pylon_client.artanis`.

```python
from pylon_client.artanis import (
    AsyncPylonClient, AsyncConfig,     # Client and config
    PylonRequestException,             # Exceptions
    Hotkey, NetUid, Weight,            # Types
    PylonTimeout,                      # Timeout config
)
```

If breaking changes need to be introduced to the client's public interface itself, a new
interface module will be created (alongside `artanis`) while the previous one remains
available.

Package `pylon_client._internal` contains private interface. Changes in this module may be introduced without warning
so importing from it is highly discouraged.

### API Versions in Pylon client

Pylon client allows access to different API versions via version attributes:

```python
async with AsyncPylonClient(config) as client:
    # V1 API
    response = await client.v1.open_access.get_latest_neurons(netuid=NetUid(1))
    response = await client.v1.identity.get_commitments()

    # Unstable API
    response = await client.unstable.open_access.get_latest_neurons(netuid=NetUid(1))
    response = await client.unstable.identity.get_commitments()
```

### API Version Namespaces (Models & Responses)

Data models (e.g., `Neuron`, `Block`) and response classes (e.g., `GetNeuronsResponse`)
are exported under version-specific namespaces:

```python
# V1 models and responses
from pylon_client.artanis.v1 import Neuron, Block, GetNeuronsResponse

# Unstable models and responses
from pylon_client.artanis.unstable import Neuron, Block, GetNeuronsResponse
```

This is useful when different API versions return objects with the same name but different
structure. You can use both versions simultaneously without name collisions:

```python
from pylon_client.artanis import v1, unstable

v1_commitments: v1.GetCommitmentsResponse = ...          # commitments: dict[Hotkey, CommitmentDataHex]
unstable_commitments: unstable.GetCommitmentsResponse = ...  # commitments: dict[Hotkey, Commitment]
```

## Implementation Details (for contributors)

This section describes the internal structure of versioning for developers working
on the Pylon codebase.

### Release Tags

Version is determined from git tags at build time using `hatch-vcs`. There are no version
files in the code.

| Product | Tag pattern | Published to |
|---------|------------|-------------|
| Client | `client-v<semver>` | PyPI (`bittensor-pylon-client`) |
| Service | `service-v<semver>` | Docker Hub (`backenddevelopersltd/bittensor-pylon`) |

### pylon_commons Versioning Structure

The `pylon_commons` package contains the source of truth for all shared types, models,
and API-specific classes. The versioning follows a hierarchy:

```
pylon_commons/
├── models.py                 # Source of truth — all model definitions
├── types/                    # Type definitions (stable, not versioned)
│   ├── bittensor.py          # Bittensor-domain NewType definitions
│   └── evm.py                # EVM-domain NewType definitions
├── _unstable/
│   ├── models.py             # Re-exports from ../models.py (canonical)
│   ├── responses.py          # Canonical response classes
│   ├── requests.py           # Canonical request classes
│   └── endpoints.py          # Canonical endpoint definitions
└── v1/
    ├── models.py             # Re-exports from ../_unstable/models.py
    ├── responses.py          # Imports from _unstable + defines v1-specific overrides
    ├── requests.py           # Imports from _unstable + defines v1-specific overrides
    └── endpoints.py          # V1 endpoint definitions
```

**Key pattern:** `_unstable/` is the canonical source. Other versions import from the next version
and override only what differs (backport).

### pylon_service Versioning Structure

The `pylon_service` package organizes its API endpoints in versioned subpackages
under `pylon_service/api/`:

```
pylon_service/api/
├── __init__.py
├── utils.py                    # Shared handler() decorator
├── v1/
│   ├── __init__.py
│   ├── api.py                  # V1 controllers (inherits from _unstable, overrides where needed)
│   └── routers.py              # V1 router mounted at /api/v1
└── _unstable/
    ├── __init__.py
    ├── api.py                  # Canonical controller implementations
    ├── routers.py              # Unstable router mounted at /api/_unstable
    ├── tasks.py                # Background tasks (ApplyWeights, SetCommitment)
    └── utils.py                # Epoch and commit window utilities
```

**Key pattern:** `_unstable/` contains the canonical endpoint implementations. Other versions inherit
from the next version's controllers and overrides only what differs, mirroring the same approach
used in `pylon_commons`.

Each version has a `routers.py` that creates a `Router` with the appropriate version prefix for the litestar app.

### pylon_client Versioning Structure

The client vendors `pylon_commons` via a symlink at
`pylon_client/_internal/pylon_commons`.

```
pylon_client/
├── artanis/
│   ├── __init__.py           # Clients, config, exceptions, types, timeout, docker
│   ├── v1.py                 # Re-exports v1 models + v1 responses
│   └── unstable.py           # Re-exports unstable models + unstable responses
└── v1/
    └── __init__.py           # Deprecated shim (emits DeprecationWarning)
```
