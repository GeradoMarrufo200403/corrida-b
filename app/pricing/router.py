from fastapi import APIRouter, Request

from app.pricing.schemas import QuoteIn, QuoteOut
from app.unit_of_work import unit_of_work

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.post("/quote", response_model=QuoteOut)
def quote(payload: QuoteIn, request: Request):
    with unit_of_work(request) as s:
        _, breakdown = s.pricing.quote(payload.items, payload.customer_email)
    return QuoteOut(**breakdown.__dict__)
