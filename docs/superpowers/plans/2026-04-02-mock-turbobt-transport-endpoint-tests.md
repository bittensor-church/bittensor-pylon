# Mock TurboBT Transport Endpoint Test Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a production `MockTurboBTtransport` that models blockchain state and records calls, then migrate the open-access neurons and validators endpoint tests to patch the transport factory instead of using `MockBittensorClient`.

**Architecture:** `pylon_service.bittensor.client` will gain a no-IO `MockTurboBTtransport` implementing `AbstractTurboBTtransport` with declarative range-based state configuration plus structured call recording. The two target test modules will patch `get_turbobt_transport()` locally so they exercise the normal `TurboBtClient` path while bypassing the shared `MockBittensorClient` fixture seam.

**Tech Stack:** Python 3.13, `pytest`, `litestar`, `turbobt`, `unittest.mock`, `pylon_commons`

---

### Task 1: Add The Production Mock Transport

**Files:**
- Modify: `pylon_service/pylon_service/bittensor/client.py`

- [ ] **Step 1: Inspect the concrete raw types already used by `TurboBtClient`**

Run:

```bash
sed -n '240,620p' pylon_service/pylon_service/bittensor/client.py
```

Expected:
- confirm `TurboBtClient` only needs raw support for `get_block()`, `list_neurons()`, and `get_subnet_state()` in the two target endpoint modules
- confirm remaining abstract methods can stay unimplemented in the mock for now

- [ ] **Step 2: Add block-range helper structures for the mock**

Add small internal helper dataclasses above `MockTurboBTtransport`:

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

And add a block-hash mapping helper shape:

```python
@dataclass(slots=True)
class _MockBlockRecord:
    block: TurboBtBlock
```

Constraints:
- keep helpers private to the module
- do not over-generalize beyond the current mock transport needs

- [ ] **Step 3: Add `MockTurboBTtransport(AbstractTurboBTtransport)`**

Implement a new production mock transport near the real transport:

```python
class MockTurboBTtransport(AbstractTurboBTtransport):
    def __init__(self) -> None:
        self._latest_block: TurboBtBlock | None = None
        self._blocks_by_number: dict[int, TurboBtBlock] = {}
        self._blocks_by_hash: dict[BlockHash, TurboBtBlock] = {}
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

- [ ] **Step 4: Implement only the raw methods needed by the target endpoint tests**

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

For the remaining abstract methods, add explicit `NotImplementedError` bodies:

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

### Task 2: Migrate Open-Access Neurons Endpoint Tests

**Files:**
- Modify: `pylon_service/tests/unit/open_access_endpoints/test_get_neurons_endpoint.py`

- [ ] **Step 1: Replace `MockBittensorClient` imports and fixtures with transport-level imports**

Update imports to use:

```python
from collections.abc import AsyncIterator
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

- [ ] **Step 2: Add module-local patch fixture that bypasses `MockBittensorClient`**

Add a fixture in the test module:

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

Use this fixture in the migrated tests instead of `test_client` directly.

- [ ] **Step 3: Add raw turbobt builders for block and neurons**

Add helper builders in the module:

```python
def _build_turbobt_block(number: int, block_hash: str) -> TurboBtBlock:
    return TurboBtBlock(block_hash, number, client=None)
```

And a neuron builder that mirrors the existing pylon neuron fixture values but returns `TurboBtNeuron`-compatible mock
objects. Prefer `types.SimpleNamespace` for the raw neuron/axon shape if constructing the actual turbobt class is
impractical:

```python
def _build_turbobt_neuron(... ) -> TurboBtNeuron:
    return cast(
        TurboBtNeuron,
        SimpleNamespace(
            uid=uid,
            coldkey=coldkey,
            hotkey=hotkey,
            active=active,
            axon_info=SimpleNamespace(ip=IPv4Address(ip), port=port, protocol=protocol),
            stake=stake,
            rank=rank,
            emission=emission,
            incentive=incentive,
            consensus=consensus,
            trust=trust,
            validator_trust=validator_trust,
            dividends=dividends,
            last_update=last_update,
            validator_permit=validator_permit,
            pruning_score=pruning_score,
        ),
    )
```

Also add a raw subnet state fixture carrying `hotkeys_stakes` and `hotkeys` for the configured neurons.

- [ ] **Step 4: Refactor the explicit-block neurons test to use the transport mock**

Rewrite `test_get_neurons_open_access_success()` so it:
- uses `patched_test_client`
- uses `mock_turbobt_transport`
- configures:
  - `set_latest_block()` if needed
  - `add_block(...)`
  - `add_neurons_range(...)`
  - `add_subnet_state_range(...)`

Example configuration:

```python
raw_block = _build_turbobt_block(123, "0xabc123")
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

- [ ] **Step 5: Refactor the latest-block neurons test the same way**

Rewrite `test_get_latest_neurons_open_access_success()` to configure:

```python
raw_block = _build_turbobt_block(123, "0xabc123")
mock_turbobt_transport.set_latest_block(raw_block)
mock_turbobt_transport.add_block(raw_block)
mock_turbobt_transport.add_neurons_range(NetUid(1), 123, None, raw_neurons)
mock_turbobt_transport.add_subnet_state_range(NetUid(1), 123, None, raw_state)
```

Then assert:

```python
assert mock_turbobt_transport.calls["get_block"] == [(BlockNumber(-1),)]
```

Keep the HTTP body assertions unchanged.

- [ ] **Step 6: Run the neurons endpoint test module**

Run:

```bash
cd pylon_service && uv run pytest tests/unit/open_access_endpoints/test_get_neurons_endpoint.py -q
```

Expected:
- the module passes
- no test in this module depends on `open_access_mock_bt_client`

- [ ] **Step 7: Commit the neurons endpoint migration**

```bash
git add pylon_service/tests/unit/open_access_endpoints/test_get_neurons_endpoint.py
git commit -m "Migrate neurons endpoint tests to mock transport"
```

### Task 3: Migrate Open-Access Validators Endpoint Tests

**Files:**
- Modify: `pylon_service/tests/unit/open_access_endpoints/test_get_validators_endpoint.py`

- [ ] **Step 1: Mirror the module-local transport patch setup**

Add the same local imports and fixtures pattern used in the neurons endpoint module:

```python
from unittest.mock import patch
import pytest_asyncio
from pylon_service.bittensor.client import MockTurboBTtransport
```

And:

```python
@pytest.fixture
def mock_turbobt_transport() -> MockTurboBTtransport: ...

@pytest_asyncio.fixture
async def patched_test_client(...): ...
```

- [ ] **Step 2: Add raw neuron/block/state builders needed for validator derivation**

Use the same raw turbobt block builder and raw neuron/state helpers as in the neurons module, duplicated locally if
needed to keep the change isolated.

The configured raw state must include stakes so `TurboBtClient.get_neurons_list()` can translate neurons and
`get_validators()` can sort/filter them normally.

- [ ] **Step 3: Refactor the explicit-block validators test**

Rewrite `test_get_validators_open_access_success()` so it configures the transport with:

```python
mock_turbobt_transport.add_block(raw_block)
mock_turbobt_transport.add_neurons_range(NetUid(1), 123, 123, raw_validators)
mock_turbobt_transport.add_subnet_state_range(NetUid(1), 123, 123, raw_state)
```

Then assert transport calls:

```python
assert mock_turbobt_transport.calls["get_block"] == [(BlockNumber(123),)]
assert mock_turbobt_transport.calls["list_neurons"] == [(NetUid(1), BlockHash("0xabc123"))]
assert mock_turbobt_transport.calls["get_subnet_state"] == [(NetUid(1), BlockHash("0xabc123"))]
```

The HTTP body assertion should remain unchanged.

- [ ] **Step 4: Refactor the latest-block validators test**

Rewrite `test_get_latest_validators_open_access_success()` to use `set_latest_block()` plus open-ended ranges and
assert:

```python
assert mock_turbobt_transport.calls["get_block"] == [(BlockNumber(-1),)]
```

- [ ] **Step 5: Run the validators endpoint test module**

Run:

```bash
cd pylon_service && uv run pytest tests/unit/open_access_endpoints/test_get_validators_endpoint.py -q
```

Expected:
- the module passes
- no test in this module depends on `open_access_mock_bt_client`

- [ ] **Step 6: Commit the validators endpoint migration**

```bash
git add pylon_service/tests/unit/open_access_endpoints/test_get_validators_endpoint.py
git commit -m "Migrate validators endpoint tests to mock transport"
```

### Task 4: Final Verification

**Files:**
- Modify: `pylon_service/pylon_service/bittensor/client.py`
- Modify: `pylon_service/tests/unit/open_access_endpoints/test_get_neurons_endpoint.py`
- Modify: `pylon_service/tests/unit/open_access_endpoints/test_get_validators_endpoint.py`

- [ ] **Step 1: Check the final diff stays in scope**

Run:

```bash
git diff --stat HEAD~3..HEAD
git diff -- pylon_service/pylon_service/bittensor/client.py \
  pylon_service/tests/unit/open_access_endpoints/test_get_neurons_endpoint.py \
  pylon_service/tests/unit/open_access_endpoints/test_get_validators_endpoint.py
```

Expected:
- only the production transport module and the two target endpoint modules changed for the functional work
- no dedicated mock-transport test files were added

- [ ] **Step 2: Run final verification**

Run:

```bash
cd pylon_service && uv run python -m py_compile \
  pylon_service/bittensor/client.py \
  tests/unit/open_access_endpoints/test_get_neurons_endpoint.py \
  tests/unit/open_access_endpoints/test_get_validators_endpoint.py
cd pylon_service && uv run pytest \
  tests/unit/open_access_endpoints/test_get_neurons_endpoint.py \
  tests/unit/open_access_endpoints/test_get_validators_endpoint.py -q
```

Expected:
- all three files compile
- both endpoint modules pass

- [ ] **Step 3: Create the final commit**

```bash
git add pylon_service/pylon_service/bittensor/client.py \
  pylon_service/tests/unit/open_access_endpoints/test_get_neurons_endpoint.py \
  pylon_service/tests/unit/open_access_endpoints/test_get_validators_endpoint.py
git commit -m "Add mock transport for endpoint tests"
```

## Self-Review

Spec coverage:
- production `MockTurboBTtransport`: covered in Task 1
- declarative block-range state and call recording: covered in Task 1
- local factory patching in target modules: covered in Tasks 2 and 3
- migration away from `open_access_mock_bt_client` in the two endpoint modules: covered in Tasks 2 and 3
- no dedicated mock-transport tests: enforced in Task 4

Placeholder scan:
- no `TODO`, `TBD`, or deferred implementation markers remain

Type consistency:
- the plan consistently uses `MockTurboBTtransport`, `AbstractTurboBTtransport`, and `get_turbobt_transport()`
- the configured raw methods match the currently needed `TurboBtClient` transport calls for these endpoint paths
