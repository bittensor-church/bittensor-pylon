## Unreleased

### BREAKING CHANGE

- Endpoints that didn't require authentication now
require it.
- Identity endpoints that were previously unprotected now
require passing proper Bearer token for authentication.

### Feat

- add open access endpoints authentication
- Add authentication to identity endpoints

## service-v1.3.0 (2026-04-13)

## service-v1.2.0 (2026-02-18)

### Feat

- Enhance commitments endpoints
- latest block info (#64)

### Fix

- fix commitments endpoint returning regged hotkeys

## service-v1.1.2 (2026-02-12)

### Feat

- Add configurable timeout
- Add configurable timeout

### Fix

- Retry set weights on block fetching failure
- Fix turbobt state breaking
- Properly handle exception when block does not exist

## service-v1.1.1 (2026-02-05)

### Fix

- Fix recent objects task not waiting before retries
- shields every turbobt operation

## service-v1.1.0 (2026-02-02)

### Feat

- Add request-scoped debug logging for Pylon service (#47)

## service-v1.0.0 (2026-01-19)

### Feat

- Add get extrinsic endpoint

### Refactor

- Make Pylon a monorepo

## service-v0.3.0 (2026-01-05)

### Feat

- Add own commitments endpoint

## service-v0.2.0 (2026-01-02)

### Feat

- Add validators list endpoints
- Add proactive caching for recent neurons

### Refactor

- Rename pylon module to pylon_client

## service-v0.1.0 (2025-12-16)

### Feat

- Add commitment endpoints
- Split endpoints into open access and identity endpoints
- add get neurons endpoints

### Fix

- Fix urls of endpoints (#32)
