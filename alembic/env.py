from logging.config import fileConfig
import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy import pool

from alembic import context
from sqlmodel import SQLModel

load_dotenv()

config = context.config

database_url = os.getenv("DATABASE_URL")
if database_url and database_url.startswith("mysql://"):
    database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.db.schema import (
    EmailServiceJob,
    EmailServiceRecipient,
    EmailServiceCertificate,
    EmailServiceEmailBlast,
)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(database_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
