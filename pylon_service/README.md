# pylon_service

This package contains the Pylon HTTP service.

This README defines the intended internal structure of `pylon_service` and the API-versioning rules that both humans
and agents should follow while modifying it. It is a design and maintenance guide, not just an overview of the current
implementation.

Pylon exposes its public HTTP API obeying semver and apiver. While semver is straightforward to follow in HTTP APIs,
apiver may be tricky, especially when optimizing the number of model classes and compatibility layers.
And matters get even trickier when you consider that some of the models used by pylon are also used by pylon_client (which also uses apiver). 
This is why, in the rest of this document, apiver considerations are a first-class problem.


## Imported standards

`pylon_service` follows the engineering standards from:

- `./engineering-standards.md`

The most important imported rules are (this is a short explanation of how those
standards have been applied here):

- external Bittensor/Subtensor communication lives behind a thin `Contact`
- `Contact` owns transport concerns only: connection, reconnect, shielding, and model translation
- reconciliation, routing, caching, filtering, and business rules live above the `Contact`
- tests mock only the external boundary, which here means the `Contact`
- routers, services, handlers, cache logic, and stores stay real in tests whenever practical

## Layering

The service is organized into the following layers:

```text
HTTP handlers                             - translate between public models and request / response models 
    |
    v
services                                  - implement logic, schedule tasks, translate from contact internal models to versioned public models
    |\                                      
    | \                        
    |  \                       
    |   tasks                             - only when needed for deferred logic execution
    |  /                       
    | /                        
    |/                         
wallet-bound BittensorContactRouter       - chooses between lite and archive contacts
    |
    v
contacts                                  - maintain a connection, reconnect and facilitate other necessary mechanisms,
    |                                       translate between turbobt / Bittensor / Subtensor models and contact internal models
    v
turbobt / Bittensor / Subtensor
```

Model layers:

- versioned response / request models
- versioned public models
- contact internal models (`pylon_commons._ustable` models, or custom models when needed to preserve older behavior)
- turbobt / Bittensor / Subtensor models

## Package structure

```text
pylon_service/
    api/
        _unstable/
            api.py          - defines versioned handlers only
            services.py     - defines versioned service entry points
            routers.py
        v1/
            api.py          - defines versioned handlers only
            services.py     - defines versioned service entry points
            routers.py
    bittensor/
        contact.py          - defines the turbobt boundary
        models.py           - defines optional contact internal models
        contact_router.py   - defines wallet-bound main/archive routing
        pool.py             - manages `BittensorContactPool` reuse
        recent/
            ...
    evm/
        contact.py          - defines the EVM RPC boundary (EvmPort, AbstractEvmContact, EvmContact)
        contact_router.py   - defines main/archive routing for EVM queries
        exceptions.py       - EVM-specific exceptions (EvmRpcError, EvmInvalidAddressError, EvmInvalidAbiError)
```

## Responsibilities

### Handlers

Handlers are short and declarative.

They:

- read request data
- obtain the wallet-bound `BittensorContactRouter` from the `BittensorContactPool` through dependencies
- obtain cache-facing collaborators such as recent-object providers through dependencies when the endpoint uses cache
- call the appropriate service
- translate domain exceptions into HTTP exceptions and status codes
- return versioned response models

Handlers do not:

- contain business logic
- perform routing decisions between lite and archive
- call turbobt / Bittensor / Subtensor directly


### Services

Services contain application logic.

They:

- implement endpoint behavior
- compose multiple `BittensorContactRouter` calls
- optionally use tasks for deferred logic execution
- access cache collaborators when the endpoint semantics require cached data
- apply filtering, sorting, reshaping, and compatibility logic
- convert between contact internal models and versioned public models

Domain grouping should stay meaningful. For example, validator reads are part of neuron-related behavior and belong in
the neuron service layer rather than in a separate `validators` service module.

Services are not HTTP-aware. That means:

- service exceptions must describe domain failure, not HTTP status
- services do not raise `NotFoundException`, `BadGatewayException`, `ServiceUnavailableException`, or other HTTP-layer
  exceptions

### Tasks

Tasks contain application deferred logic. Like services, they use `BittensorContactRouter` calls.

### BittensorContactRouter

The `BittensorContactRouter` is wallet-bound and pooled.

It:

- owns one main contact and one archive contact for the same wallet
- exposes one domain-shaped method surface matching the contact surface
- decides internally whether to use the main or archive contact
- hides archive fallback policy from services

The `BittensorContactRouter` is not a contact subclass. It only implements the same interface shape by composition.

There is no separate `BittensorContactRouter` protocol just for its own sake. The `BittensorContactRouter` should
expose the same method surface as the contact so services can use either without caring about transport details.

### Contact

The contact is the only layer that talks to turbobt (subtensor). The underlying communication lib might change one day.

It:

- opens and closes connections
- shields turbobt calls (asyncio.shield, an internal quirk fix)
- recreates connections when needed
- logs expected reconnects at `INFO` and raises a typed contact transport exception if retry still fails
- translates turbobt objects into contact internal models
- translates write inputs from Pylon models into turbobt calls

The contact does not:

- decide between lite and archive
- do any sort of postprocessing or filtering of turbobt outputs
- own cache or retry policy that belongs to services or jobs

## API versioning rules

Rules:

- contacts are not versioned
- `BittensorContactRouter` is not versioned
- handlers are versioned
- services are versioned
- DTO models are versioned

Versioned APIs and services can use their counterparts from newer versions, but **only the newest stable version can depend on unstable**. 
This ensures that introducing a change in unstable requires touching only the newest stable version to preserve compatibility.


### Handlers versioning

Versioned stable API:

- should reuse handlers from a newer API if the behavior and models are unchanged,
- should implement its own handlers using versioned services if there are behavior or model changes.

Example of a controller using its own versioned handler and re-using an unstable handler:

```python
class OpenAccessController(Controller):
    # configuration omitted
    get_commitment_endpoint = Handlers.get_commitment_endpoint
    get_neurons = UnstableHandlers.get_neurons
```

### Services versioning

Versioned services should be implemented only when there is a need to preserve different older behavior or models.

Versioned services:

- can use newer services (composition) and map results, OR
- can implement its functionality directly using `BittensorContactRouter`.

Example newer version service usage:

```python
class CommitmentService:
    async def get_commitment(self, netuid: NetUid, hotkey: Hotkey) -> tuple[Block, V1Commitment]:
        block, commitment = await self.unstable_commitment_service.get_commitment(netuid, hotkey)
        if commitment.kind != CommitmentKind.HEX_DATA:
            raise CommitmentNotFoundError()
        return block, V1Commitment.model_validate(commitment, from_attributes=True)
```

### Model versioning

Contacts use their own internal model package.

This package exists because contact-returned data may need to preserve fields that are no longer exposed by the latest
public API.

For now, contact models will often be pass-through imports of the latest canonical models. That is fine. The important
rule is that the contact layer owns its model contract and can diverge when needed.

Example layout:

```text
pylon_service/bittensor/models.py
    current contact-internal models
    often re-exporting from pylon_commons._unstable.models today
```

Example reason:

```text
contact model: Duck(name, wings, beak_color)
unstable DTO:  Duck(name, beak_color)
v1 DTO:        Duck(name, wings, beak_color)
```

If `wings` is removed from unstable but must remain in `v1`, the contact still returns a model that contains `wings`.
Then:

- unstable service maps contact `Duck` -> unstable `Duck` and drops `wings`
- v1 service maps contact `Duck` -> v1 `Duck` and preserves `wings`

The contact must not return unstable DTOs directly if doing so would destroy information needed by an older stable API.

### APIVer examples

#### Field rename

Current public field:

```text
v1 Duck:
    wings
```

New unstable field:

```text
unstable Duck:
    wing_count
```

Recommended handling:

- contact model keeps enough data for both versions
- unstable service maps `wings` -> `wing_count`
- v1 service continues returning `wings`

#### Field removal

Current public field:

```text
v1 Duck:
    wings
```

Removed from unstable:

```text
unstable Duck:
    no wings field
```

Recommended handling:

- contact model still carries `wings` if the external source still has it
- unstable service drops it
- v1 service preserves it

#### Field split

Current public field:

```text
v1 Duck:
    wings
```

New unstable fields:

```text
unstable Duck:
    left_wing
    right_wing
```

Recommended handling:

- contact model carries enough source data for both
- unstable service emits `left_wing` and `right_wing`
- v1 service combines them back into `wings` if that is still the stable contract

#### Behavior change

Suppose unstable stops returning some derived data, but `v1` already promised it.

Recommended handling:

- keep the contact returning the raw information needed for both versions
- keep the `v1` logic in `pylon_service/api/v1/services.py`
- let unstable remove the behavior in `pylon_service/api/_unstable/services.py`

This is why versioned services may differ in logic, not only in DTO conversion.

## Testing rules

Only the contact is mocked.

In tests:

- use a real `BittensorContactRouter`
- use a real `BittensorContactPool`
- use real services
- use real handlers
- use real in-process stores and cache logic when practical
- use an `autouse=True` shared-world fixture that preconfigures a consistent default chain view for all tests
- patch the contact factory to return a mock contact implementation
- assert HTTP status codes inline
- assert full response bodies via checked-in `syrupy` snapshots

The shared world is the default testing topology. Tests should not rebuild the whole neuron / subnet world from
scratch unless they are exercising a genuinely different scenario. If two tests need incompatible default state, use
different `netuid`s inside the shared world instead of fighting over one subnet.

Ordinary subnet scenarios belong in the shared world too. For example, validator-ordering and commitment-filtering
cases should use dedicated shared-world `netuid`s rather than inline per-test neuron or subnet-state builders. Per-test
transport overrides are for focused deltas, not for reconstructing normal subnet data from scratch.

Tests may still configure the mock contact directly when needed, for example:

- to simulate a state change between two public API calls
- to simulate a transport failure on one call and recovery on the next
- to override one part of the shared world for a focused scenario

Do not add durable tests whose only purpose is verifying that `MockBittensorContact` records calls or otherwise
implements obvious mock mechanics. The mock contact should be validated by the public-path tests that use it. A
temporary migration test is acceptable only if it is removed once the surrounding test seam is stable.

Recent-object cache access should be exercised through services, not by having handlers read cache directly. The cache
must return the same model shapes as `BittensorContactRouter`/contact reads so cached and uncached paths share service
logic cleanly.

### Snapshot convention

Use `syrupy` for response body snapshots.

Recommended pattern:

```python
assert response.status_code == 200
assert snapshot_json == response.json()
```

If a response contains values that are hard to freeze, use a `syrupy` matcher sparingly, for example for:

- timestamps
- generated ids
- hashes or similar opaque transport values

Prefer snapshotting the full JSON body after minimal normalization rather than asserting a few selected fields.

Recommended fixture:

```python
from syrupy.extensions.json import JSONSnapshotExtension


@pytest.fixture
def snapshot_json(snapshot):
    return snapshot.use_extension(JSONSnapshotExtension)
```

Recommended matcher usage:

```python
from syrupy.matchers import path_type

matcher = path_type(
    {
        "timestamp": (int,),
        r".*hash$": (str,),
    },
    regex=True,
)

assert response.status_code == 200
assert snapshot_json(matcher=matcher) == response.json()
```

Update procedure:

- normal verification: run `pytest` without snapshot update flags
- intentional snapshot refresh: run `pytest --snapshot-update`
- review the changed snapshot files before committing

The required public-API scenario checklist lives in:

- [tests/SCENARIOS.md](/pylon_service/tests/SCENARIOS.md)

Do not mock:

- services, in normal cases
- `BittensorContactRouter` behavior
- `BittensorContactPool` behavior
- internal helpers below the chosen public seam

Services should not generally get their own direct tests. Prefer public-path tests through handlers or jobs. Test a
service directly only when there is no reasonable public entry point.

## Construction and dependency injection

Contact implementation is chosen at composition time, not by mutating a live `BittensorContactRouter`.

The intended pattern is:

- app startup constructs the `BittensorContactPool`
- the pool constructs wallet-bound `BittensorContactRouter` instances
- `BittensorContactRouter` instances construct their contacts through a typed contact factory
- tests patch that factory to return `MockContact`

Avoid mutable APIs like `contact_router.set_contact_class(...)`. They are unsafe with pooling and background jobs.

## Background jobs and recent-data tasks

Background jobs use the same services as HTTP handlers.

That means:

- weight commit jobs call services
- commitment jobs call services
- recent-neuron update tasks call services when they need application logic
- jobs do not bypass services to talk to contacts directly unless the operation is purely transport-level, which is not
  the common case

This keeps one execution path for public behavior.


## Observability

The service ships optional, disabled-by-default integrations for error tracking and tracing. Both are enabled purely
by setting an endpoint/DSN — no separate feature flag.

### Sentry

- Enabled iff `PYLON_SENTRY_DSN` is set. Reports errors through the Litestar and asyncio integrations.

### OpenTelemetry traces

- Enabled iff `PYLON_OTEL_COLLECTOR_ENDPOINT` is set to the base URL of an OTLP collector (e.g. `http://alloy:4318`).
  Traces are exported via OTLP HTTP/protobuf to `<endpoint>/v1/traces`.
- When enabled, auto-instrumentation covers: the Litestar HTTP server (incoming requests), `httpx` and `aiohttp`
  (outgoing HTTP — chain RPC over `httpx`, web3/EVM RPC over `aiohttp`), and `SQLAlchemy` (database). The active span's
  `trace_id` / `span_id` are injected into structured logs for log↔trace correlation.
- Outgoing HTTP URLs are recorded on spans verbatim, so do **not** embed credentials in the configured RPC URLs
  (`PYLON_EVM_RPC_URL`, `PYLON_EVM_ARCHIVE_RPC_URL`, or an `http(s)://` `PYLON_BITTENSOR_NETWORK`) — see the warning in
  `pylon_commons/settings.py`. The same URLs also appear in debug logs and the Prometheus `rpc_url` metric label.
- **Not traced:** the default Bittensor chain transport in `turbobt` is websockets, for which no OpenTelemetry
  instrumentation exists — so chain RPC calls are not auto-traced. They are covered only when
  `PYLON_BITTENSOR_NETWORK` points at an `http(s)://` URI, where `turbobt` falls back to `httpx`.
- The service does not ship a collector. Running and configuring Alloy (or any OTLP collector) at the configured
  endpoint, including any tail-sampling or endpoint filtering, is the deployer's responsibility.
- **Long-lived on-chain submission spans:** background submission tasks (`apply_weights`, `set_commitment`,
  `set_revealed_commitment`) emit one short, self-contained span per retry attempt, each with its own `trace_id` and
  span links back to the originating request and the previous attempt — this keeps traces short across the (up to 200)
  retries. A *single* attempt can still take up to 120s while waiting for extrinsic finalization (~12s per block, longer
  under congestion). Backends that bound trace lifetime — notably Tempo's `max_trace_live` (default 30s) — will split
  such an attempt's trace. If you use Tempo, set `max_trace_live` to at least 180s (a margin above the 120s submission
  timeout) and `max_trace_idle` to at least 30s.
- Traces require the service to run as a single uvicorn process; both `--workers` and `WEB_CONCURRENCY` (other than
  `1`) are rejected (see `uvicorn_entrypoint.py`) because the SDK is initialised once at import and would not survive
  `fork()`.

## Change checklist

Before merging changes in `pylon_service`, verify:

- no code outside the contact talks to turbobt directly
- archive selection logic lives in the `BittensorContactRouter`
- business logic lives in services, not contacts
- contact models preserve data needed by older stable APIs
- versioned services handle DTO compatibility explicitly
- tests mock only the contact boundary
