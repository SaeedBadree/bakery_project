from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.auth import require_auth, require_role
from app.models.recipe import Ingredient, Recipe, RecipeLine, Batch, BatchConsumption
from app.models.product import Product
from app.services.production import calculate_recipe_cost, create_batch
from decimal import Decimal
from datetime import datetime, date

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/production", response_class=HTMLResponse)
async def production_dashboard(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Production dashboard"""
    recipes = db.query(Recipe).order_by(Recipe.name).all()
    batches_today = db.query(Batch).filter(
        Batch.produced_at >= datetime.combine(date.today(), datetime.min.time())
    ).order_by(Batch.produced_at.desc()).all()
    
    return templates.TemplateResponse(
        "production/dashboard.html",
        {
            "request": request,
            "recipes": recipes,
            "batches_today": batches_today
        }
    )


@router.get("/production/ingredients", response_class=HTMLResponse)
async def list_ingredients(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """List ingredients"""
    ingredients = db.query(Ingredient).order_by(Ingredient.name).all()
    return templates.TemplateResponse(
        "production/ingredients.html",
        {"request": request, "ingredients": ingredients}
    )


@router.post("/production/ingredients", response_class=HTMLResponse)
async def create_ingredient(
    request: Request,
    name: str = Form(...),
    unit: str = Form(...),
    cost_per_unit: float = Form(...),
    on_hand: float = Form(0),
    reorder_point: float = Form(0),
    user_data: dict = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Create ingredient"""
    ingredient = Ingredient(
        name=name,
        unit=unit,
        cost_per_unit=Decimal(str(cost_per_unit)),
        on_hand=Decimal(str(on_hand)),
        reorder_point=Decimal(str(reorder_point))
    )
    db.add(ingredient)
    db.commit()
    return RedirectResponse(url="/production/ingredients", status_code=302)


@router.get("/production/recipes", response_class=HTMLResponse)
async def list_recipes(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """List recipes"""
    recipes = db.query(Recipe).order_by(Recipe.name).all()
    for recipe in recipes:
        recipe.total_cost = calculate_recipe_cost(db, recipe.id)
    
    return templates.TemplateResponse(
        "production/recipes.html",
        {"request": request, "recipes": recipes}
    )


@router.get("/production/recipes/{recipe_id}", response_class=HTMLResponse)
async def view_recipe(
    request: Request,
    recipe_id: int,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """View recipe details"""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        return RedirectResponse(url="/production/recipes", status_code=302)
    
    recipe_lines = db.query(RecipeLine).filter(RecipeLine.recipe_id == recipe_id).all()
    total_cost = calculate_recipe_cost(db, recipe_id)
    cost_per_unit = total_cost / recipe.yield_qty if recipe.yield_qty > 0 else Decimal('0')
    
    return templates.TemplateResponse(
        "production/recipe_detail.html",
        {
            "request": request,
            "recipe": recipe,
            "recipe_lines": recipe_lines,
            "total_cost": total_cost,
            "cost_per_unit": cost_per_unit
        }
    )


@router.get("/production/recipes/new", response_class=HTMLResponse)
async def new_recipe(
    request: Request,
    user_data: dict = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """New recipe form"""
    ingredients = db.query(Ingredient).order_by(Ingredient.name).all()
    return templates.TemplateResponse(
        "production/recipe_form.html",
        {"request": request, "ingredients": ingredients}
    )


@router.post("/production/recipes", response_class=HTMLResponse)
async def create_recipe(
    request: Request,
    name: str = Form(...),
    yield_qty: float = Form(...),
    yield_unit: str = Form(...),
    notes: str = Form(""),
    user_data: dict = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Create recipe"""
    recipe = Recipe(
        name=name,
        yield_qty=Decimal(str(yield_qty)),
        yield_unit=yield_unit,
        notes=notes
    )
    db.add(recipe)
    db.commit()
    return RedirectResponse(url=f"/production/recipes/{recipe.id}", status_code=302)


@router.post("/production/batches", response_class=HTMLResponse)
async def create_batch_production(
    request: Request,
    recipe_id: int = Form(...),
    qty_produced: float = Form(...),
    wastage: float = Form(0),
    notes: str = Form(""),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Create batch production"""
    try:
        batch = create_batch(db, recipe_id, Decimal(str(qty_produced)), user_data["user"].id, Decimal(str(wastage)), notes)
        return RedirectResponse(url="/production", status_code=302)
    except Exception as e:
        return templates.TemplateResponse(
            "production/dashboard.html",
            {"request": request, "error": str(e)}
        )

