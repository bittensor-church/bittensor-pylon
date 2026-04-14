# Identity-Scoped Shielded Neuron Fetching Design

## Goal

Integrate `bt_ddos_shield_client` into Pylon with a low-footprint change that affects only identity-based neuron fetching. Open-access behavior must remain unchanged.

The change must apply to all identity-scoped neuron-derived reads:

- direct neuron fetches
- validator fetches
- recent-neurons refresh and reads

Any recent/cache behavior must remain partitioned by identity versus open access.

## Scope

In scope:

- `pylon_service` identity-scoped neuron fetching
- identity-scoped validator fetching because it is derived from neurons
- identity-scoped recent-neurons update path because it uses the same client
- test setup updates to use `ShieldMetagraphTestRig`
- refactor client/pool ownership from optional `Wallet` to optional `Identity`

Out of scope:

- any open-access fetch path
- changing ddos shield library logic
- changing endpoint shapes or API contracts
- changing recent cache key design beyond preserving current identity separation
- broad refactors unrelated to neuron fetching

## Current State

`BittensorClientPool.acquire()` accepts an optional `Wallet` and returns a pooled client instance keyed by wallet identity. `AbstractBittensorClient` and its implementations also store an optional wallet.

`TurboBtClient.get_neurons_list()` currently uses plain turbobt:

- get raw turbobt client
- call `subnet(netuid).list_neurons(block_hash=...)`
- fetch subnet state
- translate neurons

`get_neurons()` and `get_validators()` build on `get_neurons_list()`. The recent-neurons scheduler and provider also use the same client path, so neuron-source changes naturally propagate there.

Recent-object cache separation already exists:

- open access uses subnet-only cache context
- identity uses subnet + identity hotkey cache context

This existing separation must remain intact.

## Selected Approach

Keep the current service architecture and inject ddos-shield behavior at the narrowest shared point: `TurboBtClient.get_neurons_list()`.

Refactor pool/client ownership from optional `Wallet` to optional `Identity` so neuron fetching can decide at runtime whether the current request is identity-scoped and whether the requested subnet matches the identity subnet.

Use `ShieldedSubnetReference` only when all of the following are true:

- the client has an identity
- the requested `netuid` matches `identity.netuid`
- the call is fetching neurons

Otherwise use existing plain turbobt behavior.

## Architecture

### 1. Identity-Based Client Ownership

Replace optional wallet parameters with optional identity parameters in:

- `BittensorClientPool.acquire(identity: Identity | None)`
- `AbstractBittensorClient.__init__(identity: Identity | None, uri: ...)`
- `TurboBtClient`
- `BittensorClient`
- mocks and test fixtures that construct these clients

`AbstractBittensorClient` should expose:

- `self.identity`
- `self.wallet`, derived as `identity.wallet` when identity is present, else `None`

This keeps downstream turbobt calls working while making identity metadata available where routing decisions are needed.

### 2. Shielded Subnet Reference

Add a cached shielded subnet reference to `TurboBtClient`, created lazily and used only for identity-matching neuron fetches.

Behavior in `get_neurons_list(netuid, block)`:

1. If `self.identity is None`, use plain turbobt `subnet(netuid).list_neurons(...)`.
2. If `self.identity is not None` and `netuid != self.identity.netuid`, use plain turbobt.
3. If `self.identity is not None` and `netuid == self.identity.netuid`, use cached `ShieldedSubnetReference`.

Creation and reuse rules:

- first matching call creates the reference with `ShieldedSubnetReference.from_bittensor(...)`
- later matching calls reuse the cached reference
- the reference is associated with the currently open raw turbobt client

### 3. Client Recreation Handling

`TurboBtClient._recreate_bt_client()` currently replaces the raw turbobt client after runtime failures.

When that happens:

- invalidate the existing cached shielded subnet reference
- preserve enough state to rebuild it against the new raw client
- on the next matching neuron fetch, create a fresh shielded reference
- if a prior shielded reference exists and is structurally reusable, rebuild it with `clone(new_client)`

The important constraint is that no cached `ShieldedSubnetReference` may continue to point at a recycled raw client.

### 4. Certificate Path Derivation

Do not add new settings for certificate location.

Derive the certificate path programmatically from the identity wallet hotkey file location. The target file should live next to the hotkey file in the wallet directory layout, using a deterministic sibling filename.

Expected layout pattern:

- hotkey file: `<wallet_path>/<wallet_name>/hotkeys/<hotkey_name>`
- certificate file: `<wallet_path>/<wallet_name>/hotkeys/<hotkey_name>.pem`

This derived path is passed explicitly to the shield library when constructing the shielded subnet reference.

## Data Flow

Identity request for neurons or validators on the identity subnet:

1. endpoint resolves `Identity`
2. dependency acquires a client using that identity
3. `get_neurons_list()` detects identity-scoped matching subnet
4. shielded subnet reference fetches neurons through `bt_ddos_shield_client`
5. Pylon translates neurons and derives validators as it does today
6. recent-neurons updater stores identity-scoped results under existing identity cache keys

Identity request for a different subnet, or open-access request:

1. client falls back to existing plain turbobt `list_neurons()` path
2. all remaining logic is unchanged

## Caching and Recent Data

No recent-object cache key changes are required.

The current cache partitioning already satisfies the requirement:

- open access caches are separate from identity caches
- identity caches are separated by identity hotkey

This design preserves that behavior by changing only the neuron source for identity-matching fetches. Recent cache reads and writes continue to use the existing `SubnetContext` and `IdentitySubnetContext` logic.

## Error Handling

Preserve current client behavior:

- shielded fetching participates in the existing `_protect_turbobt()` and client recreation flow as much as possible
- non-matching netuid requests continue using standard turbobt
- if shielded neuron fetching fails because the underlying turbobt client is recycled, the cached shielded reference must be refreshed before retry

Do not add special endpoint-level error branches for ddos shield integration in this change.

## Testing

### Unit and Service Tests

Update tests to reflect the optional-identity client and pool API:

- pool tests
- dependency/fixture wiring
- mock client construction
- recent-object tests that acquire identity clients

Add focused tests for:

- open-access neuron fetching still uses plain path
- identity neuron fetching on matching subnet uses shielded subnet reference
- identity neuron fetching on non-matching subnet falls back to plain path
- cached shielded subnet reference is invalidated/rebound after raw client recreation
- identity validator fetching inherits shielded neuron source

### Shield Test Rig

Use `ShieldMetagraphTestRig` in test setup for shield-specific behavior verification. Keep this narrow:

- configure validator certificate path
- configure on-chain certificate behavior
- configure miner fixtures with shield addresses
- assert that identity-scoped neuron fetch returns shield-rewritten addresses

Do not test internals of ddos shield logic beyond proving that Pylon integrates with the library correctly.

## Files Likely Affected

- `pylon_service/pylon_service/bittensor/client.py`
- `pylon_service/pylon_service/bittensor/pool.py`
- `pylon_service/pylon_service/dependencies.py`
- `pylon_service/tests/conftest.py`
- `pylon_service/tests/mock_bittensor_client.py`
- selected unit tests under `pylon_service/tests/unit/bittensor/`
- selected endpoint tests relying on identity client acquisition

## Risks

- the wallet-to-certificate path derivation must rely on stable wallet path semantics
- the identity refactor touches constructor and pool signatures across tests
- shielded subnet reference reuse must not outlive the raw turbobt client it wraps

## Acceptance Criteria

- identity-scoped neuron fetching uses `bt_ddos_shield_client` only when `netuid == identity.netuid`
- identity-scoped validator fetching inherits the same neuron source
- identity-scoped recent-neurons updates inherit the same neuron source
- open-access neuron and validator fetching remain unchanged
- recent-object cache separation remains distinct for open access versus each identity
- shield integration is localized to client/pool internals and test setup, without endpoint contract changes
