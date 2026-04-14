## Summary

Refactor the `pylon_service/new_tests/` test tree so transport patching and raw turbobt test builders are defined once in a shared top-level `conftest.py`. This keeps the new transport-based test area readable and avoids repeating per-module setup that should be common across all `new_tests`.

## Motivation

The initial migration of endpoint tests into `pylon_service/new_tests/` intentionally duplicated setup to isolate those tests from `pylon_service/tests/conftest.py` and its `MockBittensorClient` seam. That isolation is correct, but the current shape still repeats transport patching in each module. The next cleanup is to make `new_tests/` itself the shared transport-based fixture boundary.

## Goals

- Define one common patched `MockTurboBTtransport` seam for all tests under `pylon_service/new_tests/`
- Centralize the app/client/pool/store fixtures for `new_tests/`
- Centralize raw turbobt-oriented helper builders used by the migrated endpoint tests
- Keep scenario-specific configuration in the test modules
- Prefer multiple `NetUid` values for distinct scenarios rather than separate patched transport setups

## Non-Goals

- No production behavior changes
- No changes to the old `pylon_service/tests/` tree
- No new tests for `MockTurboBTtransport`
- No broader reorganization of test helper code outside `pylon_service/new_tests/`

## Architecture

Add a shared fixture module at `pylon_service/new_tests/conftest.py`. It becomes the inherited fixture boundary for all tests in the new transport-based test tree.

That file will own:

- `MockStore`
- `bt_client_pool`
- `mock_stores`
- `reset_mock_stores`
- `test_app`
- `test_client`
- `mock_turbobt_transport`
- the patch of `pylon_service.bittensor.client.get_turbobt_transport`
- shared raw builders for turbobt block objects, turbobt neuron-like objects, and raw subnet state payloads

The existing `pylon_service/new_tests/open_access_endpoints/conftest.py` will be removed. The endpoint test modules will inherit the shared fixtures from the new top-level `conftest.py`.

## Fixture Design

The patched transport should be active for the entire `new_tests` tree by default. Tests under `new_tests/` should not need to define their own transport patch fixture unless they are explicitly testing a different seam shape.

The top-level `conftest.py` will include a comment explaining that the duplication from the legacy test tree is intentional because `pylon_service/new_tests/` is the start of a gradual migration away from `pylon_service/tests/` and its inherited `MockBittensorClient` pool seam.

Scope should remain function-level where needed so each test gets a fresh transport instance and a fresh app/client stack that sees the patched factory.

## Test Module Changes

Update these files:

- `pylon_service/new_tests/open_access_endpoints/test_get_neurons_endpoint.py`
- `pylon_service/new_tests/open_access_endpoints/test_get_validators_endpoint.py`

Changes:

- remove module-local `mock_turbobt_transport`
- remove module-local `patched_test_client`
- remove duplicated raw builder helpers that move into the shared `conftest.py`
- keep endpoint-specific domain model builders and assertions in the modules
- continue configuring scenario data by calling methods on the shared `MockTurboBTtransport`

Where a module needs a distinct transport scenario, use a different `NetUid` instead of creating a separate transport patch setup.

## Data Flow

1. A `new_tests` test requests `test_client`
2. The shared top-level `conftest.py` patches `get_turbobt_transport()` to return the per-test `MockTurboBTtransport`
3. App startup creates a real `TurboBtClient` through the normal pool path
4. `TurboBtClient` receives the patched mock transport
5. The test configures blockchain-like state on the shared mock transport and asserts both endpoint response and transport call history

## Verification

Run:

- `cd pylon_service && uv run python -m py_compile new_tests/conftest.py new_tests/open_access_endpoints/test_get_neurons_endpoint.py new_tests/open_access_endpoints/test_get_validators_endpoint.py`
- `cd pylon_service && PYLON_ENV_FILE=tests/.test-env uv run pytest new_tests/open_access_endpoints/test_get_neurons_endpoint.py new_tests/open_access_endpoints/test_get_validators_endpoint.py -q`

## Risks

- If fixture scope is too broad, pooled clients may retain a transport created under an earlier patch context
- Moving too many helpers into `conftest.py` can make it hard to see what data matters to each test module

The refactor should keep only shared seam/setup and low-level raw builders in `conftest.py`, while leaving endpoint-specific expected responses in the test modules.
