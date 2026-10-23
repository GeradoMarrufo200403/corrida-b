from fastapi import APIRouter, Request

from app.orders.schemas import ItemsUpdate, OrderCreate, OrderOut, PaymentIn
from app.unit_of_work import unit_of_work

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreate, request: Request):
    with unit_of_work(request) as s:
        return s.orders.create_order(payload.customer_email, payload.items)


@router.get("", response_model=list[OrderOut])
def list_orders(request: Request):
    with unit_of_work(request) as s:
        return s.orders.list_orders()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, request: Request):
    with unit_of_work(request) as s:
        return s.orders.get_order(order_id)


@router.put("/{order_id}/items", response_model=OrderOut)
def update_items(order_id: int, payload: ItemsUpdate, request: Request):
    with unit_of_work(request) as s:
        return s.orders.update_items(order_id, payload.items)


@router.post("/{order_id}/pay", response_model=OrderOut)
def pay_order(order_id: int, payload: PaymentIn, request: Request):
    with unit_of_work(request) as s:
        return s.orders.pay(order_id, payload.amount)


@router.post("/{order_id}/ship", response_model=OrderOut)
def ship_order(order_id: int, request: Request):
    with unit_of_work(request) as s:
        return s.orders.ship(order_id)


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, request: Request):
    with unit_of_work(request) as s:
        return s.orders.cancel(order_id)
