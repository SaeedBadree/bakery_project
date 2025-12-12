from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class POStatus(str, enum.Enum):
    DRAFT = "draft"
    ORDERED = "ordered"
    PARTIAL = "partial"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class Vendor(Base):
    __tablename__ = "vendors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    contact = Column(String(100))
    email = Column(String(100))
    phone = Column(String(50))
    address = Column(String(500))
    
    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    po_number = Column(String(50), unique=True, nullable=False, index=True)
    date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(SQLEnum(POStatus), default=POStatus.DRAFT)
    total = Column(Numeric(10, 2), default=0)
    
    vendor = relationship("Vendor", back_populates="purchase_orders")
    po_lines = relationship("POLine", back_populates="purchase_order", cascade="all, delete-orphan")


class POLine(Base):
    __tablename__ = "po_lines"
    
    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    qty_ordered = Column(Numeric(10, 2), nullable=False)
    unit_cost = Column(Numeric(10, 4), nullable=False)
    qty_received = Column(Numeric(10, 2), default=0)
    
    purchase_order = relationship("PurchaseOrder", back_populates="po_lines")
    received_lines = relationship("ReceivedLine", back_populates="po_line", cascade="all, delete-orphan")


class ReceivedLine(Base):
    __tablename__ = "received_lines"
    
    id = Column(Integer, primary_key=True, index=True)
    po_line_id = Column(Integer, ForeignKey("po_lines.id"), nullable=False)
    qty_received = Column(Numeric(10, 2), nullable=False)
    actual_cost = Column(Numeric(10, 4), nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    po_line = relationship("POLine", back_populates="received_lines")

