from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.models import Base  # noqa: F401  (registers all models on Base.metadata)

# Settings() above already reads .env for the typed config fields; this also
# puts .env's values into os.environ so a migration script can read an
# untyped one directly (e.g. MATRISATHI_APP_DB_PASSWORD in 0002_*.py) without
# every one-off migration setting needing its own Settings field.
load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Migrations always run as the migration-owner role, never the restricted
# application role — schema changes (DDL) are out of scope for app credentials.
#
# `%` is doubled because this value is stored through a ConfigParser
# (alembic's Config wraps one), which treats `%` as its own interpolation
# syntax — a literal `%` in the URL (e.g. from a percent-encoded special
# character in a password) otherwise raises ValueError with the *entire
# value, including the password, embedded in the exception message*.
config.set_main_option("sqlalchemy.url", settings.database_url_migrator.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
