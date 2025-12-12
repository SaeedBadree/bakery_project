# Tax Settings Feature - Setup Instructions

## ✅ What's Been Added

I've implemented a **System Settings** feature that allows admins to configure the tax percentage dynamically:

### 🎯 Features:
1. **Settings Page** (Admin-only)
   - Configure tax rate percentage
   - Clean, user-friendly interface
   - Input validation (0-100%)

2. **Dynamic Tax Calculation**
   - POS checkout uses the configured tax rate
   - Cart totals reflect current tax setting
   - Product cards show price with tax

3. **Navigation**
   - "⚙️ Settings" link appears for admins only

## 📋 Setup Steps

### 1. Start Your Server
```bash
python -m uvicorn app.main:app --reload
```

### 2. Initialize Settings (One-Time)
**In a new terminal**, run:
```bash
python scripts/seed_settings.py
```

This will:
- Create the `system_settings` table
- Set default tax rate to 10%

### 3. Access Settings
1. Login as **admin**
2. Click **"⚙️ Settings"** in the navigation
3. Change the tax rate as needed
4. Click **"Save Settings"**

## 🎨 How It Works

### For Admins:
- Go to Settings page
- Enter tax percentage (e.g., `15` for 15% tax)
- Save changes
- Tax immediately applies to all sales

### For All Users:
- POS checkout shows updated tax rate
- Product cards display "Price with Tax"
- Cart totals calculate correctly
- Receipts reflect current tax rate

## 📁 Files Modified/Created

### New Files:
- `app/models/settings.py` - Settings database model
- `app/routers/settings.py` - Settings API routes
- `app/templates/settings/settings.html` - Settings page UI
- `scripts/seed_settings.py` - Initial setup script
- `alembic/versions/add_system_settings.py` - Migration (manual)

### Modified Files:
- `app/main.py` - Registered settings router
- `app/routers/pos.py` - Uses dynamic tax rate
- `app/templates/base.html` - Added Settings link for admins

## 🔧 Testing

1. **Login as admin** (default: `admin` / `admin123`)
2. **Go to Settings** page
3. **Change tax rate** to 15%
4. **Go to POS/Billing**
5. **Verify** products show correct prices with 15% tax
6. **Add items to cart** and check totals
7. **Complete a sale** and verify receipt

## ⚠️ Important Notes

- Only **admins** can change tax settings
- Tax rate applies **immediately** after saving
- Changes affect **all future sales** (not past ones)
- Non-taxable products ignore the tax rate

---

**Status**: ✅ Ready to use!

Just run the setup steps above and you're good to go! 🚀

