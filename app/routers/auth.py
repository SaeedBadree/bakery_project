from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.auth import authenticate_user, get_user
from app.schemas.user import LoginRequest, UserResponse
from app.config import settings
import secrets
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Simple session storage (in production, use Redis or database sessions)
sessions = {}


def get_current_user(request: Request, db: Session = Depends(get_db)) -> dict | None:
    """Get current user from session"""
    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        return None
    if session_id not in sessions:
        return None
    user_data = sessions[session_id]
    user = get_user(db, user_data["user_id"])
    if not user or not user.is_active:
        return None
    return {"user": user, "session_id": session_id}


def require_auth(request: Request, db: Session = Depends(get_db)):
    """Dependency to require authentication"""
    user_data = get_current_user(request, db)
    if not user_data:
        # For HTMX requests, we'll handle the redirect client-side
        # For regular requests, raise exception
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"HX-Redirect": "/login"} if request.headers.get("HX-Request") == "true" else {}
        )
    return user_data


def require_role(allowed_roles: list[str]):
    """Decorator factory for role-based access control"""
    def role_checker(user_data: dict = Depends(require_auth)):
        user = user_data["user"]
        role_name = user.role.name.lower()
        if role_name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user_data
    return role_checker


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show login page"""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle login"""
    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Invalid username or password"}
        )
    
    # Create session
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {
        "user_id": user.id,
        "created_at": str(datetime.now())
    }
    
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=settings.session_max_age,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax"
    )
    return response


@router.get("/logout")
async def logout(request: Request):
    """Handle logout"""
    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id and session_id in sessions:
        del sessions[session_id]
    
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key=settings.session_cookie_name)
    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request, 
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Dashboard page"""
    from datetime import datetime, date
    from app.models.sale import Sale
    from sqlalchemy import func
    
    # Get today's sales
    today = date.today()
    today_sales = db.query(
        func.count(Sale.id).label('transaction_count'),
        func.coalesce(func.sum(Sale.total), 0).label('total_sales')
    ).filter(
        func.date(Sale.datetime) == today
    ).first()
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user_data["user"],
            "today_sales": float(today_sales.total_sales) if today_sales else 0.0,
            "today_transactions": today_sales.transaction_count if today_sales else 0
        }
    )


@router.get("/dashboard/summary", response_class=HTMLResponse)
async def dashboard_summary(
    request: Request,
    user_data: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get today's sales summary (for HTMX polling)"""
    from datetime import date
    from app.models.sale import Sale
    from sqlalchemy import func
    
    # Get today's sales
    today = date.today()
    today_sales = db.query(
        func.count(Sale.id).label('transaction_count'),
        func.coalesce(func.sum(Sale.total), 0).label('total_sales')
    ).filter(
        func.date(Sale.datetime) == today
    ).first()
    
    sales_total = float(today_sales.total_sales) if today_sales else 0.0
    transaction_count = today_sales.transaction_count if today_sales else 0
    
    return HTMLResponse(f"""
        <div class="card-header">Today's Summary</div>
        <p><strong>Sales:</strong> ${sales_total:.2f}</p>
        <p><strong>Transactions:</strong> {transaction_count}</p>
        <p style="font-size: 0.8rem; color: #6c757d; margin-top: 1rem;">Auto-refreshes every 5 seconds</p>
    """)

