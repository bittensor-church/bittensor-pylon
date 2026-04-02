# TurboBT Transport Refactor Design

## Goal

Move turbobt connection lifecycle and raw turbobt execution out of `TurboBtClient` into a lower-level
`TurboBTtransport` class.

After the change:

- `TurboBTtransport` owns `open`, `close`, client recreation, retry shielding, and all direct turbobt calls
- `TurboBtClient` owns pylon-facing behavior: translating turbobt objects into pylon models, composing multiple raw
  transport calls, and applying higher-level business rules
- the public `AbstractBittensorClient` contract remains stable for the rest of the service

## Scope

In scope:

- extracting a new `TurboBTtransport` class
- moving `open`, `close`, `_recreate_bt_client`, and `_protect_turbobt` into that class
- moving direct turbobt operations behind typed transport methods
- updating `TurboBtClient` to depend on the transport instead of directly on `turbobt.Bittensor`
- updating turbobt-focused unit tests to target the new transport boundary where appropriate

Out of scope:

- changing public API endpoint behavior
- changing `AbstractBittensorClient` method signatures
- altering archive fallback behavior in `BittensorClient`
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

Introduce a dedicated `TurboBTtransport` class in the bittensor client module and make `TurboBtClient` compose it.

`TurboBTtransport` is a thin, typed adapter over turbobt. It exposes raw methods with turbobt-native return types and
parameters where possible. It does not translate into pylon models.

`TurboBtClient` remains the implementation of `AbstractBittensorClient`. It translates transport results into
application models and handles any higher-level orchestration that needs more than one raw call.

This approach matches the requested layering directly and keeps the rest of the service stable.

## Architecture

### 1. New `TurboBTtransport`

Add a new class:

- constructor: `__init__(wallet: Wallet | None, uri: BittensorNetwork)`
- internal state: `_raw_client`, `_is_client_ready`
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

### 2. Typed Raw Transport API

`TurboBTtransport` should expose typed raw methods rather than generic callback-based access from outside.

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

### 3. `TurboBtClient` as Mapper/Composer

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

### 4. Construction and Encapsulation

`TurboBtClient` should create a `TurboBTtransport` by default:

- `self._transport = transport or TurboBTtransport(wallet=wallet, uri=uri)`

Optional transport injection is useful for focused unit tests and keeps the new dependency explicit.

The transport remains turbobt-specific and should not implement `AbstractBittensorClient`. It is a lower-level helper,
not a second public client abstraction.

### 5. Fallback Client Compatibility

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

## Testing

### Transport Tests

Move or adapt current lifecycle/resiliency tests to target `TurboBTtransport` directly:

- cancellation does not cancel in-flight turbobt call
- `RuntimeError` triggers recreation and retry
- retry failure propagates
- non-`RuntimeError` does not trigger recreation
- `_get_bt_client()` waits for readiness
- concurrent recreation deduplicates
- `open()` sets readiness
- `close()` clears readiness
- `close()` waits for recreation to finish
- recreation waits for open to finish

### Client Tests

Keep `TurboBtClient` unit tests focused on mapping/composition:

- block translation
- neuron translation with stakes
- hyperparameter translation
- certificate translation
- weight translation from hotkey to uid
- commitment filtering by registered hotkeys
- validator sorting
- extrinsic translation

When practical, client tests should mock the transport rather than the whole turbobt call chain.

### Fallback Tests

`BittensorClient` delegation tests should remain unchanged except for any constructor changes needed to instantiate
`TurboBtClient` with an internal transport.

## Files Likely Affected

- `pylon_service/pylon_service/bittensor/client.py`
- `pylon_service/tests/unit/bittensor/turbobt/conftest.py`
- `pylon_service/tests/unit/bittensor/turbobt/test_shielded.py`
- selected turbobt unit tests under `pylon_service/tests/unit/bittensor/turbobt/`

## Risks

- over-extracting too much into transport would blur the requested raw-transport boundary
- under-typing transport methods would make the new layer less useful and harder to reason about
- transport injection must not complicate normal `TurboBtClient` construction or fallback-client behavior

## Acceptance Criteria

- `TurboBTtransport` owns `open`, `close`, `_recreate_bt_client`, and `_protect_turbobt`
- direct turbobt calls move behind typed `TurboBTtransport` methods
- `TurboBtClient` no longer reaches into `turbobt.Bittensor` directly
- `TurboBtClient` remains responsible for translation into pylon models and higher-level composition
- public `AbstractBittensorClient` behavior remains unchanged for existing callers
- existing lifecycle/retry behavior is covered by transport-focused tests
