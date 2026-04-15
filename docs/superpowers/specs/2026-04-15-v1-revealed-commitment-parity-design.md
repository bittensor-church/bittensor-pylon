# V1 Revealed Commitment Parity Design

## Goal

Add the revealed-commitment endpoint family to the `v1` API so `v1` has parity with `_unstable` for revealed commitment reads and writes.

This change must preserve the existing behavioral split between the API versions:

- `v1` commitment endpoints continue filtering out timelocked commitments from normal commitment reads.
- Revealed-commitment endpoints in `v1` do not introduce extra filtering and return the revealed records as exposed by the service layer.

## Scope

In scope:

- Add the revealed-commitment routes to the `v1` API contract.
- Add the corresponding `v1` request and response exports needed by those routes.
- Add the `v1` service and handler wiring for revealed-commitment reads and writes.
- Add `v1` unit tests covering the new revealed-commitment routes.

Out of scope:

- Any change to the existing `v1` commitment-read filtering behavior.
- Any broader API refactor beyond what is needed to expose revealed commitments in `v1`.
- Any client-library expansion not required by the service-side `v1` contract.

## Endpoint Surface

Add these `v1` endpoints:

- `POST /api/v1/identity/{identity_name}/subnet/{netuid}/commitments/revealed`
- `GET /api/v1/subnet/{netuid}/block/latest/commitments/revealed`
- `GET /api/v1/subnet/{netuid}/block/latest/commitments/revealed/{hotkey}`
- `GET /api/v1/identity/{identity_name}/subnet/{netuid}/block/latest/commitments/revealed/self`

These endpoints are intended to match the `_unstable` revealed-commitment behavior and payload shape.

The existing `v1` endpoints under `/block/latest/commitments...` remain unchanged and continue serving the compatibility view that excludes timelocked commitments from normal commitment responses.

## Contract Design

`pylon_commons.v1` becomes the authoritative namespace for the new `v1` revealed-commitment routes.

Changes:

- Add the four revealed-commitment endpoint constants to `pylon_commons.v1.endpoints`.
- Export `SetRevealedCommitmentBody` from `pylon_commons.v1.bodies`.
- Export the revealed-commitment response models from `pylon_commons.v1.responses`.

The payload models themselves do not need a second version-specific shape. The version distinction here is behavioral, not structural. `v1` can therefore re-export the same underlying revealed-commitment models already used by `_unstable`, while still keeping `pylon_commons.v1` as the public source of truth for `v1` handlers and future `v1` client code.

## Service Design

Follow the service versioning rules in `pylon_service/README.md`:

- `_unstable` remains the canonical latest implementation.
- `v1` stays thin and only overrides behavior where compatibility requires divergence.

For revealed commitments, behavior is unchanged between versions, so `pylon_service.api.v1.services` should reuse `_unstable` implementations through pass-through imports or thin subclasses.

The current `v1` filtering logic for standard commitment reads stays isolated to the existing `v1` commitment service methods. No timelock filtering is added to the new revealed-commitment service methods.

## Handler Design

Add `v1` handlers in `pylon_service.api.v1.api` that mirror the `_unstable` revealed-commitment family:

- open-access latest revealed commitments
- open-access revealed commitments by hotkey
- identity latest revealed commitments for the authenticated wallet
- identity revealed-commitment write

Each handler should:

- use `v1` endpoint enums
- use `v1` request and response imports
- delegate to `v1` service entrypoints
- preserve the existing `v1` exception-mapping and dependency patterns

No router restructuring is needed beyond registering the new handlers inside the existing `v1` controllers.

## Testing

Add `v1` unit coverage paralleling the existing `_unstable` revealed-commitment tests.

Required cases:

- open-access list returns revealed commitments in the expected shape
- open-access by-hotkey returns only the targeted hotkey even when other hotkeys exist in mocked contact behavior
- identity self returns a list with more than one record for the identity hotkey and excludes other hotkeys present in mocked contact behavior
- write endpoint succeeds for valid requests
- write endpoint retries on transient failure and asserts repeated call payloads
- write endpoint fails cleanly after retry exhaustion
- write endpoint rejects invalid payloads
- write endpoint handles unknown identities

Existing `v1` commitment tests remain the proof that normal commitment reads still filter timelocked commitments. No test should weaken or replace that compatibility guarantee.

## Risks And Mitigations

Risk: `v1` starts depending directly on `_unstable` DTO namespaces.
Mitigation: expose the contract through `pylon_commons.v1` even if the underlying classes are shared.

Risk: revealed endpoints accidentally inherit the normal commitment filtering behavior.
Mitigation: keep filtering overrides limited to the existing standard commitment-read methods and add explicit `v1` tests for revealed responses.

Risk: route parity lands in the service but not in the shared contract.
Mitigation: update endpoint, body, and response exports in `pylon_commons.v1` together with the handler changes.

## Success Criteria

The design is complete when:

- `v1` exposes the full revealed-commitment route family listed above.
- `v1` revealed endpoints match `_unstable` payload behavior.
- existing `v1` commitment endpoints still filter timelocked commitments from normal commitment reads.
- `v1` unit tests cover revealed-commitment reads and writes, including retries and hotkey-targeting behavior.
