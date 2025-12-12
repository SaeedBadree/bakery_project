from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from app.models.sale import TenderType, SaleStatus


class SaleLineBase(BaseModel):
    product_id: int
    qty: Decimal
    unit_price: Decimal
    line_discount: Optional[Decimal] = 0


class SaleLineCreate(SaleLineBase):
    pass


class SaleLineResponse(SaleLineBase):
    id: int
    line_total: Decimal
    
    class Config:
        from_attributes = True


class SaleBase(BaseModel):
    customer_id: Optional[int] = None
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    tender_type: TenderType
    notes: Optional[str] = None


class SaleCreate(BaseModel):
    customer_id: Optional[int] = None
    lines: List[SaleLineCreate]
    sale_discount: Optional[Decimal] = 0
    tender_type: TenderType
    notes: Optional[str] = None


class SaleResponse(SaleBase):
    id: int
    sale_number: str
    datetime: datetime
    cashier_id: int
    shift_id: Optional[int]
    status: SaleStatus
    sale_lines: List[SaleLineResponse] = []
    
    class Config:
        from_attributes = True


class ReturnCreate(BaseModel):
    original_sale_id: int
    return_lines: List[dict]  # {line_id, qty_returned}
    reason: Optional[str] = None


class ReturnResponse(BaseModel):
    id: int
    original_sale_id: int
    datetime: datetime
    total_refund: Decimal
    reason: Optional[str] = None
    
    class Config:
        from_attributes = True

