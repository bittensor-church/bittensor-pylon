# Commitment Endpoint Coverage Design

## Goal

Expand `pylon_service` commitment endpoint unit coverage so it:

- exercises both hex-data and timelock-encrypted commitments on the `_unstable` API,
- verifies `v1` compatibility behavior for timelock-encrypted commitments,
- fully covers commitment-related write endpoints, including revealed-commitment writes,
- preserves a green `pylon_service` unit/lint/typecheck state.

## Scope

This design covers only `pylon_service` unit tests and the minimal production fixes needed if the new tests expose behavior gaps.

Included:

- `_unstable` identity and open-access commitment read endpoints
- `v1` identity and open-access commitment read endpoints
- identity `set_commitment` endpoints in `_unstable` and `v1`
- identity revealed-commitment write endpoints in `_unstable`
- revealed-commitment read endpoints in `_unstable`
- shared unit-test fixtures and snapshots needed to support the above

Excluded:

- pact coverage expansion beyond fixture support needed by unit tests
- integration tests
- unrelated write endpoints such as weights or certificates

## Existing Constraints

- `pylon_service/tests/world.py` is the shared source of seeded contact data for endpoint tests.
- Endpoint test files are split by API version and access mode; that structure should remain.
- `_unstable` commitments expose the full commitment variant shape.
- `v1` commitments are hex-only compatibility endpoints and should not expose timelock-encrypted commitments.
- Revealed-commitment endpoints already exist in `_unstable`; their write/read coverage is currently incomplete.

## Design

### 1. Shared Fixture Expansion

Extend the shared commitment fixtures in `pylon_service/tests/world.py` to model these cases explicitly:

- `hex-only` subnet: existing behavior, used by current tests
- `mixed` subnet: registered commitments containing both hex-data and timelock-encrypted variants
- `timelock-only` subnet: registered commitments containing only timelock-encrypted variants
- `filtered` subnet: includes at least one unregistered commitment, with variant coverage preserved
- `own` commitment subnet: supports both hex-data and timelock-encrypted self-read cases
- revealed-commitment seeded values for GET endpoints

Fixture data should stay small and deterministic. New netuids/constants should be added only where they improve readability of the endpoint tests.

### 2. `_unstable` Read Coverage

Add endpoint tests that verify `_unstable` preserves commitment variants:

- `GET .../commitments` returns registered hex and timelock commitments with their `kind`
- `GET .../commitments/{hotkey}` returns the correct variant object
- `GET .../commitments/self` returns the correct variant object
- filtered commitment lists still exclude unregistered hotkeys, regardless of variant kind

Timelock-encrypted response assertions must include:

- `kind: "timelock_encrypted"`
- `reveal_round`
- commitment block number, hotkey, and payload

### 3. `v1` Compatibility Coverage

Add endpoint tests that verify `v1` remains hex-only:

- mixed commitment lists return only hex-data entries
- timelock-only commitment lists return empty maps
- timelock-only `GET .../commitments/{hotkey}` returns `404`
- timelock-only `GET .../commitments/self` returns `404`

These tests define the compatibility contract rather than relying on implicit filtering behavior.

### 4. Write Coverage

#### `set_commitment`

Keep the existing endpoint tests and fill any gaps so both `_unstable` and `v1` cover:

- success
- success with `0x` prefix
- retry then success
- terminal failure mapped to `502`
- validation failures
- unknown identity `404`

Assertions should include response status/payload and mocked `set_commitment` call history.

#### `set_revealed_commitment`

Add or expand tests for `_unstable` identity write coverage:

- success
- retry then success
- terminal failure mapped to `502`
- validation failures
- unknown identity `404`

Assertions should include:

- response payload containing `reveal_round`
- mocked contact/task call history
- retry counts where applicable

### 5. Revealed-Commitment Read Coverage

Add or expand `_unstable` read tests for:

- open-access `GET .../commitments/revealed`
- open-access `GET .../commitments/revealed/{hotkey}`
- identity `GET .../commitments/revealed/self`

Coverage should include:

- success
- not found
- shape assertions for returned revealed-commitment lists

## Production Fix Policy

If new tests expose behavior gaps, fix only the directly affected implementation in:

- API handlers
- versioned services
- commitment service layer
- mocked/shared fixture plumbing

Do not bundle unrelated refactors.

## Verification

Required verification after implementation:

- targeted endpoint test files while iterating
- `cd pylon_service && uv run nox -s test`
- `cd pylon_service && uv run nox -s lint`

## Risks

- Snapshot churn if new variant payloads are introduced without tightly scoped fixtures
- Accidental behavior drift in `v1` if filtering is changed too broadly
- Overfitting write tests to task internals instead of endpoint contract

## Mitigations

- keep new fixture data minimal and named by behavior
- add explicit `v1` timelock exclusion tests before changing production code
- assert externally visible behavior first, mocked call history second
