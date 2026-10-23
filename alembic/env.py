from alembic import context
from sqlalchemy import create_engine

import app.inventory.models  # noqa: F401  (registra las tablas en Base.metadata)
import app.orders.models  # noqa: F401
from app.db import Base, database_url

target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = create_engine(database_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
