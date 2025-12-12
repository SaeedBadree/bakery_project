# Bakery POS + ERP-Lite System

A self-hosted, lightweight Point of Sale (POS) and ERP-lite system designed specifically for bakeries. Built with Python FastAPI, Jinja2 templates, HTMX, and SQLite.

## Features

### Core Modules

1. **Authentication & Roles**
   - User management with roles (admin, manager, cashier)
   - Secure password hashing
   - Role-based access control

2. **POS Sales**
   - Product catalog with categories
   - Checkout screen with HTMX-powered cart
   - Tax calculation (configurable rate)
   - Discounts (line-level and sale-level)
   - Multiple tender types (cash, card, transfer, on-account)
   - Print-friendly receipts
   - Returns and refunds
   - Sale voids (manager/admin only)

3. **Shift Management**
   - Shift open/close workflow
   - Cash drawer tracking
   - Cash in/out events (paid-out, drops)
   - End-of-day reconciliation
   - Over/short calculation
   - CSV export for reconciliation reports

4. **Inventory Management**
   - Product on-hand tracking
   - Stock adjustments with audit trail
   - Stock take workflow
   - Low-stock alerts

5. **Production Management**
   - Ingredient management
   - Recipe builder with cost calculation
   - Batch production tracking
   - Automatic ingredient deduction
   - Finished goods inventory updates
   - Wastage tracking
   - Production schedule view

6. **Purchasing**
   - Vendor management
   - Purchase order creation
   - PO receiving with cost variance handling
   - Ingredient inventory updates

7. **Accounts Receivable**
   - Customer management
   - On-account sales create AR invoices
   - Payment recording
   - Aging buckets (0-30, 31-60, 61-90, 90+ days)
   - Customer statements (print-friendly)

8. **Reporting**
   - Daily sales reports with tender breakdown
   - Top-selling products
   - Inventory valuation
   - Wastage reports

## Installation

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for containerized deployment)
- OR Python virtual environment (for local development)

### Docker Deployment (Recommended)

1. Clone or download this repository

2. Build and run with Docker Compose:
```bash
docker-compose up -d
```

3. Access the application at `http://localhost:8000`

4. Login with default credentials (see below)

### Local Development Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run database migrations:
```bash
python -m alembic upgrade head
```

4. Seed the database with demo data:
```bash
python scripts/seed.py
```

5. Start the development server:
```bash
uvicorn app.main:app --reload
```

6. Access at `http://localhost:8000`

## Default Credentials

After seeding the database, use these credentials:

- **Admin**: `admin` / `demo123`
- **Manager**: `manager` / `demo123`
- **Cashier**: `cashier` / `demo123`

**Important**: Change these passwords immediately in production!

## Database Backup & Restore

### Backup SQLite Database

```bash
# Simple copy (while app is stopped)
cp bakery.db bakery.db.backup

# Or use SQLite backup command
sqlite3 bakery.db ".backup bakery.db.backup"
```

### Restore SQLite Database

```bash
# Stop the application first
# Then restore
cp bakery.db.backup bakery.db

# Or with Docker
docker-compose exec bakery-pos cp /app/bakery.db.backup /app/bakery.db
```

### Automated Backup Script

Create a cron job or scheduled task:

```bash
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)
cp bakery.db "$BACKUP_DIR/bakery_$DATE.db"
# Keep only last 30 days
find "$BACKUP_DIR" -name "bakery_*.db" -mtime +30 -delete
```

## Receipt Printing

The system generates print-friendly receipts using CSS print media queries.

### Browser Print

1. Complete a sale
2. View the receipt page
3. Click "Print" button or use browser print (Ctrl+P / Cmd+P)
4. Select your printer and print

### Thermal Printer Setup

For thermal printers (e.g., 80mm receipt printers):

1. Configure printer settings in your OS
2. Use browser print dialog
3. Set paper size to "80mm x 297mm" or custom size
4. Adjust margins as needed

### Print Settings

- Paper size: 80mm width (thermal) or A4 (standard)
- Margins: Minimal (0.5cm recommended)
- Scale: 100% (no scaling)

## Project Structure

```
bakery-pos/
├── app/
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   ├── routers/         # FastAPI routes
│   ├── templates/       # Jinja2 templates
│   └── static/          # CSS and static files
├── alembic/             # Database migrations
├── tests/                # Unit tests
├── scripts/              # Utility scripts
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Configuration

Edit `app/config.py` or set environment variables:

- `DATABASE_URL`: Database connection string (default: `sqlite:///./bakery.db`)
- `SECRET_KEY`: Session secret key (change in production!)
- `DEFAULT_TAX_RATE`: Default tax rate (default: 0.10 = 10%)

## Development

### Running Tests

```bash
pytest tests/
```

### Creating Migrations

```bash
# After modifying models
python -m alembic revision --autogenerate -m "Description"
python -m alembic upgrade head
```

### Code Style

The project follows PEP 8. Consider using:
- `black` for formatting
- `flake8` for linting
- `mypy` for type checking

## Troubleshooting

### Database Locked Error

If you see "database is locked" errors:
- Ensure only one instance of the app is running
- Check for long-running transactions
- Restart the application

### Migration Issues

If migrations fail:
```bash
# Check current migration status
python -m alembic current

# Downgrade if needed
python -m alembic downgrade -1

# Re-run migrations
python -m alembic upgrade head
```

### Port Already in Use

If port 8000 is in use:
- Change port in `docker-compose.yml` or uvicorn command
- Or stop the process using port 8000

## Security Notes

- **Change default passwords** before production use
- **Set a strong SECRET_KEY** in production
- **Use HTTPS** in production (reverse proxy with nginx/traefik)
- **Regular backups** are essential
- **Restrict database file permissions** (chmod 600 bakery.db)

## License

This project is provided as-is for self-hosted use.

## Support

For issues, questions, or contributions, please refer to the project repository.

## Roadmap

See `roadmap.md` for planned features and improvements.
