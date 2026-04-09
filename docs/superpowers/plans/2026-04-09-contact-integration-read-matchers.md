# Contact Integration Read Matchers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace brittle exact chain-value assertions in the contact read integration suite with `dirty_equals` matchers while keeping full payload shape checks.

**Architecture:** Keep the test logic in `pylon_service/tests/integration/contact/test_reads.py` and add `dirty-equals` to the existing `pylon_service` dev extra. Swap volatile literal values in the expected snapshot payloads for `dirty_equals` matcher instances and keep matcher-bearing expected payloads on the left side of equality assertions.

**Tech Stack:** Python, pytest, `uv`, Docker-backed integration tests

---

### Task 1: Add the matcher dependency and use it in the contact read test module

**Files:**
- Modify: `pylon_service/tests/integration/contact/test_reads.py`
- Modify: `pylon_service/pyproject.toml`
- Modify: `pylon_service/uv.lock`
- Test: `pylon_service/tests/integration/contact/test_reads.py`

- [ ] **Step 1: Write the failing test**

```python
from dirty_equals import IsInt, IsStr
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pylon_service && uv run python -c "from dirty_equals import IsInt, IsStr"`
Expected: FAIL with `ModuleNotFoundError` before the dependency is added.

- [ ] **Step 3: Write minimal implementation**

```toml
[project.optional-dependencies]
dev = [
    ...,
    "dirty-equals>=0.11",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd pylon_service && uv run python -c "from dirty_equals import IsInt, IsStr"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pylon_service/tests/integration/contact/test_reads.py
git commit -m "test: stabilize contact integration read assertions"
```

### Task 2: Replace volatile literal values with `dirty_equals` matchers in the snapshot expectations

**Files:**
- Modify: `pylon_service/tests/integration/contact/test_reads.py`
- Test: `pylon_service/tests/integration/contact/test_reads.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_get_block_returns_prepared_snapshot_block(open_contact):
    block = await get_snapshot_block(open_contact)
    assert dump_model(block) == SNAPSHOT_BLOCK
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pylon_service && uv run pytest tests/integration/contact/test_reads.py::test_get_block_returns_prepared_snapshot_block -q`
Expected: FAIL if the snapshot block hash differs from the literal fixture.

- [ ] **Step 3: Write minimal implementation**

```python
SNAPSHOT_BLOCK = {
    "number": 238,
    "hash": IsStr(regex=r"^0x[0-9a-fA-F]{64}$"),
}

EXPECTED_TIMESTAMP_EXTRINSIC["call"]["call_args"][0]["value"] = IsInt(ge=0)
EXPECTED_TIMESTAMP_EXTRINSIC["call"]["call_hash"] = IsStr(regex=r"^0x[0-9a-fA-F]{64}$")
EXPECTED_TIMESTAMP_EXTRINSIC["extrinsic_hash"] = IsStr(regex=r"^0x[0-9a-fA-F]{64}$")
EXPECTED_MEV_SHIELD_EXTRINSIC["call"]["call_args"][0]["value"] = IsStr(regex=r"^0x[0-9a-fA-F]+$")
EXPECTED_MEV_SHIELD_EXTRINSIC["call"]["call_hash"] = IsStr(regex=r"^0x[0-9a-fA-F]{64}$")
EXPECTED_MEV_SHIELD_EXTRINSIC["extrinsic_hash"] = IsStr(regex=r"^0x[0-9a-fA-F]{64}$")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd pylon_service && uv run pytest tests/integration/contact/test_reads.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pylon_service/tests/integration/contact/test_reads.py
git commit -m "test: use matchers for volatile contact snapshot values"
```

### Task 3: Keep assertion style readable by putting expected matcher payloads on the left-hand side

**Files:**
- Modify: `pylon_service/tests/integration/contact/test_reads.py`
- Test: `pylon_service/tests/integration/contact/test_reads.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_get_neurons_returns_full_snapshot_mapping(open_contact, prepared_netuid):
    block = await get_snapshot_block(open_contact)
    neurons = await open_contact.get_neurons(prepared_netuid, block)
    assert dump_model(neurons) == EXPECTED_NEURONS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pylon_service && uv run pytest tests/integration/contact/test_reads.py -q`
Expected: FAIL if any nested volatile field remains literal.

- [ ] **Step 3: Write minimal implementation**

```python
assert SNAPSHOT_BLOCK == dump_model(block)
assert EXPECTED_NEURONS == dump_model(neurons)
assert EXPECTED_TIMESTAMP_EXTRINSIC == dump_model(timestamp_extrinsic)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd pylon_service && uv run pytest tests/integration/contact/test_reads.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pylon_service/tests/integration/contact/test_reads.py
git commit -m "test: keep strict shape checks with contact snapshot matchers"
```
