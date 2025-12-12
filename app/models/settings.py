from sqlalchemy import Column, Integer, String, Float
from app.database import Base

class SystemSettings(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(String(500), nullable=False)
    description = Column(String(500), nullable=True)
    
    def __repr__(self):
        return f"<SystemSettings {self.setting_key}={self.setting_value}>"
