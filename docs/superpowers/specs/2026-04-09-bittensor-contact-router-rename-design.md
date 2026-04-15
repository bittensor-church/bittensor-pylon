# Bittensor Contact Router Rename Design

## Goal

Remove naming ambiguity between the service's wallet-bound Bittensor routing object and Litestar routers by renaming
the concrete bittensor-layer symbols and updating current documentation to use the new terminology consistently.

## Current Context

The service currently uses:

- `BittensorRouter` for the wallet-bound object that composes main and archive contacts and routes bittensor calls
- `BittensorClientPool` for the pool that owns and reuses those wallet-bound objects

This is confusing in two ways:

- `router` can be conflated with Litestar `Router` objects in the HTTP layer
- `client pool` implies pooled raw clients rather than pooled contact-routing facades

The repository documentation also currently describes the same architectural layer as a "router", which reinforces the
confusion.

## Approved Naming

The approved canonical names are:

- `BittensorRouter` -> `BittensorContactRouter`
- `BittensorClientPool` -> `BittensorContactPool`

There will be no compatibility aliases. The old names are internal-only and should be removed completely rather than
supported in parallel.

## Design

### Symbol Rename

Rename the concrete class names, generic bounds, constructor defaults, dependency annotations, fixtures, test helpers,
and local variable names anywhere they refer to these concrete types.

This includes:

- imports
- type annotations
- docstrings
- log messages
- exception text that names the pool or router type
- test names and test descriptions where they mention the old names

### Documentation Rename

Current repository documentation should use `BittensorContactRouter` consistently for the wallet-bound layer.

That includes:

- architecture prose in `pylon_service/README.md`
- developer-facing docs that describe the pool or the wallet-bound routing object
- inline docstrings that describe the runtime object as a router or client pool

The intent is not only to rename code symbols, but also to make the conceptual language clear: this layer is the
`BittensorContactRouter`, distinct from Litestar routers and built on top of contacts.

### Scope Boundary

This is a nomenclature refactor only. It should not:

- change routing behavior between main and archive contacts
- change pooling lifecycle behavior
- refactor module layout unless needed strictly to complete the rename
- introduce compatibility shims or aliases

Historical design and plan documents under `docs/superpowers/` should be treated as historical records, not active API
or architecture docs. They do not need bulk rewriting unless one is directly referenced by current contributor-facing
documentation and would materially mislead readers.

## Affected Areas

The implementation plan should expect changes in at least these areas:

- `pylon_service/pylon_service/bittensor/router.py`
- `pylon_service/pylon_service/bittensor/pool.py`
- `pylon_service/pylon_service/dependencies.py`
- `pylon_service/pylon_service/bittensor/recent/tasks.py`
- bittensor-layer unit tests in `pylon_service/tests/unit/bittensor/`
- shared test fixtures in `pylon_service/tests/conftest.py`
- repository and package docs, especially `pylon_service/README.md`

Additional files should be included if search confirms they import or document the renamed classes.

## Verification Expectations

Verification should prove that the rename is complete and behavior is unchanged.

Minimum checks:

- targeted search shows no remaining `BittensorRouter` or `BittensorClientPool` references in active code/docs
- service tests covering the bittensor router and pool still pass
- any tests that depend on renamed fixtures, imports, or type checks are updated and passing

Historical `docs/superpowers/specs/` and `docs/superpowers/plans/` files may still contain the old names if they are
left intentionally unchanged as historical artifacts.

## Risks

- over-renaming generic uses of the word "router" that actually refer to Litestar routers
- partial rename in tests or docs that leaves contributor-facing terminology inconsistent
- widening the refactor into unrelated architecture cleanup

The implementation plan should keep the search-and-replace surface explicit and distinguish bittensor-layer routing
terminology from HTTP routing terminology.
