"""
Add custom_tax_rate column to products table
Run this script to update the database
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal, engine
from sqlalchemy import text

def add_custom_tax_rate_column():
    """Add custom_tax_rate column to products table"""
    db = SessionLocal()
    try:
        # Check if column already exists
        result = db.execute(text("PRAGMA table_info(products)"))
        columns = [row[1] for row in result]
        
        if 'custom_tax_rate' not in columns:
            print("Adding custom_tax_rate column to products table...")
            db.execute(text("ALTER TABLE products ADD COLUMN custom_tax_rate NUMERIC(5, 4)"))
            db.commit()
            print("✅ Column added successfully!")
        else:
            print("ℹ️  custom_tax_rate column already exists")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_custom_tax_rate_column()

