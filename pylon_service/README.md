# pylon_service

This package contains the Pylon HTTP service.

This README defines the intended internal structure of `pylon_service` and the API-versioning rules that both humans
and agents should follow while modifying it. It is a design and maintenance guide, not just an overview of the current
implementation.

## Imported standards

`pylon_service` follows the engineering standards from:

- `/Users/junie/synced_p/new_bittensor_ddos_shield/docs/engineering-standards.md`

The most important imported rules are:

- external Bittensor/Subtensor communication lives behind a thin `Contact`
- `Contact` owns transport concerns only: connection, reconnect, shielding, and model translation
- reconciliation, routing, caching, filtering, and business rules live above the `Contact`
- tests mock only the external boundary, which here means the `Contact`
- routers, services, handlers, cache logic, and stores stay real in tests whenever practical

## Status

Some of the code in this package still reflects an older structure. This README describes the structure we are moving
toward and should be used as the decision rule during refactors.

## Layering

The service is organized into four layers:

```text
HTTP handlers
    |
    v
versioned services
    |
    v
wallet-bound router
    |
    v
contacts
    |
    v
turbobt / Bittensor / Subtensor
```

And the model flow is:

```text
contact internal models
    -> canonical internal service data
    -> versioned API DTO models
```

## Responsibilities

### Handlers

Handlers are short and declarative.

They:

- read request data
- obtain the wallet-bound router from the pool through dependencies
- call the appropriate versioned service
- return versioned DTO models or explicit endpoint-specific responses

Handlers do not:

- contain business logic
- perform routing decisions between lite and archive
- call turbobt directly
- inherit from handlers in another API version

Handler inheritance is forbidden because it makes unstable behavior leak into stable versions.

### Services

Services contain application logic.

They:

- implement endpoint behavior
- compose multiple router calls
- apply filtering, sorting, reshaping, and compatibility logic
- convert between contact-internal models and versioned DTO models
- are used by both HTTP handlers and background tasks

Services may inherit across versions because they are internal and not directly exposed to clients.

The intended versioning pattern is:

```text
pylon_service/api/_unstable/services.py
    canonical latest service implementations

pylon_service/api/v1/services.py
    pass-through imports when behavior is unchanged
    subclasses when v1 behavior must remain different
```

Example:

```python
from pylon_service.api._unstable.services import NeuronService as UnstableNeuronService


class NeuronService(UnstableNeuronService):
    pass
```

If a stable version must preserve older behavior, subclass and override only what differs.

### Router

The router is wallet-bound and pooled.

It:

- owns one main contact and one archive contact for the same wallet
- exposes one domain-shaped method surface matching the contact surface
- decides internally whether to use the main or archive contact
- hides archive fallback policy from services

The router is not a contact subclass. It only implements the same interface shape by composition.

There is no separate router protocol just for its own sake. The router should expose the same method surface as the
contact so services can use either without caring about transport details.

### Contact

The contact is the only layer that talks to turbobt.

It:

- opens and closes connections
- shields turbobt calls
- recreates connections when needed
- translates turbobt objects into Pylon contact-internal models
- translates write inputs from Pylon models into turbobt calls

The contact does not:

- decide between lite and archive
- do any sort of postprocessing or filtering of turbobt outputs
- own cache or retry policy that belongs to services or jobs

## Contact models

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

## API versioning rules

API versioning is explicit and layered.

This diagram shows data dependency and transformation flow, not a package tree:

```text
contact models
    -> router + latest internal service logic
    -> unstable services + unstable DTOs
    -> stable services + stable DTOs
```

Meaning:

- contacts return rich internal models
- the router and latest internal services operate on those models directly
- unstable services map those models into the latest public DTOs
- stable services like `v1` may build on the same lower-layer data while preserving older public behavior

The important rule is that older stable APIs must not depend on unstable DTOs as their source of truth. They depend on
the lower-layer contact data and convert it into their own DTOs.

Rules:

- contacts are not versioned
- router is not versioned
- handlers are versioned
- services are versioned
- DTO models are versioned
- endpoint response wrapper classes should exist only when they add shape or endpoint-specific meaning

If a payload is exactly a DTO model, return that DTO model directly. Do not add empty wrapper classes just to repeat the
same shape under a second name.

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

- use a real router
- use a real pool
- use real services
- use real handlers
- use real in-process stores and cache logic when practical
- patch the contact factory to return a mock contact implementation

Do not mock:

- services, in normal cases
- router behavior
- pool behavior
- internal helpers below the chosen public seam

Services should not generally get their own direct tests. Prefer public-path tests through handlers or jobs. Test a
service directly only when there is no reasonable public entry point.

## Construction and dependency injection

Contact implementation is chosen at composition time, not by mutating a live router.

The intended pattern is:

- app startup constructs the router pool
- the pool constructs wallet-bound routers
- routers construct their contacts through a typed contact factory
- tests patch that factory to return `MockContact`

Avoid mutable APIs like `router.set_contact_class(...)`. They are unsafe with pooling and background jobs.

## Background jobs and recent-data tasks

Background jobs use the same services as HTTP handlers.

That means:

- weight commit jobs call services
- commitment jobs call services
- recent-neuron update tasks call services when they need application logic
- jobs do not bypass services to talk to contacts directly unless the operation is purely transport-level, which is not
  the common case

This keeps one execution path for public behavior.

## Package sketch

Target structure:

```text
pylon_service/
    api/
        _unstable/
            api.py
            services.py
            routers.py
        v1/
            api.py
            services.py
            routers.py
    bittensor/
        contact.py
        models.py
        router.py
        pool.py
        recent/
            ...
    services/
        ...
```

Meaning:

- `api/*/api.py` defines handlers only
- `api/*/services.py` defines versioned service entry points
- `bittensor/contact.py` defines the turbobt boundary
- `bittensor/models.py` defines contact-internal models
- `bittensor/router.py` defines wallet-bound main/archive routing
- `bittensor/pool.py` manages router reuse

## Change checklist

Before merging changes in `pylon_service`, verify:

- no handler inherits from another API version's handler
- no code outside the contact talks to turbobt directly
- archive selection logic lives in the router
- business logic lives in services, not contacts
- contact models preserve data needed by older stable APIs
- versioned services handle DTO compatibility explicitly
- tests mock only the contact boundary
