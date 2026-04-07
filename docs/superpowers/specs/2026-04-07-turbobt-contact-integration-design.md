# TurboBtContact Integration Coverage Design

## Goal

Add a new live-chain integration suite under `pylon_service/tests/integration/contact/` that exercises the public
`TurboBtContact` API directly against local subtensor chains.

The suite should:

- cover all public `TurboBtContact` methods
- use strong, explicit assertions for read methods wherever the prepared chain state is deterministic
- keep `get_latest_block()` and `get_block_timestamp()` as smoke tests because block number and timestamp keep moving
- verify write effects on-chain where the chain exposes a stable readback path

## Current Problem

The repository has only a minimal unit test for `TurboBtContact`, and the existing integration tests cover the HTTP
service layer instead of the contact boundary itself.

This leaves the real `turbobt` translation layer largely unverified on a live chain:

- translated read models such as `Neuron`, `SubnetState`, `Commitment`, and `NeuronCertificate` are not checked
  directly against local-chain state
- contact write methods are not exercised directly
- method-level failures such as mistargeted weight writes are not covered at the contact boundary

## Chain Topology

Use three separate local-chain lifecycles:

1. The existing `pylon_service/tests/integration/` suite keeps its current chain fixture and behavior.
2. The new contact read suite uses one separate pre-prepared snapshot chain shared across a single read-test module.
3. The new contact write suite uses one separate chain configured specifically for contact write scenarios.

This separation keeps:

- existing service integration tests isolated from contact-level mutations
- all read expectations stable against one immutable prepared snapshot
- write scenarios free to mutate dedicated subnets without contaminating reads

## Test Layout

Add a new directory:

- `pylon_service/tests/integration/contact/conftest.py`
- `pylon_service/tests/integration/contact/test_reads.py`
- `pylon_service/tests/integration/contact/test_writes.py`

`conftest.py` should provide:

- a dedicated read-chain fixture based on `prepared-localnet:latest`
- a dedicated write-chain fixture built from a fresh chain plus setup helpers
- open-access and wallet-backed `TurboBtContact` fixtures for the relevant wallets
- expected-state helpers for the prepared read chain

## Read Suite

`test_reads.py` should run all read methods against one pre-prepared snapshot chain.

Covered methods:

- `get_block()`
- `get_latest_block()` as a smoke test only
- `get_block_timestamp()` as a smoke test only
- `get_neurons_list()`
- `get_neurons()`
- `get_hyperparams()`
- `get_subnet_state()`
- `get_commitment()`
- `get_commitments()`
- `get_certificates()`
- `get_certificate()`
- `get_signed_block()`
- `get_extrinsic()`

Assertion rules:

- `get_block()` should assert an exact known block when using a chosen stable block number from the prepared chain.
- `get_latest_block()` should only assert that a block is returned and is structurally valid.
- `get_block_timestamp()` should only assert that a plausible timestamp is returned for the requested block.
- `get_neurons_list()` should assert the full translated `list[Neuron]` for a prepared subnet.
- `get_neurons()` should assert the full `SubnetNeurons` object for the same subnet.
- `get_hyperparams()` should assert the full translated hyperparameter object for the chosen subnet.
- `get_subnet_state()` should assert the full translated subnet state for the chosen subnet.
- `get_commitment()` and `get_commitments()` should assert exact commitment payloads for the prepared commitments.
- `get_certificates()` and `get_certificate()` should assert exact certificate state for the prepared wallets if the
  chain contains certificates, otherwise exact empty or `None` results.
- `get_signed_block()` should assert the structure for a known existing block.
- `get_extrinsic()` should assert a concrete decoded extrinsic from that block and also cover the out-of-range `None`
  case.

The read suite should keep expectations explicit in test helpers/constants rather than deriving expected values from the
same `TurboBtContact` methods under test.

## Write Suite

`test_writes.py` should use a dedicated fresh chain prepared specifically for contact writes.

That chain should include:

- one subnet for direct `set_weights()` on default weight behavior
- one subnet configured for commit-reveal so `commit_weights()` can run on the intended path
- registered neurons and funded wallets required for all write scenarios

The write suite should cover:

- `set_commitment()`
- `set_weights()`
- `commit_weights()`
- `generate_certificate_keypair()`

Verification rules:

- `set_commitment()` should write a new commitment and verify it with `get_commitment()`.
- `set_weights()` should be a success-path smoke test on the direct-weight subnet.
- `commit_weights()` should be a success-path smoke test on the commit-reveal subnet and assert a returned
  `RevealRound`.
- `generate_certificate_keypair()` should assert the returned keypair shape and verify the resulting certificate via
  `get_certificate()`.

## Mistargeted Weights

The write suite should also include explicit mistargeted weight tests for both direct and commit-reveal writes.

These tests should:

- target hotkeys or UIDs that are not valid for the selected subnet
- assert the concrete exceptions raised by the live `turbobt` path

The goal is to verify that `TurboBtContact` surfaces real chain errors correctly instead of flattening them.

## Required LocalChainManager Support

The current `LocalChainManager` already supports:

- wallet creation
- transfers
- subnet creation
- neuron registration
- staking
- commitments
- weights rate limit changes

The write-suite setup will likely need one additional admin helper to enable commit-reveal on a dedicated subnet via
the owner or sudo path, so the suite can exercise `commit_weights()` on the correct chain configuration.

That helper belongs in `tests/integration/localchain/manager.py`, not inside the tests.

## Non-Goals

- no changes to production `TurboBtContact` behavior unless the live-chain suite exposes a real bug
- no snapshot-based assertions for moving-target reads such as latest block or timestamp
- no reuse of the HTTP service integration fixtures for the new contact tests
- no broad parametrized matrix that hides which contact method failed

## Verification

The work is complete when:

- the new `tests/integration/contact/` suite exists and covers all public `TurboBtContact` methods
- `get_latest_block()` and `get_block_timestamp()` are smoke-tested only
- deterministic reads assert full translated results where practical, including full neuron collections
- writes run on a dedicated write chain with separate direct and commit-reveal subnets
- mistargeted direct and commit-reveal writes assert concrete exceptions
- `cd pylon_service && PYLON_ENV_FILE=tests/.test-env uv run pytest -s -vv tests/integration/contact/` passes
- the existing `cd pylon_service && PYLON_ENV_FILE=tests/.test-env uv run pytest -s -vv tests/integration/` suite
  still passes
