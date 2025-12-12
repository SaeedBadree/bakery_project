from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date, timedelta
from app.models.ar import AREntry, AREntryType


def calculate_aging(db: Session, customer_id: int) -> dict:
    """Calculate AR aging buckets"""
    entries = db.query(AREntry).filter(
        AREntry.customer_id == customer_id,
        AREntry.entry_type == AREntryType.INVOICE,
        AREntry.balance > 0
    ).all()
    
    today = date.today()
    aging = {
        "0-30": Decimal('0'),
        "31-60": Decimal('0'),
        "61-90": Decimal('0'),
        "90+": Decimal('0')
    }
    
    for entry in entries:
        days_old = (today - entry.date).days
        
        if days_old <= 30:
            aging["0-30"] += entry.balance
        elif days_old <= 60:
            aging["31-60"] += entry.balance
        elif days_old <= 90:
            aging["61-90"] += entry.balance
        else:
            aging["90+"] += entry.balance
    
    return aging

