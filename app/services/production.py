from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from decimal import Decimal
from app.models.recipe import Recipe, RecipeLine, Batch, BatchConsumption, Ingredient
from app.models.product import Product
from app.models.inventory import InventoryAdjustment, ItemType


def calculate_recipe_cost(db: Session, recipe_id: int) -> Decimal:
    """Calculate total cost of a recipe"""
    recipe_lines = db.query(RecipeLine).filter(RecipeLine.recipe_id == recipe_id).all()
    total_cost = Decimal('0')
    
    for line in recipe_lines:
        ingredient = db.query(Ingredient).filter(Ingredient.id == line.ingredient_id).first()
        if ingredient:
            total_cost += line.qty * ingredient.cost_per_unit
    
    return total_cost


def create_batch(
    db: Session,
    recipe_id: int,
    qty_produced: Decimal,
    user_id: int,
    wastage: Decimal = Decimal('0'),
    notes: str = ""
) -> Batch:
    """Create a batch production record"""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    # Calculate multiplier
    multiplier = qty_produced / recipe.yield_qty
    
    # Create batch
    batch = Batch(
        recipe_id=recipe_id,
        qty_produced=qty_produced,
        wastage=wastage,
        notes=notes,
        user_id=user_id
    )
    db.add(batch)
    db.flush()
    
    # Deduct ingredients
    recipe_lines = db.query(RecipeLine).filter(RecipeLine.recipe_id == recipe_id).all()
    for line in recipe_lines:
        ingredient = db.query(Ingredient).filter(Ingredient.id == line.ingredient_id).first()
        if not ingredient:
            continue
        
        qty_used = line.qty * multiplier
        
        # Check if enough inventory
        if ingredient.on_hand < qty_used:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient {ingredient.name}. Need {qty_used}, have {ingredient.on_hand}"
            )
        
        # Deduct ingredient
        ingredient.on_hand -= qty_used
        
        # Record consumption
        consumption = BatchConsumption(
            batch_id=batch.id,
            ingredient_id=ingredient.id,
            qty_used=qty_used
        )
        db.add(consumption)
        
        # Record adjustment
        adjustment = InventoryAdjustment(
            item_type=ItemType.INGREDIENT,
            item_id=ingredient.id,
            qty_change=-qty_used,
            reason=f"Batch {batch.id} - {recipe.name}",
            user_id=user_id
        )
        db.add(adjustment)
    
    # Add finished goods to inventory (assuming recipe name matches product name)
    # In a real system, you'd have a recipe->product mapping
    product = db.query(Product).filter(Product.name.ilike(f"%{recipe.name}%")).first()
    if product:
        product.on_hand += qty_produced - wastage
        
        adjustment = InventoryAdjustment(
            item_type=ItemType.PRODUCT,
            item_id=product.id,
            qty_change=qty_produced - wastage,
            reason=f"Batch {batch.id} - {recipe.name}",
            user_id=user_id
        )
        db.add(adjustment)
    
    db.commit()
    db.refresh(batch)
    return batch

