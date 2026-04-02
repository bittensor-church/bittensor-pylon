# `new_tests` Conventions

This directory is the transport-seam test area for `pylon_service`.

It exists separately from `pylon_service/tests/` so these tests do not inherit the older
`MockBittensorClient` pool setup from that tree. Tests here use the real `TurboBtClient`
path with a patched `MockTurboBTtransport`.

## Shared Blockchain Seed

`new_tests/conftest.py` defines one default in-memory blockchain world and seeds it automatically
for every test with `autouse=True`.

That shared seed currently includes:

- one default block
- one default netuid
- one default subnet neuron set
- both validator-permitted and non-validator neurons in the same subnet

The important rule is:

**Neuron and validator endpoint tests should read from the same seeded blockchain state.**

Validators are not modeled as a separate fake subnet or separate fake response universe.
They are the subset of seeded neurons for which the real application logic treats
`validator_permit=True` as validator membership.

This keeps the tests closer to the real behavior:

- `/neurons` returns the full seeded subnet view
- `/validators` runs against that same chain state and returns the filtered validator view

## Writing New Tests Here

Prefer using the shared seeded world from `new_tests/conftest.py` rather than creating local
per-module chain fixtures.

In practice, that means:

- do not duplicate `block`, `raw_block`, `subnet_neurons`, `raw_neurons`, or similar fixtures in test modules
- do not patch `get_turbobt_transport()` in individual test files
- do not manually seed the transport in each test unless the test is explicitly about custom chain shaping

Tests should usually only depend on:

- `test_client`
- `mock_turbobt_transport` when asserting transport call history
- shared seeded fixtures such as the default netuid or default block

## Extending the Seed

The default model is one shared blockchain seed, but future tests may need additional subnet data.

When that happens:

- keep the default seeded world intact
- extend it through the shared `additional_transport_seed_instructions` seam in `new_tests/conftest.py`
- use additional `NetUid` values rather than replacing the default subnet unless the test truly requires it

The goal is gradual migration toward one readable, consistent transport-based test style for this tree.
