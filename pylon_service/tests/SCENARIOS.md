# Public API Test Scenarios

This file lists the required public-API test scenarios for `pylon_service` before the internal refactor proceeds.

The list is derived from:

- [api/_unstable/api.py](/pylon_service/pylon_service/api/_unstable/api.py)
- [api/v1/api.py](/pylon_service/pylon_service/api/v1/api.py)
- [pylon_commons/_unstable/endpoints.py](/pylon_commons/pylon_commons/_unstable/endpoints.py)
- [pylon_commons/v1/endpoints.py](/pylon_commons/pylon_commons/v1/endpoints.py)

It is a checklist of scenario names, not a statement that each scenario needs its own physical test file.

## Naming

Use this test naming pattern:

```text
test_{version}_{scope}_{endpoint}_{scenario}
```

Where:

- `version` is `unstable` or `v1`
- `scope` is `public`, `open_access`, or `identity`
- `endpoint` is the endpoint family name
- `scenario` describes the expected behavior

Unless noted otherwise, read-only subnet scenarios apply to:

- `_unstable` open-access endpoint
- `_unstable` identity endpoint
- `v1` open-access endpoint
- `v1` identity endpoint

Identity-only write scenarios apply to both `_unstable` and `v1`.

## Cross-Cutting Scenarios

These are not specific to one handler implementation, but they are part of the public behavior:

- `test_{version}_identity_any_identity_scoped_endpoint_unknown_identity_returns_404`
- `test_{version}_identity_identity_login_unknown_identity_returns_404`

Request-body validation scenarios:

- `test_{version}_public_identity_login_missing_token_returns_400_or_422`
- `test_{version}_identity_put_weights_empty_weights_returns_400_or_422`
- `test_{version}_identity_put_weights_invalid_weight_type_returns_400_or_422`
- `test_{version}_identity_put_weights_invalid_hotkey_returns_400_or_422`
- `test_{version}_identity_set_commitment_invalid_hex_returns_400_or_422`
- `test_{version}_identity_generate_certificate_keypair_unsupported_algorithm_returns_400_or_422`

Note: use the exact framework status code actually produced by Litestar/Pydantic for validation failures and then lock it
down in the snapshots/assertions.

## Public Block-Level Endpoints

### `POST /api/{version}/login/identity/{identity_name}`

- `test_{version}_public_identity_login_returns_identity_metadata`
- `test_{version}_public_identity_login_unknown_identity_returns_404`
- `test_{version}_public_identity_login_missing_token_returns_400_or_422`

### `GET /api/{version}/block/latest`

- `test_{version}_public_latest_block_info_returns_latest_block_info`

### `GET /api/{version}/block/{block_number}/extrinsic/{extrinsic_index}`

- `test_{version}_public_get_extrinsic_returns_decoded_extrinsic`
- `test_{version}_public_get_extrinsic_missing_block_returns_404`
- `test_{version}_public_get_extrinsic_missing_extrinsic_returns_404`

## Shared Read Endpoint Scenarios

The scenario names in this section apply to both open-access and identity routes unless explicitly limited.

### `GET .../block/{block_number}/neurons`

- `test_{version}_{scope}_get_neurons_returns_block_neurons`
- `test_{version}_{scope}_get_neurons_missing_block_returns_404`

### `GET .../block/latest/neurons`

- `test_{version}_{scope}_get_latest_neurons_returns_latest_neurons`

### `GET .../block/recent/neurons`

- `test_{version}_{scope}_get_recent_neurons_returns_cached_neurons`
- `test_{version}_{scope}_get_recent_neurons_missing_cache_returns_503`
- `test_{version}_{scope}_get_recent_neurons_stale_cache_returns_503`

### `GET .../block/{block_number}/validators`

- `test_{version}_{scope}_get_validators_returns_only_validator_permit_neurons_sorted_by_total_stake_desc`
- `test_{version}_{scope}_get_validators_missing_block_returns_404`

### `GET .../block/latest/validators`

- `test_{version}_{scope}_get_latest_validators_returns_only_validator_permit_neurons_sorted_by_total_stake_desc`

### `GET .../block/latest/certificates`

- `test_{version}_{scope}_get_certificates_returns_all_certificates`
- `test_{version}_{scope}_get_certificates_returns_empty_map_when_none_exist`

### `GET .../block/latest/certificates/{hotkey}`

- `test_{version}_{scope}_get_certificate_by_hotkey_returns_certificate`
- `test_{version}_{scope}_get_certificate_by_hotkey_missing_certificate_returns_404`

### `GET .../block/latest/commitments`

This endpoint needs mixed-result coverage because the service must not let one bad/unregistered item poison the whole
response.

For `_unstable`:

- `test_unstable_{scope}_get_commitments_returns_all_registered_commitments`
- `test_unstable_{scope}_get_commitments_filters_unregistered_commitments_and_keeps_valid_items`
- `test_unstable_{scope}_get_commitments_returns_empty_map_when_none_exist`

For `v1`:

- `test_v1_{scope}_get_commitments_returns_registered_commitments_as_hex_map`
- `test_v1_{scope}_get_commitments_filters_unregistered_commitments_and_keeps_valid_items`
- `test_v1_{scope}_get_commitments_returns_empty_map_when_none_exist`

### `GET .../block/latest/commitments/{hotkey}`

For `_unstable`:

- `test_unstable_{scope}_get_commitment_by_hotkey_returns_commitment_object`
- `test_unstable_{scope}_get_commitment_by_hotkey_missing_commitment_returns_404`

For `v1`:

- `test_v1_{scope}_get_commitment_by_hotkey_returns_v1_commitment_shape`
- `test_v1_{scope}_get_commitment_by_hotkey_missing_commitment_returns_404`

## Identity-Only Endpoint Scenarios

### `PUT /api/{version}/identity/{identity_name}/subnet/{netuid}/weights`

- `test_{version}_identity_put_weights_returns_schedule_ack`
- `test_{version}_identity_put_weights_unknown_identity_returns_404`
- `test_{version}_identity_put_weights_empty_weights_returns_400_or_422`
- `test_{version}_identity_put_weights_invalid_weight_type_returns_400_or_422`
- `test_{version}_identity_put_weights_invalid_hotkey_returns_400_or_422`

The response is immediate scheduling acknowledgment, so transport failures inside the background job are not asserted on
this endpoint's HTTP response. They should be covered through job tests and downstream effects.

### `POST /api/{version}/identity/{identity_name}/subnet/{netuid}/commitments`

- `test_{version}_identity_set_commitment_returns_created_ack`
- `test_{version}_identity_set_commitment_unknown_identity_returns_404`
- `test_{version}_identity_set_commitment_invalid_hex_returns_400_or_422`
- `test_{version}_identity_set_commitment_retry_exhausted_returns_502`

### `GET /api/{version}/identity/{identity_name}/subnet/{netuid}/block/latest/certificates/self`

- `test_{version}_identity_get_own_certificate_returns_certificate`
- `test_{version}_identity_get_own_certificate_unknown_identity_returns_404`
- `test_{version}_identity_get_own_certificate_missing_certificate_returns_404`

### `GET /api/{version}/identity/{identity_name}/subnet/{netuid}/block/latest/commitments/self`

For `_unstable`:

- `test_unstable_identity_get_own_commitment_returns_commitment_object`
- `test_unstable_identity_get_own_commitment_unknown_identity_returns_404`
- `test_unstable_identity_get_own_commitment_missing_commitment_returns_404`

For `v1`:

- `test_v1_identity_get_own_commitment_returns_v1_commitment_shape`
- `test_v1_identity_get_own_commitment_unknown_identity_returns_404`
- `test_v1_identity_get_own_commitment_missing_commitment_returns_404`

### `POST /api/{version}/identity/{identity_name}/subnet/{netuid}/certificates/self`

- `test_{version}_identity_generate_certificate_keypair_returns_created_keypair`
- `test_{version}_identity_generate_certificate_keypair_unknown_identity_returns_404`
- `test_{version}_identity_generate_certificate_keypair_unsupported_algorithm_returns_400_or_422`
- `test_{version}_identity_generate_certificate_keypair_generation_failure_returns_502`

## Unstable Open-Access General Endpoints

These endpoints are only available in the `_unstable` API and are not subnet-scoped.

### `GET /api/_unstable/openaccess/block/latest`

- `test_unstable_open_access_latest_block_info_returns_latest_block_info`

### `GET /api/_unstable/openaccess/block/{block_number}/extrinsic/{extrinsic_index}`

- `test_unstable_open_access_get_extrinsic_returns_decoded_extrinsic`
- `test_unstable_open_access_get_extrinsic_missing_block_returns_404`
- `test_unstable_open_access_get_extrinsic_missing_extrinsic_returns_404`

### `GET /api/_unstable/openaccess/block/latest/drand/last_stored_round`

- `test_unstable_open_access_get_drand_last_stored_round_returns_round`

### `POST /api/_unstable/openaccess/evm/contracts/{contract_address}/logs`

- `test_unstable_open_access_evm_logs_returns_logs`
- `test_unstable_open_access_evm_logs_returns_empty_list_when_no_logs`
- `test_unstable_open_access_evm_logs_invalid_address_returns_400`
- `test_unstable_open_access_evm_logs_invalid_abi_returns_422`
- `test_unstable_open_access_evm_logs_rpc_error_returns_502`
- `test_unstable_open_access_evm_logs_missing_abi_returns_400`
- `test_unstable_open_access_evm_logs_missing_token_returns_401`

## Coverage Notes

Before implementation proceeds, the intended test suite should satisfy all of the following:

- every public endpoint has at least one explicit happy-path test
- every explicit unhappy path in handler or dependency code is covered
- response status codes are asserted inline
- full response bodies are asserted, preferably with `syrupy` snapshots
- `syrupy` matchers are used only for values that are genuinely hard to freeze
- mixed-result collection scenarios are covered for commitments
- shared-world fixture data is the default setup; per-test transport overrides are used only when needed for state
  transitions or focused failures
