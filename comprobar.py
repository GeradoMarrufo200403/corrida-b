"""Clase 5. Actividad 1. Comprobador de cancelacion.

Uso (desde la raiz de la carpeta que quiere comprobar, junto a la carpeta app):
    python comprobar.py          # comprobaciones K1 a K10 (antes del giro)
    python comprobar.py --giro   # comprobaciones G1 a G5 (despues del giro)

Imprime PASS o FAIL por comprobacion y un resumen. No modifica su codigo.
Usa la base de datos de DATABASE_URL (archivo .env de esa carpeta) y la VACIA al iniciar cada comprobacion:
no la apunte a una base con datos que le importen.
"""
import sys
from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.container import Container
from app.main import create_app
from app.notifications import ConsoleNotificationSender
from app.seed import reset_and_seed
from app.shared.clock import FixedClock

TAB = "CAC-TAB-70"


def entorno():
    clock = FixedClock(datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc))
    notifier = ConsoleNotificationSender()
    container = Container(clock=clock, notifier=notifier)
    reset_and_seed(container.engine, clock)  # base limpia y catalogo fresco en cada comprobacion
    client = TestClient(create_app(container), raise_server_exceptions=False)
    return client, clock, notifier


def crear(c, qty, email="ana@correo.com"):
    return c.post("/orders", json={"customer_email": email, "items": [{"sku": TAB, "quantity": qty}]}).json()


def pagar(c, o):
    c.post(f"/orders/{o['id']}/pay", json={"amount": o["total"]})
    return o["id"]


def disponible(c):
    return c.get(f"/inventory/{TAB}").json()["available"]


def D(x):
    return Decimal(str(x))


# ---------- Antes del giro ----------
def k1():
    c, _, _ = entorno(); o = crear(c, 2)
    r = c.post(f"/orders/{o['id']}/cancel")
    return r.status_code == 200 and r.json()["status"] == "CANCELLED"


def k2():
    c, _, _ = entorno(); o = crear(c, 10)
    antes = disponible(c)
    c.post(f"/orders/{o['id']}/cancel")
    return antes == 70 and disponible(c) == 80


def k3():
    c, _, _ = entorno(); oid = pagar(c, crear(c, 3))
    r = c.post(f"/orders/{oid}/cancel")
    return r.status_code == 409 and c.get(f"/orders/{oid}").json()["status"] == "PAID"


def k4():
    c, _, _ = entorno(); oid = pagar(c, crear(c, 10))
    antes = disponible(c)
    c.post(f"/orders/{oid}/cancel")
    return disponible(c) == antes == 70


def k5():
    c, _, _ = entorno(); oid = pagar(c, crear(c, 2))
    c.post(f"/orders/{oid}/ship")
    return c.post(f"/orders/{oid}/cancel").status_code == 409 and c.get(f"/orders/{oid}").json()["status"] == "SHIPPED"


def k6():
    c, _, _ = entorno(); o = crear(c, 2)
    c.post(f"/orders/{o['id']}/cancel")
    return c.post(f"/orders/{o['id']}/cancel").status_code == 409


def k7():
    c, _, _ = entorno()
    return c.post("/orders/999/cancel").status_code == 404


def k8():
    c, _, _ = entorno(); o = crear(c, 2)
    c.post(f"/orders/{o['id']}/cancel")
    return c.post(f"/orders/{o['id']}/pay", json={"amount": o["total"]}).status_code == 409


def k9():
    c, _, n = entorno(); o = crear(c, 2)
    antes = len(n.sent)
    c.post(f"/orders/{o['id']}/cancel")
    return len(n.sent) == antes


def k10():
    c, _, _ = entorno(); a = crear(c, 5); crear(c, 7)
    c.post(f"/orders/{a['id']}/cancel")
    return disponible(c) == 80 - 7


PRE = [
    ("K1", "Cancelar un pedido pendiente lo deja en CANCELLED", k1),
    ("K2", "Al cancelarlo, lo apartado vuelve a estar disponible", k2),
    ("K3", "Un pedido pagado NO se cancela (409) y sigue en PAID", k3),
    ("K4", "El rechazo de un pedido pagado no libera nada de lo apartado", k4),
    ("K5", "Un pedido enviado NO se cancela (409) y sigue en SHIPPED", k5),
    ("K6", "Cancelar dos veces el mismo pedido responde 409", k6),
    ("K7", "Cancelar un pedido que no existe responde 404", k7),
    ("K8", "Un pedido cancelado ya no se puede pagar (409)", k8),
    ("K9", "Cancelar no envia correos al cliente", k9),
    ("K10", "Cancelar un pedido no toca lo apartado por otros pedidos", k10),
]


# ---------- Despues del giro ----------
def g1():
    c, clock, _ = entorno(); oid = pagar(c, crear(c, 6)); clock.advance(hours=23)
    r = c.post(f"/orders/{oid}/cancel").json()
    return r["status"] == "CANCELLED" and D(r["refund_amount"]) == D("459.00") and D(r["penalty"]) == D("0.00")


def g2():
    c, clock, _ = entorno(); oid = pagar(c, crear(c, 6)); clock.advance(hours=24)
    r = c.post(f"/orders/{oid}/cancel").json()
    return D(r["penalty"]) == D("0.00") and D(r["refund_amount"]) == D("459.00")


def g3():
    c, clock, _ = entorno(); oid = pagar(c, crear(c, 6)); clock.advance(hours=24, minutes=1)
    r = c.post(f"/orders/{oid}/cancel").json()
    return D(r["penalty"]) == D("45.90") and D(r["refund_amount"]) == D("413.10")


def g4():
    c, clock, _ = entorno(); o = crear(c, 6); clock.advance(hours=20)
    c.post(f"/orders/{o['id']}/pay", json={"amount": o["total"]}); clock.advance(hours=10)
    return D(c.post(f"/orders/{o['id']}/cancel").json()["penalty"]) == D("0.00")


def g5():
    c, clock, _ = entorno(); o = crear(c, 6, email="x@vip.com"); oid = pagar(c, o); clock.advance(hours=30)
    r = c.post(f"/orders/{oid}/cancel").json()
    return D(o["total"]) == D("436.05") and D(r["penalty"]) == D("43.61") and D(r["refund_amount"]) == D("392.44")


GIRO = [
    ("G1", "Pagado y cancelado a las 23 h: se devuelve todo y la retencion es 0.00", g1),
    ("G2", "Cancelado exactamente a las 24 h del pago: sigue siendo gratis", g2),
    ("G3", "Pasadas 24 h: retiene 10% (45.90) y devuelve el resto (413.10)", g3),
    ("G4", "La ventana de 24 h cuenta desde el pago, no desde la creacion", g4),
    ("G5", "El 10% se calcula sobre el total con descuentos y a centavos", g5),
]


def verificar_base():
    from sqlalchemy import text
    try:
        c = Container()
        with c.engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM orders LIMIT 1"))
    except Exception as e:
        print("No pude usar la base de datos de esta carpeta:", type(e).__name__)
        print("Revise que Postgres este arriba (docker compose up -d) y que haya corrido: python setup_db.py")
        sys.exit(2)


def main():
    verificar_base()
    giro = "--giro" in sys.argv
    pruebas = GIRO if giro else PRE
    print("Comprobacion", "DESPUES del giro" if giro else "ANTES del giro", "\n")
    ok = 0
    for clave, texto, fn in pruebas:
        try:
            paso = bool(fn())
        except Exception as e:  # una excepcion cuenta como FAIL
            paso = False
            texto += f" (error: {type(e).__name__})"
        ok += paso
        print(f"{'PASS' if paso else 'FAIL'}  {clave}  {texto}")
    print(f"\nResultado: {ok} de {len(pruebas)}")


if __name__ == "__main__":
    main()
