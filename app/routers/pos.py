from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.auth import require_auth
from app.models.product import Product, Category
from app.models.sale import TenderType
from app.models.shift import Shift, ShiftStatus
from app.models.ar import Customer
from app.services.pos import create_sale, get_sale, void_sale, create_return
from app.schemas.sale import SaleCreate, SaleLineCreate
from decimal import Decimal
import json

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/pos/checkout", response_class=HTMLResponse)
async def checkout_page(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """POS checkout page"""
    categories = db.query(Category).order_by(Category.sort_order, Category.name).all()
    products = db.query(Product).filter(Product.is_active == True).order_by(Product.name).all()
    
    return templates.TemplateResponse(
        "pos/checkout.html",
        {
            "request": request,
            "user": user_data["user"],
            "categories": categories,
            "products": products
        }
    )


@router.post("/pos/add-to-cart", response_class=HTMLResponse)
async def add_to_cart(
    request: Request,
    product_id: int = Form(...),
    qty: float = Form(1),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Add product to cart (HTMX endpoint)"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or not product.is_active:
        return HTMLResponse("<div class='alert alert-error'>Product not found</div>")
    
    # Get cart from session (stored in cookie/session)
    cart = request.cookies.get("cart", "[]")
    try:
        cart_items = json.loads(cart)
    except:
        cart_items = []
    
    # Check if product already in cart
    found = False
    for item in cart_items:
        if item["product_id"] == product_id:
            item["qty"] += qty
            found = True
            break
    
    if not found:
        cart_items.append({
            "product_id": product_id,
            "product_name": product.name,
            "product_sku": product.sku,
            "qty": qty,
            "unit_price": float(product.price),
            "taxable": product.taxable,
            "line_discount": 0
        })
    
    # Render cart partial
    return render_cart_partial(cart_items, db)


@router.post("/pos/update-cart", response_class=HTMLResponse)
async def update_cart(
    request: Request,
    item_index: int = Form(...),
    qty: float = Form(...),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Update cart item quantity"""
    cart = request.cookies.get("cart", "[]")
    try:
        cart_items = json.loads(cart)
    except:
        cart_items = []
    
    if 0 <= item_index < len(cart_items):
        if qty <= 0:
            cart_items.pop(item_index)
        else:
            cart_items[item_index]["qty"] = qty
    
    return render_cart_partial(cart_items, db)


@router.post("/pos/remove-from-cart", response_class=HTMLResponse)
async def remove_from_cart(
    request: Request,
    item_index: int = Form(...),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Remove item from cart"""
    cart = request.cookies.get("cart", "[]")
    try:
        cart_items = json.loads(cart)
    except:
        cart_items = []
    
    if 0 <= item_index < len(cart_items):
        cart_items.pop(item_index)
    
    return render_cart_partial(cart_items, db)


@router.post("/pos/apply-discount", response_class=HTMLResponse)
async def apply_discount(
    request: Request,
    item_index: int = Form(None),
    discount: float = Form(0),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Apply discount to line or whole sale"""
    cart = request.cookies.get("cart", "[]")
    try:
        cart_items = json.loads(cart)
    except:
        cart_items = []
    
    if item_index is not None and 0 <= item_index < len(cart_items):
        cart_items[item_index]["line_discount"] = discount
    else:
        # Apply to whole sale (stored separately)
        pass  # Will be handled in complete_sale
    
    return render_cart_partial(cart_items, db)


@router.post("/pos/complete-sale", response_class=HTMLResponse)
async def complete_sale(
    request: Request,
    tender_type: str = Form(...),
    customer_id: int = Form(None),
    sale_discount: float = Form(0),
    notes: str = Form(""),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Complete a sale"""
    cart = request.cookies.get("cart", "[]")
    try:
        cart_items = json.loads(cart)
    except:
        cart_items = []
    
    if not cart_items:
        return templates.TemplateResponse(
            "pos/checkout.html",
            {
                "request": request,
                "user": user_data["user"],
                "error": "Cart is empty"
            }
        )
    
    # Build sale lines
    sale_lines = []
    for item in cart_items:
        sale_lines.append(SaleLineCreate(
            product_id=item["product_id"],
            qty=Decimal(str(item["qty"])),
            unit_price=Decimal(str(item["unit_price"])),
            line_discount=Decimal(str(item.get("line_discount", 0)))
        ))
    
    # Create sale
    sale_data = SaleCreate(
        customer_id=customer_id,
        lines=sale_lines,
        sale_discount=Decimal(str(sale_discount)),
        tender_type=TenderType(tender_type),
        notes=notes
    )
    
    try:
        sale = create_sale(db, sale_data, user_data["user"].id)
        
        # Clear cart
        response = RedirectResponse(
            url=f"/pos/receipt/{sale.id}",
            status_code=302
        )
        response.delete_cookie("cart")
        return response
    except Exception as e:
        return templates.TemplateResponse(
            "pos/checkout.html",
            {
                "request": request,
                "user": user_data["user"],
                "error": str(e)
            }
        )


@router.get("/pos/receipt/{sale_id}", response_class=HTMLResponse)
async def receipt(
    request: Request,
    sale_id: int,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Print receipt"""
    sale = get_sale(db, sale_id)
    return templates.TemplateResponse(
        "pos/receipt.html",
        {"request": request, "sale": sale}
    )


@router.get("/pos/search-customer", response_class=HTMLResponse)
async def search_customer(
    request: Request,
    q: str = Query(""),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Search customers (HTMX)"""
    if not q:
        return HTMLResponse("")
    
    customers = db.query(Customer).filter(
        Customer.name.ilike(f"%{q}%")
    ).limit(10).all()
    
    return templates.TemplateResponse(
        "pos/customer_search_results.html",
        {"request": request, "customers": customers}
    )


def render_cart_partial(cart_items: list, db: Session) -> HTMLResponse:
    """Render cart partial for HTMX"""
    from app.config import settings
    
    subtotal = Decimal('0')
    taxable_subtotal = Decimal('0')
    
    for item in cart_items:
        line_total = Decimal(str(item["qty"])) * Decimal(str(item["unit_price"])) - Decimal(str(item.get("line_discount", 0)))
        subtotal += line_total
        if item.get("taxable", True):
            taxable_subtotal += line_total
    
    tax_rate = Decimal(str(settings.default_tax_rate))
    tax_amount = (taxable_subtotal * tax_rate).quantize(Decimal('0.01'))
    total = subtotal + tax_amount
    
    html = f"""
    <div id="cart-items">
        {"".join([f'''
        <div class="cart-item">
            <div>
                <strong>{item["product_name"]}</strong><br>
                <small>{item["product_sku"]}</small>
            </div>
            <div>
                <input type="number" 
                       hx-post="/pos/update-cart" 
                       hx-trigger="change" 
                       hx-target="#cart-container"
                       hx-include="[name='item_index']"
                       name="qty" 
                       value="{item["qty"]}" 
                       min="0" 
                       step="0.01"
                       style="width: 80px;">
                <input type="hidden" name="item_index" value="{idx}">
                <button hx-post="/pos/remove-from-cart" 
                        hx-target="#cart-container"
                        hx-include="[name='item_index']"
                        name="item_index" 
                        value="{idx}"
                        class="btn btn-danger btn-sm">Remove</button>
            </div>
            <div class="text-right">
                ${float(item["unit_price"]):.2f} × {item["qty"]} = ${float(Decimal(str(item["qty"])) * Decimal(str(item["unit_price"])) - Decimal(str(item.get("line_discount", 0)))):.2f}
            </div>
        </div>
        ''' for idx, item in enumerate(cart_items)])}
    </div>
    <div class="cart-totals">
        <div>Subtotal: <strong>${float(subtotal):.2f}</strong></div>
        <div>Tax: <strong>${float(tax_amount):.2f}</strong></div>
        <div class="total">Total: <strong>${float(total):.2f}</strong></div>
    </div>
    """
    
    return HTMLResponse(html)

