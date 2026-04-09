# Contact Resilience Logging Design

## Goal

Change `TurboBtContact` so expected Subtensor disconnects are treated as routine transport events rather than
traceback-worthy failures, while final contact-level transport failure is raised as a typed Pylon exception that upper
layers can handle consistently.

The integration suite should then explicitly guard that Pylon does not regress back to traceback-heavy reconnect
logging for these expected scenarios.

## Current Problem

`TurboBtContact` currently treats transient transport breakage too noisily inside Pylon:

- reconnect paths in `pylon_service/pylon_service/bittensor/contact.py` use traceback logging
- permanent failure after retry still propagates raw lower-level exceptions instead of a Pylon-owned transport error
- resilience integration tests verify recovery and metrics, but they do not assert the Pylon log shape, so noisy
  reconnect logging can return unnoticed

Losing the Subtensor connection is an expected production event. It should be visible, but only as a brief
informational record unless the contact operation truly fails.

## Scope

This change is limited to Pylon-owned behavior.

In scope:

- `TurboBtContact` retry, logging, and final exception translation
- shared HTTP exception mapping for the new typed contact failure
- unit and integration coverage that prevents traceback-style Pylon reconnect logs from returning
- a brief note in `pylon_service/README.md` describing the intended behavior

Out of scope:

- any attempt to suppress or rewrite upstream `turbobt` or `websockets` logger behavior in this PR
- transport policy changes in the router, services, or jobs beyond consuming the new typed exception
- adding new metrics

## Desired Contact Contract

`TurboBtContact` should keep the existing high-level resilience strategy:

- perform the operation through the current client
- if a reconnect-worthy transport/runtime failure occurs, recreate the client and retry once
- if the retry succeeds, return the result

What changes is how the contact reports these states.

### Expected Reconnect Path

For expected disconnect and reconnect events, the contact should emit one-line `INFO` logs without traceback output.

The log message should identify only the relevant transport gist, such as:

- operation name
- contact URI
- exception type
- concise exception message

This preserves operational visibility without treating normal connection churn as an application error.

### Final Failure Path

If the operation still fails after the recreate-and-retry flow, the contact should raise a typed Pylon exception for
both reads and writes.

That exception should:

- live in `pylon_service/pylon_service/bittensor/exceptions.py`
- represent a contact-level transport failure rather than a business-domain failure
- carry structured context needed by higher layers, at minimum the operation name, URI, original exception type, and a
  concise transport gist
- avoid embedding traceback text in the exception detail

The contact should not eagerly log the final failure with traceback just to preserve information that is already
available on the exception object.

## Exception Mapping Above The Contact

The shared handler wrapper in `pylon_service/pylon_service/api/utils.py` should map the new typed contact transport
failure to a stable gateway-style HTTP response.

This keeps the transport rule centralized:

- contact owns retry and failure translation
- handlers own HTTP representation
- services and jobs can later choose policy based on the typed exception instead of parsing raw transport exceptions or
  log text

This design intentionally keeps transport semantics out of `BittensorContactRouter`, which should remain a routing
facade rather than a second transport-policy layer.

## Test Design

### Unit Coverage

`pylon_service/tests/unit/bittensor/contact/test_turbobt_contact.py` should add focused assertions for the new
contract:

- transient `RuntimeError` and `ConnectionClosed` recovery logs are emitted at `INFO`
- those transient recovery logs do not carry traceback data
- permanent failure after retry raises the new typed Pylon contact transport exception
- the raised exception exposes the expected transport gist and preserved cause information

The existing recreation tests already provide most of the transport setup needed for these additions.

### Integration Coverage

The resilience integration tests should start asserting the Pylon log contract in addition to recovery and histogram
behavior.

Add `caplog` assertions to:

- `pylon_service/tests/integration/contact_resilience/test_proxy_recovery.py`
- `pylon_service/tests/integration/contact_resilience/test_restart_recovery.py`

Those assertions should be scoped to `pylon_service.bittensor.contact` and verify that expected disconnect/recovery
scenarios do not produce traceback-bearing Pylon records.

The integration tests should not assert anything about upstream `turbobt` logging in this PR. The purpose here is only
to prevent regressions in Pylon-owned logging behavior.

## Documentation

`pylon_service/README.md` should gain a single sentence in the contact section explaining that expected reconnects are
logged at `INFO`, while final transport failure is surfaced as a typed contact exception.

That note should stay brief and should not turn the README into an operational logging guide.

## File Surface

Expected files to modify:

- `pylon_service/pylon_service/bittensor/contact.py`
- `pylon_service/pylon_service/bittensor/exceptions.py`
- `pylon_service/pylon_service/api/utils.py`
- `pylon_service/tests/unit/bittensor/contact/test_turbobt_contact.py`
- `pylon_service/tests/integration/contact_resilience/test_proxy_recovery.py`
- `pylon_service/tests/integration/contact_resilience/test_restart_recovery.py`
- `pylon_service/README.md`

## Verification

The work is complete when:

- reconnect handling in `TurboBtContact` emits one-line `INFO` logs without traceback output for expected transient
  failures
- permanent contact failure after retry raises a typed Pylon transport exception for both reads and writes
- the shared HTTP wrapper maps that typed contact exception consistently
- unit tests cover both the transient-log path and the final typed-failure path
- resilience integration tests fail if Pylon starts emitting traceback-bearing reconnect logs again
- the `README` change is one sentence only
