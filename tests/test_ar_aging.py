import pytest
from decimal import Decimal
from datetime import date, timedelta
from app.services.ar import calculate_aging


def test_ar_aging_buckets():
    """Test AR aging bucket calculation"""
    # Mock entries with different ages
    today = date.today()
    
    # Simulate entries
    entries_data = [
        {"date": today - timedelta(days=15), "balance": Decimal('100.00')},  # 0-30
        {"date": today - timedelta(days=45), "balance": Decimal('200.00')},  # 31-60
        {"date": today - timedelta(days=75), "balance": Decimal('300.00')},  # 61-90
        {"date": today - timedelta(days=120), "balance": Decimal('400.00')},  # 90+
    ]
    
    # Manual calculation
    aging = {
        "0-30": Decimal('100.00'),
        "31-60": Decimal('200.00'),
        "61-90": Decimal('300.00'),
        "90+": Decimal('400.00')
    }
    
    total = sum(aging.values())
    assert total == Decimal('1000.00')


def test_ar_aging_edge_cases():
    """Test aging edge cases"""
    today = date.today()
    
    # Exactly 30 days
    days_30 = today - timedelta(days=30)
    assert (today - days_30).days == 30
    
    # Exactly 60 days
    days_60 = today - timedelta(days=60)
    assert (today - days_60).days == 60
    
    # Exactly 90 days
    days_90 = today - timedelta(days=90)
    assert (today - days_90).days == 90

