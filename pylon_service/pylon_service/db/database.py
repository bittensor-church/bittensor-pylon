import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from pylon_service.settings import database_settings

engine = create_async_engine(database_settings.get_url())


@event.listens_for(engine.sync_engine, "connect")
def configure_sqlite(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


session_factory = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def run_migrations() -> None:
    service_root = Path(__file__).resolve().parents[2]
    alembic_cfg_path = service_root / "alembic.ini"

    if not os.path.exists(alembic_cfg_path):
        raise FileNotFoundError(f"Alembic config file not found: {alembic_cfg_path}")

    alembic_cfg = Config(alembic_cfg_path)
    command.upgrade(alembic_cfg, "head")
