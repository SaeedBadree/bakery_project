from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class TenderType(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    ON_ACCOUNT = "on_account"


class SaleStatus(str, enum.Enum):
    COMPLETED = "completed"
    VOIDED = "voided"
    RETURNED = "returned"


class Sale(Base):
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True)
    sale_number = Column(String(50), unique=True, nullable=False, index=True)
    datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    cashier_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0)
    discount_amount = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), nullable=False)
    tender_type = Column(SQLEnum(TenderType), nullable=False)
    status = Column(SQLEnum(SaleStatus), default=SaleStatus.COMPLETED)
    notes = Column(String(500))
    
    cashier = relationship("User", back_populates="sales")
    shift = relationship("Shift", back_populates="sales")
    customer = relationship("Customer", back_populates="sales")
    sale_lines = relationship("SaleLine", back_populates="sale", cascade="all, delete-orphan")
    returns = relationship("Return", back_populates="original_sale")


class SaleLine(Base):
    __tablename__ = "sale_lines"
    
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    qty = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    line_discount = Column(Numeric(10, 2), default=0)
    line_total = Column(Numeric(10, 2), nullable=False)
    
    sale = relationship("Sale", back_populates="sale_lines")
    product = relationship("Product", back_populates="sale_lines")
    return_lines = relationship("ReturnLine", back_populates="original_line")


class Return(Base):
    __tablename__ = "returns"
    
    id = Column(Integer, primary_key=True, index=True)
    original_sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String(500))
    total_refund = Column(Numeric(10, 2), nullable=False)
    
    original_sale = relationship("Sale", back_populates="returns")
    return_lines = relationship("ReturnLine", back_populates="return_obj", cascade="all, delete-orphan")


class ReturnLine(Base):
    __tablename__ = "return_lines"
    
    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(Integer, ForeignKey("returns.id"), nullable=False)
    original_line_id = Column(Integer, ForeignKey("sale_lines.id"), nullable=False)
    qty_returned = Column(Numeric(10, 2), nullable=False)
    refund_amount = Column(Numeric(10, 2), nullable=False)
    
    return_obj = relationship("Return", back_populates="return_lines")
    original_line = relationship("SaleLine", back_populates="return_lines")

