from pydantic import BaseModel


class LineIn(BaseModel):
    sku: str
    quantity: int
