# Router-Level Exception Handlers Design

## Goal

Replace the ad hoc `_raise_http_error()` helper usage in `pylon_service` with Litestar `exception_handlers`
registered on the version routers, while preserving the current HTTP status codes and response bodies.

The mapping logic should come from one shared module today, but `v1` and `_unstable` must each register handlers in
their own router so either version can diverge later without importing HTTP behavior from the other.

## Current Problem

The current implementation defines `_raise_http_error()` in
`pylon_service/pylon_service/api/_unstable/api.py` and imports it into `pylon_service/pylon_service/api/v1/api.py`.

That creates two problems:

- `v1` depends on `_unstable` for HTTP-layer behavior
- many handlers contain repetitive `try/except Exception` blocks whose only purpose is mapping domain exceptions into
  HTTP exceptions

This is awkward in Litestar because the framework already supports layered exception handling, and it conflicts with
the service README guidance that versioned handlers should translate domain exceptions at the HTTP boundary without
cross-version leakage.

## Approach

Move the shared exception-to-HTTP translation into a common HTTP-layer module such as
`pylon_service/pylon_service/api/exception_handlers.py`.

That module should own:

- the handler callables that translate domain exceptions into `NotFoundException`, `ServiceUnavailableException`, and
  `BadGatewayException`
- a shared `exception_handlers` mapping suitable for Litestar router registration

`pylon_service/pylon_service/api/v1/routers.py` and
`pylon_service/pylon_service/api/_unstable/routers.py` should each import that shared mapping and pass it to their own
`Router(...)` constructor via `exception_handlers=...`.

This keeps the current behavior centralized without making one API version depend on the other for HTTP behavior.

## Registration Boundary

The registration point should be version-local and router-level.

Why router-level:

- it applies to both controller methods and standalone function handlers mounted on the version router
- it keeps the mapping near the version assembly point instead of scattering it across controllers
- it provides a clear future extension point where `v1` or `_unstable` can override or replace the shared mapping

Why not app-level:

- this behavior is part of versioned API assembly, not global app policy
- app-level registration would make later per-version divergence harder

Why not controller-level only:

- standalone handlers such as `get_extrinsic_endpoint` and `get_latest_block_info_endpoint` are mounted alongside
  controllers and should be covered by the same version-local policy where relevant

## Handler Behavior

Handlers that currently do nothing except catch an exception and call `_raise_http_error()` should be simplified to let
domain exceptions propagate to Litestar.

The shared mapping should preserve the current behavior:

- `BlockNotFoundError`
- `ExtrinsicNotFoundError`
- `CertificateNotFoundError`
- `CommitmentNotFoundError`
  - map to `404 Not Found`
- `RecentObjectMissingError`
- `RecentObjectStaleError`
  - map to `503 Service Unavailable`
- `CertificateGenerationFailedError`
  - map to `502 Bad Gateway`

The response payload shape should remain whatever Litestar currently produces for those HTTP exceptions so the existing
tests continue to pass without snapshot changes.

## Explicit Endpoint Exceptions

Not every endpoint should be rewritten to use the shared router mapping.

Endpoints that intentionally translate a broader or different failure mode should keep explicit local handling until
there is a clear shared rule for them. In the current code, `set_commitment_endpoint()` is the main example because it
maps arbitrary task failure into `BadGatewayException` rather than a narrow domain-exception set.

The refactor should therefore remove only the explicit exception handling that is redundant with the shared router
mapping.

## File Responsibilities

The intended file boundaries after the refactor are:

- `pylon_service/pylon_service/api/exception_handlers.py`
  - shared domain-exception to HTTP-exception handler functions and reusable mapping
- `pylon_service/pylon_service/api/v1/routers.py`
  - version-local registration of shared exception handlers for `v1`
- `pylon_service/pylon_service/api/_unstable/routers.py`
  - version-local registration of shared exception handlers for `_unstable`
- `pylon_service/pylon_service/api/v1/api.py`
  - versioned handlers with no import from `_unstable.api` for HTTP error translation
- `pylon_service/pylon_service/api/_unstable/api.py`
  - versioned handlers with `_raise_http_error()` removed

## Testing Expectations

This should be a no-behavior-change refactor from the public HTTP perspective.

The existing unit tests already cover the key response classes:

- `404` for missing blocks, extrinsics, certificates, and commitments
- `503` for missing or stale recent objects
- `502` for certificate generation failures and commitment submission failures where explicitly handled

The implementation should therefore prefer reusing the existing tests rather than rewriting them. If a test fails after
the refactor, that should be treated as evidence that the router-level handler registration changed externally observed
behavior and needs adjustment.

Verification should specifically confirm that router-level registration catches exceptions from:

- controller methods on `OpenAccessController`
- controller methods on `IdentityController`
- standalone route handlers registered directly on each version router, especially `get_extrinsic_endpoint`

## Non-Goals

- no change to service-layer exception types
- no change to public route structure
- no change to response body shape or status codes
- no attempt to generalize unrelated endpoint-specific error handling in the same pass
- no cross-version import of HTTP behavior from `v1` to `_unstable` or vice versa

## Verification

The refactor is complete when:

- `_raise_http_error()` is removed
- `v1/api.py` no longer imports HTTP error translation from `_unstable/api.py`
- both version routers register exception handlers locally
- the existing `404`, `503`, and `502` endpoint tests still pass without expected-output changes
- the focused `pylon_service` unit test runs for affected endpoint suites pass cleanly
