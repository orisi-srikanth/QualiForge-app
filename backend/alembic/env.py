import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, create_engine
from sqlalchemy import pool

from alembic import context

# Ensure both backend and repo root are in python path
_env_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_env_dir)
_repo_dir = os.path.dirname(_backend_dir)
for _p in [_repo_dir, _backend_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from backend.app.core.config import settings
    from backend.app.db.models import Base
except ImportError:
    from app.core.config import settings
    from app.db.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    url = settings.DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True if url.startswith("sqlite") else False,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        db_file = url.split("///")[-1] if "///" in url else url.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(os.path.abspath(db_file)), exist_ok=True)

    connectable = create_engine(
        url,
        connect_args=connect_args,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True if url.startswith("sqlite") else False,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
