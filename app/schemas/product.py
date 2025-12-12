from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime


class CategoryBase(BaseModel):
    name: str
    sort_order: Optional[int] = 0


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None


class CategoryResponse(CategoryBase):
    id: int
    
    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    sku: str
    name: str
    category_id: int
    price: Decimal
    cost: Optional[Decimal] = 0
    taxable: bool = True
    is_active: bool = True
    on_hand: Optional[Decimal] = 0


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[Decimal] = None
    cost: Optional[Decimal] = None
    taxable: Optional[bool] = None
    is_active: Optional[bool] = None
    on_hand: Optional[Decimal] = None


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

