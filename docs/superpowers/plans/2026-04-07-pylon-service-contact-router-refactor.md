# Pylon Service Contact/Router Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `pylon_service`'s current mixed client architecture with a thin transport-only contact layer, a wallet-bound archive-routing layer, and versioned services while preserving the public HTTP API.

**Architecture:** Split turbobt communication into a `Contact` boundary that owns connection lifecycle and turbobt-to-Pylon translation only. Build a pooled wallet-bound router above it that chooses main vs archive contacts. Move domain behavior into services, with versioned service entrypoints handling API-compatibility differences and DTO mapping.

**Tech Stack:** Python 3.13, Litestar, turbobt, pydantic, pytest, pytest-asyncio, httpx, tenacity, syrupy

---

## File Structure Map

### Create

- `pylon_service/pylon_service/bittensor/models.py`
- `pylon_service/pylon_service/bittensor/contact.py`
- `pylon_service/pylon_service/bittensor/router.py`
- `pylon_service/pylon_service/services/__init__.py`
- `pylon_service/pylon_service/services/blocks.py`
- `pylon_service/pylon_service/services/neurons.py`
- `pylon_service/pylon_service/services/certificates.py`
- `pylon_service/pylon_service/services/commitments.py`
- `pylon_service/pylon_service/services/weights.py`
- `pylon_service/pylon_service/api/_unstable/services.py`
- `pylon_service/pylon_service/api/v1/services.py`
- `pylon_service/tests/unit/bittensor/contact/__init__.py`
- `pylon_service/tests/unit/bittensor/contact/test_turbobt_contact.py`
- `pylon_service/tests/unit/bittensor/test_router.py`
- `pylon_service/tests/world.py`

### Modify

- `pylon_service/pylon_service/bittensor/pool.py`
- `pylon_service/pylon_service/dependencies.py`
- `pylon_service/pylon_service/lifespans.py`
- `pylon_service/pylon_service/api/_unstable/api.py`
- `pylon_service/pylon_service/api/v1/api.py`
- `pylon_service/pylon_service/api/_unstable/tasks.py`
- `pylon_service/pylon_service/bittensor/recent/tasks.py`
- `pylon_service/pylon_service/main.py`
- `pylon_service/pyproject.toml`
- `pylon_service/tests/conftest.py`
- `pylon_service/tests/unit/conftest.py`
- `pylon_service/tests/unit/open_access_endpoints/*.py`
- `pylon_service/tests/unit/identity_endpoints/*.py`
- `pylon_service/tests/unit/bittensor/test_bittensor_client_pool.py`
- `pylon_service/tests/unit/bittensor/test_bittensor_client_delegation.py`

### Delete after migration

- `pylon_service/pylon_service/bittensor/client.py`
- `pylon_service/tests/mock_bittensor_client.py`
- `pylon_service/tests/unit/bittensor/turbobt/*`

The final deletion should happen only after all imports and tests are migrated to the new files.

## Task 1: Introduce Contact Models And Contact Boundary

**Files:**
- Create: `pylon_service/pylon_service/bittensor/models.py`
- Create: `pylon_service/pylon_service/bittensor/contact.py`
- Test: `pylon_service/tests/unit/bittensor/contact/test_turbobt_contact.py`

- [ ] **Step 1: Write the failing turbobt-contact smoke test**

```python
import pytest
from pylon_commons.types import BittensorNetwork

from pylon_service.bittensor.contact import TurboBtContact


@pytest.mark.asyncio
async def test_turbobt_contact_requires_open_before_use():
    contact = TurboBtContact(wallet=None, uri=BittensorNetwork("mock://test"))

    with pytest.raises(AttributeError, match="not open"):
        await contact.get_latest_block()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd pylon_service && uv run pytest tests/unit/bittensor/contact/test_turbobt_contact.py -q`

Expected: FAIL with `ModuleNotFoundError` for `pylon_service.bittensor.contact`

- [ ] **Step 3: Create the contact-internal model module**

```python
from pylon_commons.models import *  # noqa: F403

# Contact models intentionally start as pass-through exports of the latest canonical models.
# This module is the seam where contact-only fields may be added later without forcing DTO shape.
```

- [ ] **Step 4: Create the contact boundary and implementations**

```python
class BittensorPort(Protocol):
    wallet: Wallet | None
    uri: BittensorNetwork
    hotkey: Hotkey

    async def open(self) -> None: ...
    async def close(self) -> None: ...
    async def get_block(self, number: BlockNumber) -> Block | None: ...
    async def get_latest_block(self) -> Block: ...
    async def get_block_timestamp(self, block: Block) -> Timestamp: ...
    async def get_neurons_list(self, netuid: NetUid, block: Block) -> list[Neuron]: ...
    async def get_hyperparams(self, netuid: NetUid, block: Block) -> SubnetHyperparams | None: ...
    async def get_certificates(self, netuid: NetUid, block: Block) -> dict[Hotkey, NeuronCertificate]: ...
    async def get_certificate(self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None) -> NeuronCertificate | None: ...
    async def generate_certificate_keypair(self, netuid: NetUid, algorithm: CertificateAlgorithm) -> NeuronCertificateKeypair | None: ...
    async def get_subnet_state(self, netuid: NetUid, block: Block) -> SubnetState: ...
    async def commit_weights(self, netuid: NetUid, weights: dict[Hotkey, Weight]) -> RevealRound: ...
    async def set_weights(self, netuid: NetUid, weights: dict[Hotkey, Weight]) -> None: ...
    async def get_neurons(self, netuid: NetUid, block: Block) -> SubnetNeurons: ...
    async def get_commitment(self, netuid: NetUid, block: Block, hotkey: Hotkey | None = None) -> Commitment | None: ...
    async def get_commitments(self, netuid: NetUid, block: Block) -> SubnetCommitments: ...
    async def set_commitment(self, netuid: NetUid, data: CommitmentDataBytes) -> None: ...
    async def get_validators(self, netuid: NetUid, block: Block) -> SubnetValidators: ...
    async def get_signed_block(self, block: Block) -> SignedBlock | None: ...
    async def get_extrinsic(self, block: Block, extrinsic_index: ExtrinsicIndex) -> Extrinsic | None: ...
```

```python
class TurboBtContact:
    def __init__(self, wallet: Wallet | None, uri: BittensorNetwork):
        self.wallet = wallet
        self.uri = uri
        self._raw_client: Bittensor | None = None
        self._is_client_ready = asyncio.Event()

    async def open(self) -> None:
        assert self._raw_client is None
        self._raw_client = Bittensor(wallet=self.wallet, uri=self.uri)
        await asyncio.shield(self._raw_client.__aenter__())
        self._is_client_ready.set()

    async def close(self) -> None:
        assert self._raw_client is not None
        raw_client = self._raw_client
        self._raw_client = None
        self._is_client_ready.clear()
        await asyncio.shield(raw_client.__aexit__(None, None, None))

    async def _protect_turbobt[T](self, coro_factory: Callable[[Bittensor], Awaitable[T]]) -> T:
        if self._raw_client is None:
            raise AttributeError("The contact is not open.")
        try:
            return await asyncio.shield(coro_factory(self._raw_client))
        except RuntimeError:
            await self.close()
            await self.open()
            assert self._raw_client is not None
            return await asyncio.shield(coro_factory(self._raw_client))
```

```python
class MockBittensorContact:
    def __init__(self, wallet: Any | None = None, uri: BittensorNetwork = BittensorNetwork("mock://test")):
        self.wallet = wallet
        self.uri = uri
        self.calls: defaultdict[str, list[tuple[Any, ...]]] = defaultdict(list)
        self._behave = Behave()

    def enqueue(self, method_name: str, behavior: Behavior) -> None:
        self._behave.add_behavior(method_name, behavior)
```

Move all turbobt translation logic from `client.py` into `TurboBtContact`, but stop at transport translation. Do not keep:

- archive fallback
- validator filtering/sorting as service policy
- commitment filtering as service policy
- hotkey-to-uid resolution as weight policy

Add `MockBittensorContact` in the same module, but do not add durable tests whose only purpose is checking that the
mock records calls. The mock will be exercised through router, handler, and job tests later in the plan.

- [ ] **Step 5: Add a typed contact factory**

```python
@dataclass(slots=True)
class ContactFactory:
    contact_cls: type[BittensorPort] = TurboBtContact

    def create(self, wallet: Wallet | None, uri: BittensorNetwork) -> BittensorPort:
        return self.contact_cls(wallet=wallet, uri=uri)
```

Make this factory the composition-time seam that tests will patch.

- [ ] **Step 6: Run the contact tests**

Run: `cd pylon_service && uv run pytest tests/unit/bittensor/contact/test_turbobt_contact.py -q`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add pylon_service/pylon_service/bittensor/models.py \
        pylon_service/pylon_service/bittensor/contact.py \
        pylon_service/tests/unit/bittensor/contact/test_turbobt_contact.py
git commit -m "refactor: split turbobt transport into contact layer"
```

## Task 1.5: Add Snapshot Testing Support And Conventions

**Files:**
- Modify: `pylon_service/pyproject.toml`
- Modify: `pylon_service/tests/conftest.py`
- Modify: `pylon_service/tests/unit/conftest.py`

- [ ] **Step 1: Write the failing snapshot fixture import test**

```python
def test_snapshot_json_fixture_uses_json_extension(snapshot_json):
    assert snapshot_json is not None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd pylon_service && uv run pytest tests/unit/test_snapshot_fixture.py -q`

Expected: FAIL because `snapshot_json` does not exist and `syrupy` is not installed

- [ ] **Step 3: Add `syrupy` as a dev dependency**

```toml
[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio>=1.0.0",
    "polyfactory>=2.22.2",
    "pact-python>=2.0.0",
    "bittensor-pylon-client",
    "docker",
    "httpx",
    "ruff",
    "pyright",
    "nox",
    "syrupy",
]
```

- [ ] **Step 4: Add shared snapshot fixtures and matcher helpers**

```python
from syrupy.extensions.json import JSONSnapshotExtension
from syrupy.matchers import path_type


@pytest.fixture
def snapshot_json(snapshot):
    return snapshot.use_extension(JSONSnapshotExtension)


@pytest.fixture
def response_matchers():
    def factory(*, timestamp_paths: tuple[str, ...] = (), regex_paths: dict[str, tuple[type, ...]] | None = None):
        mapping: dict[str, tuple[type, ...]] = {path: (int,) for path in timestamp_paths}
        if regex_paths:
            mapping.update(regex_paths)
        return path_type(mapping, regex=True)

    return factory
```

Keep matcher usage sparse. The default path is full-body snapshotting with no matcher.

- [ ] **Step 5: Run the fixture test**

Run: `cd pylon_service && uv run pytest tests/unit/test_snapshot_fixture.py -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pylon_service/pyproject.toml \
        pylon_service/tests/conftest.py \
        pylon_service/tests/unit/conftest.py \
        pylon_service/tests/unit/test_snapshot_fixture.py
git commit -m "test: add syrupy snapshot fixtures"
```

## Task 2: Add Wallet-Bound Router And Move Archive Fallback There

**Files:**
- Create: `pylon_service/pylon_service/bittensor/router.py`
- Modify: `pylon_service/pylon_service/bittensor/pool.py`
- Modify: `pylon_service/pylon_service/dependencies.py`
- Modify: `pylon_service/pylon_service/lifespans.py`
- Test: `pylon_service/tests/unit/bittensor/test_router.py`
- Test: `pylon_service/tests/unit/bittensor/test_bittensor_client_pool.py`

- [ ] **Step 1: Write the failing router tests from current delegation behavior**

```python
async def test_router_uses_archive_for_stale_block(main_contact, archive_contact, block_factory, neuron_factory):
    router = BittensorRouter(
        wallet=None,
        main_contact=main_contact,
        archive_contact=archive_contact,
        archive_blocks_cutoff=ArchiveBlocksCutoff(300),
    )
    latest = block_factory.build(number=BlockNumber(500))
    old = block_factory.build(number=BlockNumber(100))
    expected = [neuron_factory.build()]

    main_contact.enqueue("get_latest_block", latest)
    archive_contact.enqueue("get_neurons_list", expected)

    result = await router.get_neurons_list(NetUid(1), old)

    assert result == expected
    assert archive_contact.calls["get_neurons_list"] == [(NetUid(1), old)]
```

- [ ] **Step 2: Run the router tests to verify they fail**

Run: `cd pylon_service && uv run pytest tests/unit/bittensor/test_router.py -q`

Expected: FAIL with `ModuleNotFoundError` for `pylon_service.bittensor.router`

- [ ] **Step 3: Implement the router**

```python
class BittensorRouter:
    def __init__(
        self,
        wallet: Wallet | None,
        main_contact: BittensorPort,
        archive_contact: BittensorPort,
        archive_blocks_cutoff: ArchiveBlocksCutoff,
    ) -> None:
        self.wallet = wallet
        self._main_contact = main_contact
        self._archive_contact = archive_contact
        self._archive_blocks_cutoff = archive_blocks_cutoff

    async def open(self) -> None:
        await self._main_contact.open()
        await self._archive_contact.open()

    async def close(self) -> None:
        await self._main_contact.close()
        await self._archive_contact.close()
```

```python
    async def _delegate[T](
        self,
        operation_name: str,
        main_call: Callable[[], Awaitable[T]],
        archive_call: Callable[[], Awaitable[T]],
        block: Block | None = None,
    ) -> T:
        if block is not None:
            latest_block = await self._main_contact.get_latest_block()
            if latest_block.number - block.number > self._archive_blocks_cutoff:
                return await archive_call()
        try:
            return await main_call()
        except UnknownBlock:
            if block is None:
                raise
            return await archive_call()
```

Expose the same method names as the contact surface by forwarding through `_delegate`.

- [ ] **Step 4: Change the pool to pool routers instead of contacts**

```python
class BittensorClientPool[BTClient]:
    def __init__(
        self,
        contact_factory: ContactFactory,
        archive_uri: BittensorNetwork,
        uri: BittensorNetwork,
        archive_blocks_cutoff: ArchiveBlocksCutoff,
        pool_closing_timeout: float = 60,
    ) -> None:
        self._pool: dict[WalletKey | None, BittensorRouter] = {}
```

```python
router = BittensorRouter(
    wallet=wallet,
    main_contact=self.contact_factory.create(wallet, self.client_kwargs["uri"]),
    archive_contact=self.contact_factory.create(wallet, self.client_kwargs["archive_uri"]),
    archive_blocks_cutoff=self.client_kwargs["archive_blocks_cutoff"],
)
await router.open()
```

Rename the generic bound and local variables from “client” to “router” where that improves readability.

- [ ] **Step 5: Update app dependencies and lifespans**

```python
async def bt_router_identity_dep(
    bt_client_pool: BittensorClientPool[BittensorRouter], identity: Identity
) -> AsyncGenerator[BittensorRouter]:
    async with bt_client_pool.acquire(wallet=identity.wallet) as router:
        yield router
```

Use the router in dependencies, but keep the public dependency names stable until the handler refactor lands to minimize churn.

- [ ] **Step 6: Run router and pool tests**

Run: `cd pylon_service && uv run pytest tests/unit/bittensor/test_router.py tests/unit/bittensor/test_bittensor_client_pool.py -q`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add pylon_service/pylon_service/bittensor/router.py \
        pylon_service/pylon_service/bittensor/pool.py \
        pylon_service/pylon_service/dependencies.py \
        pylon_service/pylon_service/lifespans.py \
        pylon_service/tests/unit/bittensor/test_router.py \
        pylon_service/tests/unit/bittensor/test_bittensor_client_pool.py
git commit -m "refactor: add wallet-bound bittensor router"
```

## Task 3: Move Domain Logic Into Canonical Services

**Files:**
- Create: `pylon_service/pylon_service/services/blocks.py`
- Create: `pylon_service/pylon_service/services/neurons.py`
- Create: `pylon_service/pylon_service/services/certificates.py`
- Create: `pylon_service/pylon_service/services/commitments.py`
- Create: `pylon_service/pylon_service/services/weights.py`
- Modify: `pylon_service/pylon_service/api/_unstable/tasks.py`
- Modify: `pylon_service/pylon_service/bittensor/recent/tasks.py`
- Modify: `pylon_service/pylon_service/dependencies.py`

- [ ] **Step 1: Write a failing public-path test for one moved behavior**

```python
async def test_latest_validators_sorts_by_total_stake_descending(test_client, snapshot_json):
    response = await test_client.get("/api/_unstable/subnet/1/block/latest/validators")

    assert response.status_code == 200
    assert snapshot_json == response.json()
```

- [ ] **Step 2: Run the validator test to verify it fails after the contact/router split**

Run: `cd pylon_service && uv run pytest tests/unit/open_access_endpoints/test_get_validators_endpoint.py -q`

Expected: FAIL because validators are no longer computed in the transport layer

- [ ] **Step 3: Implement canonical services**

```python
class BlockNotFoundError(Exception):
    pass


class BlockService:
    async def get_existing_block(self, router: BittensorPort, block_number: BlockNumber) -> Block:
        block = await router.get_block(block_number)
        if block is None:
            raise BlockNotFoundError(f"Block {block_number} not found.")
        return block
```

```python
class NeuronService:
    async def get_neurons(self, router: BittensorPort, netuid: NetUid, block: Block) -> SubnetNeurons:
        return await router.get_neurons(netuid, block)

    async def get_latest_neurons(self, router: BittensorPort, netuid: NetUid) -> SubnetNeurons:
        block = await router.get_latest_block()
        return await router.get_neurons(netuid, block)

    async def get_validators(self, router: BittensorPort, netuid: NetUid, block: Block) -> SubnetValidators:
        subnet_neurons = await router.get_neurons(netuid, block)
        validators = [neuron for neuron in subnet_neurons.neurons.values() if neuron.validator_permit]
        validators.sort(key=lambda neuron: neuron.stakes.total, reverse=True)
        return SubnetValidators(block=block, validators=validators)

    async def get_recent_neurons(
        self,
        recent_object_provider: RecentObjectProvider,
    ) -> SubnetNeurons:
        return await recent_object_provider.get(SubnetNeurons)
```

```python
class CommitmentService:
    async def get_commitments(self, router: BittensorPort, netuid: NetUid, block: Block) -> SubnetCommitments:
        commitments = await router.get_commitments(netuid, block)
        state = await router.get_subnet_state(netuid, block)
        registered_hotkeys = set(state.hotkeys)
        filtered = {
            hotkey: commitment
            for hotkey, commitment in commitments.commitments.items()
            if hotkey in registered_hotkeys
        }
        return SubnetCommitments(block=commitments.block, commitments=filtered)
```

```python
class WeightsService:
    async def apply_weights(self, router: BittensorPort, netuid: NetUid, weights: dict[Hotkey, Weight]) -> None:
        latest_block = await router.get_latest_block()
        hyperparams = await router.get_hyperparams(netuid, latest_block)
        if hyperparams is None:
            raise RuntimeError("Failed to fetch hyperparameters")
        translated_weights = await self._translate_weights(router, netuid, weights)
        if hyperparams.commit_reveal_weights_enabled and hyperparams.commit_reveal_weights_enabled != CommitReveal.DISABLED:
            await router.commit_weights(netuid, translated_weights)
        else:
            await router.set_weights(netuid, translated_weights)
```

Move hotkey-to-uid translation into `WeightsService` rather than leaving it in the contact.
Define domain exceptions for:

- missing block
- missing certificate
- missing commitment
- missing recent object
- stale recent object
- certificate generation failure
- commitment submission failure

Handlers will translate these into HTTP-layer exceptions later.

- [ ] **Step 4: Move recent-cache access into services and pass cache providers through dependencies**

```python
async def recent_object_provider_open_access_dep(netuid: NetUid, request: Request) -> RecentObjectProvider:
    return _create_recent_object_provider(request, SubnetContext(netuid))
```

Keep the dependency provider, but handlers should pass the provider into services instead of reading cache directly.

- [ ] **Step 5: Update background jobs and recent tasks to call services**

```python
class ApplyWeights(
    BackgroundTask,
    duration_metric=apply_weights_job_duration,
    metric_labels={"netuid": Attr("_netuid"), "hotkey": Attr("_hotkey")},
):
    def __init__(self, service: WeightsService, router: BittensorPort, weights: dict[Hotkey, Weight], netuid: NetUid):
        self._service = service
        self._router = router
```

```python
await self._service.apply_weights(self._router, self._netuid, self._weights)
```

```python
class UpdateRecentNeurons(UpdateRecentObject[SubnetNeurons, SubnetContext]):
    def __init__(self, store: Store, pool: BittensorClientPool, neuron_service: NeuronService) -> None:
        super().__init__(store, pool)
        self._neuron_service = neuron_service
```

- [ ] **Step 6: Run focused tests**

Run: `cd pylon_service && uv run pytest tests/unit/open_access_endpoints/test_get_validators_endpoint.py tests/unit/bittensor/recent/tasks/test_update_recent_neurons_task.py -q`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add pylon_service/pylon_service/services \
        pylon_service/pylon_service/api/_unstable/tasks.py \
        pylon_service/pylon_service/bittensor/recent/tasks.py \
        pylon_service/pylon_service/dependencies.py \
        pylon_service/tests/unit/open_access_endpoints/test_get_validators_endpoint.py \
        pylon_service/tests/unit/bittensor/recent/tasks/test_update_recent_neurons_task.py
git commit -m "refactor: move bittensor domain logic into services"
```

## Task 4: Add Versioned Service Entry Points And DTO Compatibility

**Files:**
- Create: `pylon_service/pylon_service/api/_unstable/services.py`
- Create: `pylon_service/pylon_service/api/v1/services.py`
- Test: `pylon_service/tests/unit/open_access_endpoints/test_get_commitments_endpoint.py`
- Test: `pylon_service/tests/unit/identity_endpoints/test_get_commitment_by_hotkey_endpoint.py`

- [ ] **Step 1: Write the failing v1 commitments test**

```python
async def test_v1_commitments_returns_hex_strings(test_client, snapshot_json):
    response = await test_client.get("/api/v1/subnet/1/block/latest/commitments")

    assert response.status_code == 200
    assert snapshot_json == response.json()
```

- [ ] **Step 2: Run the commitments tests to verify they fail**

Run: `cd pylon_service && uv run pytest tests/unit/open_access_endpoints/test_get_commitments_endpoint.py tests/unit/identity_endpoints/test_get_commitment_by_hotkey_endpoint.py -q`

Expected: FAIL because handlers still serialize directly from router results

- [ ] **Step 3: Implement `_unstable` service entrypoints**

```python
from pylon_service.services.commitments import CommitmentService as CanonicalCommitmentService
from pylon_service.services.neurons import NeuronService as CanonicalNeuronService


class CommitmentService(CanonicalCommitmentService):
    async def to_get_commitments_response(
        self,
        router: BittensorPort,
        netuid: NetUid,
    ) -> GetCommitmentsResponse:
        block = await router.get_latest_block()
        result = await self.get_commitments(router, netuid, block)
        return GetCommitmentsResponse.model_validate(result, from_attributes=True)
```

- [ ] **Step 4: Implement `v1` service overrides**

```python
from pylon_service.api._unstable.services import CommitmentService as UnstableCommitmentService


class CommitmentService(UnstableCommitmentService):
    async def to_get_commitments_response(
        self,
        router: BittensorPort,
        netuid: NetUid,
    ) -> v1_responses.GetCommitmentsResponse:
        block = await router.get_latest_block()
        result = await self.get_commitments(router, netuid, block)
        return v1_responses.GetCommitmentsResponse(
            block=result.block,
            commitments={hotkey: item.commitment for hotkey, item in result.commitments.items()},
        )
```

Create equivalent pass-through or override classes for blocks, neurons, certificates, commitments, and weights.

- [ ] **Step 5: Run the versioned endpoint tests**

Run: `cd pylon_service && uv run pytest tests/unit/open_access_endpoints/test_get_commitments_endpoint.py tests/unit/identity_endpoints/test_get_commitment_by_hotkey_endpoint.py -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pylon_service/pylon_service/api/_unstable/services.py \
        pylon_service/pylon_service/api/v1/services.py \
        pylon_service/tests/unit/open_access_endpoints/test_get_commitments_endpoint.py \
        pylon_service/tests/unit/identity_endpoints/test_get_commitment_by_hotkey_endpoint.py
git commit -m "refactor: add versioned pylon service entrypoints"
```

## Task 5: Make Handlers Declarative And Remove Cross-Version Inheritance

**Files:**
- Modify: `pylon_service/pylon_service/api/_unstable/api.py`
- Modify: `pylon_service/pylon_service/api/v1/api.py`
- Modify: `pylon_service/pylon_service/dependencies.py`
- Test: `pylon_service/tests/unit/open_access_endpoints/test_get_neurons_endpoint.py`
- Test: `pylon_service/tests/unit/identity_endpoints/test_put_weights_endpoint.py`

- [ ] **Step 1: Write a failing handler-level regression test**

```python
async def test_v1_open_access_controller_uses_v1_commitment_service(test_client, monkeypatch):
    calls: list[str] = []

    class SpyCommitmentService(CommitmentService):
        async def to_get_commitments_response(self, router, netuid):
            calls.append("v1")
            return await super().to_get_commitments_response(router, netuid)

    monkeypatch.setattr(v1_services, "CommitmentService", SpyCommitmentService)

    response = await test_client.get("/api/v1/subnet/1/block/latest/commitments")

    assert response.status_code == 200
    assert calls == ["v1"]
```

- [ ] **Step 2: Run the handler regression test**

Run: `cd pylon_service && uv run pytest tests/unit/open_access_endpoints/test_get_commitments_endpoint.py -q`

Expected: FAIL because `v1` still inherits handler implementations from `_unstable`

- [ ] **Step 3: Refactor `_unstable` handlers to call services only**

```python
@handler(Endpoint.LATEST_NEURONS)
async def get_latest_neurons(self, bt_client: BittensorPort, netuid: NetUid) -> GetNeuronsResponse:
    return await services.NeuronService().get_latest_neurons_response(bt_client, netuid)
```

```python
@handler(Endpoint.RECENT_NEURONS)
async def get_recent_neurons(
    self,
    recent_object_provider: RecentObjectProvider,
) -> GetNeuronsResponse:
    try:
        return await services.NeuronService().get_recent_neurons_response(recent_object_provider)
    except services.RecentObjectMissingError as exc:
        raise ServiceUnavailableException("Recent neurons data is not available. Cache update may not have finished yet or subnet may not be configured for caching recent objects.") from exc
    except services.RecentObjectStaleError as exc:
        raise ServiceUnavailableException("Recent neurons data is stale. Cache update may be failing.") from exc
```

```python
@handler(Endpoint.SUBNET_WEIGHTS)
async def put_weights_endpoint(self, data: SetWeightsBody, bt_client: BittensorPort, netuid: NetUid) -> Response:
    ApplyWeights(service=services.WeightsService(), router=bt_client, weights=data.weights, netuid=netuid).schedule()
    return Response({"detail": "weights update scheduled", "count": len(data.weights)}, status_code=status_codes.HTTP_200_OK)
```

Keep handler logic limited to dependency capture, one service call, and HTTP-specific exception translation.
For all service failures, map domain exceptions here rather than raising HTTP exceptions from services.

- [ ] **Step 4: Replace v1 handler inheritance with explicit controllers**

```python
class OpenAccessController(Controller):
    path = "/subnet/{netuid:int}/"
    dependencies = {
        "bt_client": Provide(bt_client_open_access_dep),
        "recent_object_provider": Provide(recent_object_provider_open_access_dep),
    }

    @handler(Endpoint.LATEST_COMMITMENTS)
    async def get_commitments_endpoint(self, bt_client: BittensorPort, netuid: NetUid) -> GetCommitmentsResponse:
        return await services.CommitmentService().to_get_commitments_response(bt_client, netuid)
```

Write out the v1 controllers directly. Do not subclass `_unstable` controllers.

- [ ] **Step 5: Run endpoint tests**

Run: `cd pylon_service && uv run pytest tests/unit/open_access_endpoints tests/unit/identity_endpoints -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pylon_service/pylon_service/api/_unstable/api.py \
        pylon_service/pylon_service/api/v1/api.py \
        pylon_service/pylon_service/dependencies.py \
        pylon_service/tests/unit/open_access_endpoints \
        pylon_service/tests/unit/identity_endpoints
git commit -m "refactor: make versioned handlers declarative"
```

## Task 6: Rework Test Infrastructure To Mock Only Contacts

**Files:**
- Modify: `pylon_service/tests/conftest.py`
- Modify: `pylon_service/tests/unit/conftest.py`
- Modify: `pylon_service/tests/integration/conftest.py`
- Create: `pylon_service/tests/world.py`
- Delete: `pylon_service/tests/mock_bittensor_client.py`
- Modify: unit tests under `pylon_service/tests/unit`

- [ ] **Step 1: Write a failing shared-world test**

```python
async def test_shared_world_serves_latest_neurons_without_per_test_setup(test_client):
    response = await test_client.get("/api/_unstable/subnet/1/block/latest/neurons")

    assert response.status_code == 200
    assert response.json()["block"]["number"] == 100
    assert len(response.json()["neurons"]) >= 1
```

- [ ] **Step 2: Run the fixture test**

Run: `cd pylon_service && uv run pytest tests/unit/open_access_endpoints/test_get_latest_neurons_endpoint.py -q`

Expected: FAIL because the current tests still require per-test mock transport world setup

- [ ] **Step 3: Add the shared-world module and autouse fixture**

```python
@dataclass
class SharedWorld:
    latest_block: Block
    subnet_1_neurons: SubnetNeurons
    subnet_2_neurons: SubnetNeurons
    subnet_1_commitments: SubnetCommitments
    subnet_2_commitments: SubnetCommitments
```

```python
async def configure_contact(self, contact: MockBittensorContact) -> None:
    contact.reset()
    contact.enqueue("get_latest_block", self.latest_block)
    contact.enqueue("get_neurons", self.subnet_1_neurons)
    contact.enqueue("get_neurons", self.subnet_2_neurons)
    ...
```

```python
@pytest.fixture(autouse=True)
async def shared_world_fixture(shared_world, open_access_mock_contact, sn1_mock_contact, sn2_mock_contact):
    await shared_world.configure_contact(open_access_mock_contact)
    await shared_world.configure_contact(sn1_mock_contact)
    await shared_world.configure_contact(sn2_mock_contact)
```

Use multiple `netuid`s in the shared world when tests need incompatible default state.
Provide world builders for both happy and unhappy HTTP paths so tests can assert full response bodies without rebuilding
the chain state inline in every file.

- [ ] **Step 4: Patch the contact factory in test app setup**

```python
@pytest.fixture(scope="session")
def mock_contact_factory():
    return ContactFactory(contact_cls=MockBittensorContact)
```

```python
with (
    patch.object(lifespans, "contact_factory", mock_contact_factory),
    patch.object(lifespans, "scheduler_lifespan", mock_scheduler_lifespan),
    patch.object(main, "stores", {**mock_stores}),
):
    app = create_app()
```

Expose fixtures named `open_access_mock_contact`, `sn1_mock_contact`, and `sn2_mock_contact` by acquiring routers from the real pool and then selecting the underlying mock contact from the router instance.

- [ ] **Step 5: Update unit tests to rely on the shared world by default and override the mock contact only when needed**

```python
response = await test_client.get("/api/_unstable/subnet/1/block/latest/neurons")
assert response.status_code == 200
assert snapshot_json == response.json()
```

```python
open_access_mock_contact.enqueue("get_latest_block", changed_block)
response = await test_client.get("/api/_unstable/subnet/1/block/latest/neurons")
assert response.status_code == 200
assert snapshot_json == response.json()
```

Replace all references to `MockBittensorClient` with `MockBittensorContact`.
Document the shared-world convention in comments/docstrings near the fixture so humans and agents know to extend the
world first and only override transport behavior locally when a test needs a state transition.
Convert endpoint tests to:

- explicit happy-path tests
- explicit unhappy-path tests
- inline status-code assertions
- full-body `syrupy` snapshots
- matcher use only for hard-to-freeze values

- [ ] **Step 6: Run all unit tests**

Run: `cd pylon_service && uv run pytest tests/unit -q`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add pylon_service/tests/conftest.py \
        pylon_service/tests/unit/conftest.py \
        pylon_service/tests/integration/conftest.py \
        pylon_service/tests/world.py \
        pylon_service/tests/unit \
        pylon_service/tests/mock_bittensor_client.py
git commit -m "test: patch contact factory and use mock contacts"
```

## Task 7: Delete The Old Client Module And Run Full Verification

**Files:**
- Delete: `pylon_service/pylon_service/bittensor/client.py`
- Modify: imports that still point at `pylon_service.bittensor.client`

- [ ] **Step 1: Search for remaining old-client imports**

Run: `cd pylon_service && rg -n "bittensor\\.client|AbstractBittensorClient|TurboBtClient|BittensorClient" pylon_service tests`

Expected: only references in migration targets or zero results

- [ ] **Step 2: Remove the old module and update imports**

```python
from pylon_service.bittensor.contact import BittensorPort, ContactFactory, MockBittensorContact, TurboBtContact
from pylon_service.bittensor.router import BittensorRouter
```

Delete the old client module only after the search from Step 1 confirms there are no live imports left.

- [ ] **Step 3: Run the targeted service test suite**

Run: `cd pylon_service && uv run pytest tests/unit tests/integration/test_get_neurons.py tests/integration/test_set_weights.py tests/integration/test_set_commitment.py -q`

Expected: PASS

- [ ] **Step 4: Run the package checks**

Run: `cd pylon_service && uv run ruff check . && uv run pyright && uv run pytest -q`

Expected:
- `ruff check`: no diagnostics
- `pyright`: `0 errors`
- `pytest`: all tests pass

- [ ] **Step 5: Commit**

```bash
git add pylon_service/pylon_service \
        pylon_service/tests
git commit -m "refactor: migrate pylon service to contact router services layers"
```

## Self-Review

### Spec coverage

- Contact split and mock contact: covered by Tasks 1 and 6
- Router replaces `BittensorClient` routing without inheritance: covered by Task 2
- Handlers become short and declarative: covered by Task 5
- Services become the home for logic and background jobs: covered by Task 3
- API-version behavior stays explicit without handler inheritance: covered by Tasks 4 and 5
- Contact-internal models preserve compatibility data: covered by Task 1 and Task 4
- Tests mock only the contact and share one default world: covered by Task 6
- Snapshot-based full response assertions with sparse matcher usage: covered by Tasks 1.5 and 6
- Recent neurons and weight/commitment jobs keep working: covered by Tasks 3, 5, and 7

### Placeholder scan

- No `TODO` or `TBD` markers remain.
- Each task includes exact files, commands, and concrete code snippets.

### Type consistency

- Shared runtime typing is `BittensorPort`.
- The transport seam is `ContactFactory`.
- The pooled runtime object is `BittensorRouter`.
- Versioned logic is in `api/_unstable/services.py` and `api/v1/services.py`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-07-pylon-service-contact-router-refactor.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
