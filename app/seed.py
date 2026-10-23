import json
import os
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.inventory.models import Lot, Product
from app.shared.clock import Clock

CATALOG_PATH = Path(__file__).resolve().parent.parent / "seed" / "catalog.json"


def load_catalog(session: Session, clock: Clock, path: Path = CATALOG_PATH) -> None:
    """Carga productos y lotes. Las fechas de caducidad son relativas al día de arranque.
    Es idempotente: si el producto ya existe, no lo toca."""
    data = json.loads(path.read_text(encoding="utf-8"))
    today = clock.today()
    for item in data["products"]:
        if session.get(Product, item["sku"]) is not None:
            continue
        session.add(Product(sku=item["sku"], name=item["name"], price=Decimal(item["price"]), perishable=item["perishable"]))
        session.flush()
        for lot in item["lots"]:
            session.add(
                Lot(
                    code=lot["code"],
                    sku=item["sku"],
                    quantity=lot["quantity"],
                    expires_on=today + timedelta(days=lot["expires_in_days"]),
                    reserved=0,
                )
            )


def reset_and_seed(engine: Engine, clock: Clock) -> None:
    """SOLO PARA PRUEBAS Y DESARROLLO: vacía todas las tablas y vuelve a cargar el catálogo."""
    if os.environ.get("ORDERFLOW_ENV", "development") == "production":
        raise RuntimeError("reset_and_seed está prohibido en producción")
    with Session(engine) as session:
        session.execute(
            text(
                "TRUNCATE reservation_allocations, reservations, order_items, orders, lots, products "
                "RESTART IDENTITY CASCADE"
            )
        )
        load_catalog(session, clock)
        session.commit()
