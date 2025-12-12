from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from decimal import Decimal
from datetime import datetime
from app.models.sale import Sale, SaleLine, Return, ReturnLine, TenderType, SaleStatus
from app.models.product import Product
from app.models.shift import Shift, ShiftStatus
from app.models.ar import Customer, AREntry, AREntryType
from app.models.inventory import InventoryAdjustment, ItemType
from app.schemas.sale import SaleCreate
from app.config import settings


def calculate_tax(subtotal: Decimal, taxable_amount: Decimal, tax_rate: Decimal = None) -> Decimal:
    """Calculate tax amount"""
    if tax_rate is None:
        tax_rate = Decimal(str(settings.default_tax_rate))
    return (taxable_amount * tax_rate).quantize(Decimal('0.01'))


def create_sale(db: Session, sale_data: SaleCreate, cashier_id: int, shift_id: int = None) -> Sale:
    """Create a new sale"""
    # Shift is optional - can be None for direct sales
    # if not shift_id:
    #     shift = db.query(Shift).filter(
    #         Shift.cashier_id == cashier_id,
    #         Shift.status == ShiftStatus.OPEN
    #     ).first()
    #     if shift:
    #         shift_id = shift.id
    
    # Calculate totals
    subtotal = Decimal('0')
    taxable_subtotal = Decimal('0')
    
    sale_lines = []
    for line_data in sale_data.lines:
        product = db.query(Product).filter(Product.id == line_data.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {line_data.product_id} not found"
            )
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {product.name} is not active"
            )
        
        line_total = (line_data.qty * line_data.unit_price) - line_data.line_discount
        subtotal += line_total
        if product.taxable:
            taxable_subtotal += line_total
        
        sale_lines.append({
            "product_id": product.id,
            "qty": line_data.qty,
            "unit_price": line_data.unit_price,
            "line_discount": line_data.line_discount,
            "line_total": line_total
        })
    
    # Apply sale-level discount
    discount_amount = sale_data.sale_discount or Decimal('0')
    subtotal_after_discount = subtotal - discount_amount
    taxable_subtotal_after_discount = taxable_subtotal - discount_amount
    
    # Calculate tax
    tax_amount = calculate_tax(subtotal_after_discount, taxable_subtotal_after_discount)
    total = subtotal_after_discount + tax_amount
    
    # Generate sale number
    last_sale = db.query(Sale).order_by(Sale.id.desc()).first()
    sale_number = f"SALE-{datetime.now().strftime('%Y%m%d')}-{last_sale.id + 1 if last_sale else 1:04d}"
    
    # Create sale
    sale = Sale(
        sale_number=sale_number,
        cashier_id=cashier_id,
        shift_id=shift_id,
        customer_id=sale_data.customer_id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        discount_amount=discount_amount,
        total=total,
        tender_type=sale_data.tender_type,
        status=SaleStatus.COMPLETED,
        notes=sale_data.notes
    )
    db.add(sale)
    db.flush()
    
    # Create sale lines and update inventory
    for line_data in sale_lines:
        line = SaleLine(
            sale_id=sale.id,
            product_id=line_data["product_id"],
            qty=line_data["qty"],
            unit_price=line_data["unit_price"],
            line_discount=line_data["line_discount"],
            line_total=line_data["line_total"]
        )
        db.add(line)
        
        # Update product inventory
        product = db.query(Product).filter(Product.id == line_data["product_id"]).first()
        product.on_hand -= line_data["qty"]
        
        # Record inventory adjustment
        adjustment = InventoryAdjustment(
            item_type=ItemType.PRODUCT,
            item_id=product.id,
            qty_change=-line_data["qty"],
            reason=f"Sale {sale.sale_number}",
            user_id=cashier_id
        )
        db.add(adjustment)
    
    # Handle on-account sales (create AR entry)
    if sale_data.tender_type == TenderType.ON_ACCOUNT:
        if not sale_data.customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer required for on-account sales"
            )
        customer = db.query(Customer).filter(Customer.id == sale_data.customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        # Create AR entry
        ar_entry = AREntry(
            customer_id=customer.id,
            entry_type=AREntryType.INVOICE,
            sale_id=sale.id,
            amount=total,
            date=datetime.now().date(),
            balance=total,
            notes=f"Invoice for sale {sale.sale_number}"
        )
        db.add(ar_entry)
        
        # Update customer balance
        customer.balance += total
    
    db.commit()
    db.refresh(sale)
    return sale


def get_sale(db: Session, sale_id: int) -> Sale:
    """Get a sale by ID"""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found"
        )
    return sale


def void_sale(db: Session, sale_id: int, reason: str, user_id: int) -> Sale:
    """Void a sale (manager/admin only)"""
    sale = get_sale(db, sale_id)
    if sale.status == SaleStatus.VOIDED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sale already voided"
        )
    
    # Reverse inventory
    for line in sale.sale_lines:
        product = db.query(Product).filter(Product.id == line.product_id).first()
        product.on_hand += line.qty
        
        adjustment = InventoryAdjustment(
            item_type=ItemType.PRODUCT,
            item_id=product.id,
            qty_change=line.qty,
            reason=f"Void sale {sale.sale_number}: {reason}",
            user_id=user_id
        )
        db.add(adjustment)
    
    # Reverse AR if on-account
    if sale.tender_type == TenderType.ON_ACCOUNT and sale.customer_id:
        customer = db.query(Customer).filter(Customer.id == sale.customer_id).first()
        if customer:
            customer.balance -= sale.total
            # Reverse AR entry
            ar_entry = db.query(AREntry).filter(
                AREntry.sale_id == sale.id,
                AREntry.entry_type == AREntryType.INVOICE
            ).first()
            if ar_entry:
                ar_entry.balance = Decimal('0')
    
    sale.status = SaleStatus.VOIDED
    sale.notes = f"{sale.notes or ''}\nVOIDED: {reason}".strip()
    db.commit()
    db.refresh(sale)
    return sale


def create_return(db: Session, return_data: dict, user_id: int) -> Return:
    """Create a return/refund"""
    original_sale = get_sale(db, return_data["original_sale_id"])
    
    total_refund = Decimal('0')
    return_lines = []
    
    for line_data in return_data["return_lines"]:
        original_line = db.query(SaleLine).filter(SaleLine.id == line_data["line_id"]).first()
        if not original_line or original_line.sale_id != original_sale.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid sale line"
            )
        
        if line_data["qty_returned"] > original_line.qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot return more than sold"
            )
        
        refund_amount = (line_data["qty_returned"] / original_line.qty) * original_line.line_total
        total_refund += refund_amount
        
        return_lines.append({
            "original_line_id": original_line.id,
            "qty_returned": line_data["qty_returned"],
            "refund_amount": refund_amount
        })
        
        # Update inventory
        product = db.query(Product).filter(Product.id == original_line.product_id).first()
        product.on_hand += line_data["qty_returned"]
        
        adjustment = InventoryAdjustment(
            item_type=ItemType.PRODUCT,
            item_id=product.id,
            qty_change=line_data["qty_returned"],
            reason=f"Return for sale {original_sale.sale_number}",
            user_id=user_id
        )
        db.add(adjustment)
    
    # Create return
    return_obj = Return(
        original_sale_id=original_sale.id,
        user_id=user_id,
        reason=return_data.get("reason"),
        total_refund=total_refund
    )
    db.add(return_obj)
    db.flush()
    
    # Create return lines
    for line_data in return_lines:
        return_line = ReturnLine(
            return_id=return_obj.id,
            original_line_id=line_data["original_line_id"],
            qty_returned=line_data["qty_returned"],
            refund_amount=line_data["refund_amount"]
        )
        db.add(return_line)
    
    # Update sale status
    original_sale.status = SaleStatus.RETURNED
    
    db.commit()
    db.refresh(return_obj)
    return return_obj

