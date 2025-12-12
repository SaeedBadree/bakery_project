import pytest
from decimal import Decimal


def test_recipe_cost_calculation():
    """Test recipe cost calculation"""
    # Mock recipe lines
    recipe_lines = [
        {"ingredient": "Flour", "qty": Decimal('500'), "cost_per_unit": Decimal('0.002')},  # $1.00
        {"ingredient": "Sugar", "qty": Decimal('200'), "cost_per_unit": Decimal('0.003')},  # $0.60
        {"ingredient": "Eggs", "qty": Decimal('4'), "cost_per_unit": Decimal('0.25')},  # $1.00
    ]
    
    total_cost = sum(line["qty"] * line["cost_per_unit"] for line in recipe_lines)
    assert total_cost == Decimal('2.60')


def test_cost_per_unit():
    """Test cost per unit calculation"""
    total_cost = Decimal('2.60')
    yield_qty = Decimal('12')  # Makes 12 units
    
    cost_per_unit = total_cost / yield_qty
    assert cost_per_unit == Decimal('0.2167')  # Rounded


def test_batch_cost_scaling():
    """Test batch cost scales with quantity"""
    base_cost = Decimal('2.60')
    base_yield = Decimal('12')
    
    # Double the batch
    multiplier = Decimal('2')
    scaled_cost = base_cost * multiplier
    scaled_yield = base_yield * multiplier
    
    cost_per_unit = scaled_cost / scaled_yield
    assert cost_per_unit == base_cost / base_yield  # Should be same

