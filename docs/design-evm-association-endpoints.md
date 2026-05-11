# Design: EVM Association Endpoints

## Background

The `AssociatedEvmAddress` storage map on-chain links subnet UIDs to EVM (H160) addresses,
recording the last block where ownership was proven. Two functions in
`associations.py` provide two distinct query patterns we want to
expose through pylon_service.

### POC Script (`associations.py`)

```python
from pprint import pprint
from typing import NamedTuple, NewType

import bittensor

NetUid = NewType("NetUid", int)
BlockNumber = NewType("BlockNumber", int)
EvmAddress = NewType("EvmAddress", str)
Uid = NewType("Uid", int)
Hotkey = NewType("Hotkey", str)


class EvmAssociation(NamedTuple):
    uid: Uid
    hotkey: Hotkey
    evm_address: EvmAddress
    last_block_where_ownership_was_proven: BlockNumber


def get_evm_keys(
    subtensor: bittensor.Subtensor,
    netuid: NetUid,
    block: BlockNumber,
    uid_to_hotkey: dict[Uid, Hotkey] | None = None,
) -> dict[Hotkey, EvmAssociation]:
    if uid_to_hotkey is None:
        metagraph_info = subtensor.get_metagraph_info(netuid=netuid, block=block)
        assert metagraph_info is not None, "failed to get metagraph info"
        uid_to_hotkey = {Uid(i): Hotkey(hk) for i, hk in enumerate(metagraph_info.hotkeys)}

    associations = subtensor.query_map_subtensor(
        "AssociatedEvmAddress", block=block, params=[netuid]
    )

    result = {}
    for uid, scale_obj in associations:
        hotkey = uid_to_hotkey.get(Uid(uid))
        if hotkey is None:
            continue
        evm_address_raw, association_block = scale_obj.value
        evm_address = EvmAddress("0x" + bytes(evm_address_raw[0]).hex())
        result[hotkey] = EvmAssociation(
            Uid(uid), hotkey, evm_address, BlockNumber(association_block)
        )

    return result


def get_evm_keys_block_range(
    subtensor: bittensor.Subtensor,
    netuid: NetUid,
    start_block: BlockNumber,
    end_block: BlockNumber,
) -> dict[Hotkey, list[EvmAssociation]]:
    metagraph_info = subtensor.get_metagraph_info(netuid=netuid, block=end_block)
    assert metagraph_info is not None, "failed to get metagraph info"
    uid_to_hotkey = {Uid(i): Hotkey(hk) for i, hk in enumerate(metagraph_info.hotkeys)}
    uid_reg_block = {
        Uid(i): BlockNumber(b) for i, b in enumerate(metagraph_info.block_at_registration)
    }

    result: dict[Hotkey, set[EvmAssociation]] = {}
    queried_blocks: set[BlockNumber] = set()
    blocks_to_query: set[BlockNumber] = {end_block}

    while blocks_to_query:
        block = blocks_to_query.pop()
        if block in queried_blocks:
            continue
        queried_blocks.add(block)

        for hotkey, assoc in get_evm_keys(subtensor, netuid, block, uid_to_hotkey).items():
            # Skip if this block predates the current hotkey's registration — at that
            # block the UID belonged to a different hotkey.
            if block < uid_reg_block[assoc.uid]:
                continue
            result.setdefault(hotkey, set()).add(assoc)
            prev_block = BlockNumber(assoc.last_block_where_ownership_was_proven - 1)
            if (
                assoc.last_block_where_ownership_was_proven > start_block
                and prev_block >= start_block
                and prev_block >= uid_reg_block[assoc.uid]
                and prev_block not in queried_blocks
            ):
                blocks_to_query.add(prev_block)

    return {hotkey: list(assocs) for hotkey, assocs in result.items()}


def main() -> None:
    netuid = NetUid(12)
    with bittensor.Subtensor(network="archive") as subtensor:
        start_block = BlockNumber(8130010 - 7200 * 7)
        end_block = BlockNumber(8130010 - 7200 * 7 + 100)
        associations = get_evm_keys_block_range(subtensor, netuid, start_block, end_block)

    print(start_block, end_block)
    pprint(dict(associations))


if __name__ == "__main__":
    main()
```

---

## New Types & Models

**`pylon_commons/types.py`**

```python
EvmAddress = NewType("EvmAddress", str)  # "0x"-prefixed H160
```

**`pylon_commons/models.py`** — new model:

```python
class EvmAssociation(BittensorModel):
    uid: NeuronUid
    hotkey: Hotkey
    evm_address: EvmAddress
    last_block_where_ownership_was_proven: BlockNumber
```

---

## Endpoint 1 — EVM Associations at a Block

**`GET /api/_unstable/subnet/{netuid}/block/{block_number}/evm-associations`**
**`GET /api/_unstable/subnet/{netuid}/block/latest/evm-associations`**

Maps to `get_evm_keys()`. Returns every hotkey → EVM association recorded at exactly that block.
Both paths share the same handler function; the `latest` variant resolves the current head block
before calling it.

**Access**: Open Access (read-only, `open_access_token`)

**Path params**: `netuid`, `block_number` (omitted on the `latest` path)

**Response** (`GetEvmAssociationsResponse`):

```json
{
  "block": {"number": 1234, "hash": "0x..."},
  "associations": {
    "5C4hr...": {
      "uid": 42,
      "evm_address": "0xabcd...",
      "last_block_where_ownership_was_proven": 1234
    }
  }
}
```

**Implementation**: Add `get_evm_associations(netuid, block) → dict[Hotkey, EvmAssociation]`
to `BittensorPort` (protocol), `AbstractBittensorContact` (abstract method), and
`BittensorContactRouter` (with archive fallback), wrapping
the turbobt `SubtensorModule.AssociatedEvmAddress` storage map iteration and mapping UIDs to
hotkeys via `get_subnet_state()`. Implement in `TurboBtContact` (inside `contact.py`). Two separate `Endpoint` enum members are needed
(`EVM_ASSOCIATIONS` and `EVM_ASSOCIATIONS_LATEST`) so that Litestar has unique reverse names,
but both point to the same handler. Handler lives in `OpenAccessController` (and mirrored in
`IdentityController`).

---

## Endpoint 2 — EVM Associations over a Block Range

**`GET /api/_unstable/subnet/{netuid}/evm-associations?start_block={start}&end_block={end}`**

Maps to `get_evm_keys_block_range()`. Walks history by following the
`last_block_where_ownership_was_proven - 1` pointers back from `end_block`, filters by the
current hotkey's registration block, and returns per-hotkey association history.

**Access**: Open Access

**Query params**: `start_block`, `end_block` (both required)

**Response** (`GetEvmAssociationsRangeResponse`):

```json
{
  "associations": {
    "5C4hr...": [
      {"uid": 7, "evm_address": "0xabcd...", "last_block_where_ownership_was_proven": 1234},
      {"uid": 7, "evm_address": "0xabcd...", "last_block_where_ownership_was_proven": 900}
    ]
  }
}
```

**Implementation**: The logic requires `get_subnet_state()` (already on `BittensorContactRouter`)
for `block_at_registration` and `hotkeys`, plus multiple `get_evm_associations()` calls. This
is a service-layer concern (not contact-layer), since it orchestrates multiple calls. A new
`EvmAssociationService` (or addition to `services.py`) handles the fan-out loop.

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Access pattern | Open Access only | Both are read-only chain queries; no wallet needed |
| Range params | Query params (not path) | `start_block`/`end_block` are filters, not resource identifiers |
| Block for range endpoint | Uses `end_block` for metagraph lookup | Matches original logic: hotkey→UID mapping taken at `end_block` |
| Response key (range) | `Hotkey` string | Stable across UID reassignments; matches how other endpoints key neuron data |

---

## Performance Concern

Endpoint 2 is **potentially expensive**: it makes O(D) chain queries where D is the number of
distinct `last_block_where_ownership_was_proven` values in the range (worst case: one query per
unique block touched). For long ranges with many association changes this can be hundreds of
round trips. Two mitigations to apply before implementation:

1. **Input validation**: Enforce a max block range (e.g. `end_block - start_block ≤ 50_400`, ~1 week).
2. **Request timeout**: Set a short Litestar handler timeout (e.g. 30s) and return 504 if exceeded.

Both limits can be exposed as settings in `pylon_commons/settings.py`.

---

## Files to Touch

| File | Change |
|---|---|
| `pylon_commons/types.py` | Add `EvmAddress` |
| `pylon_commons/models.py` | Add `EvmAssociation` |
| `pylon_commons/_unstable/endpoints.py` | Add `EVM_ASSOCIATIONS`, `EVM_ASSOCIATIONS_LATEST`, `EVM_ASSOCIATIONS_RANGE` |
| `pylon_commons/_unstable/responses.py` | Add `GetEvmAssociationsResponse`, `GetEvmAssociationsRangeResponse` |
| `pylon_service/pylon_service/bittensor/contact.py` | Add `get_evm_associations()` to `BittensorPort` protocol, add abstract method to `AbstractBittensorContact`, implement in `TurboBtContact` via turbobt `AssociatedEvmAddress` storage map |
| `pylon_service/pylon_service/bittensor/contact_router.py` | Add delegating wrapper with archive fallback |
| `pylon_service/pylon_service/api/_unstable/services.py` | Add `EvmAssociationService` |
| `pylon_service/pylon_service/api/_unstable/api.py` | Register handlers in both controllers |
| `pylon_service/tests/unit/open_access_endpoints/` | New test files per endpoint |
| `pylon_client/...` | Add client methods for both endpoints |
