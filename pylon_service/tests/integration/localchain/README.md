# Localchain

Localchain is a Docker-based local Bittensor blockchain used for integration testing. It runs
[`subtensor-localnet`](https://github.com/opentensor/subtensor) with fast block times, providing
a fully functional chain that can be seeded with test data and snapshotted for repeatable test runs.

## Purpose

Integration tests need a real blockchain to interact with — mocking the chain would defeat the purpose
of end-to-end verification. Localchain solves this by:

- Running a real subtensor node inside Docker
- Pre-seeding it with accounts, subnets, neurons, stake, and commitments
- Snapshotting the container state so every test run starts from the same baseline

## Building the Snapshot

Before running integration tests, you must build the prepared snapshot image:

```bash
# From the repository root:
nox -s prepare-localchain

# Or from pylon_service:
cd pylon_service && nox -s prepare-localchain
```

This runs `prepare_chain.py`, which:

1. Starts a fresh `ghcr.io/opentensor/subtensor-localnet:main` container
2. Seeds it with test data (see [Seeded Data](#seeded-data) below)
3. Commits the container state as Docker image `prepared-localnet:latest`

The resulting snapshot preserves the full chain state and can be started repeatedly without
re-running the seeding process.

## Seeded Data

### Accounts

Four pre-generated dev accounts are available (defined in `dev_accounts.py`), with wallet files
stored in `tests/wallets/`:

| Account | Substrate URI | Role |
|---------|---------------|------|
| Alice   | `//Alice`     | Validator, subnet owner, sudo (pre-funded on localnet) |
| Bob     | `//Bob`       | Validator |
| Charlie | `//Charlie`   | Non-validator |
| Dave    | `//Dave`      | Non-validator |

On localnet, coldkey and hotkey are derived from the same URI, so their SS58 addresses are identical.

The snapshot also creates **251 filler wallets** from deterministic URIs (`//Filler0` through
`//Filler250`) in a temporary wallet directory while preparing the chain. These wallets are used
only to fill subnet neuron capacity and are not persisted as test wallets.

### TAO Transfers

Alice (pre-funded by the localnet genesis) transfers **100,000 TAO** to each of: Bob, Charlie, Dave.
Alice also transfers **500 TAO** to each filler wallet.

### Subnets

Two subnets are registered (owned by Alice):

| Subnet | Netuid | Tempo | Purpose |
|--------|--------|-------|---------|
| Subnet 1 | 1 | 100 (default) | General testing |
| Subnet 2 | 2 | 50 (low) | Fast commit-reveal weight tests |

Subtokens are enabled on both subnets.

### Neurons

Each prepared subnet contains **256 neurons**:

| UID Range | Account(s) | Role |
|-----------|------------|------|
| 0 | Built-in localnet neuron | Validator |
| 1 | Alice | Validator |
| 2 | Bob | Validator |
| 3 | Charlie | Non-validator |
| 4 | Dave | Non-validator |
| 5-255 | Filler wallets | Non-validator |

### Stake

Validators (Alice and Bob) each stake **10,000 TAO** on both subnets (4 stake operations total).

### Commitments

Set on **subnet 1** only:

| Account | Commitment |
|---------|------------|
| Charlie | `"commitment-charlie"` |
| Dave    | `"commitment-dave"` |

### Other Configuration

- **Admin freeze window**: Disabled (set to 0). The default of 10 blocks can cause silent sudo
  call failures.
- **Bulk registration tuning**: `MaxRegistrationsPerBlock` and `TargetRegistrationsPerInterval`
  are raised to 256, and `TxRateLimit` is set to 0 on both prepared subnets before filler
  registration.
- **Drand.NextUnsignedAt**: Set to `current_block + 80` — see [Drand Workaround](#drand-workaround)
  below.

## Particularities

### Drand Workaround

Bittensor uses [drand](https://drand.love/) randomness beacons for commit-reveal weight operations.
The chain's offchain worker fetches drand rounds and stores them on-chain. Two storage values
control this process:

- **`Drand.LastStoredRound`** — Tells the offchain worker the last drand round stored on-chain.
  Each block, the worker fetches up to 50 rounds starting from this value.
- **`Drand.NextUnsignedAt`** — Tells the offchain worker at which block to perform the next
  drand fetch.

#### The Problem

When a snapshot container starts, both storage values are stale — they reflect the state at
snapshot creation time, which may be days or weeks in the past. The offchain worker begins
fetching from the old `LastStoredRound` value and would need to catch up through potentially
millions of rounds before reaching the current one. Since the localnet runs in fast-block mode,
the worker can never keep up, so it effectively never reaches the current drand round.

This means any operation that depends on current drand randomness (e.g., commit-reveal weights)
will not work.

#### The Solution

The workaround uses a two-phase approach:

**Phase 1 — At snapshot build time** (`prepare_chain.py`):

Set `Drand.NextUnsignedAt` to `current_block + DRAND_WORKER_MARGIN` (currently 80 blocks). This
tells the offchain worker to **not start fetching** until 80 blocks after the snapshot block.
This buys time to update `LastStoredRound` before the worker begins.

**Phase 2 — At container start time** (test fixtures):

Immediately after starting the container, set `Drand.LastStoredRound` and
`Drand.OldestStoredRound` to the **current real-world drand round** (fetched via
`bittensor_drand.get_latest_round()`). This way, when the worker eventually starts (after the
margin expires), it begins from the current round instead of the stale one.

```python
# In test conftest.py (simplified):
with LocalChainManager(container) as manager:
    latest_round = bittensor_drand.get_latest_round()
    await manager.set_drand_last_stored_round(alice.wallet, latest_round)
    await manager.set_drand_oldest_stored_round(alice.wallet, latest_round)
    yield manager
```

#### Why Both Phases Are Needed

Setting only `LastStoredRound` at container start is insufficient — between the container starting
and the storage update completing, the offchain worker has already queued fetch operations on
several blocks using the stale round number. Even though the updated value does take effect, the
already-queued fetches for old rounds still need to complete first. These stale fetches take a long
time to process, delaying the worker from getting to the current round for tens of seconds.

By delaying the worker's start via `NextUnsignedAt` (phase 1), we ensure it has not yet queued
any work by the time `LastStoredRound` is updated (phase 2).

> **Important**: `Drand.NextUnsignedAt` must always be set as the **last operation** before the
> Docker snapshot is committed. If more operations are added after it, they consume the block
> margin, potentially causing the worker to start before `LastStoredRound` can be updated at
> container start time.

## File Structure

| File | Description |
|------|-------------|
| `dev_accounts.py` | `DevAccount` enum with pre-seeded accounts (Alice, Bob, Charlie, Dave) |
| `manager.py` | `LocalChainManager` — Docker container lifecycle and chain operations via turbobt |
| `prepare_chain.py` | Snapshot preparation script — seeds data and creates `prepared-localnet:latest` |
