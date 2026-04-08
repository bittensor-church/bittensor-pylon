# TurboBtContact Behavior Test Restoration Design

## Goal

Restore the valuable behavior-level regression coverage that was lost when
`pylon_service/tests/unit/bittensor/turbobt/test_shielded.py` disappeared during the
`TurboBtClient` to `TurboBtContact` refactor.

This pass should reintroduce only the transport behaviors that remain part of the current `Contact`
responsibility:

- shielding a turbobt call from caller cancellation
- recreating the raw transport and retrying once after `RuntimeError`
- propagating a repeated `RuntimeError`
- propagating non-`RuntimeError` failures without recreation

## Current Problem

The current contact unit coverage is too thin for the failure-handling logic that now lives in
`TurboBtContact`.

`TurboBtContact` is explicitly responsible for connection lifecycle, shielding, and recreation, but
the unit suite currently covers only the "not open" error path. The removed `test_shielded.py`
contained several behavior checks that still map directly to the new contact layer.

Without restoring those cases, regressions in `_protect_turbobt()` or the recreate-on-runtime-error
flow could land without any focused unit failure.

## Approach

Add direct unit tests for `TurboBtContact` in the existing file
`pylon_service/tests/unit/bittensor/contact/test_turbobt_contact.py`.

The tests should patch `pylon_service.bittensor.contact.Bittensor` so they can control the raw
transport precisely and verify recreation behavior through constructor and `__aexit__` call counts.

All restored behavior tests should exercise `TurboBtContact.get_block()` so the suite stays minimal
while still passing through the shared `_protect_turbobt()` path.

## Test Structure

Keep the existing `test_turbobt_contact.py` module and expand it with local fixtures/helpers rather
than creating a second suite.

The module should provide:

- a patched `Bittensor` constructor fixture that returns autospecced raw-client mocks
- a helper or fixture for a default opened `TurboBtContact`
- a default block-reference mock whose `.get()` behavior can be customized per test

The suite should keep the existing "requires open before use" test and add four behavior tests:

1. cancelling the caller task does not cancel the underlying turbobt block fetch
2. a `RuntimeError` during block fetch recreates the contact and retries once successfully
3. a second `RuntimeError` on retry propagates to the caller
4. a non-`RuntimeError` propagates without recreating the contact

## Assertion Rules

The tests should assert only behavior that remains meaningful at the contact boundary.

Allowed assertions:

- returned `Block` values
- raised exception type and message
- old raw client `__aexit__` called when recreation happens
- new raw client constructed and used for the retry
- no recreation for non-`RuntimeError`
- underlying mocked turbobt coroutine completes after caller cancellation

Avoid assertions that pin private coordination details, including:

- direct assertions about `_is_client_ready` transitions
- concurrent `_recreate_bt_client()` deduplication behavior
- open/close sequencing details that are only implementation mechanics

## Non-Goals

- no production-code changes in `TurboBtContact`
- no restoration of the old event/locking tests
- no router-, pool-, or integration-level coverage in this pass
- no attempt to reproduce the full deleted `test_shielded.py` suite

## Verification

Implementation verification should follow a TDD red/green cycle one behavior at a time.

The work is complete when:

- `pylon_service/tests/unit/bittensor/contact/test_turbobt_contact.py` contains the four restored
  behavior tests plus the existing "not open" test
- the restored tests exercise `TurboBtContact.get_block()`
- the tests verify shielding and recreate-on-runtime-error behavior without asserting private event
  timing
- `cd pylon_service && uv run pytest tests/unit/bittensor/contact/test_turbobt_contact.py -q`
  passes
