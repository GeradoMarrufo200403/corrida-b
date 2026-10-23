import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_URL = "postgresql+psycopg://orderflow:orderflow@localhost:5432/orderflow"


class Base(DeclarativeBase):
    """Base de los modelos. Todo cambio de esquema debe acompañarse de una migración Alembic."""


def database_url() -> str:
    load_dotenv(ROOT / ".env")
    return os.environ.get("DATABASE_URL", DEFAULT_URL)


def make_engine(url: str | None = None) -> Engine:
    return create_engine(url or database_url(), pool_pre_ping=True)
