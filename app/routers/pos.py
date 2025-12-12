from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.auth import require_auth
from app.models.product import Product, Category
from app.models.sale import TenderType, Sale, SaleLine
# Shift system removed for simplicity
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
    from app.routers.settings import get_setting
    
    # Get default tax rate from settings
    default_tax_rate_str = get_setting(db, "tax_rate", "0.10")
    default_tax_rate = float(default_tax_rate_str)
    
    categories = db.query(Category).order_by(Category.sort_order, Category.name).all()
    products = db.query(Product).filter(Product.is_active == True).order_by(Product.name).all()
    
    # Calculate price with tax for each product
    for product in products:
        if product.taxable:
            # Use custom tax rate if set, otherwise use default
            tax_rate = float(product.custom_tax_rate) if product.custom_tax_rate else default_tax_rate
            product.price_with_tax = float(product.price) * (1 + tax_rate)
        else:
            product.price_with_tax = float(product.price)
    
    return templates.TemplateResponse(
        "pos/checkout.html",
        {
            "request": request,
            "user": user_data["user"],
            "categories": categories,
            "products": products
        }
    )


@router.get("/pos/render-cart", response_class=HTMLResponse)
async def render_cart(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Render cart partial (GET endpoint for initial load)"""
    cart = request.cookies.get("cart", "[]")
    try:
        cart_items = json.loads(cart)
    except:
        cart_items = []
    
    return render_cart_partial(cart_items, db)


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
    
    # Get cart from cookies
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
    
    # Render cart partial with full cart container
    import json as json_lib
    cart_json = json_lib.dumps(cart_items)
    response = render_cart_partial(cart_items, db)
    # Ensure cookie is set with proper attributes
    response.set_cookie("cart", cart_json, max_age=3600*24, httponly=False, samesite="lax", path="/")
    return response


@router.post("/pos/update-cart", response_class=HTMLResponse)
async def update_cart(
    request: Request,
    item_index: int = Form(None),
    qty: float = Form(None),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Update cart item quantity"""
    # Try to get item_index from any form field name pattern
    form_data = await request.form()
    item_index = None
    qty = None
    
    for key, value in form_data.items():
        if key.startswith("item_index_"):
            item_index = int(value)
        elif key.startswith("qty_") and key != "qty":
            qty = float(value)
    
    if item_index is None or qty is None:
        # Fallback to direct form fields
        item_index = form_data.get("item_index", None)
        qty = form_data.get("qty", None)
        if item_index is not None:
            item_index = int(item_index)
        if qty is not None:
            qty = float(qty)
    
    cart = request.cookies.get("cart", "[]")
    try:
        cart_items = json.loads(cart)
    except:
        cart_items = []
    
    if item_index is not None and 0 <= item_index < len(cart_items):
        if qty is not None:
            if qty <= 0:
                cart_items.pop(item_index)
            else:
                cart_items[item_index]["qty"] = qty
    
    import json as json_lib
    cart_json = json_lib.dumps(cart_items)
    response = render_cart_partial(cart_items, db)
    response.set_cookie("cart", cart_json, max_age=3600*24, httponly=False, samesite="lax", path="/")
    return response


@router.post("/pos/remove-from-cart", response_class=HTMLResponse)
async def remove_from_cart(
    request: Request,
    item_index: int = Form(None),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Remove item from cart"""
    # Try to get item_index from any form field name pattern
    form_data = await request.form()
    item_index = None
    
    for key, value in form_data.items():
        if key.startswith("item_index_"):
            item_index = int(value)
            break
    
    if item_index is None:
        item_index = form_data.get("item_index", None)
        if item_index is not None:
            item_index = int(item_index)
    
    cart = request.cookies.get("cart", "[]")
    try:
        cart_items = json.loads(cart)
    except:
        cart_items = []
    
    if item_index is not None and 0 <= item_index < len(cart_items):
        cart_items.pop(item_index)
    
    import json as json_lib
    cart_json = json_lib.dumps(cart_items)
    response = render_cart_partial(cart_items, db)
    response.set_cookie("cart", cart_json, max_age=3600*24, httponly=False, samesite="lax", path="/")
    return response


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
    # Try to get cart from form data first (more reliable)
    form_data = await request.form()
    cart = None
    cart_from_form = form_data.get("cart_data", None)
    
    if cart_from_form:
        cart = cart_from_form
    else:
        # Fallback to cookies
        cart = request.cookies.get("cart", "[]")
    
    # Parse cart JSON - handle various formats
    cart_items = []
    if cart:
        try:
            # Try parsing directly
            cart_items = json.loads(cart)
        except json.JSONDecodeError:
            # Try URL decoding first if it fails
            try:
                import urllib.parse
                decoded_cart = urllib.parse.unquote(cart)
                cart_items = json.loads(decoded_cart)
            except:
                # Last resort - try to extract JSON from string
                try:
                    # Find JSON array in string
                    import re
                    json_match = re.search(r'\[.*\]', cart)
                    if json_match:
                        cart_items = json.loads(json_match.group())
                except:
                    cart_items = []
    
    if not cart_items or len(cart_items) == 0:
        return templates.TemplateResponse(
            "pos/checkout.html",
            {
                "request": request,
                "user": user_data["user"],
                "error": "Cart is empty"
            }
        )
    
    # Handle customer_id - convert empty string to None
    if customer_id == "" or customer_id == "0":
        customer_id = None
    elif customer_id:
        try:
            customer_id = int(customer_id)
        except (ValueError, TypeError):
            customer_id = None
    
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
        sale = create_sale(db, sale_data, user_data["user"].id, shift_id=None)
        
        # Clear cart
        response = RedirectResponse(
            url=f"/pos/receipt/{sale.id}",
            status_code=302
        )
        response.set_cookie("cart", "[]", max_age=0, path="/", samesite="lax", httponly=False)
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
    """Display printable invoice/receipt after sale completion"""
    from sqlalchemy.orm import joinedload
    
    # Load sale with all relationships for invoice display
    sale = db.query(Sale).options(
        joinedload(Sale.customer),
        joinedload(Sale.cashier),
        joinedload(Sale.sale_lines).joinedload(SaleLine.product)
    ).filter(Sale.id == sale_id).first()
    
    if not sale:
        return templates.TemplateResponse(
            "pos/checkout.html",
            {
                "request": request,
                "user": user_data["user"],
                "error": "Sale not found"
            }
        )
    
    return templates.TemplateResponse(
        "pos/receipt.html",
        {
            "request": request,
            "sale": sale,
            "user": user_data["user"]
        }
    )


@router.get("/pos/search-customer", response_class=HTMLResponse)
async def search_customer(
    request: Request,
    q: str = Query(""),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Search customers (HTMX)"""
    # Also try to get from query params directly
    if not q:
        q = request.query_params.get("q", "")
    
    if not q or len(q.strip()) < 2:
        return HTMLResponse("")
    
    customers = db.query(Customer).filter(
        Customer.name.ilike(f"%{q.strip()}%")
    ).limit(10).all()
    
    return templates.TemplateResponse(
        "pos/customer_search_results.html",
        {"request": request, "customers": customers}
    )


def render_cart_partial(cart_items: list, db: Session) -> HTMLResponse:
    """Render cart items container content for HTMX"""
    from app.routers.settings import get_setting
    import json as json_lib
    
    # Get tax rate from settings
    tax_rate_str = get_setting(db, "tax_rate", "0.10")
    tax_rate = Decimal(tax_rate_str)
    
    cart_count = sum(float(item.get("qty", 1)) for item in cart_items)
    count_text = f"{int(cart_count)} item{'s' if cart_count != 1 else ''}"
    
    if not cart_items:
        html = f"""
        <div id="cart-items" style="flex: 1 1 auto; overflow-y: auto; overflow-x: hidden; min-height: 150px; max-height: 400px; background: white; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.75rem;">
            <div class="cart-empty">
                <div class="cart-empty-icon">🛒</div>
                <p>Your cart is empty</p>
                <p style="font-size: 0.85rem; margin-top: 0.5rem;">Add products to get started</p>
            </div>
        </div>
        <div class="cart-totals-modern" id="cart-totals" style="flex-shrink: 0;">
            <div class="total-line">
                <span>Subtotal</span>
                <span>$0.00</span>
            </div>
            <div class="total-line">
                <span>Tax</span>
                <span>$0.00</span>
            </div>
            <div class="total-line total">
                <span>Total</span>
                <span>$0.00</span>
            </div>
        </div>
        <p id="cart-count" hx-swap-oob="true">0 items</p>
        <div id="complete-btn-wrapper" hx-swap-oob="true">
            <button type="button" class="complete-sale-btn" id="complete-btn" onclick="completeSale()" style="opacity: 0.5; cursor: not-allowed;">Complete Sale</button>
        </div>
        """
        response = HTMLResponse(html)
        response.set_cookie("cart", "[]", max_age=3600*24, httponly=False, samesite="lax", path="/")
        return response
    
    subtotal = Decimal('0')
    taxable_subtotal = Decimal('0')
    
    for item in cart_items:
        line_total = Decimal(str(item["qty"])) * Decimal(str(item["unit_price"])) - Decimal(str(item.get("line_discount", 0)))
        subtotal += line_total
        if item.get("taxable", True):
            taxable_subtotal += line_total
    
    tax_amount = (taxable_subtotal * tax_rate).quantize(Decimal('0.01'))
    total = subtotal + tax_amount
    
    items_html = "".join([f'''
        <div class="cart-item-modern">
            <div class="cart-item-info">
                <div class="cart-item-name">{item["product_name"]}</div>
                <div class="cart-item-details">{item["product_sku"]} • ${float(item["unit_price"]):.2f} each</div>
            </div>
            <div class="cart-item-qty">
                <form hx-post="/pos/update-cart" hx-target=".cart-items-container" hx-swap="innerHTML" style="display: inline;">
                    <input type="hidden" name="item_index" value="{idx}">
                    <input type="hidden" name="qty" value="{max(0, item['qty'] - 1)}">
                    <button class="qty-btn" type="submit">-</button>
                </form>
                <span class="qty-display">{item["qty"]}</span>
                <form hx-post="/pos/update-cart" hx-target=".cart-items-container" hx-swap="innerHTML" style="display: inline;">
                    <input type="hidden" name="item_index" value="{idx}">
                    <input type="hidden" name="qty" value="{item['qty'] + 1}">
                    <button class="qty-btn" type="submit">+</button>
                </form>
            </div>
            <div class="cart-item-price">${float(Decimal(str(item["qty"])) * Decimal(str(item["unit_price"])) - Decimal(str(item.get("line_discount", 0)))):.2f}</div>
            <form hx-post="/pos/remove-from-cart" hx-target=".cart-items-container" hx-swap="innerHTML" style="display: inline;">
                <input type="hidden" name="item_index" value="{idx}">
                <button class="qty-btn" type="submit" style="background: #fee; color: #c33;">×</button>
            </form>
        </div>
    ''' for idx, item in enumerate(cart_items)])
    
    html = f"""
    <div id="cart-items" style="flex: 1 1 auto; overflow-y: auto; overflow-x: hidden; min-height: 150px; max-height: 400px; background: white; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.75rem;">
        {items_html}
    </div>
    <div class="cart-totals-modern" id="cart-totals" style="flex-shrink: 0;">
        <div class="total-line">
            <span>Subtotal</span>
            <span>${float(subtotal):.2f}</span>
        </div>
        <div class="total-line">
            <span>Tax ({float(tax_rate)*100:.0f}%)</span>
            <span>${float(tax_amount):.2f}</span>
        </div>
        <div class="total-line total">
            <span>Total</span>
            <span>${float(total):.2f}</span>
        </div>
    </div>
    <p id="cart-count" hx-swap-oob="true">{count_text}</p>
    <div id="complete-btn-wrapper" hx-swap-oob="true">
        <button type="button" class="complete-sale-btn" id="complete-btn" onclick="completeSale()">Complete Sale (${float(total):.2f})</button>
    </div>
    """
    
    response = HTMLResponse(html)
    response.set_cookie("cart", json_lib.dumps(cart_items), max_age=3600*24, httponly=False, samesite="lax", path="/")
    return response

