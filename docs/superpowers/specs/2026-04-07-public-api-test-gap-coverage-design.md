# Public API Test Gap Coverage Design

## Goal

Fill the missing public HTTP test coverage in `pylon_service` so the suite explicitly covers the documented public API
surface for both `v1` and `_unstable`, with full response-body assertions captured as `syrupy` snapshots.

Also add a focused coverage report for handlers and services so the test pass can measure how well those public-path and
application-logic layers are exercised, without yet gating the build on a minimum threshold.

## Current Problem

The current unit HTTP suite covers only part of `v1` and almost none of `_unstable`.

The most important gaps are:

- no `_unstable` public HTTP coverage
- missing `200` happy paths for several `v1` endpoints such as block neurons, latest neurons, validators, commitment
  reads, and own commitment
- missing coverage for login and latest-block-info
- missing commitments-collection endpoint coverage
- missing explicit unknown-identity `404` coverage across identity-scoped endpoints

This leaves [SCENARIOS.md](/Users/junie/synced_p/bittensor-pylon/pylon_service/tests/SCENARIOS.md) out of sync with the
actual suite.

## Approach

Use a scenario-first test expansion.

Each public API scenario listed in `SCENARIOS.md` should have an explicit unit HTTP test, or an explicit reason in the
scenario document if the scenario is intentionally out of scope. The implementation should favor readable tests over
heavy parametrized matrices.

The test style remains:

- status code asserted inline
- full response body asserted with `syrupy`
- shared `autouse=True` world fixture provides defaults
- per-test mock-contact overrides are used only when a scenario needs different transport behavior
- coverage reporting is limited to handlers and services for this pass

## Test Structure

Keep version boundaries visible in the test layout.

The implementation should preserve the current `v1` endpoint groupings and add `_unstable` endpoint coverage in a
parallel structure instead of hiding version differences inside a single large parameter matrix.

Preferred organization:

- keep `tests/unit/open_access_endpoints/` and `tests/unit/identity_endpoints/` for `v1`
- add matching `_unstable` endpoint directories for `_unstable`
- add shared public-route tests for versioned login/latest-block/extrinsic where that improves clarity, otherwise keep
  them version-specific

The key rule is readability: when a test fails, the failing scenario should be obvious from the test name and snapshot
path alone.

## Required Scenario Coverage

This pass should add or complete tests for:

- `POST /api/{version}/login/identity/{identity_name}`
  - success
  - unknown identity
  - missing token or invalid body
- `GET /api/{version}/block/latest`
  - success
- `GET /api/{version}/block/{block_number}/extrinsic/{extrinsic_index}`
  - already partly covered in `v1`; add `_unstable` parity
- `GET .../block/{block_number}/neurons`
  - `200` happy path
  - existing `404` path retained
- `GET .../block/latest/neurons`
  - `200` happy path
- `GET .../block/recent/neurons`
  - existing success and `503` paths retained
- `GET .../block/{block_number}/validators`
  - `200` happy path asserting only validator-permit neurons in expected order
  - existing `404` path retained
- `GET .../block/latest/validators`
  - `200` happy path
- `GET .../block/latest/certificates`
  - already covered in `v1`; add `_unstable` parity
- `GET .../block/latest/certificates/{hotkey}`
  - already partly covered in `v1`; add `_unstable` parity
- `GET .../block/latest/commitments`
  - all-valid success
  - mixed-result filtering success
  - empty result success
- `GET .../block/latest/commitments/{hotkey}`
  - `200` happy path
  - existing `404` path retained
- `GET .../block/latest/commitments/self`
  - `200` happy path
  - existing `404` path retained
- `GET .../block/latest/certificates/self`
  - already partly covered in `v1`; add `_unstable` parity
- `POST .../certificates/self`
  - already partly covered in `v1`; add `_unstable` parity plus unknown-identity case
- `PUT .../weights`
  - existing scheduling and validation paths retained
  - add unknown-identity case
- `POST .../commitments`
  - existing ack/validation/retry paths retained
  - add unknown-identity case

## Unknown Identity Rule

Unknown-identity `404` behavior should be covered explicitly in HTTP tests rather than inferred from one representative
route.

At minimum, each identity-only endpoint family should have its own unknown-identity test:

- login
- neurons read
- validators read
- commitments read
- own certificate
- own commitment
- weights
- set commitment
- generate certificate keypair

## Snapshot Rules

- snapshots must be deterministic
- recent-neuron happy-path tests should continue seeding factories
- matchers remain sparse and only for values that are genuinely difficult to freeze
- if a scenario produces two distinct successful responses in one test, separate snapshot files are acceptable

## Coverage Reporting

This pass should add an explicit coverage-reporting command that focuses on:

- `pylon_service/api/_unstable/`
- `pylon_service/api/v1/`
- `pylon_service/services/`

The report should be easy to run locally and in CI later, but it should not yet fail the run based on a percentage
threshold.

The purpose of the report in this pass is:

- confirm that the new HTTP test coverage actually reaches the handlers and services we care about
- highlight remaining gaps after the scenario expansion
- create a stable reporting scope that can later be extended to other parts of the codebase

It is acceptable if uncovered lines remain after this pass, as long as the report is produced and reviewed.

## Non-Goals

- no change to runtime service behavior
- no change to public API shape
- no extra tests whose only purpose is checking `MockBittensorContact` mechanics
- no broad matrix abstraction that obscures scenario names

## Verification

The implementation is complete when:

- the public API scenarios in `SCENARIOS.md` are satisfied for both `v1` and `_unstable`
- all new happy and unhappy path tests assert full response bodies
- a focused coverage report for handlers and services is generated and reviewed
- `cd pylon_service && uv run --python 3.13 pytest tests/unit -q` passes
