from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.auth import require_auth, require_role
from app.models.product import Product, Category
from app.schemas.product import ProductCreate, ProductUpdate, CategoryCreate

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/products", response_class=HTMLResponse)
async def list_products(
    request: Request,
    category_id: int = Query(None),
    search: str = Query(None),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """List all products"""
    query = db.query(Product).filter(Product.is_active == True)
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if search:
        query = query.filter(
            Product.name.ilike(f"%{search}%") |
            Product.sku.ilike(f"%{search}%")
        )
    
    products = query.order_by(Product.name).all()
    categories = db.query(Category).order_by(Category.sort_order, Category.name).all()
    
    return templates.TemplateResponse(
        "products/list.html",
        {
            "request": request,
            "user": user_data["user"],
            "products": products,
            "categories": categories,
            "selected_category": category_id,
            "search": search
        }
    )


@router.get("/products/new", response_class=HTMLResponse)
async def new_product(
    request: Request,
    user_data: dict = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Show new product form"""
    categories = db.query(Category).order_by(Category.sort_order, Category.name).all()
    return templates.TemplateResponse(
        "products/form.html",
        {"request": request, "user": user_data["user"], "categories": categories, "product": None}
    )


@router.post("/products", response_class=HTMLResponse)
async def create_product(
    request: Request,
    sku: str = Form(...),
    name: str = Form(...),
    category_id: int = Form(...),
    price: float = Form(...),
    cost: float = Form(0),
    taxable: bool = Form(True),
    custom_tax_rate: float = Form(None),
    on_hand: float = Form(0),
    user_data: dict = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Create a new product"""
    from decimal import Decimal
    
    # Check if SKU exists
    if db.query(Product).filter(Product.sku == sku).first():
        categories = db.query(Category).order_by(Category.sort_order, Category.name).all()
        return templates.TemplateResponse(
            "products/form.html",
            {
                "request": request,
                "user": user_data["user"],
                "categories": categories,
                "product": None,
                "error": "SKU already exists"
            }
        )
    
    # Convert custom tax rate from percentage to decimal
    custom_tax_decimal = None
    if custom_tax_rate is not None and custom_tax_rate > 0:
        custom_tax_decimal = Decimal(str(custom_tax_rate / 100))
    
    product = Product(
        sku=sku,
        name=name,
        category_id=category_id,
        price=Decimal(str(price)),
        cost=Decimal(str(cost)),
        taxable=taxable,
        custom_tax_rate=custom_tax_decimal,
        on_hand=Decimal(str(on_hand)),
        is_active=True
    )
    db.add(product)
    db.commit()
    
    return RedirectResponse(url="/products", status_code=302)


@router.get("/products/{product_id}/edit", response_class=HTMLResponse)
async def edit_product(
    request: Request,
    product_id: int,
    user_data: dict = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Show edit product form"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return RedirectResponse(url="/products", status_code=302)
    
    categories = db.query(Category).order_by(Category.sort_order, Category.name).all()
    return templates.TemplateResponse(
        "products/form.html",
        {"request": request, "user": user_data["user"], "categories": categories, "product": product}
    )


@router.post("/products/{product_id}", response_class=HTMLResponse)
async def update_product(
    request: Request,
    product_id: int,
    sku: str = Form(...),
    name: str = Form(...),
    category_id: int = Form(...),
    price: float = Form(...),
    cost: float = Form(0),
    taxable: bool = Form(True),
    custom_tax_rate: float = Form(None),
    is_active: bool = Form(True),
    on_hand: float = Form(0),
    user_data: dict = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Update a product"""
    from decimal import Decimal
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return RedirectResponse(url="/products", status_code=302)
    
    # Check SKU uniqueness if changed
    if product.sku != sku:
        if db.query(Product).filter(Product.sku == sku).first():
            categories = db.query(Category).order_by(Category.sort_order, Category.name).all()
            return templates.TemplateResponse(
                "products/form.html",
                {
                    "request": request,
                    "user": user_data["user"],
                    "categories": categories,
                    "product": product,
                    "error": "SKU already exists"
                }
            )
    
    # Convert custom tax rate from percentage to decimal
    custom_tax_decimal = None
    if custom_tax_rate is not None and custom_tax_rate > 0:
        custom_tax_decimal = Decimal(str(custom_tax_rate / 100))
    
    product.sku = sku
    product.name = name
    product.category_id = category_id
    product.price = Decimal(str(price))
    product.cost = Decimal(str(cost))
    product.taxable = taxable
    product.custom_tax_rate = custom_tax_decimal
    product.is_active = is_active
    product.on_hand = Decimal(str(on_hand))
    
    db.commit()
    return RedirectResponse(url="/products", status_code=302)


@router.get("/categories", response_class=HTMLResponse)
async def list_categories(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """List all categories"""
    categories = db.query(Category).order_by(Category.sort_order, Category.name).all()
    return templates.TemplateResponse(
        "products/categories.html",
        {"request": request, "user": user_data["user"], "categories": categories}
    )


@router.post("/categories", response_class=HTMLResponse)
async def create_category(
    request: Request,
    name: str = Form(...),
    sort_order: int = Form(0),
    user_data: dict = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Create a new category"""
    if db.query(Category).filter(Category.name == name).first():
        categories = db.query(Category).order_by(Category.sort_order, Category.name).all()
        return templates.TemplateResponse(
            "products/categories.html",
            {
                "request": request,
                "user": user_data["user"],
                "categories": categories,
                "error": "Category already exists"
            }
        )
    
    category = Category(name=name, sort_order=sort_order)
    db.add(category)
    db.commit()
    
    return RedirectResponse(url="/categories", status_code=302)

