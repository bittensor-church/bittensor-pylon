# Mock TurboBT Transport Endpoint Test Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a production `MockTurboBTtransport` that models blockchain state and records calls, then migrate the open-access neurons and validators endpoint tests into `pylon_service/new_tests/` so they use the transport seam instead of `MockBittensorClient`.

**Architecture:** `pylon_service.bittensor.client` will gain a no-IO `MockTurboBTtransport` implementing `AbstractTurboBTtransport` with declarative range-based state configuration plus structured call recording. The migrated endpoint tests will live under `pylon_service/new_tests/open_access_endpoints/` with their own local fixtures so they do not inherit the old shared `MockBittensorClient` pool seam, and they will patch `get_turbobt_transport()` locally to exercise the normal `TurboBtClient` path.

**Tech Stack:** Python 3.13, `pytest`, `pytest-asyncio`, `litestar`, `turbobt`, `unittest.mock`, `pylon_commons`

---

### Task 1: Add The Production Mock Transport

**Files:**
- Modify: `pylon_service/pylon_service/bittensor/client.py`

- [ ] **Step 1: Inspect the raw operations the migrated endpoint tests will need**

Run:

```bash
sed -n '240,860p' pylon_service/pylon_service/bittensor/client.py
```

Expected:
- confirm the migrated endpoint paths only need `get_block()`, `list_neurons()`, and `get_subnet_state()` from the mock transport
- confirm the remaining abstract methods can stay explicitly unimplemented in this change

- [ ] **Step 2: Add private helper structures for block-range lookup**

Add small private dataclasses above `MockTurboBTtransport`:

```python
@dataclass(slots=True)
class _BlockRange[T]:
    start: int
    end: int | None
    value: T

    def contains(self, block_number: int) -> bool:
        if block_number < self.start:
            return False
        return self.end is None or block_number <= self.end
```

And:

```python
@dataclass(slots=True)
class _MockBlockRecord:
    block: TurboBtBlock
```

Constraints:
- keep them private to the module
- do not add unnecessary generality beyond this mock’s needs

- [ ] **Step 3: Add `MockTurboBTtransport(AbstractTurboBTtransport)`**

Implement a new production mock transport near `TurboBTtransport`:

```python
class MockTurboBTtransport(AbstractTurboBTtransport):
    def __init__(self) -> None:
        self._latest_block: TurboBtBlock | None = None
        self._blocks_by_number: dict[int, _MockBlockRecord] = {}
        self._blocks_by_hash: dict[BlockHash, _MockBlockRecord] = {}
        self._neurons: dict[NetUid, list[_BlockRange[list[TurboBtNeuron]]]] = {}
        self._subnet_states: dict[NetUid, list[_BlockRange[dict[str, Any]]]] = {}
        self.calls: dict[str, list[tuple[Any, ...]]] = defaultdict(list)

    @property
    def bittensor(self) -> Bittensor | None:
        return None

    async def open(self) -> None:
        self.calls["open"].append(())

    async def close(self) -> None:
        self.calls["close"].append(())
```

Add declarative configuration methods:

```python
def set_latest_block(self, block: TurboBtBlock) -> None: ...
def add_block(self, block: TurboBtBlock) -> None: ...
def add_neurons_range(
    self, netuid: NetUid, start: int, end: int | None, neurons: list[TurboBtNeuron]
) -> None: ...
def add_subnet_state_range(
    self, netuid: NetUid, start: int, end: int | None, state: dict[str, Any]
) -> None: ...
def reset(self) -> None: ...
```

Constraints:
- every public method records calls in `calls[...]`
- no external IO
- `bittensor` remains `None`

- [ ] **Step 4: Implement the raw methods needed by the migrated endpoint tests**

Implement these methods with real lookup logic:

```python
async def get_block(self, number: BlockNumber) -> TurboBtBlock | None: ...
async def list_neurons(self, netuid: NetUid, block_hash: BlockHash) -> list[TurboBtNeuron]: ...
async def get_subnet_state(self, netuid: NetUid, block_hash: BlockHash) -> dict[str, Any]: ...
```

Lookup behavior:
- `get_block(LATEST_BLOCK_MARK)` returns the configured latest block
- other block requests return a configured matching block by number
- `list_neurons()` and `get_subnet_state()` resolve the block number from `block_hash`
- if no configured range matches, raise `LookupError` with netuid and block details

For the remaining abstract methods, add explicit `NotImplementedError` bodies such as:

```python
raise NotImplementedError("MockTurboBTtransport does not implement get_certificates in this change")
```

- [ ] **Step 5: Run syntax verification on the client module**

Run:

```bash
cd pylon_service && uv run python -m py_compile pylon_service/bittensor/client.py
```

Expected:
- no syntax errors

- [ ] **Step 6: Commit the production mock transport**

```bash
git add pylon_service/pylon_service/bittensor/client.py
git commit -m "Add mock TurboBT transport"
```

### Task 2: Create The Isolated `new_tests` Fixture Layer

**Files:**
- Create: `pylon_service/new_tests/open_access_endpoints/conftest.py`

- [ ] **Step 1: Add a local fixture module for the new test tree**

Create `pylon_service/new_tests/open_access_endpoints/conftest.py` with only the fixtures needed by the migrated
endpoint tests.

It should include a comment like:

```python
# These fixtures intentionally duplicate a subset of the older test setup.
# This directory is the start of a gradual migration away from pylon_service/tests/,
# so these tests must not inherit the shared MockBittensorClient-based pool seam.
```

- [ ] **Step 2: Recreate the minimal app/test-client fixture stack without `MockBittensorClient`**

Build local fixtures for:

- `mock_stores`
- `reset_mock_stores`
- `test_app`
- `test_client`

Use the same Litestar app construction pattern as the existing tests, but set:

```python
app.state.bittensor_client_pool = BittensorClientPool(
    uri=BittensorNetwork("ws://localhost:8000"),
    archive_uri=BittensorNetwork("ws://localhost:8001"),
)
```

Also:
- patch the scheduler lifespan to a no-op
- patch stores the same way as the old test app
- disable response cache
- keep `app.debug = True`

- [ ] **Step 3: Run a smoke syntax check for the new fixture module**

Run:

```bash
cd pylon_service && uv run python -m py_compile new_tests/open_access_endpoints/conftest.py
```

Expected:
- no syntax errors

- [ ] **Step 4: Commit the isolated fixture layer**

```bash
git add pylon_service/new_tests/open_access_endpoints/conftest.py
git commit -m "Add isolated fixtures for new transport tests"
```

### Task 3: Migrate Open-Access Neurons Endpoint Tests

**Files:**
- Create: `pylon_service/new_tests/open_access_endpoints/test_get_neurons_endpoint.py`
- Delete: `pylon_service/tests/unit/open_access_endpoints/test_get_neurons_endpoint.py`

- [ ] **Step 1: Copy the existing neurons endpoint tests into the new tree**

Start by copying the current module into the new location:

```bash
cp pylon_service/tests/unit/open_access_endpoints/test_get_neurons_endpoint.py \
  pylon_service/new_tests/open_access_endpoints/test_get_neurons_endpoint.py
```

Then edit only the new file.

- [ ] **Step 2: Replace `MockBittensorClient` usage with transport-level imports and fixtures**

Update imports to use:

```python
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest_asyncio
from turbobt.block import Block as TurboBtBlock
from turbobt.neuron import Neuron as TurboBtNeuron

from pylon_service.bittensor.client import MockTurboBTtransport
```

Remove:

```python
from tests.mock_bittensor_client import MockBittensorClient
```

Add local fixtures:

```python
@pytest.fixture
def mock_turbobt_transport() -> MockTurboBTtransport:
    return MockTurboBTtransport()


@pytest_asyncio.fixture
async def patched_test_client(
    test_client: AsyncTestClient, mock_turbobt_transport: MockTurboBTtransport
) -> AsyncIterator[AsyncTestClient]:
    with patch(
        "pylon_service.bittensor.client.get_turbobt_transport",
        return_value=mock_turbobt_transport,
    ):
        yield test_client
```

- [ ] **Step 3: Add raw builders and raw subnet-state fixtures**

Add a raw block builder:

```python
def _build_turbobt_block(number: int, block_hash: str) -> TurboBtBlock:
    return TurboBtBlock(block_hash, number, client=None)
```

Add a raw neuron builder using `SimpleNamespace` and `cast(TurboBtNeuron, ...)`.

Add a raw subnet-state builder returning a dict with:

- `hotkeys`
- `hotkeys_stakes`

The `hotkeys_stakes` values must produce the same stakes the existing HTTP assertions expect.

- [ ] **Step 4: Refactor the explicit-block neurons test to use the transport mock**

Rewrite `test_get_neurons_open_access_success()` so it:
- uses `patched_test_client`
- uses `mock_turbobt_transport`
- configures:
  - `add_block(...)`
  - `add_neurons_range(...)`
  - `add_subnet_state_range(...)`

Then assert:

```python
assert mock_turbobt_transport.calls["get_block"] == [(BlockNumber(123),)]
assert mock_turbobt_transport.calls["list_neurons"] == [(NetUid(1), BlockHash("0xabc123"))]
assert mock_turbobt_transport.calls["get_subnet_state"] == [(NetUid(1), BlockHash("0xabc123"))]
```

Keep the HTTP response assertion functionally unchanged.

- [ ] **Step 5: Refactor the latest-block neurons test the same way**

Rewrite `test_get_latest_neurons_open_access_success()` to configure:

```python
mock_turbobt_transport.set_latest_block(raw_block)
mock_turbobt_transport.add_block(raw_block)
mock_turbobt_transport.add_neurons_range(NetUid(1), 123, None, raw_neurons)
mock_turbobt_transport.add_subnet_state_range(NetUid(1), 123, None, raw_state)
```

Then assert:

```python
assert mock_turbobt_transport.calls["get_block"] == [(BlockNumber(-1),)]
```

- [ ] **Step 6: Remove the old neurons endpoint test module**

Delete:

```bash
rm pylon_service/tests/unit/open_access_endpoints/test_get_neurons_endpoint.py
```

- [ ] **Step 7: Run the migrated neurons endpoint test module**

Run:

```bash
cd pylon_service && uv run pytest new_tests/open_access_endpoints/test_get_neurons_endpoint.py -q
```

Expected:
- the new module passes
- it does not depend on `open_access_mock_bt_client`

- [ ] **Step 8: Commit the neurons endpoint migration**

```bash
git add pylon_service/new_tests/open_access_endpoints/test_get_neurons_endpoint.py \
  pylon_service/tests/unit/open_access_endpoints/test_get_neurons_endpoint.py
git commit -m "Migrate neurons endpoint tests to new transport seam"
```

### Task 4: Migrate Open-Access Validators Endpoint Tests

**Files:**
- Create: `pylon_service/new_tests/open_access_endpoints/test_get_validators_endpoint.py`
- Delete: `pylon_service/tests/unit/open_access_endpoints/test_get_validators_endpoint.py`

- [ ] **Step 1: Copy the existing validators endpoint tests into the new tree**

Start by copying the current module into the new location:

```bash
cp pylon_service/tests/unit/open_access_endpoints/test_get_validators_endpoint.py \
  pylon_service/new_tests/open_access_endpoints/test_get_validators_endpoint.py
```

- [ ] **Step 2: Mirror the transport patch setup and raw builders**

Add the same local imports and fixtures pattern as the new neurons module:

```python
from unittest.mock import patch
import pytest_asyncio
from pylon_service.bittensor.client import MockTurboBTtransport
```

Also add:
- `mock_turbobt_transport`
- `patched_test_client`
- raw block builder
- raw neuron builder
- raw subnet-state builder

- [ ] **Step 3: Refactor the explicit-block validators test**

Rewrite `test_get_validators_open_access_success()` so it configures:

```python
mock_turbobt_transport.add_block(raw_block)
mock_turbobt_transport.add_neurons_range(NetUid(1), 123, 123, raw_neurons)
mock_turbobt_transport.add_subnet_state_range(NetUid(1), 123, 123, raw_state)
```

Then assert:

```python
assert mock_turbobt_transport.calls["get_block"] == [(BlockNumber(123),)]
assert mock_turbobt_transport.calls["list_neurons"] == [(NetUid(1), BlockHash("0xabc123"))]
assert mock_turbobt_transport.calls["get_subnet_state"] == [(NetUid(1), BlockHash("0xabc123"))]
```

Keep the HTTP response assertion functionally unchanged.

- [ ] **Step 4: Refactor the latest-block validators test**

Rewrite `test_get_latest_validators_open_access_success()` to use `set_latest_block()` plus open-ended ranges and
assert:

```python
assert mock_turbobt_transport.calls["get_block"] == [(BlockNumber(-1),)]
```

- [ ] **Step 5: Remove the old validators endpoint test module**

Delete:

```bash
rm pylon_service/tests/unit/open_access_endpoints/test_get_validators_endpoint.py
```

- [ ] **Step 6: Run the migrated validators endpoint test module**

Run:

```bash
cd pylon_service && uv run pytest new_tests/open_access_endpoints/test_get_validators_endpoint.py -q
```

Expected:
- the new module passes
- it does not depend on `open_access_mock_bt_client`

- [ ] **Step 7: Commit the validators endpoint migration**

```bash
git add pylon_service/new_tests/open_access_endpoints/test_get_validators_endpoint.py \
  pylon_service/tests/unit/open_access_endpoints/test_get_validators_endpoint.py
git commit -m "Migrate validators endpoint tests to new transport seam"
```

### Task 5: Final Verification

**Files:**
- Modify: `pylon_service/pylon_service/bittensor/client.py`
- Create: `pylon_service/new_tests/open_access_endpoints/conftest.py`
- Create: `pylon_service/new_tests/open_access_endpoints/test_get_neurons_endpoint.py`
- Create: `pylon_service/new_tests/open_access_endpoints/test_get_validators_endpoint.py`

- [ ] **Step 1: Check the final diff stays in scope**

Run:

```bash
git diff --stat HEAD~4..HEAD
git diff -- pylon_service/pylon_service/bittensor/client.py \
  pylon_service/new_tests/open_access_endpoints/conftest.py \
  pylon_service/new_tests/open_access_endpoints/test_get_neurons_endpoint.py \
  pylon_service/new_tests/open_access_endpoints/test_get_validators_endpoint.py
```

Expected:
- the functional changes are limited to the production transport module and the new isolated test tree
- no dedicated mock-transport test files were added

- [ ] **Step 2: Run final verification**

Run:

```bash
cd pylon_service && uv run python -m py_compile \
  pylon_service/bittensor/client.py \
  new_tests/open_access_endpoints/conftest.py \
  new_tests/open_access_endpoints/test_get_neurons_endpoint.py \
  new_tests/open_access_endpoints/test_get_validators_endpoint.py
cd pylon_service && uv run pytest \
  new_tests/open_access_endpoints/test_get_neurons_endpoint.py \
  new_tests/open_access_endpoints/test_get_validators_endpoint.py -q
```

Expected:
- all files compile
- both migrated endpoint modules pass

- [ ] **Step 3: Create the final commit**

```bash
git add pylon_service/pylon_service/bittensor/client.py \
  pylon_service/new_tests/open_access_endpoints/conftest.py \
  pylon_service/new_tests/open_access_endpoints/test_get_neurons_endpoint.py \
  pylon_service/new_tests/open_access_endpoints/test_get_validators_endpoint.py \
  pylon_service/tests/unit/open_access_endpoints/test_get_neurons_endpoint.py \
  pylon_service/tests/unit/open_access_endpoints/test_get_validators_endpoint.py
git commit -m "Add mock transport for migrated endpoint tests"
```

## Self-Review

Spec coverage:
- production `MockTurboBTtransport`: covered in Task 1
- declarative block-range state and call recording: covered in Task 1
- isolated `new_tests` fixture layer and migration comment: covered in Task 2
- local factory patching in migrated modules: covered in Tasks 3 and 4
- migration away from `open_access_mock_bt_client` in the two endpoint modules: covered in Tasks 3 and 4
- no dedicated mock-transport tests: enforced in Task 5

Placeholder scan:
- no `TODO`, `TBD`, or deferred implementation markers remain

Type consistency:
- the plan consistently uses `MockTurboBTtransport`, `AbstractTurboBTtransport`, and `get_turbobt_transport()`
- the migrated test paths consistently use `pylon_service/new_tests/open_access_endpoints/`
