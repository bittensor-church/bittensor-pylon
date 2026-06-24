import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from enum import StrEnum
from typing import Self

import structlog
from bittensor_wallet import Wallet
from pydantic import BaseModel, ConfigDict
from pylon_commons.types import ArchiveBlocksCutoff, HotkeyName, WalletName

from pylon_service.bittensor.contact import ContactFactory
from pylon_service.bittensor.contact_router import BittensorContactRouter

logger = structlog.stdlib.get_logger(__name__)


class BittensorContactPoolInvalidState(Exception):
    pass


class WalletKey(BaseModel):
    """
    Unique identifier for a wallet configuration.
    """

    wallet_name: WalletName
    hotkey_name: HotkeyName
    path: str

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_wallet(cls, wallet: Wallet) -> Self:
        return cls(
            wallet_name=WalletName(wallet.name),
            hotkey_name=HotkeyName(wallet.hotkey_str),
            path=wallet.path,
        )


class BittensorContactPool[RouterT: BittensorContactRouter]:
    """
    Pool from which bittensor contact routers can be acquired based on the provided wallet.
    One contact router is shared for the same wallet.
    Once a contact router is opened, the connection is maintained until the pool itself is closed.
    The pool is concurrency safe, but not thread safe:
      - lock ensures that no two tasks will create the same contact router instance simultaneously;
        they will use the same instance,
      - when the pool closes, first it waits for all the acquired contact routers to be released,
        then closes the contact routers gracefully.
    The pool may be re-opened after it is closed.
    """

    class State(StrEnum):
        OPEN = "open"
        CLOSING = "closing"
        CLOSED = "closed"

    def __init__(
        self,
        contact_router_cls: type[RouterT] = BittensorContactRouter,
        contact_factory: ContactFactory | None = None,
        pool_closing_timeout: float = 60,
        **client_kwargs,
    ) -> None:
        if "wallet" in client_kwargs:
            raise ValueError("Wallet may not be given as a client kwarg in the contact pool.")
        self.state = self.State.CLOSED
        self.contact_router_cls = contact_router_cls
        self.contact_factory = contact_factory or ContactFactory()
        self.closing_timeout = pool_closing_timeout
        self._pool: dict[WalletKey | None, RouterT] = {}
        self._close_condition = asyncio.Condition()
        self._acquire_lock = asyncio.Lock()
        self._acquire_counter = 0
        self.client_kwargs = client_kwargs

    async def __aenter__(self) -> Self:
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def open(self):
        self._verify_not_open()
        logger.info("opening_contact_pool", object=self.contact_router_cls.__name__)
        self.state = self.State.OPEN

    async def close(self):
        self._verify_open()
        logger.info("closing_contact_pool_initialized", object=self.contact_router_cls.__name__)
        self.state = self.State.CLOSING
        logger.info(
            "contact_pool_entered_closing_state",
            closing_timeout=self.closing_timeout,
            acquire_counter=self._acquire_counter,
        )
        try:
            async with asyncio.timeout(self.closing_timeout):
                async with self._close_condition:
                    await self._close_condition.wait_for(self._can_close)
        except TimeoutError:
            logger.exception("contact_pool_close_timeout")
        else:
            logger.info("closing_all_contact_routers")
        await asyncio.gather(
            *(contact_router.close() for contact_router in self._pool.values()), return_exceptions=True
        )
        self._pool.clear()
        self.state = self.State.CLOSED
        logger.info("contact_pool_closed", object=self.contact_router_cls.__name__)

    def _can_close(self) -> bool:
        return self._acquire_counter == 0

    def _verify_open(self):
        if self.state != self.State.OPEN:
            raise BittensorContactPoolInvalidState("The pool is not open.")

    def _verify_not_open(self):
        if self.state == self.State.OPEN:
            raise BittensorContactPoolInvalidState("The pool is open.")

    @asynccontextmanager
    async def acquire(self, wallet: Wallet | None) -> AsyncGenerator[RouterT]:
        """
        Acquire an instance of a bittensor contact router with connection ready.
        The contact router will use the provided wallet to perform requests (or no wallet if None is passed).
        Acquiring task MUST NOT close the contact router as it may break other tasks that use the same instance.

        Warning: Do not await for the pool to close from inside this context manager as this may cause a deadlock!

        Raises:
            BittensorContactPoolInvalidState: When acquire is called when the pool is not open.
        """
        self._verify_open()
        self._acquire_counter += 1
        wallet_key = wallet and WalletKey.from_wallet(wallet)
        wallet_name = wallet.name if wallet else None
        logger.debug(
            "acquiring_contact_router",
            wallet_name=wallet_name,
            acquire_counter=self._acquire_counter,
        )
        async with self._acquire_lock:
            if wallet_key in self._pool:
                contact_router = self._pool[wallet_key]
            else:
                logger.debug("opening_new_contact_router", wallet_name=wallet_name)
                contact_router = self._pool[wallet_key] = self.contact_router_cls(
                    wallet=wallet,
                    main_contact=self.contact_factory.create(wallet, self.client_kwargs["uri"]),
                    archive_contact=self.contact_factory.create(wallet, self.client_kwargs["archive_uri"]),
                    archive_blocks_cutoff=self.client_kwargs.get("archive_blocks_cutoff", ArchiveBlocksCutoff(300)),
                )
                await contact_router.open()
        try:
            yield contact_router
        finally:
            async with self._close_condition:
                self._acquire_counter -= 1
                logger.debug(
                    "returning_contact_router",
                    wallet_name=wallet_name,
                    acquire_counter=self._acquire_counter,
                )
                self._close_condition.notify_all()
