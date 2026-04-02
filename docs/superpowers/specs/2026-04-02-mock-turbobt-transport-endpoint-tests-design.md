# Mock TurboBT Transport For Endpoint Tests Design

## Goal

Add a no-IO mock implementation of `AbstractTurboBTtransport` in production code and use it to migrate two endpoint
test modules away from `MockBittensorClient`:

- `pylon_service/tests/unit/open_access_endpoints/test_get_neurons_endpoint.py`
- `pylon_service/tests/unit/open_access_endpoints/test_get_validators_endpoint.py`

The mock transport must:

- model the shape of chain data over block ranges and per-subnet state
- record calls in a structured way so tests can assert what happened

## Scope

In scope:

- adding `MockTurboBTtransport` next to the real transport seam in production code
- giving it declarative APIs for block- and subnet-scoped raw chain state
- recording method calls on the mock transport
- patching `get_turbobt_transport()` locally inside the two target test modules
- refactoring those two modules to use the mock transport instead of `MockBittensorClient`

Out of scope:

- changing the shared `mock_bt_client_pool` fixture globally
- migrating other test modules
- adding dedicated tests for `MockTurboBTtransport`
- removing `MockBittensorClient`

## Current State

The service test app is wired around `BittensorClientPool(client_cls=MockBittensorClient, ...)` in
`pylon_service/tests/conftest.py`.

The two target endpoint modules currently:

- depend on `open_access_mock_bt_client: MockBittensorClient`
- configure return values through `mock_behavior(...)`
- assert `MockBittensorClient.calls[...]`

This keeps tests above an older client seam rather than the new transport seam. It also configures behavior in method
terms instead of describing chain state.

## Selected Approach

Add a production `MockTurboBTtransport(AbstractTurboBTtransport)` and patch `get_turbobt_transport()` only within the
two target test modules.

Those modules will continue to use the normal app and the normal `TurboBtClient`, but their local patch will cause the
client to receive a no-IO transport instance instead of the real transport. This bypasses the shared
`MockBittensorClient` fixture path for those modules without requiring a global test harness rewrite.

## Architecture

### 1. Production Mock Transport

Add `MockTurboBTtransport` in `pylon_service/pylon_service/bittensor/client.py`.

It implements `AbstractTurboBTtransport` and has two responsibilities:

1. represent chain state declaratively
2. record structured call history

Core internal state:

- `latest_block: TurboBtBlock | None`
- range-based per-subnet neuron datasets
- range-based per-subnet state datasets
- `calls: dict[str, list[tuple[Any, ...]]]`

The mock should expose declarative setup helpers in domain terms, for example:

- `set_latest_block(block: TurboBtBlock | None) -> None`
- `add_neurons_range(netuid: NetUid, start: int, end: int | None, neurons: list[TurboBtNeuron]) -> None`
- `add_subnet_state_range(netuid: NetUid, start: int, end: int | None, state: dict[str, Any]) -> None`
- `reset() -> None`

Range semantics:

- closed range when `end` is provided
- open-ended range when `end is None`
- later registrations may override earlier ones for the same netuid/range overlap

Lookup behavior:

- `get_block(number)` returns the configured latest block for `LATEST_BLOCK_MARK`, otherwise a block matching the
  requested number if resolvable from configured data
- `list_neurons(netuid, block_hash)` resolves the block number from the hash and returns the matching configured neuron
  dataset
- `get_subnet_state(netuid, block_hash)` resolves the block number from the hash and returns the matching configured
  state dataset

Unused abstract methods may raise `NotImplementedError` in this change if the two migrated modules do not touch them.
That keeps the mock scoped to current needs.

### 2. Call Recording

Every public transport method should append its externally visible arguments to `calls[method_name]`.

Example:

- `calls["get_block"] == [(BlockNumber(123),)]`
- `calls["list_neurons"] == [(NetUid(1), BlockHash("0xabc123"))]`
- `calls["get_subnet_state"] == [(NetUid(1), BlockHash("0xabc123"))]`

This keeps assertions at the contact boundary rather than on deeper internals.

### 3. Targeted Test Patching

Do not modify the shared `pylon_service/tests/conftest.py` pool fixtures.

Instead, in each target module:

- create a module-local `MockTurboBTtransport` fixture
- patch `pylon_service.bittensor.client.get_turbobt_transport` to return that fixture
- use the normal test app/client stack

The patch must apply before requests cause `TurboBtClient` instances to be created for that module’s tests.

### 4. Test Refactor Shape

Refactor the two modules so they:

- stop depending on `open_access_mock_bt_client`
- configure the mock transport using block/state/neuron datasets
- assert `mock_turbobt_transport.calls[...]`

For neurons endpoint tests:

- configure latest or explicit block
- configure subnet neuron list for netuid 1 over the relevant block range
- configure subnet state for netuid 1 over the relevant block range so `TurboBtClient.get_neurons_list()` can build
  stakes

For validators endpoint tests:

- configure latest or explicit block
- configure neuron list and subnet state so `TurboBtClient.get_validators()` can derive validators through the normal
  client logic

The test assertions on HTTP response bodies should remain functionally unchanged.

## Error Handling

`MockTurboBTtransport` should fail clearly when a requested dataset is not configured:

- raise `LookupError` or `AssertionError` with enough context to show the missing netuid/block lookup

This is preferable to returning empty placeholders because it makes incorrect test setup obvious.

## Files Likely Affected

- `pylon_service/pylon_service/bittensor/client.py`
- `pylon_service/tests/unit/open_access_endpoints/test_get_neurons_endpoint.py`
- `pylon_service/tests/unit/open_access_endpoints/test_get_validators_endpoint.py`

## Risks

- if the test-module patch is applied too late, the client pool may still create clients through the old seam
- raw turbobt object construction in tests may be slightly verbose if helper builders are missing
- over-building the mock now would recreate the same maintenance problem as `MockBittensorClient`

## Acceptance Criteria

- `MockTurboBTtransport` exists in production code and implements `AbstractTurboBTtransport`
- the mock transport can express per-subnet datasets over block ranges and remember method calls
- the two target endpoint modules no longer use `open_access_mock_bt_client`
- the two target endpoint modules patch `get_turbobt_transport()` locally
- no dedicated mock-transport tests are added in this change
