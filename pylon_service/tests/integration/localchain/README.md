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

Before running integration tests, you must build the prepared snapshot images:
- `prepared-e2e-localnet:latest` for e2e tests
- `prepared-contact-localnet:latest` for contact tests

```bash
# From the repository root:
nox -s prepare-e2e-localchain
nox -s prepare-contact-localchain

# Or from pylon_service:
cd pylon_service && nox -s prepare-e2e-localchain
cd pylon_service && nox -s prepare-contact-localchain
```

This runs `prepare_e2e_chain.py` or `prepare_contact_chain.py` respectively, which:

1. Starts a fresh `ghcr.io/opentensor/subtensor-localnet:main` container
2. Seeds it with test data (see [Seeded Data](#seeded-data) below)
3. Commits the container state as Docker image `prepared-e2e-localnet:latest` or `prepared-contact-localnet:latest`

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

### Seeded data for e2e tests

#### Filler Accounts

The snapshot creates **251 filler wallets** from deterministic URIs (`//Filler0` through
`//Filler250`) in a temporary wallet directory while preparing the chain. These wallets are used
only to fill subnet neuron capacity and are not persisted as test wallets.

#### TAO Transfers

Alice (pre-funded by the localnet genesis) transfers **100,000 TAO** to each of: Bob, Charlie, Dave.
Alice also transfers **500 TAO** to each filler wallet.


#### Subnets

Four subnets are registered (owned by Alice):

| Subnet | Netuid | Tempo | Purpose |
|--------|--------|-------|---------|
| Subnet 1 | 1 | 100 (default) | Read testing |
| Subnet 2 | 2 | 50 (low) | Fast commit-reveal weight and write tests |
| Subnet 3 | 3 | 50 (low) | Mechanism weight tests |
| Subnet 4 | 4 | 50 (low) | Dedicated to `test_set_weights_succeeds_after_registration` — only Alice registered, `WeightsRateLimit=0`. **This test permanently mutates subnet 4 state** (registers Charlie, adds stake), so the subnet must remain single-tenant. |

Subtokens are enabled on all four subnets.

#### Neurons

**Subnets 1 and 2** each contain **256 neurons**:

| UID Range | Account(s) | Role |
|-----------|------------|------|
| 0 | Built-in localnet neuron | Validator |
| 1 | Alice | Validator |
| 2 | Bob | Validator |
| 3 | Charlie | Non-validator |
| 4 | Dave | Non-validator |
| 5-255 | Filler wallets | Non-validator |

**Subnet 3** contains the built-in localnet neuron plus Alice, Bob, Charlie, and Dave. Filler wallets
are intentionally absent.

**Subnet 4** contains only the built-in localnet neuron and Alice. Bob, Charlie, Dave, and the
filler wallets are intentionally absent.

#### Stake

Validators (Alice and Bob) each stake **10 TAO** on subnets 1-3 (6 stake operations total).
Subnet 4 has no initial validator stake; `test_set_weights_succeeds_after_registration` registers
Charlie and adds stake during the test.

#### Commitments

Set on **subnet 1** only:

| Account | Type | Value                         |
|---------|------|-------------------------------|
| Alice   | revealed commitment | `"revealed-commitment-alice"` |
| Bob     | revealed commitment | `"revealed-commitment-bob"`   |
| Charlie | commitment | `"commitment-charlie"`        |
| Dave    | commitment | `"commitment-dave"`           |

#### Evm Associations

Set on **subnet 1** only. Evm key associations for Alice and Charlie.

### Seeded data for contact tests

#### TAO Transfers

Alice (pre-funded by the localnet genesis) transfers **100,000 TAO** to each of: Bob, Charlie, Dave.

#### Subnets

Four subnets are registered (owned by Alice):

| Subnet   | Netuid | Tempo | Purpose                                                      |
|----------|--------|-------|--------------------------------------------------------------|
| Subnet 2 | 2      | 50    | No commit-reveal tests, existing evm association tests       |
| Subnet 3 | 3      | 50    | Commit-reveal weight tests                                   |
| Subnet 4 | 4      | 50    | No commit-reveal weight with mechanism for set weight tests  |
| Subnet 5 | 5      | 50    | Commit-reveal weight with mechanisms for commit weight tests |

Subtokens are enabled on all subnets.

#### Neurons

Each prepared subnet contains **4 neurons**:

| UID Range | Account(s) | Role |
|-----------|------------|------|
| 1 | Alice | Validator |
| 2 | Bob | Validator |
| 3 | Charlie | Non-validator |
| 4 | Dave | Non-validator |

#### Stake

Validators (Alice and Bob) each stake **10 TAO** on all subnets.

#### Commitments

Set on **subnet 2** only:

| Account | Type                | Value                           |
|---------|---------------------|---------------------------------|
| Alice   | revealed commitment | `"revealed-commitment-alice"`   |
| Bob     | commitment          | `"commitment-bob"`              |
| Charlie | revealed commitment | `"revealed-commitment-charlie"` |
| Dave    | commitment          | `"commitment-dave"`             |

#### Evm Associations

Set on **subnet 2**only. Evm key associations for Alice and Charlie.

### Other Configuration

- **Admin freeze window**: Disabled (set to 0). The default of 10 blocks can cause silent sudo
  call failures.
- **Bulk registration tuning**: `MaxRegistrationsPerBlock` and `TargetRegistrationsPerInterval`
  are raised to 256, and `TxRateLimit` is set to 0 on e2e subnets 1 and 2 before filler
  registration. `MaxBurn` is also capped just above the chain's `MaxBurnLowerBound` (0.1 TAO):
  each burned registration swaps its burn from TAO into the subnet's alpha reserve, and the burn
  ramps up (`BurnIncreaseMult`) after every registration, so an uncapped burn would drain the
  alpha reserve below the swap pallet's `MinimumReserve` and make bulk registration fail with
  `ReservesTooLow`.
- **Drand.NextUnsignedAt**: Set to `current_block + 80` — see [Drand Workaround](#drand-workaround)
  below.

## Particularities

### Dedicated Subnets for State-Modifying Tests

Tests that **permanently modify subnet state** (registering neurons, adding stake,
changing hyperparameters that other tests rely on) MUST NOT share a subnet with
other tests — otherwise test execution order would affect results.

When writing such a test, prefer creating a **dedicated subnet** for it in
`prepare_e2e_chain.py` (as was done for subnet 4, used exclusively by
`test_set_weights_succeeds_after_registration`). Document the ownership in the
*Subnets* table above so it stays a single-tenant subnet.

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

**Phase 1 — At snapshot build time** (`prepare_e2e_chain.py`, `prepare_contact_chain.py`):

Set `Drand.NextUnsignedAt` to `current_block + DRAND_WORKER_MARGIN` (currently 80 blocks). This
tells the offchain worker to **not start fetching** until 80 blocks after the snapshot block.
This buys time to update `LastStoredRound` before the worker begins.
```python
await manager.offset_drand_next_unsigned_at()
```

**Phase 2 — At container start time** (test fixtures):

On the current localnet runtime the worker no longer catches up from a stale round on its own — it stalls
after a single fetch batch — and if it wakes on the stale round it floods the chain with pulse extrinsics,
which can starve the pin writes and deadlock. So `synchronize_drand_last_stored_round()` does, in order:

1. **Hold** the worker asleep by pushing `Drand.NextUnsignedAt` far into the future — done *first*, while the
   worker is still idle behind the phase 1 margin, so a slow `get_latest_round()` or storage write cannot lose
   the race.
2. **Pin** `Drand.LastStoredRound` and `Drand.OldestStoredRound` to the **current real-world drand round**
   (fetched via `bittensor_drand.get_latest_round()`).
3. **Wake** the worker by moving `Drand.NextUnsignedAt` back to a few blocks out; it now resumes from the
   pinned current round instead of the stale one, without ever flooding.
4. **Verify** the worker is actually tracking the current round, re-pinning as a safety net if the observed
   gap is still large.

```python
# In test conftest.py (simplified):
with LocalChainManager(container) as manager:
    await manager.synchronize_drand_last_stored_round()
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

Waiting for the chain to catch up is necessary because the worker will not process 
drand based operations (commit weight, set reveal commitment) until `LastStoredRound` 
is being updated.

> **Important**: `Drand.NextUnsignedAt` must always be set as the **last operation** before the
> Docker snapshot is committed. If more operations are added after it, they consume the block
> margin, potentially causing the worker to start before `LastStoredRound` can be updated at
> container start time.

## File Structure

| File | Description |
|------|-------------|
| `dev_accounts.py` | `DevAccount` enum with pre-seeded accounts (Alice, Bob, Charlie, Dave) |
| `manager.py` | `LocalChainManager` — Docker container lifecycle and chain operations via turbobt |
| `prepare_e2e_chain.py` | E2E snapshot preparation script — seeds data and creates `prepared-e2e-localnet:latest` |
| `prepare_contact_chain.py` | Contact snapshot preparation script — seeds data and creates `prepared-contact-localnet:latest` |
