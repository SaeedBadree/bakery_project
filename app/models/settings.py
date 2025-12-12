from sqlalchemy import Column, Integer, String, Numeric
from app.database import Base


class Setting(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(500), nullable=False)
    value_type = Column(String(20), default="string")  # string, number, boolean

