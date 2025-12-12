from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class ItemType(str, enum.Enum):
    PRODUCT = "product"
    INGREDIENT = "ingredient"


class InventoryAdjustment(Base):
    __tablename__ = "inventory_adjustments"
    
    id = Column(Integer, primary_key=True, index=True)
    item_type = Column(SQLEnum(ItemType), nullable=False)
    item_id = Column(Integer, nullable=False)  # product_id or ingredient_id
    qty_change = Column(Numeric(10, 2), nullable=False)  # positive for increase, negative for decrease
    reason = Column(String(500), nullable=False)
    datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

