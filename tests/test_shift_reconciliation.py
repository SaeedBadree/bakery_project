import pytest
from decimal import Decimal


def test_shift_reconciliation():
    """Test shift cash reconciliation"""
    opening_float = Decimal('100.00')
    cash_sales = Decimal('250.00')
    cash_in = Decimal('50.00')   # Paid-in
    cash_out = Decimal('30.00')  # Paid-out
    
    expected_cash = opening_float + cash_sales + cash_in - cash_out
    assert expected_cash == Decimal('370.00')


def test_over_short_calculation():
    """Test over/short calculation"""
    expected_cash = Decimal('370.00')
    counted_cash = Decimal('365.00')
    
    over_short = counted_cash - expected_cash
    assert over_short == Decimal('-5.00')  # Short $5


def test_over_cash():
    """Test over cash scenario"""
    expected_cash = Decimal('370.00')
    counted_cash = Decimal('375.00')
    
    over_short = counted_cash - expected_cash
    assert over_short == Decimal('5.00')  # Over $5


def test_cash_events():
    """Test cash event calculations"""
    opening_float = Decimal('100.00')
    cash_sales = Decimal('200.00')
    
    # Multiple cash events
    events = [
        {"type": "cash_in", "amount": Decimal('20.00')},
        {"type": "cash_out", "amount": Decimal('10.00')},
        {"type": "drop", "amount": Decimal('50.00')},
    ]
    
    cash_in_total = sum(e["amount"] for e in events if e["type"] == "cash_in")
    cash_out_total = sum(e["amount"] for e in events if e["type"] in ["cash_out", "drop"])
    
    expected = opening_float + cash_sales + cash_in_total - cash_out_total
    assert expected == Decimal('260.00')

