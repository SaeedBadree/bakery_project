from fastapi import FastAPI, Request, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from app.config import settings
from app.routers import (
    auth, pos, products, inventory, reports, transactions
)
from app.routers import settings as settings_router

app = FastAPI(title=settings.app_name, debug=settings.debug)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions, especially for HTMX requests"""
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        # Check if this is an HTMX request
        if request.headers.get("HX-Request") == "true":
            # Return HTML that redirects
            return HTMLResponse(
                '<script>window.location.href = "/login";</script>'
                '<div class="alert alert-error">Session expired. Please <a href="/login">login again</a>.</div>',
                status_code=401
            )
        # Regular request - redirect
        return RedirectResponse(url="/login", status_code=302)
    # For other exceptions, use default behavior
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(auth.router, tags=["auth"])
app.include_router(pos.router, tags=["pos"])
app.include_router(products.router, tags=["products"])
app.include_router(inventory.router, tags=["inventory"])
app.include_router(transactions.router, tags=["transactions"])
app.include_router(settings_router.router, tags=["settings"])
# Simplified - removed production, purchasing, ar, shifts
# app.include_router(production.router, tags=["production"])
# app.include_router(purchasing.router, tags=["purchasing"])
# app.include_router(ar.router, tags=["ar"])
app.include_router(reports.router, tags=["reports"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to dashboard or login"""
    return RedirectResponse(url="/login", status_code=302)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=True,
        reload_excludes=["venv/*", "*.pyc", "__pycache__/*", ".git/*", "*.db", "alembic/versions/__pycache__/*"]
    )

