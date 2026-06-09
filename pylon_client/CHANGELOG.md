## client-v2.2.0 (2026-06-09)

### Feat

- Endpoint to read alpha prices for subnets
- Associate hotkeys with EVM keys

## client-v2.1.0 (2026-05-29)

### Feat

- robust weight setting

## client-v2.0.0 (2026-05-13)

### BREAKING CHANGE

- block time is no longer accepted as argument for setting revealed commitments but is read from the settings.
- Endpoints that didn't require authentication now
require it.
- Identity endpoints that were previously unprotected now
require passing proper Bearer token for authentication.

### Feat

- mechanism support (#81)
- add open access endpoints authentication
- Add authentication to identity endpoints

## client-v1.9.0 (2026-04-13)

### Fix

- export response structs in v1 (#67)

## client-v1.8.0 (2026-02-20)

### Feat

- Add api versioning to the pylon client
- Enhance commitments endpoints
- latest block info (#64)

## client-v1.7.0 (2026-02-12)

### Feat

- Add configurable timeout
- Add configurable timeout

## client-v1.6.1 (2026-02-10)

### Fix

- Properly handle exception when block does not exist

## client-v1.6.0 (2026-02-02)

## client-v1.5.0 (2026-01-15)

### Feat

- Add get extrinsic endpoint

### Refactor

- Make Pylon a monorepo

## client-v1.4.0 (2026-01-07)

### Feat

- Add is_serving property to AxonInfo

## client-v1.3.0 (2026-01-05)

### Feat

- Add own commitments endpoint

## client-v1.2.1 (2026-01-05)

### Feat

- Provide recent neurons via pylon client

### Fix

- Add missing get validators endpoints to the pylon client

## client-v1.1.0 (2026-01-02)

### Feat

- Add validators list endpoints

## client-v1.0.0 (2025-12-23)

### Refactor

- Rename pylon module to pylon_client

## client-v0.1.1 (2025-12-23)

### Fix

- Add missing imports to v1 module

## client-v0.1.0 (2025-12-16)

### BREAKING CHANGE

- Pylon client interface changed significantly: now
methods are used instead of passing PylonRequest object directly.
Impacts: client
Issue: BACT-169

### Feat

- Add commitment endpoints
- Introduce identity API to Pylon Client
- Split endpoints into open access and identity endpoints
- add get neurons endpoints
