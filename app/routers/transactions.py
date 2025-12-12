from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.routers.auth import require_auth, require_role
from app.models.sale import Sale, SaleLine
from app.models.product import Product
from datetime import datetime, date, timedelta
from decimal import Decimal

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/transactions/history", response_class=HTMLResponse)
async def transaction_history(
    request: Request,
    start_date: str = Query(None),
    end_date: str = Query(None),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Transaction history with date filtering"""
    from sqlalchemy.orm import joinedload
    
    # Build query
    query = db.query(Sale).options(
        joinedload(Sale.customer),
        joinedload(Sale.cashier),
        joinedload(Sale.sale_lines)
    )
    
    # Apply date filters
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(func.date(Sale.datetime) >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(func.date(Sale.datetime) <= end)
        except ValueError:
            pass
    
    # If no dates specified, show last 30 days
    if not start_date and not end_date:
        thirty_days_ago = date.today() - timedelta(days=30)
        query = query.filter(func.date(Sale.datetime) >= thirty_days_ago)
        start_date = thirty_days_ago.strftime('%Y-%m-%d')
        end_date = date.today().strftime('%Y-%m-%d')
    
    # Get transactions ordered by date (newest first)
    transactions = query.order_by(Sale.datetime.desc()).all()
    
    # Calculate total (exclude voided transactions)
    from app.models.sale import SaleStatus
    total_amount = sum(sale.total for sale in transactions if sale.status != SaleStatus.VOIDED)
    
    return templates.TemplateResponse(
        "transactions/history.html",
        {
            "request": request,
            "user": user_data["user"],
            "transactions": transactions,
            "total_amount": float(total_amount),
            "start_date": start_date,
            "end_date": end_date
        }
    )


@router.post("/transactions/void/{sale_id}")
async def void_transaction(
    sale_id: int,
    request: Request,
    user_data: dict = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Void a transaction (admin only)"""
    from app.models.sale import SaleStatus
    
    # Get the sale
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    
    if not sale:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Check if already voided using status
    if sale.status == SaleStatus.VOIDED:
        raise HTTPException(status_code=400, detail="Transaction already voided")
    
    # Mark as voided using existing status field
    sale.status = SaleStatus.VOIDED
    sale.notes = (sale.notes or "") + f" [VOIDED by {user_data['user'].username} at {datetime.now().strftime('%Y-%m-%d %H:%M')}]"
    
    # Reverse inventory changes
    for line in sale.sale_lines:
        product = db.query(Product).filter(Product.id == line.product_id).first()
        if product:
            # Add back the quantity that was sold
            product.on_hand += line.qty
    
    db.commit()
    
    return JSONResponse({"success": True, "message": "Transaction voided successfully"})

