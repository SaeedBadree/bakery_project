from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Enum as SQLEnum, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class AREntryType(str, enum.Enum):
    INVOICE = "invoice"
    PAYMENT = "payment"


class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(100))
    phone = Column(String(50))
    address = Column(String(500))
    credit_limit = Column(Numeric(10, 2), default=0)
    balance = Column(Numeric(10, 2), default=0)
    
    sales = relationship("Sale", back_populates="customer")
    ar_entries = relationship("AREntry", back_populates="customer")


class AREntry(Base):
    __tablename__ = "ar_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    entry_type = Column(SQLEnum(AREntryType), nullable=False)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)  # For invoice entries
    amount = Column(Numeric(10, 2), nullable=False)
    date = Column(Date, nullable=False, server_default=func.current_date())
    due_date = Column(Date)
    balance = Column(Numeric(10, 2), nullable=False)  # Remaining balance
    notes = Column(String(500))
    
    customer = relationship("Customer", back_populates="ar_entries")

