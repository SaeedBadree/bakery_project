from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.database import get_db
from app.routers.auth import require_auth
from app.models.sale import Sale, SaleLine, TenderType
from app.models.product import Product
from app.models.recipe import Ingredient, Batch
from decimal import Decimal
from datetime import datetime, date, timedelta
import csv
import io

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/reports", response_class=HTMLResponse)
async def reports_dashboard(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Reports dashboard"""
    return templates.TemplateResponse(
        "reports/dashboard.html",
        {"request": request}
    )


@router.get("/reports/daily-sales", response_class=HTMLResponse)
async def daily_sales_report(
    request: Request,
    report_date: str = Query(None),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Daily sales report"""
    if report_date:
        target_date = datetime.strptime(report_date, "%Y-%m-%d").date()
    else:
        target_date = date.today()
    
    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time())
    
    sales = db.query(Sale).filter(
        Sale.datetime >= start_datetime,
        Sale.datetime <= end_datetime,
        Sale.status != "voided"
    ).all()
    
    # Group by tender type
    tender_totals = {}
    for sale in sales:
        tender = sale.tender_type.value
        if tender not in tender_totals:
            tender_totals[tender] = Decimal('0')
        tender_totals[tender] += sale.total
    
    total_sales = sum(sale.total for sale in sales)
    
    return templates.TemplateResponse(
        "reports/daily_sales.html",
        {
            "request": request,
            "sales": sales,
            "tender_totals": tender_totals,
            "total_sales": total_sales,
            "report_date": target_date
        }
    )


@router.get("/reports/top-products", response_class=HTMLResponse)
async def top_products_report(
    request: Request,
    days: int = Query(30),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Top selling products report"""
    start_date = datetime.now() - timedelta(days=days)
    
    # Query top products by quantity sold
    top_products = db.query(
        Product.id,
        Product.name,
        Product.sku,
        func.sum(SaleLine.qty).label('total_qty'),
        func.sum(SaleLine.line_total).label('total_revenue')
    ).join(
        SaleLine, SaleLine.product_id == Product.id
    ).join(
        Sale, Sale.id == SaleLine.sale_id
    ).filter(
        Sale.datetime >= start_date,
        Sale.status != "voided"
    ).group_by(
        Product.id, Product.name, Product.sku
    ).order_by(
        desc('total_qty')
    ).limit(20).all()
    
    return templates.TemplateResponse(
        "reports/top_products.html",
        {
            "request": request,
            "top_products": top_products,
            "days": days
        }
    )


@router.get("/reports/inventory-valuation", response_class=HTMLResponse)
async def inventory_valuation(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Inventory valuation report"""
    products = db.query(Product).filter(Product.is_active == True).all()
    ingredients = db.query(Ingredient).all()
    
    product_value = sum(p.on_hand * (p.cost or Decimal('0')) for p in products)
    ingredient_value = sum(i.on_hand * i.cost_per_unit for i in ingredients)
    total_value = product_value + ingredient_value
    
    return templates.TemplateResponse(
        "reports/inventory_valuation.html",
        {
            "request": request,
            "products": products,
            "ingredients": ingredients,
            "product_value": product_value,
            "ingredient_value": ingredient_value,
            "total_value": total_value
        }
    )


@router.get("/reports/wastage", response_class=HTMLResponse)
async def wastage_report(
    request: Request,
    start_date: str = Query(None),
    end_date: str = Query(None),
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Wastage report"""
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start = datetime.now() - timedelta(days=30)
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end = datetime.now()
    
    batches = db.query(Batch).filter(
        Batch.produced_at >= start,
        Batch.produced_at <= end,
        Batch.wastage > 0
    ).order_by(Batch.produced_at.desc()).all()
    
    total_wastage = sum(b.wastage for b in batches)
    
    return templates.TemplateResponse(
        "reports/wastage.html",
        {
            "request": request,
            "batches": batches,
            "total_wastage": total_wastage,
            "start_date": start.date(),
            "end_date": end.date()
        }
    )

