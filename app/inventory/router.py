from fastapi import APIRouter, Request

from app.inventory.schemas import ProductOut
from app.unit_of_work import unit_of_work

router = APIRouter(tags=["inventory"])


@router.get("/products", response_model=list[ProductOut])
def list_products(request: Request):
    with unit_of_work(request) as s:
        return s.inventory_repo.list_products()


@router.get("/inventory/{sku}")
def stock(sku: str, request: Request):
    with unit_of_work(request) as s:
        return s.inventory.stock_of(sku)
