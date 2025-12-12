from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class ShiftStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class CashEventType(str, enum.Enum):
    CASH_IN = "cash_in"
    CASH_OUT = "cash_out"
    DROP = "drop"


class Shift(Base):
    __tablename__ = "shifts"
    
    id = Column(Integer, primary_key=True, index=True)
    cashier_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    opened_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    opening_float = Column(Numeric(10, 2), nullable=False)
    expected_cash = Column(Numeric(10, 2), default=0)
    counted_cash = Column(Numeric(10, 2), nullable=True)
    over_short = Column(Numeric(10, 2), default=0)
    status = Column(SQLEnum(ShiftStatus), default=ShiftStatus.OPEN)
    
    cashier = relationship("User", back_populates="shifts")
    sales = relationship("Sale", back_populates="shift")
    cash_events = relationship("CashEvent", back_populates="shift", cascade="all, delete-orphan")


class CashEvent(Base):
    __tablename__ = "cash_events"
    
    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    event_type = Column(SQLEnum(CashEventType), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    reason = Column(String(500))
    datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    shift = relationship("Shift", back_populates="cash_events")

