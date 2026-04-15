# Bittensor Contact Router Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the wallet-bound bittensor routing object to `BittensorContactRouter` and the pool to `BittensorContactPool` across active code, tests, docstrings, and contributor-facing docs with no compatibility aliases.

**Architecture:** Keep behavior unchanged. Rename the concrete router module/class first, then rename the pool and its tests, then update dependency wiring and handler/test terminology so active runtime code no longer mixes `router`, `client`, and Litestar `Router` naming for the same bittensor-layer object. Finish by updating contributor-facing docs and running a repo search that excludes historical plan/spec artifacts.

**Tech Stack:** Python 3.14, Litestar, pytest, uv, ripgrep

---

### Task 1: Rename The Router Module And Class

**Files:**
- Create: `pylon_service/pylon_service/bittensor/contact_router.py`
- Delete: `pylon_service/pylon_service/bittensor/router.py`
- Create: `pylon_service/tests/unit/bittensor/test_contact_router.py`
- Delete: `pylon_service/tests/unit/bittensor/test_router.py`

- [ ] **Step 1: Write the failing test**

Rename the router unit test file and update it to use the new module path and class name before implementation exists.

```python
from pylon_service.bittensor.contact_router import BittensorContactRouter


@pytest.fixture
def contact_router(main_contact, archive_contact):
    return BittensorContactRouter(
        wallet=Wallet(),
        main_contact=main_contact,
        archive_contact=archive_contact,
        archive_blocks_cutoff=ArchiveBlocksCutoff(300),
    )


@pytest.mark.asyncio
async def test_contact_router_recent_block_uses_main_contact(
    contact_router, main_contact, archive_contact, test_neuron
):
    recent_block = Block(number=BlockNumber(450), hash=BlockHash("0xrecent"))
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))
    expected_neurons = [test_neuron]

    async with contact_router:
        async with main_contact.mock_behavior(
            get_latest_block=[latest_block],
            get_neurons_list=[expected_neurons],
        ):
        result = await contact_router.get_neurons_list(netuid=NetUid(1), block=recent_block)

    assert result == expected_neurons
    assert main_contact.calls["get_latest_block"] == [()]
    assert main_contact.calls["get_neurons_list"] == [(NetUid(1), recent_block)]
    assert archive_contact.calls["get_neurons_list"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pylon_service && uv run pytest tests/unit/bittensor/test_contact_router.py -q`
Expected: FAIL with `ModuleNotFoundError` for `pylon_service.bittensor.contact_router` or `ImportError` for `BittensorContactRouter`.

- [ ] **Step 3: Write minimal implementation**

Move `router.py` to `contact_router.py` and rename the class/docstring there without changing fallback behavior.

```python
class BittensorContactRouter:
    """
    Wallet-bound facade that exposes the contact interface while routing stale-block reads to archive.
    """

    def __init__(
        self,
        wallet: Wallet | None,
        main_contact: AbstractBittensorContact,
        archive_contact: AbstractBittensorContact,
        archive_blocks_cutoff: ArchiveBlocksCutoff,
    ) -> None:
        self.wallet = wallet
        self.hotkey = main_contact.hotkey
        self.uri = main_contact.uri
        self.archive_uri = archive_contact.uri
        self._main_contact = main_contact
        self._archive_contact = archive_contact
        self._archive_blocks_cutoff = archive_blocks_cutoff
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd pylon_service && uv run pytest tests/unit/bittensor/test_contact_router.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pylon_service/pylon_service/bittensor/contact_router.py \
        pylon_service/tests/unit/bittensor/test_contact_router.py
git add -u pylon_service/pylon_service/bittensor/router.py \
           pylon_service/tests/unit/bittensor/test_router.py
git commit -m "refactor: rename bittensor router to contact router"
```

### Task 2: Rename The Pool Type Around The New Router

**Files:**
- Modify: `pylon_service/pylon_service/bittensor/pool.py`
- Modify: `pylon_service/tests/unit/bittensor/test_contact_router.py`
- Create: `pylon_service/tests/unit/bittensor/test_bittensor_contact_pool.py`
- Delete: `pylon_service/tests/unit/bittensor/test_bittensor_client_pool.py`

- [ ] **Step 1: Write the failing test**

Rename the pool unit test file and update imports, test names, and type annotations to the new names.

```python
from pylon_service.bittensor.contact_router import BittensorContactRouter
from pylon_service.bittensor.pool import (
    BittensorContactPool,
    BittensorContactPoolInvalidState,
    WalletKey,
)


async def acquire_client(
    pool: BittensorContactPool[BittensorContactRouter], wallet: Wallet | None, barrier: asyncio.Barrier
) -> BittensorContactRouter:
    async with pool.acquire(wallet=wallet) as client:
        await barrier.wait()
    return client


@pytest.mark.asyncio
async def test_bittensor_contact_pool_proper_use(barrier_factory):
    barrier = await barrier_factory(6)
    wallets = [Wallet(), Wallet()]
    pool = BittensorContactPool(
        uri="ws://localhost:8000",
        archive_uri="ws://localhost:8001",
    )
    await pool.open()
    assert pool.state == BittensorContactPool.State.OPEN

    tasks = [asyncio.create_task(acquire_client(pool, wallets[i % 2], barrier)) for i in range(5)]
    await wait_until(lambda: barrier.n_waiting == barrier.parties - 1)
    assert pool._acquire_counter == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pylon_service && uv run pytest tests/unit/bittensor/test_bittensor_contact_pool.py -q`
Expected: FAIL with `ImportError` for `BittensorContactPool` and `BittensorContactPoolInvalidState`.

- [ ] **Step 3: Write minimal implementation**

Rename the pool symbols to match the new router type and update defaults/logging/docstrings accordingly.

```python
from pylon_service.bittensor.contact_router import BittensorContactRouter


class BittensorContactPoolInvalidState(Exception):
    pass


class BittensorContactPool[RouterT: BittensorContactRouter]:
    """
    Pool from which bittensor contact routers can be acquired based on the provided wallet.
    One contact router is shared for the same wallet.
    """

    def __init__(
        self,
        router_cls: type[RouterT] = BittensorContactRouter,
        contact_factory: ContactFactory | None = None,
        pool_closing_timeout: float = 60,
        **client_kwargs,
    ) -> None:
        if "wallet" in client_kwargs:
            raise ValueError("Wallet may not be given as a client kwarg in the client pool.")
        self.state = self.State.CLOSED
        self.router_cls = router_cls
        self.contact_factory = contact_factory or ContactFactory()
        self.closing_timeout = pool_closing_timeout
        self._pool: dict[WalletKey | None, RouterT] = {}
        self._close_condition = asyncio.Condition()
        self._acquire_lock = asyncio.Lock()
        self._acquire_counter = 0
        self.client_kwargs = client_kwargs

    def _verify_open(self):
        if self.state != self.State.OPEN:
            raise BittensorContactPoolInvalidState("The pool is not open.")
```

Also rename the pool test assertions and docstrings from `client pool` to `contact pool`, and update any remaining
references in `test_contact_router.py` if they still import the old router path.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd pylon_service && uv run pytest tests/unit/bittensor/test_contact_router.py tests/unit/bittensor/test_bittensor_contact_pool.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pylon_service/pylon_service/bittensor/pool.py \
        pylon_service/tests/unit/bittensor/test_contact_router.py \
        pylon_service/tests/unit/bittensor/test_bittensor_contact_pool.py
git add -u pylon_service/tests/unit/bittensor/test_bittensor_client_pool.py
git commit -m "refactor: rename bittensor client pool"
```

### Task 3: Rename Runtime Wiring, Dependency Keys, And Test Fixtures

**Files:**
- Modify: `pylon_service/pylon_service/dependencies.py`
- Modify: `pylon_service/pylon_service/lifespans.py`
- Modify: `pylon_service/pylon_service/main.py`
- Modify: `pylon_service/pylon_service/scheduler.py`
- Modify: `pylon_service/pylon_service/api/v1/api.py`
- Modify: `pylon_service/pylon_service/api/_unstable/api.py`
- Modify: `pylon_service/pylon_service/bittensor/recent/tasks.py`
- Modify: `pylon_service/tests/conftest.py`
- Modify: `pylon_service/tests/unit/bittensor/recent/tasks/test_recent_object_update_task_executor.py`
- Modify: `pylon_service/tests/unit/bittensor/recent/tasks/test_update_recent_object_task.py`
- Modify: `pylon_service/tests/unit/bittensor/recent/tasks/test_update_recent_neurons_task.py`

- [ ] **Step 1: Write the failing test**

Update the shared fixtures and recent-task tests to use the new naming before the runtime wiring is changed.

```python
from pylon_service.bittensor.contact_router import BittensorContactRouter
from pylon_service.bittensor.pool import BittensorContactPool


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def mock_bt_contact_pool():
    async with BittensorContactPool(
        router_cls=BittensorContactRouter,
        contact_factory=ContactFactory(contact_cls=MockBittensorContact),
        uri="mock://main",
        archive_uri="mock://archive",
        archive_blocks_cutoff=ArchiveBlocksCutoff(10_000_000),
    ) as pool:
        yield pool


class Task(UpdateRecentObject):
    def __init__(self, store: Store, pool: BittensorContactPool, object_: AnObjectModel) -> None:
        super().__init__(store, pool)
```

Update handler parameter names and dependency keys in the API modules to the target nomenclature:

```python
dependencies = {
    "bt_contact_router": Provide(bt_contact_router_open_access_dep),
    "recent_object_provider": Provide(recent_object_provider_open_access_dep),
}


async def get_latest_neurons(
    self, bt_contact_router: BittensorContactRouter, netuid: NetUid
) -> GetNeuronsResponse:
    return await neuron_service.get_latest_neurons(bt_contact_router, netuid)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pylon_service && uv run pytest tests/unit/bittensor/recent/tasks/test_recent_object_update_task_executor.py tests/unit/bittensor/recent/tasks/test_update_recent_object_task.py tests/unit/bittensor/recent/tasks/test_update_recent_neurons_task.py -q`
Expected: FAIL during import or collection because runtime code still exposes `BittensorClientPool`, `BittensorRouter`,
`bt_client_pool`, or `bittensor_client_pool`.

- [ ] **Step 3: Write minimal implementation**

Rename the runtime wiring to the new canonical terms consistently.

In `dependencies.py`:

```python
from pylon_service.bittensor.contact_router import BittensorContactRouter
from pylon_service.bittensor.pool import BittensorContactPool


async def bt_contact_pool_dep(state: State) -> BittensorContactPool:
    """
    Pool of bittensor contact routers. Every contact router used in the service should be taken from the pool to
    maintain and reuse connections.
    """
    return state.bittensor_contact_pool


async def bt_contact_router_identity_dep(
    bt_contact_pool: BittensorContactPool[BittensorContactRouter], identity: Identity
) -> AsyncGenerator[BittensorContactRouter]:
    async with bt_contact_pool.acquire(wallet=identity.wallet) as contact_router:
        yield contact_router
```

In `lifespans.py` and `main.py`:

```python
@asynccontextmanager
async def bittensor_contact_pool(app: Litestar) -> AsyncGenerator[None]:
    logger.debug("Initializing bittensor contact pool.")
    async with BittensorContactPool(
        contact_factory=contact_factory,
        uri=settings.bittensor_network,
        archive_uri=settings.bittensor_archive_network,
        archive_blocks_cutoff=settings.bittensor_archive_blocks_cutoff,
    ) as pool:
        app.state.bittensor_contact_pool = pool
        yield
```

```python
lifespan=[lifespans.bittensor_contact_pool, lifespans.scheduler_lifespan],
dependencies={"bt_contact_pool": Provide(dependencies.bt_contact_pool_dep, use_cache=True)},
```

In `scheduler.py`, update the app state lookup to the renamed pool:

```python
updater = UpdateRecentNeurons(app.stores.get(StoreName.RECENT_OBJECTS), app.state.bittensor_contact_pool)
executor = RecentObjectUpdateTaskExecutor(updater, timeout=timeout, contexts=contexts)
```

In `api/v1/api.py` and `api/_unstable/api.py`, rename imports, dependency keys, and handler parameter names from
`bt_client` to `bt_contact_router`.

In `bittensor/recent/tasks.py`, rename pool annotations/docstrings from `BittensorClientPool` to
`BittensorContactPool`, but keep the contact-level argument name `client: BittensorPort` unchanged where the object is
actually a contact-shaped service dependency rather than the pool/router type.

In `tests/conftest.py`, rename:

```python
async def mock_bt_contact_pool():
    async with BittensorContactPool(
        router_cls=BittensorContactRouter,
        contact_factory=ContactFactory(contact_cls=MockBittensorContact),
        uri="mock://main",
        archive_uri="mock://archive",
        archive_blocks_cutoff=ArchiveBlocksCutoff(10_000_000),
    ) as pool:
        yield pool


def test_app(mock_bt_contact_pool, mock_stores):
    @asynccontextmanager
    async def mock_lifespan(app):
        app.state.bittensor_contact_pool = mock_bt_contact_pool
        yield

    with patch.object(lifespans, "bittensor_contact_pool", mock_lifespan):
        app = create_app()
```

Also update recent-task tests that assert router instances:

```python
assert all(isinstance(call[1], BittensorContactRouter) for call in calls)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd pylon_service && uv run pytest tests/unit/bittensor/recent/tasks/test_recent_object_update_task_executor.py tests/unit/bittensor/recent/tasks/test_update_recent_object_task.py tests/unit/bittensor/recent/tasks/test_update_recent_neurons_task.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pylon_service/pylon_service/dependencies.py \
        pylon_service/pylon_service/lifespans.py \
        pylon_service/pylon_service/main.py \
        pylon_service/pylon_service/scheduler.py \
        pylon_service/pylon_service/api/v1/api.py \
        pylon_service/pylon_service/api/_unstable/api.py \
        pylon_service/pylon_service/bittensor/recent/tasks.py \
        pylon_service/tests/conftest.py \
        pylon_service/tests/unit/bittensor/recent/tasks/test_recent_object_update_task_executor.py \
        pylon_service/tests/unit/bittensor/recent/tasks/test_update_recent_object_task.py \
        pylon_service/tests/unit/bittensor/recent/tasks/test_update_recent_neurons_task.py
git commit -m "refactor: rename bittensor contact router wiring"
```

### Task 4: Update Contributor Docs And Verify No Active Old Names Remain

**Files:**
- Modify: `pylon_service/README.md`
- Modify: `pylon_service/pylon_service/metrics.py`

- [ ] **Step 1: Write the failing verification**

Before editing docs, run a search over active code/docs that should be clean after the rename.

Run: `rg -n "BittensorRouter|BittensorClientPool|bittensor_client_pool|bt_client_pool|wallet-bound router|client pool|bittensor/router.py|test_router.py|test_bittensor_client_pool.py" pylon_service README.md docs --glob '!docs/superpowers/**'`
Expected: FINDS matches in active code and `pylon_service/README.md`.

- [ ] **Step 2: Write the documentation changes**

Update the package README and metrics docstring to use the new terminology and file names.

```markdown
The service is organized into four layers:

HTTP handlers
    |
    v
versioned services
    |
    v
wallet-bound BittensorContactRouter
    |
    v
contacts
    |
    v
turbobt / Bittensor / Subtensor
```

```markdown
- obtain the wallet-bound `BittensorContactRouter` from the `BittensorContactPool` through dependencies
- use a real `BittensorContactRouter`
- app startup constructs the `BittensorContactPool`
- the pool constructs wallet-bound `BittensorContactRouter` instances
- `bittensor/contact_router.py` defines wallet-bound main/archive routing
- `bittensor/pool.py` manages `BittensorContactPool` reuse
```

In `metrics.py`:

```python
"""Total number of archive client fallback events.

Labels:
    reason: Reason for fallback (e.g., "unknown_block", "stale_block").
          See pylon_service.bittensor.contact_router.BittensorContactRouter for fallback behavior details.
"""
```

- [ ] **Step 3: Run verification to confirm the rename is complete**

Run: `rg -n "BittensorRouter|BittensorClientPool|bittensor_client_pool|bt_client_pool|wallet-bound router|client pool|bittensor/router.py|test_router.py|test_bittensor_client_pool.py" pylon_service README.md docs --glob '!docs/superpowers/**'`
Expected: NO MATCHES

Run: `rg -n "\\bbt_client\\b|mock_bt_client_pool|bt_client_identity_dep|bt_client_open_access_dep|bt_client_pool_dep" pylon_service/pylon_service/api pylon_service/pylon_service/dependencies.py pylon_service/tests/conftest.py`
Expected: NO MATCHES

Run: `cd pylon_service && uv run pytest tests/unit/bittensor/test_contact_router.py tests/unit/bittensor/test_bittensor_contact_pool.py tests/unit/bittensor/recent/tasks/test_recent_object_update_task_executor.py tests/unit/bittensor/recent/tasks/test_update_recent_object_task.py tests/unit/bittensor/recent/tasks/test_update_recent_neurons_task.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add pylon_service/README.md \
        pylon_service/pylon_service/metrics.py
git commit -m "docs: rename bittensor contact router terminology"
```

- [ ] **Step 5: Final review**

Run: `git diff --check`
Expected: NO OUTPUT

Run: `git status --short`
Expected: clean worktree for files touched by this plan, aside from unrelated pre-existing user changes.
