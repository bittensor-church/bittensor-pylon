from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from pylon_service.db import models  # noqa: F401
from pylon_service.db.database import Base
from pylon_service.settings import database_settings

# Alembic Config object providing access to the values within the .ini file in use.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = database_settings.get_url(async_db=False)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using URL from database_settings"""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_settings.get_url(async_db=False)
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    # Used when Alembic is asked to generate SQL instead of touching the DB,
    # e.g. `alembic upgrade head --sql`.
    run_migrations_offline()
else:
    # Used whenever Alembic applies migrations to a real DB connection,
    # including `alembic upgrade head` and startup-triggered migrations.
    run_migrations_online()
