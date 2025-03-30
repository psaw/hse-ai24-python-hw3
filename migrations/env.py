import os
import sys


from sqlalchemy import create_engine  # Use create_engine
from sqlalchemy import pool
from sqlalchemy.engine import URL  # Import URL for building connection string

from logging.config import fileConfig
from src.models import Base
from alembic import context

DB_USER = os.getenv("DB_USER", "user")
DB_PASS = os.getenv("DB_PASS", "password")
DB_HOST = os.getenv("DB_HOST", "db")  # Critical one
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "app")

# ############################################################################
# Construct the database URL manually (i.e. ignore 'alembic.ini')
# Need this for migrations at runtime (not at build time)
# ############################################################################

# Using URL object for robustness
database_url_obj = URL.create(
    drivername="postgresql",  # Use the standard sync driver for Alembic
    username=DB_USER,
    password=DB_PASS,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
)
database_url_str = database_url_obj.render_as_string(hide_password=False)
# ----------------------------------------------------------------------------


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Remove setting options in config, we'll use the constructed URL directly
# section = config.config_ini_section
# config.set_section_option(section, "DB_USER", DB_USER)
# ... other set_section_option calls removed ...

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Offline mode can still use the URL from alembic.ini if needed,
    # or we can use the manually constructed one.
    # Let's use the manual one for consistency.
    # url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=database_url_str,  # Use manually constructed URL
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Use the manually constructed URL to create an engine
    connectable = create_engine(database_url_str, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
