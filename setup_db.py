"""Prepara la base de datos de ESTA carpeta: la crea si no existe, aplica las migraciones y carga el catálogo.

Uso (con Postgres arriba: docker compose up -d):
    python setup_db.py

Lee DATABASE_URL del archivo .env. Es seguro ejecutarlo varias veces.
"""
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db import database_url, make_engine
from app.seed import load_catalog
from app.shared.clock import SystemClock


def ensure_database(url) -> None:
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database}).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
            print(f"Base creada: {url.database}")
    admin.dispose()


def main() -> int:
    url = make_url(database_url())
    try:
        ensure_database(url)
    except OperationalError:
        print("No se pudo conectar a Postgres. ¿Corriste 'docker compose up -d' y esperaste a que esté listo?")
        return 1
    command.upgrade(Config("alembic.ini"), "head")
    engine = make_engine()
    with Session(engine) as session:
        load_catalog(session, SystemClock())
        session.commit()
    print(f"Listo: base '{url.database}' migrada y con catálogo cargado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
