# TurboBT Transport Refactor Design

## Goal

Move turbobt connection lifecycle and raw turbobt execution out of `TurboBtClient` into a lower-level
`TurboBTtransport` class.

After the change:

- `AbstractTurboBTtransport` defines the turbobt contact boundary
- `TurboBTtransport` implements that boundary and owns `open`, `close`, client recreation, retry shielding, and all direct turbobt calls
- a module-level factory function returns transport instances and becomes the patch point for future tests
- `TurboBtClient` owns pylon-facing behavior: translating turbobt objects into pylon models, composing multiple raw
  transport calls, and applying higher-level business rules
- `TurboBtClient` exposes the underlying `turbobt.Bittensor` client as a public attribute delegated from the transport
- the public `AbstractBittensorClient` contract remains stable for the rest of the service

## Scope

In scope:

- adding `AbstractTurboBTtransport`
- extracting a new `TurboBTtransport` class
- adding a module-level transport factory function used by `TurboBtClient`
- moving `open`, `close`, `_recreate_bt_client`, and `_protect_turbobt` into that class
- moving direct turbobt operations behind typed transport methods
- updating `TurboBtClient` to depend on the transport instead of directly on `turbobt.Bittensor`
- exposing the raw `turbobt.Bittensor` instance through `TurboBtClient`
- adding the external engineering standards document into this repository

Out of scope:

- changing public API endpoint behavior
- changing `AbstractBittensorClient` method signatures
- altering archive fallback behavior in `BittensorClient`
- implementing a mock transport in this change
- adding new tests for `TurboBTtransport`
- adding or modifying existing `TurboBtClient` tests in this change
- unrelated refactors in pooling, dependencies, or metrics behavior

## Current State

`TurboBtClient` currently mixes:

- lifecycle and resiliency concerns for the raw `turbobt.Bittensor` client
- direct turbobt calls such as `subnet(...).list_neurons()`, `get_state()`, `commitments.fetch()`, `weights.commit()`
- translation into pylon models such as `Block`, `Neuron`, `SubnetState`, `Commitment`, and `Extrinsic`

This produces a class with two layers of responsibility:

1. transport concerns: client creation, readiness synchronization, cancellation shielding, and runtime-error recovery
2. domain concerns: pylon model translation, hotkey resolution, filtering, sorting, and composing multiple calls

The current tests already reflect this split conceptually. For example, `test_shielded.py` is almost entirely about
transport lifecycle behavior even though those behaviors live on `TurboBtClient`.

## Selected Approach

Introduce a dedicated `AbstractTurboBTtransport` plus a concrete `TurboBTtransport` in the bittensor client module and
make `TurboBtClient` compose the abstract transport through a module-level factory seam.

`TurboBTtransport` is a thin, typed adapter over turbobt. It exposes raw methods with turbobt-native return types and
parameters where possible. It does not translate into pylon models.

`TurboBtClient` remains the implementation of `AbstractBittensorClient`. It translates transport results into
application models and handles any higher-level orchestration that needs more than one raw call.

`TurboBtClient` should not instantiate the concrete transport class directly. Instead, it calls a module-level factory
function that returns `AbstractTurboBTtransport`. That factory is the intended patch point for future no-IO mock
implementations.

This approach matches the requested layering directly, creates a clean test seam without adding test work yet, and
keeps the rest of the service stable.

## Architecture

### 1. New Transport Abstraction

Add a new abstract boundary:

- `class AbstractTurboBTtransport(ABC)`

This abstract should define:

- a public `bittensor` attribute or property exposing `Bittensor | None`
- lifecycle methods:
  - `open()`
  - `close()`
- typed raw turbobt operations needed by `TurboBtClient`

This is the transport-oriented contact seam for turbobt access inside `pylon_service`.

### 2. New `TurboBTtransport`

Add a concrete class:

- constructor: `__init__(wallet: Wallet | None, uri: BittensorNetwork)`
- internal state: `_raw_client`, `_is_client_ready`
- public raw-client exposure:
  - `bittensor -> Bittensor | None`
- lifecycle methods:
  - `open()`
  - `close()`
  - `_get_bt_client()`
  - `_recreate_bt_client()`
  - `_protect_turbobt()`

These methods are moved with behavior preserved. The current concurrency rules remain:

- `open()` initializes and enters the raw client, then marks it ready
- `close()` waits for readiness before closing and clearing the client
- concurrent recreations are deduplicated by the readiness event
- protected calls are shielded from task cancellation
- `RuntimeError` during a turbobt operation triggers one client recreation and one retry

`bittensor` should expose the current raw turbobt client instance held by the transport. `TurboBtClient` then exposes
the same object publicly via delegation so current or future callers have an escape hatch without reintroducing raw
construction in application code.

### 3. Typed Raw Transport API

`AbstractTurboBTtransport` and `TurboBTtransport` should expose typed raw methods rather than generic callback-based
access from outside.

Representative method set:

- `get_block(number: BlockNumber) -> TurboBtBlock | None`
- `get_block_timestamp(block_number: BlockNumber) -> datetime`
- `list_neurons(netuid: NetUid, block_hash: BlockHash) -> list[TurboBtNeuron]`
- `get_hyperparameters(netuid: NetUid, block_hash: BlockHash) -> TurboBtSubnetHyperparams | None`
- `get_certificates(netuid: NetUid, block_hash: BlockHash) -> dict[str, TurboBtNeuronCertificate] | None`
- `get_certificate(netuid: NetUid, hotkey: Hotkey, block_hash: BlockHash) -> TurboBtNeuronCertificate | None`
- `generate_certificate_keypair(netuid: NetUid, algorithm: TurboBtCertificateAlgorithm) -> TurboBtNeuronCertificateKeypair | None`
- `get_subnet_state(netuid: NetUid, block_hash: BlockHash) -> dict[str, Any]`
- `commit_weights(netuid: NetUid, weights: dict[int, float]) -> int`
- `set_weights(netuid: NetUid, weights: dict[int, float]) -> None`
- `get_commitment(netuid: NetUid, hotkey: Hotkey, block_hash: BlockHash) -> dict[str, Any] | None`
- `fetch_commitments(netuid: NetUid, block_hash: BlockHash) -> dict[str, dict[str, Any]]`
- `set_commitment(netuid: NetUid, data: bytes) -> None`
- `get_signed_block(block_hash: BlockHash) -> SignedBlock | None`

These methods should use turbobt-facing parameter and return types. If a turbobt call returns an untyped structure in
practice, the transport method should still annotate the narrowest honest Python type instead of returning `Any`
unnecessarily.

### 4. Factory Function

Add a module-level factory function in the bittensor client module, for example:

- `def get_turbobt_transport(wallet: Wallet | None, uri: BittensorNetwork) -> AbstractTurboBTtransport`

Default behavior:

- return `TurboBTtransport(wallet=wallet, uri=uri)`

Usage rule:

- `TurboBtClient` must call this function instead of instantiating `TurboBTtransport` directly
- downstream tests can later patch this function to return a no-IO mock transport implementing the same abstract

This is intentionally the main seam for substituting the transport without patching deep client internals.

### 5. `TurboBtClient` as Mapper/Composer

`TurboBtClient` continues to implement `AbstractBittensorClient`, but it no longer owns raw turbobt lifecycle.

Responsibilities kept in `TurboBtClient`:

- `_resolve_hotkey()`
- pylon model translation helpers
- converting raw block data into `Block`
- converting raw neuron data and subnet state into `Neuron` and `SubnetNeurons`
- converting raw hyperparameters and certificate data into pylon models
- filtering registered commitments
- sorting validators
- translating hotkey-based weights into uid-based weights before transport submission

`TurboBtClient.open()` and `TurboBtClient.close()` become simple delegations to the transport.

It also exposes a public raw-client attribute:

- `client.bittensor -> Bittensor | None`

This should delegate to the transport's raw client reference rather than store a second copy.

### 6. Construction and Encapsulation

`TurboBtClient` should obtain its transport through the module-level factory:

- `self._transport = transport or get_turbobt_transport(wallet=wallet, uri=uri)`

Optional direct transport injection remains useful as a local override, but the normal code path should go through the
factory function because that is the official patch point.

The transport remains turbobt-specific and should not implement `AbstractBittensorClient`. It is a lower-level helper,
not a second public client abstraction.

### 7. Fallback Client Compatibility

`BittensorClient` continues to wrap `TurboBtClient` instances, not transports.

No fallback logic moves into `TurboBTtransport`. Archive selection remains a higher-level policy in `BittensorClient`,
which delegates public `AbstractBittensorClient` methods to main or archive `TurboBtClient` instances as it does now.

## Data Flow

Example: `TurboBtClient.get_neurons_list(netuid, block)`

1. `TurboBtClient` calls `self._transport.list_neurons(netuid, block.hash)`
2. `TurboBtClient` calls `self.get_subnet_state(netuid, block)`
3. `TurboBtClient` translates raw turbobt neurons with the fetched stakes
4. caller receives translated pylon `Neuron` models

Example: `TurboBtClient.get_block(number)`

1. `TurboBtClient` calls `self._transport.get_block(number)`
2. if the raw result is missing required values, return `None`
3. otherwise translate to pylon `Block`

Example: `TurboBtClient.commit_weights(netuid, weights)`

1. `TurboBtClient` fetches latest block and neurons through the transport
2. `TurboBtClient` translates hotkeys to neuron uids and logs missing hotkeys
3. `TurboBtClient` calls `self._transport.commit_weights(netuid, translated_weights)`
4. `TurboBtClient` wraps the returned reveal round in `RevealRound`

## Error Handling

Behavior remains unchanged at the public client boundary.

Transport layer:

- shields raw turbobt operations from caller cancellation
- retries once after `RuntimeError` by recreating the raw client
- preserves readiness synchronization rules during open, recreate, and close

Client layer:

- preserves current `ValueError` behavior when a hotkey is required but no wallet exists
- preserves `None` handling for absent blocks, certificates, or commitments
- continues to log missing hotkeys during weight translation
- exposes the raw turbobt client as a convenience escape hatch, but higher-level code should continue to prefer the
  public `AbstractBittensorClient` methods for normal behavior

## Testing

No new tests should be added in this change.

Do not modify existing `TurboBtClient` tests or add new `TurboBTtransport` tests yet. The goal of this refactor is to
establish the seam first, so later investigation can choose the right mock transport shape and testing strategy.

## Files Likely Affected

- `pylon_service/pylon_service/bittensor/client.py`
- `docs/engineering-standards.md`

## Risks

- over-extracting too much into transport would blur the requested raw-transport boundary
- under-typing transport methods would make the new layer less useful and harder to reason about
- the public raw `bittensor` exposure can become a boundary leak if higher-level code starts bypassing `TurboBtClient`
  methods routinely
- the factory seam must remain the default construction path or tests will fall back to patching deep internals again

## Acceptance Criteria

- `AbstractTurboBTtransport` defines the raw turbobt contact boundary used by `TurboBtClient`
- `TurboBTtransport` owns `open`, `close`, `_recreate_bt_client`, and `_protect_turbobt`
- `get_turbobt_transport()` is the default construction seam and returns `AbstractTurboBTtransport`
- direct turbobt calls move behind typed `TurboBTtransport` methods
- `TurboBtClient` no longer reaches into `turbobt.Bittensor` directly
- `TurboBtClient` exposes the underlying `turbobt.Bittensor` instance as a public delegated attribute
- `TurboBtClient` remains responsible for translation into pylon models and higher-level composition
- public `AbstractBittensorClient` behavior remains unchanged for existing callers
- no new tests are added and no existing `TurboBtClient` tests are modified in this change
