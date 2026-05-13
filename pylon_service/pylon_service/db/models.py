import enum
from datetime import datetime

from pylon_commons.types import BlockNumber, Hotkey, IdentityName, MechanismId, NetUid, Weight
from sqlalchemy import JSON, DateTime, Enum, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from pylon_service.db.database import Base


class TaskStatus(enum.Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class WeightTask(Base):
    __tablename__ = "weight_tasks"
    __table_args__ = (
        Index(
            "ix_weight_tasks_epoch_lookup",
            "identity_name",
            "mechanism_id",
            "status",
            "start_block_number",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus, native_enum=False), default=TaskStatus.RUNNING)

    identity_name: Mapped[IdentityName] = mapped_column(String)
    weights: Mapped[dict[Hotkey, Weight]] = mapped_column(JSON)
    netuid: Mapped[NetUid] = mapped_column(Integer)
    mechanism_id: Mapped[MechanismId] = mapped_column(Integer)
    hotkey: Mapped[Hotkey] = mapped_column(String)
    start_block_number: Mapped[BlockNumber | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
