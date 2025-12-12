from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.auth import require_role
from app.models.settings import SystemSettings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_setting(db: Session, key: str, default: str = None):
    """Get a setting value by key"""
    setting = db.query(SystemSettings).filter(SystemSettings.setting_key == key).first()
    return setting.setting_value if setting else default

def set_setting(db: Session, key: str, value: str, description: str = None):
    """Set or update a setting value"""
    setting = db.query(SystemSettings).filter(SystemSettings.setting_key == key).first()
    if setting:
        setting.setting_value = value
        if description:
            setting.description = description
    else:
        setting = SystemSettings(setting_key=key, setting_value=value, description=description)
        db.add(setting)
    db.commit()
    return setting

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    user_data: dict = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """System settings page (admin only)"""
    tax_rate = get_setting(db, "tax_rate", "0.10")
    
    return templates.TemplateResponse(
        "settings/settings.html",
        {
            "request": request,
            "user": user_data["user"],
            "tax_rate": float(tax_rate) * 100,  # Convert to percentage
        }
    )

@router.post("/settings/update", response_class=RedirectResponse)
async def update_settings(
    request: Request,
    tax_rate: float = Form(...),
    user_data: dict = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Update system settings (admin only)"""
    if tax_rate < 0 or tax_rate > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tax rate must be between 0 and 100"
        )
    
    # Convert percentage to decimal
    tax_rate_decimal = tax_rate / 100
    
    set_setting(
        db, 
        "tax_rate", 
        str(tax_rate_decimal), 
        "Default sales tax rate"
    )
    
    return RedirectResponse(url="/settings?success=1", status_code=status.HTTP_302_FOUND)

