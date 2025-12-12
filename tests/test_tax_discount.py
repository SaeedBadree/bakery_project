import pytest
from decimal import Decimal
from app.services.pos import calculate_tax


def test_tax_calculation():
    """Test tax calculation"""
    subtotal = Decimal('100.00')
    taxable_amount = Decimal('100.00')
    tax_rate = Decimal('0.10')
    
    tax = calculate_tax(subtotal, taxable_amount, tax_rate)
    assert tax == Decimal('10.00')


def test_tax_on_non_taxable():
    """Test tax calculation with non-taxable items"""
    subtotal = Decimal('100.00')
    taxable_amount = Decimal('50.00')  # Only half is taxable
    tax_rate = Decimal('0.10')
    
    tax = calculate_tax(subtotal, taxable_amount, tax_rate)
    assert tax == Decimal('5.00')


def test_discount_before_tax():
    """Test discount applied before tax"""
    subtotal = Decimal('100.00')
    discount = Decimal('10.00')
    subtotal_after_discount = subtotal - discount
    taxable_amount = subtotal_after_discount
    tax_rate = Decimal('0.10')
    
    tax = calculate_tax(subtotal_after_discount, taxable_amount, tax_rate)
    assert tax == Decimal('9.00')  # 10% of $90
    total = subtotal_after_discount + tax
    assert total == Decimal('99.00')

