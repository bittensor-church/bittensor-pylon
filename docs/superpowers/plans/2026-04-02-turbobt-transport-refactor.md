# TurboBT Transport Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract turbobt lifecycle and raw SDK access behind an abstract transport boundary, keep `TurboBtClient` as the higher-level mapper/composer, and add a patchable factory seam without changing or adding tests in this change.

**Architecture:** `pylon_service.bittensor.client` will define `AbstractTurboBTtransport`, a concrete `TurboBTtransport`, and a module-level `get_turbobt_transport()` factory. `TurboBtClient` will delegate raw turbobt access to the transport, expose the current `Bittensor` instance through a public delegated attribute, and keep all pylon-model translation and higher-level composition above the transport boundary.

**Tech Stack:** Python 3.14, `turbobt`, `asyncio`, `abc`, `pylon_commons`, `ruff`, `pyright`

---

### Task 1: Add The Standards Document To This Repository

**Files:**
- Create: `docs/engineering-standards.md`
- Reference: `/Users/junie/synced_p/new_bittensor_ddos_shield/docs/engineering-standards.md`

- [ ] **Step 1: Copy the standards document into the repo**

Mirror the external standards file into this repository without rewriting its content:

```bash
cp /Users/junie/synced_p/new_bittensor_ddos_shield/docs/engineering-standards.md docs/engineering-standards.md
```

Expected result:
- `docs/engineering-standards.md` exists in this repository
- the content matches the external source document

- [ ] **Step 2: Verify the copied file is present and readable**

Run:

```bash
sed -n '1,40p' docs/engineering-standards.md
```

Expected:
- the file starts with `# Engineering Standards`

- [ ] **Step 3: Commit the standards doc copy**

```bash
git add docs/engineering-standards.md
git commit -m "Add engineering standards document"
```

### Task 2: Define The TurboBT Transport Contact Boundary And Factory

**Files:**
- Modify: `pylon_service/pylon_service/bittensor/client.py`

- [ ] **Step 1: Add the abstract transport contract near the top of the bittensor client module**

Insert a new abstract transport directly after `AbstractBittensorClient` so the transport seam is defined in the same module as the current turbobt implementation:

```python
class AbstractTurboBTtransport(ABC):
    @property
    @abstractmethod
    def bittensor(self) -> Bittensor | None:
        """
        Returns the currently opened raw turbobt client instance, if any.
        """

    @abstractmethod
    async def open(self) -> None:
        """
        Opens the transport and prepares the raw turbobt client.
        """

    @abstractmethod
    async def close(self) -> None:
        """
        Closes the transport and releases the raw turbobt client.
        """

    @abstractmethod
    async def get_block(self, number: BlockNumber) -> TurboBtBlock | None:
        pass

    @abstractmethod
    async def get_block_timestamp(self, block_number: BlockNumber) -> Any:
        pass

    @abstractmethod
    async def list_neurons(self, netuid: NetUid, block_hash: BlockHash) -> list[TurboBtNeuron]:
        pass

    @abstractmethod
    async def get_hyperparameters(self, netuid: NetUid, block_hash: BlockHash) -> TurboBtSubnetHyperparams | None:
        pass

    @abstractmethod
    async def get_certificates(
        self, netuid: NetUid, block_hash: BlockHash
    ) -> dict[str, TurboBtNeuronCertificate] | None:
        pass

    @abstractmethod
    async def get_certificate(
        self, netuid: NetUid, hotkey: Hotkey, block_hash: BlockHash
    ) -> TurboBtNeuronCertificate | None:
        pass

    @abstractmethod
    async def generate_certificate_keypair(
        self, netuid: NetUid, algorithm: TurboBtCertificateAlgorithm
    ) -> TurboBtNeuronCertificateKeypair | None:
        pass

    @abstractmethod
    async def get_subnet_state(self, netuid: NetUid, block_hash: BlockHash) -> dict[str, Any]:
        pass

    @abstractmethod
    async def commit_weights(self, netuid: NetUid, weights: dict[int, float]) -> int:
        pass

    @abstractmethod
    async def set_weights(self, netuid: NetUid, weights: dict[int, float]) -> None:
        pass

    @abstractmethod
    async def get_commitment(
        self, netuid: NetUid, hotkey: Hotkey, block_hash: BlockHash
    ) -> dict[str, Any] | None:
        pass

    @abstractmethod
    async def fetch_commitments(self, netuid: NetUid, block_hash: BlockHash) -> dict[str, dict[str, Any]]:
        pass

    @abstractmethod
    async def set_commitment(self, netuid: NetUid, data: bytes) -> None:
        pass

    @abstractmethod
    async def get_signed_block(self, block_hash: BlockHash) -> SignedBlock | None:
        pass
```

Notes:
- use the real turbobt types already imported in the file
- keep the interface raw and transport-oriented
- do not put any pylon model translation into this abstract

- [ ] **Step 2: Rename the concrete turbobt holder into the transport implementation**

Refactor the current lifecycle-heavy part of `TurboBtClient` into:

```python
class TurboBTtransport(AbstractTurboBTtransport):
    def __init__(self, wallet: Wallet | None, uri: BittensorNetwork):
        self.wallet = wallet
        self.uri = uri
        self._raw_client: Bittensor | None = None
        self._is_client_ready = asyncio.Event()

    @property
    def bittensor(self) -> Bittensor | None:
        return self._raw_client
```

Move these existing methods from `TurboBtClient` into `TurboBTtransport` with behavior preserved:

```python
async def _get_bt_client(self) -> Bittensor: ...
async def open(self) -> None: ...
async def close(self) -> None: ...
async def _recreate_bt_client(self) -> None: ...
async def _protect_turbobt[T](self, coro_factory: Callable[[Bittensor], Awaitable[T]]) -> T: ...
```

Then add raw transport methods implemented in terms of `_protect_turbobt()`:

```python
async def get_block(self, number: BlockNumber) -> TurboBtBlock | None:
    return await self._protect_turbobt(lambda c: c.block(number).get())

async def list_neurons(self, netuid: NetUid, block_hash: BlockHash) -> list[TurboBtNeuron]:
    return await self._protect_turbobt(lambda c: c.subnet(netuid).list_neurons(block_hash=block_hash))

async def get_subnet_state(self, netuid: NetUid, block_hash: BlockHash) -> dict[str, Any]:
    return await self._protect_turbobt(lambda c: c.subnet(netuid).get_state(block_hash))
```

Apply the same pattern to the remaining raw operations used by `TurboBtClient`.

- [ ] **Step 3: Add the module-level factory function and make it the default construction seam**

Add this below the concrete transport class:

```python
_turbobt_transport_instance_factory = TurboBTtransport


def get_turbobt_transport(wallet: Wallet | None, uri: BittensorNetwork) -> AbstractTurboBTtransport:
    return _turbobt_transport_instance_factory(wallet=wallet, uri=uri)
```

Constraints:
- keep the function simple and stateless
- do not add a mock implementation in this change
- the function must return the abstract type so callers depend on the seam, not the concrete class

- [ ] **Step 4: Run focused static verification on the transport extraction**

Run:

```bash
cd pylon_service && uv run python -m py_compile pylon_service/bittensor/client.py
```

Expected:
- no syntax errors

- [ ] **Step 5: Commit the transport boundary extraction**

```bash
git add pylon_service/pylon_service/bittensor/client.py
git commit -m "Extract TurboBT transport boundary"
```

### Task 3: Refactor `TurboBtClient` To Use The Transport Seam

**Files:**
- Modify: `pylon_service/pylon_service/bittensor/client.py`

- [ ] **Step 1: Update `TurboBtClient` construction to depend on the abstract transport**

Change the constructor to accept an optional transport override and otherwise resolve one through the factory:

```python
class TurboBtClient(AbstractBittensorClient):
    def __init__(
        self,
        wallet: Wallet | None,
        uri: BittensorNetwork,
        transport: AbstractTurboBTtransport | None = None,
    ):
        super().__init__(wallet, uri)
        self._transport = transport or get_turbobt_transport(wallet=wallet, uri=uri)

    @property
    def bittensor(self) -> Bittensor | None:
        return self._transport.bittensor
```

Constraints:
- `TurboBtClient` must not construct `TurboBTtransport` directly
- the public `bittensor` attribute must delegate to the transport instead of duplicating state

- [ ] **Step 2: Replace direct turbobt access in `TurboBtClient` with transport calls**

Refactor each public method to consume raw transport methods instead of `_protect_turbobt()` or `_raw_client` directly.

Representative replacements:

```python
async def open(self) -> None:
    await self._transport.open()

async def close(self) -> None:
    await self._transport.close()

async def get_block(self, number: BlockNumber) -> Block | None:
    block_obj = await self._transport.get_block(number)
    if block_obj is None or block_obj.number is None or block_obj.hash is None:
        return None
    return Block(number=BlockNumber(block_obj.number), hash=BlockHash(block_obj.hash))

async def get_subnet_state(self, netuid: NetUid, block: Block) -> SubnetState:
    state = await self._transport.get_subnet_state(netuid, block.hash)
    return SubnetState(**state)  # type: ignore[arg-type]
```

Apply the same change pattern to:
- `get_block_timestamp`
- `get_neurons_list`
- `get_hyperparams`
- `get_certificates`
- `get_certificate`
- `generate_certificate_keypair`
- `_translate_weights`
- `commit_weights`
- `set_weights`
- `get_commitment`
- `get_commitments`
- `set_commitment`
- `get_signed_block`

Do not change:
- pylon model translation helpers
- `_resolve_hotkey`
- validator sorting logic
- archive fallback logic in `BittensorClient`

- [ ] **Step 3: Remove transport-only state and helpers from `TurboBtClient`**

Delete these members from `TurboBtClient` once all call sites are migrated:

```python
self._raw_client
self._is_client_ready
async def _get_bt_client(...)
async def _recreate_bt_client(...)
async def _protect_turbobt(...)
```

Expected result:
- `TurboBtClient` no longer touches `turbobt.Bittensor` directly
- only the transport knows how to create, close, recreate, and protect the raw client

- [ ] **Step 4: Run module-level verification and one existing focused test selection without editing tests**

Run:

```bash
cd pylon_service && uv run python -m py_compile pylon_service/bittensor/client.py
```

Then run:

```bash
cd pylon_service && nox -s test -- tests/unit/bittensor/test_bittensor_client_delegation.py
```

Expected:
- the module compiles
- the fallback wrapper test still passes without any test edits

If the test command is too heavy in this environment, replace it with:

```bash
cd pylon_service && uv run pytest tests/unit/bittensor/test_bittensor_client_delegation.py -q
```

- [ ] **Step 5: Commit the `TurboBtClient` transport adoption**

```bash
git add pylon_service/pylon_service/bittensor/client.py
git commit -m "Refactor TurboBtClient to use transport"
```

### Task 4: Final Verification And Cleanup

**Files:**
- Modify: `pylon_service/pylon_service/bittensor/client.py`
- Create: `docs/engineering-standards.md`

- [ ] **Step 1: Review the final diff for scope control**

Run:

```bash
git diff --stat HEAD~2..HEAD
git diff -- pylon_service/pylon_service/bittensor/client.py docs/engineering-standards.md
```

Expected:
- only the client module and the copied standards doc are part of the functional change
- no test files were added or modified

- [ ] **Step 2: Run final verification commands**

Run:

```bash
cd pylon_service && uv run python -m py_compile pylon_service/bittensor/client.py
cd pylon_service && uv run pytest tests/unit/bittensor/test_bittensor_client_delegation.py -q
```

Expected:
- syntax is valid
- at least one existing behavior-level test covering the wrapper still passes

- [ ] **Step 3: Create the final commit**

```bash
git add docs/engineering-standards.md pylon_service/pylon_service/bittensor/client.py
git commit -m "Refactor turbobt access behind transport seam"
```

## Self-Review

Spec coverage:
- abstract transport boundary: covered in Task 2
- concrete `TurboBTtransport`: covered in Task 2
- module-level factory seam: covered in Task 2
- `TurboBtClient` delegation and public `bittensor` exposure: covered in Task 3
- standards doc copy: covered in Task 1
- no test additions or edits: enforced in Tasks 3 and 4

Placeholder scan:
- no `TODO`, `TBD`, or deferred implementation notes remain

Type consistency:
- plan consistently uses `AbstractTurboBTtransport`, `TurboBTtransport`, and `get_turbobt_transport()`
- `TurboBtClient.bittensor` is consistently delegated from the transport
