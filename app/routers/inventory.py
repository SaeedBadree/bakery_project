from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.auth import require_auth, require_role
from app.models.product import Product
from app.models.inventory import InventoryAdjustment, ItemType
from app.models.recipe import Ingredient
from decimal import Decimal

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/inventory", response_class=HTMLResponse)
async def inventory_dashboard(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Inventory dashboard"""
    products = db.query(Product).filter(Product.is_active == True).order_by(Product.name).all()
    ingredients = db.query(Ingredient).order_by(Ingredient.name).all()
    
    # Low stock alerts
    low_stock_products = [p for p in products if p.on_hand < 10]  # Threshold
    low_stock_ingredients = [i for i in ingredients if i.on_hand < i.reorder_point]
    
    return templates.TemplateResponse(
        "inventory/dashboard.html",
        {
            "request": request,
            "user": user_data["user"],
            "products": products,
            "ingredients": ingredients,
            "low_stock_products": low_stock_products,
            "low_stock_ingredients": low_stock_ingredients
        }
    )


@router.post("/inventory/adjust", response_class=HTMLResponse)
async def adjust_inventory(
    request: Request,
    item_type: str = Form(...),
    item_id: int = Form(...),
    qty_change: float = Form(...),
    reason: str = Form(...),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Adjust inventory"""
    if item_type == "product":
        item = db.query(Product).filter(Product.id == item_id).first()
        if not item:
            return RedirectResponse(url="/inventory", status_code=302)
        item.on_hand += Decimal(str(qty_change))
    elif item_type == "ingredient":
        item = db.query(Ingredient).filter(Ingredient.id == item_id).first()
        if not item:
            return RedirectResponse(url="/inventory", status_code=302)
        item.on_hand += Decimal(str(qty_change))
    else:
        return RedirectResponse(url="/inventory", status_code=302)
    
    adjustment = InventoryAdjustment(
        item_type=ItemType(item_type),
        item_id=item_id,
        qty_change=Decimal(str(qty_change)),
        reason=reason,
        user_id=user_data["user"].id
    )
    db.add(adjustment)
    db.commit()
    
    return RedirectResponse(url="/inventory", status_code=302)


@router.get("/inventory/stocktake", response_class=HTMLResponse)
async def stocktake_page(
    request: Request,
    user_data: dict = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Stock take page"""
    products = db.query(Product).filter(Product.is_active == True).order_by(Product.name).all()
    return templates.TemplateResponse(
        "inventory/stocktake.html",
        {"request": request, "user": user_data["user"], "products": products}
    )


@router.post("/inventory/stocktake", response_class=HTMLResponse)
async def process_stocktake(
    request: Request,
    user_data: dict = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Process stock take"""
    # Get form data (would need to parse multiple items)
    # Simplified - in real app would handle multiple items
    return RedirectResponse(url="/inventory", status_code=302)

