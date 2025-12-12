from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.auth import require_auth, require_role
from app.models.ar import Customer, AREntry, AREntryType
from app.services.ar import calculate_aging
from decimal import Decimal
from datetime import date, timedelta

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/ar", response_class=HTMLResponse)
async def ar_dashboard(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """AR dashboard"""
    customers = db.query(Customer).order_by(Customer.name).all()
    
    # Calculate totals
    total_ar = sum(c.balance for c in customers)
    
    return templates.TemplateResponse(
        "ar/dashboard.html",
        {
            "request": request,
            "customers": customers,
            "total_ar": total_ar
        }
    )


@router.get("/ar/customers", response_class=HTMLResponse)
async def list_customers(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """List customers"""
    customers = db.query(Customer).order_by(Customer.name).all()
    return templates.TemplateResponse(
        "ar/customers.html",
        {"request": request, "customers": customers}
    )


@router.post("/ar/customers", response_class=HTMLResponse)
async def create_customer(
    request: Request,
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    address: str = Form(""),
    credit_limit: float = Form(0),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Create customer"""
    customer = Customer(
        name=name,
        email=email,
        phone=phone,
        address=address,
        credit_limit=Decimal(str(credit_limit)),
        balance=Decimal('0')
    )
    db.add(customer)
    db.commit()
    return RedirectResponse(url="/ar/customers", status_code=302)


@router.get("/ar/customers/{customer_id}", response_class=HTMLResponse)
async def customer_detail(
    request: Request,
    customer_id: int,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Customer detail with ledger"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return RedirectResponse(url="/ar/customers", status_code=302)
    
    entries = db.query(AREntry).filter(AREntry.customer_id == customer_id).order_by(AREntry.date.desc()).all()
    
    # Calculate aging
    aging = calculate_aging(db, customer_id)
    
    return templates.TemplateResponse(
        "ar/customer_detail.html",
        {
            "request": request,
            "customer": customer,
            "entries": entries,
            "aging": aging
        }
    )


@router.post("/ar/customers/{customer_id}/payment", response_class=HTMLResponse)
async def record_payment(
    request: Request,
    customer_id: int,
    amount: float = Form(...),
    notes: str = Form(""),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Record payment"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return RedirectResponse(url="/ar/customers", status_code=302)
    
    payment_amount = Decimal(str(amount))
    
    # Create payment entry
    entry = AREntry(
        customer_id=customer_id,
        entry_type=AREntryType.PAYMENT,
        amount=payment_amount,
        date=date.today(),
        balance=payment_amount,  # Will be allocated
        notes=notes
    )
    db.add(entry)
    
    # Update customer balance
    customer.balance -= payment_amount
    
    db.commit()
    return RedirectResponse(url=f"/ar/customers/{customer_id}", status_code=302)


@router.get("/ar/customers/{customer_id}/statement", response_class=HTMLResponse)
async def customer_statement(
    request: Request,
    customer_id: int,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Print customer statement"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return RedirectResponse(url="/ar/customers", status_code=302)
    
    entries = db.query(AREntry).filter(AREntry.customer_id == customer_id).order_by(AREntry.date).all()
    aging = calculate_aging(db, customer_id)
    
    return templates.TemplateResponse(
        "ar/statement.html",
        {
            "request": request,
            "customer": customer,
            "entries": entries,
            "aging": aging
        }
    )

