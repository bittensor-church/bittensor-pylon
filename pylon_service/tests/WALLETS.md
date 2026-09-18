# Test wallets

The default `dev_wallets` fixture supplies native SDK v11 keyfiles for Alice, Bob,
Charlie, and Dave. It generates them from their well-known Substrate URIs in a
session directory created by `tmp_path_factory`. Pytest manages its retention and
cleanup. `DevAccount.wallet` uses that same directory during tests. Standalone
chain-preparation scripts use a separate `TemporaryDirectory`, cleaned up at normal
process shutdown. Both paths share the wallet generator. Addresses stay deterministic,
so existing chain snapshots remain compatible. No keyfiles are stored in the repository.

The fixture sets the wallet path before checking the identity fixture contract or
starting the shared test world. The generic `wallet` fixture also uses native Alice.

## Legacy compatibility

`integration/client_service_e2e/test_wallet_compatibility.py` covers only legacy
wallets. Its `generated_legacy_wallet` fixture runs isolated, pinned producers:

| Format | Producer |
|---|---|
| Without `cryptoType` | bittensor-wallet 4.0.1 |
| Bittensor 10.5 CLI | bittensor 10.5.0, bittensor-cli 9.22.0, bittensor-wallet 4.1.0 |

The CLI generates fresh coldkeys and hotkeys with `new-coldkey` and `new-hotkey`.
Expected addresses are read from the producer's JSON; there are no fixed keys,
mnemonics, or addresses in these tests. Encryption is disabled. `uv` must be on
PATH, with package-index access on the first run; later runs reuse its cache.
Generation uses the current Python interpreter and fails on prompts or timeouts.

Each legacy format gets its own localchain and Pylon service. The test verifies
registration and submits and reads back a signed commitment through PylonClient.
The rest of the test suite uses v11 wallets by default.

From `pylon_service`, after the turbobt release prerequisite in the package README:

```sh
uv run nox -s test
uv run nox -s test-integration-e2e -- -k test_legacy_wallet_can_read_and_sign
```

## Docker

Pylon test containers upload the generated wallet directory through the Docker API
before starting the service. This works with local and remote Docker daemons and
requires no host bind mount, manual wallet copying, or `PYLON_TEST_WALLETS_PATH`.
The copied keys live only in disposable test containers.
