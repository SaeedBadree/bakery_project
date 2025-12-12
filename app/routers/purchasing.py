from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.auth import require_auth, require_role
from app.models.purchasing import Vendor, PurchaseOrder, POLine, ReceivedLine, POStatus
from app.models.recipe import Ingredient
from decimal import Decimal
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/purchasing", response_class=HTMLResponse)
async def purchasing_dashboard(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Purchasing dashboard"""
    vendors = db.query(Vendor).order_by(Vendor.name).all()
    pos = db.query(PurchaseOrder).order_by(PurchaseOrder.date.desc()).limit(20).all()
    
    return templates.TemplateResponse(
        "purchasing/dashboard.html",
        {"request": request, "vendors": vendors, "pos": pos}
    )


@router.get("/purchasing/vendors", response_class=HTMLResponse)
async def list_vendors(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """List vendors"""
    vendors = db.query(Vendor).order_by(Vendor.name).all()
    return templates.TemplateResponse(
        "purchasing/vendors.html",
        {"request": request, "vendors": vendors}
    )


@router.post("/purchasing/vendors", response_class=HTMLResponse)
async def create_vendor(
    request: Request,
    name: str = Form(...),
    contact: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    address: str = Form(""),
    user_data: dict = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Create vendor"""
    vendor = Vendor(
        name=name,
        contact=contact,
        email=email,
        phone=phone,
        address=address
    )
    db.add(vendor)
    db.commit()
    return RedirectResponse(url="/purchasing/vendors", status_code=302)


@router.get("/purchasing/pos/new", response_class=HTMLResponse)
async def new_po(
    request: Request,
    user_data: dict = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """New PO form"""
    vendors = db.query(Vendor).order_by(Vendor.name).all()
    ingredients = db.query(Ingredient).order_by(Ingredient.name).all()
    return templates.TemplateResponse(
        "purchasing/po_form.html",
        {"request": request, "vendors": vendors, "ingredients": ingredients}
    )


@router.post("/purchasing/pos", response_class=HTMLResponse)
async def create_po(
    request: Request,
    vendor_id: int = Form(...),
    user_data: dict = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Create PO"""
    # Generate PO number
    last_po = db.query(PurchaseOrder).order_by(PurchaseOrder.id.desc()).first()
    po_number = f"PO-{datetime.now().strftime('%Y%m%d')}-{last_po.id + 1 if last_po else 1:04d}"
    
    po = PurchaseOrder(
        vendor_id=vendor_id,
        po_number=po_number,
        status=POStatus.DRAFT,
        total=Decimal('0')
    )
    db.add(po)
    db.commit()
    
    return RedirectResponse(url=f"/purchasing/pos/{po.id}", status_code=302)


@router.get("/purchasing/pos/{po_id}", response_class=HTMLResponse)
async def view_po(
    request: Request,
    po_id: int,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """View PO details"""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        return RedirectResponse(url="/purchasing", status_code=302)
    
    return templates.TemplateResponse(
        "purchasing/po_detail.html",
        {"request": request, "po": po}
    )


@router.get("/purchasing/pos/{po_id}/receive", response_class=HTMLResponse)
async def receive_po_page(
    request: Request,
    po_id: int,
    user_data: dict = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Receive PO page"""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        return RedirectResponse(url="/purchasing", status_code=302)
    
    return templates.TemplateResponse(
        "purchasing/receive.html",
        {"request": request, "po": po}
    )


@router.post("/purchasing/pos/{po_id}/receive", response_class=HTMLResponse)
async def receive_po(
    request: Request,
    po_id: int,
    user_data: dict = Depends(require_role(["admin", "manager"])),
    db: Session = Depends(get_db)
):
    """Receive PO and update inventory"""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        return RedirectResponse(url="/purchasing", status_code=302)
    
    # Process receiving (simplified - would parse form data for each line)
    for line in po.po_lines:
        if line.qty_received < line.qty_ordered:
            # Update received qty and inventory
            qty_to_receive = line.qty_ordered - line.qty_received
            line.qty_received = line.qty_ordered
            
            ingredient = db.query(Ingredient).filter(Ingredient.id == line.ingredient_id).first()
            if ingredient:
                ingredient.on_hand += qty_to_receive
                ingredient.cost_per_unit = line.unit_cost  # Update cost
    
    po.status = POStatus.RECEIVED
    db.commit()
    
    return RedirectResponse(url="/purchasing", status_code=302)

