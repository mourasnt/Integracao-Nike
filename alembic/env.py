from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

from app.db import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except KeyError as ke:
        # Some minimal alembic.ini files may omit [formatters]; fall back to basic logging
        import logging
        logging.basicConfig(level=logging.INFO)
        try:
            import logging as _log
            _log.getLogger(__name__).warning("alembic.ini missing [formatters] section: %s", str(ke))
        except Exception:
            pass
    except Exception as e:
        # Any other logging configuration error should not stop migrations; use basic config
        import logging
        logging.basicConfig(level=logging.INFO)
        try:
            import logging as _log
            _log.getLogger(__name__).exception("Failed to configure logging from alembic.ini: %s", str(e))
        except Exception:
            pass

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def get_url():
    from app.core.config import settings
    return settings.database_url

config.set_main_option("sqlalchemy.url", get_url())

def run_migrations_offline():
    pass


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    from sqlalchemy.ext.asyncio import create_async_engine

    connectable = create_async_engine(get_url())
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())
