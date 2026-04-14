## Summary

Refine `pylon_service/new_tests/conftest.py` so it not only patches the transport seam, but also seeds a default in-memory blockchain scenario automatically for every `new_tests` test via `autouse=True`. The migrated neuron and validator endpoint tests should read from the same seeded subnet state, with validators emerging from the real filtering logic rather than a separate validator-only fixture universe.

## Motivation

The current `new_tests` setup centralizes the transport patch and raw builders, but the endpoint modules still define scenario fixtures such as `block`, `subnet_neurons`, `raw_neurons`, `subnet_validators`, and `raw_validators`. That leaves too much chain-shaping detail in the modules and makes tests noisier than necessary.

The next step is to treat `pylon_service/new_tests/` as a common seeded test world:

- one shared default block
- one shared default subnet dataset
- automatic transport seeding for every test

This keeps test methods focused on endpoint behavior and assertions rather than repetitive chain-state setup.

## Goals

- Seed a default chain state automatically for all tests under `pylon_service/new_tests/`
- Ensure the neuron and validator endpoint tests run against the same seeded subnet
- Remove endpoint-local scenario fixtures like `subnet_neurons`, `raw_neurons`, `subnet_validators`, `raw_validators`, `block`, and `raw_block`
- Keep an extension seam for future tests to add extra netuids when needed

## Non-Goals

- No production code changes
- No new tests
- No changes to the legacy `pylon_service/tests/` tree
- No attempt to generalize every possible future chain scenario now

## Architecture

`pylon_service/new_tests/conftest.py` becomes responsible for both shared fixture wiring and default chain seeding.

It will define:

- one default `Block`
- one default raw turbobt block
- one default `NetUid`
- one default `SubnetNeurons` dataset containing both validator-permitted and non-validator neurons
- one derived raw neuron list
- one derived raw subnet state
- one `autouse=True` fixture that seeds the shared `MockTurboBTtransport` with that default state before each test

The validators endpoint tests will use the same seeded subnet as the neurons endpoint tests. The difference in response comes from the existing `TurboBtClient.get_validators()` behavior, not from a different seeded dataset.

## Fixture Design

The top-level `conftest.py` should expose concrete shared fixtures for the default seeded world, such as:

- default netuid
- default block
- default raw block
- default subnet neurons
- default raw neurons
- default raw subnet state

An `autouse=True` fixture should consume those fixtures and seed `mock_turbobt_transport` on every test:

1. set latest block
2. add block
3. add neurons range for the default netuid
4. add subnet state range for the default netuid

For future multi-netuid tests, the top-level `conftest.py` should also provide a small extension seam, for example a fixture that returns additional seed instructions as a list. The default value can be empty now. The `autouse` seeding fixture can apply those extra instructions after seeding the default subnet.

## Test Module Changes

Update:

- `pylon_service/new_tests/open_access_endpoints/test_get_neurons_endpoint.py`
- `pylon_service/new_tests/open_access_endpoints/test_get_validators_endpoint.py`

Changes:

- remove local scenario fixtures for block and chain objects
- consume the shared default seeded world from `new_tests/conftest.py`
- keep only endpoint-specific assertions and invalid-input cases
- use the same default netuid in both modules

The validators tests should continue asserting the filtered validator response from the shared seeded neuron set.

## Data Flow

1. A `new_tests` test starts
2. The shared top-level `conftest.py` patches `get_turbobt_transport()` and constructs the app/client stack
3. The `autouse` seeding fixture loads the default block and subnet data into `MockTurboBTtransport`
4. The endpoint test performs its request without needing to mention chain setup explicitly
5. Assertions validate endpoint response and transport call history

## Verification

Run:

- `cd pylon_service && uv run python -m py_compile new_tests/conftest.py new_tests/open_access_endpoints/test_get_neurons_endpoint.py new_tests/open_access_endpoints/test_get_validators_endpoint.py`
- `cd pylon_service && PYLON_ENV_FILE=tests/.test-env uv run pytest new_tests/open_access_endpoints/test_get_neurons_endpoint.py new_tests/open_access_endpoints/test_get_validators_endpoint.py -q`

## Risks

- If the shared seeded dataset becomes too specific, later tests may fight the defaults rather than benefit from them
- If future extension points are too implicit, tests adding extra netuids may become hard to read

To keep this balanced, the shared top-level `conftest.py` should provide one well-named default seeded world plus one narrow extension seam for additional netuid data.
