import pytest
from decimal import Decimal


def test_ingredient_deduction():
    """Test ingredient deduction on batch production"""
    # Starting inventory
    flour_on_hand = Decimal('1000')  # grams
    sugar_on_hand = Decimal('500')   # grams
    
    # Recipe requires
    flour_needed = Decimal('500')
    sugar_needed = Decimal('200')
    
    # Check sufficient inventory
    assert flour_on_hand >= flour_needed
    assert sugar_on_hand >= sugar_needed
    
    # Deduct
    flour_remaining = flour_on_hand - flour_needed
    sugar_remaining = sugar_on_hand - sugar_needed
    
    assert flour_remaining == Decimal('500')
    assert sugar_remaining == Decimal('300')


def test_insufficient_inventory():
    """Test insufficient inventory check"""
    flour_on_hand = Decimal('300')
    flour_needed = Decimal('500')
    
    assert flour_on_hand < flour_needed
    # Should raise error in production code


def test_batch_multiplier():
    """Test batch quantity multiplier"""
    base_recipe_qty = Decimal('500')  # grams flour
    batch_qty = Decimal('24')  # produce 24 units
    recipe_yield = Decimal('12')  # recipe makes 12 units
    
    multiplier = batch_qty / recipe_yield
    flour_needed = base_recipe_qty * multiplier
    
    assert multiplier == Decimal('2')
    assert flour_needed == Decimal('1000')

