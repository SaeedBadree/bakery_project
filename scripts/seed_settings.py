"""
Seed script to initialize default system settings
Run this after starting the server for the first time
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal, engine, Base
from app.models.settings import SystemSettings

def seed_settings():
    """Initialize default system settings"""
    Base.metadata.create_all(bind=engine, tables=[SystemSettings.__table__])
    
    db = SessionLocal()
    try:
        # Check if tax_rate already exists
        existing = db.query(SystemSettings).filter(SystemSettings.setting_key == "tax_rate").first()
        if not existing:
            tax_rate_setting = SystemSettings(
                setting_key="tax_rate",
                setting_value="0.10",
                description="Default sales tax rate (10%)"
            )
            db.add(tax_rate_setting)
            db.commit()
            print("✅ Default tax rate (10%) has been set!")
        else:
            print(f"ℹ️  Tax rate already exists: {float(existing.setting_value) * 100}%")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_settings()

