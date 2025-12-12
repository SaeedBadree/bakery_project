from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.auth import require_auth, require_role
from app.models.shift import Shift, CashEvent, ShiftStatus, CashEventType
from app.models.sale import Sale, TenderType
from decimal import Decimal

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/shifts", response_class=HTMLResponse)
async def list_shifts(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """List all shifts"""
    shifts = db.query(Shift).order_by(Shift.opened_at.desc()).limit(50).all()
    return templates.TemplateResponse(
        "shifts/list.html",
        {"request": request, "shifts": shifts}
    )


@router.get("/shifts/open", response_class=HTMLResponse)
async def open_shift_page(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Show open shift form"""
    # Check if already has open shift
    existing = db.query(Shift).filter(
        Shift.cashier_id == user_data["user"].id,
        Shift.status == ShiftStatus.OPEN
    ).first()
    
    if existing:
        return RedirectResponse(url="/shifts/current", status_code=302)
    
    return templates.TemplateResponse(
        "shifts/open.html",
        {"request": request}
    )


@router.post("/shifts/open", response_class=HTMLResponse)
async def open_shift(
    request: Request,
    opening_float: float = Form(...),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Open a new shift"""
    # Check if already has open shift
    existing = db.query(Shift).filter(
        Shift.cashier_id == user_data["user"].id,
        Shift.status == ShiftStatus.OPEN
    ).first()
    
    if existing:
        return RedirectResponse(url="/shifts/current", status_code=302)
    
    shift = Shift(
        cashier_id=user_data["user"].id,
        opening_float=Decimal(str(opening_float)),
        expected_cash=Decimal(str(opening_float)),
        status=ShiftStatus.OPEN
    )
    db.add(shift)
    db.commit()
    
    return RedirectResponse(url="/shifts/current", status_code=302)


@router.get("/shifts/current", response_class=HTMLResponse)
async def current_shift(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """View current shift"""
    shift = db.query(Shift).filter(
        Shift.cashier_id == user_data["user"].id,
        Shift.status == ShiftStatus.OPEN
    ).first()
    
    if not shift:
        return RedirectResponse(url="/shifts/open", status_code=302)
    
    # Calculate expected cash
    cash_sales = db.query(Sale).filter(
        Sale.shift_id == shift.id,
        Sale.tender_type == TenderType.CASH,
        Sale.status != "voided"
    ).all()
    cash_total = sum(sale.total for sale in cash_sales)
    
    # Get cash events
    cash_events = db.query(CashEvent).filter(CashEvent.shift_id == shift.id).all()
    cash_in = sum(e.amount for e in cash_events if e.event_type == CashEventType.CASH_IN)
    cash_out = sum(e.amount for e in cash_events if e.event_type in [CashEventType.CASH_OUT, CashEventType.DROP])
    
    expected_cash = shift.opening_float + cash_total + cash_in - cash_out
    shift.expected_cash = expected_cash
    db.commit()
    
    return templates.TemplateResponse(
        "shifts/current.html",
        {
            "request": request,
            "shift": shift,
            "cash_events": cash_events,
            "expected_cash": expected_cash
        }
    )


@router.post("/shifts/{shift_id}/cash-event", response_class=HTMLResponse)
async def add_cash_event(
    request: Request,
    shift_id: int,
    event_type: str = Form(...),
    amount: float = Form(...),
    reason: str = Form(""),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Add cash event"""
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift or shift.status != ShiftStatus.OPEN:
        return RedirectResponse(url="/shifts", status_code=302)
    
    event = CashEvent(
        shift_id=shift_id,
        event_type=CashEventType(event_type),
        amount=Decimal(str(amount)),
        reason=reason
    )
    db.add(event)
    db.commit()
    
    return RedirectResponse(url="/shifts/current", status_code=302)


@router.get("/shifts/{shift_id}/close", response_class=HTMLResponse)
async def close_shift_page(
    request: Request,
    shift_id: int,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Show close shift form"""
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift or shift.status != ShiftStatus.OPEN:
        return RedirectResponse(url="/shifts", status_code=302)
    
    return templates.TemplateResponse(
        "shifts/close.html",
        {"request": request, "shift": shift}
    )


@router.post("/shifts/{shift_id}/close", response_class=HTMLResponse)
async def close_shift(
    request: Request,
    shift_id: int,
    counted_cash: float = Form(...),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Close a shift"""
    from datetime import datetime
    
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift or shift.status != ShiftStatus.OPEN:
        return RedirectResponse(url="/shifts", status_code=302)
    
    shift.counted_cash = Decimal(str(counted_cash))
    shift.over_short = shift.counted_cash - shift.expected_cash
    shift.closed_at = datetime.now()
    shift.status = ShiftStatus.CLOSED
    
    db.commit()
    
    return RedirectResponse(url=f"/shifts/{shift_id}/reconciliation", status_code=302)


@router.get("/shifts/{shift_id}/reconciliation", response_class=HTMLResponse)
async def reconciliation(
    request: Request,
    shift_id: int,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Show reconciliation report"""
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        return RedirectResponse(url="/shifts", status_code=302)
    
    sales = db.query(Sale).filter(Sale.shift_id == shift_id).all()
    cash_events = db.query(CashEvent).filter(CashEvent.shift_id == shift_id).all()
    
    return templates.TemplateResponse(
        "shifts/reconciliation.html",
        {
            "request": request,
            "shift": shift,
            "sales": sales,
            "cash_events": cash_events
        }
    )

