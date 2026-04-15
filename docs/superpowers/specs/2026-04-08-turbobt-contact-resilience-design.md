# TurboBtContact Resilience Integration Design

## Goal

Add a dedicated resilience-focused integration suite under `pylon_service/tests/integration/contact_resilience/`
that exercises a single live `TurboBtContact` instance through transport disruption, task cancellation, and transport
recovery scenarios.

The suite should prove two things for each scenario:

- the failure mode actually happens
- the same `TurboBtContact` instance can complete a later read after the disruption is removed

The failure assertions should be backed by in-process Prometheus histogram observations from
`pylon_bittensor_operation_duration_seconds`, not by scraping the service `/metrics` endpoint.

## Current Problem

The repository now has direct contact integration coverage for normal read and write behavior, but it still does not
exercise how `TurboBtContact` behaves when the underlying subtensor transport becomes unhealthy or abruptly changes
state.

The untested gaps are:

- connection loss while reusing an already-open contact
- cancellation of an in-flight read on a live contact
- asymmetric transport breakage where TCP traffic can flow one way but not the other

Without these scenarios, the integration suite does not verify whether the live `turbobt` boundary remains usable
after realistic disruption patterns.

## Package Layout

Create a new sibling integration package:

- `pylon_service/tests/integration/contact_resilience/`

Planned files:

- `pylon_service/tests/integration/contact_resilience/__init__.py`
- `pylon_service/tests/integration/contact_resilience/conftest.py`
- `pylon_service/tests/integration/contact_resilience/test_restart_recovery.py`
- `pylon_service/tests/integration/contact_resilience/test_cancellation_recovery.py`
- `pylon_service/tests/integration/contact_resilience/test_proxy_recovery.py`

This package is intentionally separate from `tests/integration/contact/` so functional API coverage and resilience
coverage remain easy to reason about independently.

## Shared Test Mechanics

The new package should reuse the existing local-chain tooling from `tests/integration/localchain/` and the existing
contact fixture pattern from `tests/integration/contact/conftest.py`.

`conftest.py` in the resilience package should provide only the fixtures specific to these scenarios:

- a package-scoped `LocalChainManager` based on `prepared-localnet:latest`
- direct `TurboBtContact` fixtures opened with `async with TurboBtContact(...) as contact: yield contact`
- proxy-specific URL or contact fixtures for the toxiproxy scenario
- a package-scoped Docker-managed `toxiproxy` container fixture
- a helper for reading Prometheus histogram child values and returning labeled counts for delta assertions

The metrics helper should inspect the in-process Prometheus histogram object directly rather than parsing Prometheus
text output. Tests should snapshot metric state before the action under test and assert deltas afterward, so existing
samples from other tests do not matter.

## Metric Contract

The resilience contract is defined only in terms of the existing histogram
`pylon_bittensor_operation_duration_seconds`.

For each scenario, tests should assert deltas on the relevant labeled histogram series:

- baseline or post-recovery reads produce at least one new sample with `status="success"`
- forced restart and proxy-disruption reads produce at least one new sample with `status="error"`
- the cancelled read produces at least one new sample with `status="cancelled"`

The assertions should target the `operation` label for the specific read method under test, preferably
`get_latest_block`, and should filter to the contact URI used by that scenario.

The suite should not add new production metrics for this pass.

## Restart Recovery Scenario

`test_restart_recovery.py` should verify that an already-open contact remains usable after the local subtensor process
is stopped and started again.

Expected sequence:

1. Open a `TurboBtContact` against the local chain.
2. Perform a baseline successful read such as `get_latest_block()`.
3. Stop the local subtensor container via the existing `LocalChainManager`.
4. Retry reads until a transport failure is observed and assert that the failure is real.
5. Restart the same `LocalChainManager` instance so the endpoint remains the same.
6. Retry reads until the same contact instance succeeds again.
7. Assert histogram deltas include both `error` and later `success` samples for the read operation.

The test should not create a second contact instance for the recovery assertion.

## Cancellation Recovery Scenario

`test_cancellation_recovery.py` should verify that cancelling an in-flight read task does not poison the contact for
future reads.

To make cancellation deterministic, the test should first put the transport into a blocked state. The recommended
approach is to route the contact through a temporary proxy condition that causes the read to hang instead of returning
immediately.

Expected sequence:

1. Open a `TurboBtContact`.
2. Activate the blocking condition before the read starts.
3. Launch `get_latest_block()` in an `asyncio.Task`.
4. Wait until the task is in-flight, then cancel it.
5. Assert `asyncio.CancelledError`.
6. Remove the blocking condition.
7. Perform a fresh read on the same contact instance and assert success.
8. Assert histogram deltas include one `cancelled` sample and a later `success` sample.

The test should verify the contact still works after cancellation, not merely that the task can be cancelled.

## Proxy Recovery Scenario

`test_proxy_recovery.py` should verify that the contact can recover after an asymmetric transport failure introduced by
`toxiproxy`.

The test harness should start a disposable `toxiproxy` Docker container and configure a proxy in front of the local
subtensor websocket endpoint. `TurboBtContact` should connect through the proxy rather than directly to the chain.

Expected sequence:

1. Create the proxied websocket endpoint.
2. Open a `TurboBtContact` through the proxy and perform a baseline successful read.
3. Add a one-way toxic that breaks only one direction of the stream.
4. Attempt a read and assert that it fails while the toxic is active.
5. Remove the toxic or reset the proxy.
6. Retry the read until the same contact instance succeeds again.
7. Assert histogram deltas include both `error` and later `success` samples.

The toxiproxy control path should use its HTTP API directly, for example through `httpx`, rather than introducing an
additional test dependency.

## Failure Determinism

These tests should not rely on single-shot timing luck.

They should use bounded retry helpers where needed to establish:

- that shutdown has actually produced a failing read before restart
- that a proxy toxic is actually active before recording the failure assertion
- that recovery has actually happened before asserting the post-recovery success

If a scenario cannot force a clear failure signal, the test should fail rather than silently accepting a false
positive.

## Non-Goals

- no changes to production `TurboBtContact` behavior in this pass
- no new production metrics
- no coverage through the HTTP service or `/metrics` endpoint
- no custom Python TCP proxy implementation when `toxiproxy` already covers the asymmetric-failure requirement
- no second contact instance created just to prove recovery

## Verification

The work is complete when:

- the new `tests/integration/contact_resilience/` package exists with the three scenario modules
- each scenario verifies that the expected failure really occurred
- each scenario verifies that the same `TurboBtContact` instance later succeeds
- metric assertions are based on in-process histogram deltas for `success`, `error`, and `cancelled` as applicable
- the proxy scenario uses a Docker-managed `toxiproxy` sidecar and its HTTP API
- `cd pylon_service && PYLON_ENV_FILE=tests/.test-env uv run pytest -s -vv tests/integration/contact_resilience/`
  passes
