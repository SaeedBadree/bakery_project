"""
Seed script to populate database with demo data
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import *
from app.services.auth import get_password_hash
from decimal import Decimal


def seed_database():
    """Seed the database with demo data"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # Create roles
        admin_role = Role(name="admin", permissions='{"all": true}')
        manager_role = Role(name="manager", permissions='{"sales": true, "inventory": true}')
        cashier_role = Role(name="cashier", permissions='{"sales": true}')
        
        db.add(admin_role)
        db.add(manager_role)
        db.add(cashier_role)
        db.flush()
        
        # Create users
        admin = User(
            username="admin",
            email="admin@bakery.com",
            password_hash=get_password_hash("demo123"),
            role_id=admin_role.id,
            is_active=True
        )
        manager = User(
            username="manager",
            email="manager@bakery.com",
            password_hash=get_password_hash("demo123"),
            role_id=manager_role.id,
            is_active=True
        )
        cashier = User(
            username="cashier",
            email="cashier@bakery.com",
            password_hash=get_password_hash("demo123"),
            role_id=cashier_role.id,
            is_active=True
        )
        
        db.add(admin)
        db.add(manager)
        db.add(cashier)
        db.flush()
        
        # Create categories
        categories_data = [
            ("Breads", 1),
            ("Pastries", 2),
            ("Cakes", 3),
            ("Cookies", 4),
            ("Beverages", 5),
        ]
        
        categories = {}
        for name, sort_order in categories_data:
            cat = Category(name=name, sort_order=sort_order)
            db.add(cat)
            db.flush()
            categories[name] = cat
        
        # Create products
        products_data = [
            ("BREAD-001", "White Bread", "Breads", Decimal('4.50'), Decimal('1.50'), True, Decimal('50')),
            ("BREAD-002", "Whole Wheat", "Breads", Decimal('5.00'), Decimal('1.75'), True, Decimal('30')),
            ("PAST-001", "Croissant", "Pastries", Decimal('3.50'), Decimal('1.00'), True, Decimal('40')),
            ("PAST-002", "Danish", "Pastries", Decimal('4.00'), Decimal('1.25'), True, Decimal('35')),
            ("CAKE-001", "Chocolate Cake", "Cakes", Decimal('25.00'), Decimal('8.00'), True, Decimal('5')),
            ("CAKE-002", "Vanilla Cake", "Cakes", Decimal('22.00'), Decimal('7.00'), True, Decimal('6')),
            ("COOK-001", "Chocolate Chip", "Cookies", Decimal('2.50'), Decimal('0.75'), True, Decimal('100')),
            ("COOK-002", "Sugar Cookie", "Cookies", Decimal('2.00'), Decimal('0.50'), True, Decimal('80')),
            ("BEV-001", "Coffee", "Beverages", Decimal('3.00'), Decimal('0.50'), False, Decimal('200')),
            ("BEV-002", "Tea", "Beverages", Decimal('2.50'), Decimal('0.40'), False, Decimal('150')),
        ]
        
        for sku, name, cat_name, price, cost, taxable, on_hand in products_data:
            product = Product(
                sku=sku,
                name=name,
                category_id=categories[cat_name].id,
                price=price,
                cost=cost,
                taxable=taxable,
                on_hand=on_hand,
                is_active=True
            )
            db.add(product)
        
        # Create ingredients
        ingredients_data = [
            ("Flour", "g", Decimal('0.002'), Decimal('50000'), Decimal('10000')),
            ("Sugar", "g", Decimal('0.003'), Decimal('20000'), Decimal('5000')),
            ("Butter", "g", Decimal('0.005'), Decimal('10000'), Decimal('2000')),
            ("Eggs", "unit", Decimal('0.25'), Decimal('100'), Decimal('20')),
            ("Milk", "ml", Decimal('0.001'), Decimal('20000'), Decimal('5000')),
            ("Yeast", "g", Decimal('0.01'), Decimal('1000'), Decimal('200')),
            ("Chocolate", "g", Decimal('0.008'), Decimal('5000'), Decimal('1000')),
            ("Vanilla Extract", "ml", Decimal('0.02'), Decimal('500'), Decimal('100')),
        ]
        
        ingredients = {}
        for name, unit, cost, on_hand, reorder in ingredients_data:
            ing = Ingredient(
                name=name,
                unit=unit,
                cost_per_unit=cost,
                on_hand=on_hand,
                reorder_point=reorder
            )
            db.add(ing)
            db.flush()
            ingredients[name] = ing
        
        # Create recipes
        white_bread = Recipe(
            name="White Bread",
            yield_qty=Decimal('2'),
            yield_unit="loaves",
            notes="Basic white bread recipe"
        )
        db.add(white_bread)
        db.flush()
        
        # Recipe lines for white bread
        db.add(RecipeLine(recipe_id=white_bread.id, ingredient_id=ingredients["Flour"].id, qty=Decimal('500')))
        db.add(RecipeLine(recipe_id=white_bread.id, ingredient_id=ingredients["Yeast"].id, qty=Decimal('10')))
        if "Salt" in ingredients:
            db.add(RecipeLine(recipe_id=white_bread.id, ingredient_id=ingredients["Salt"].id, qty=Decimal('10')))
        
        # Create customers
        customers_data = [
            ("John's Cafe", "john@cafe.com", "555-0101", "123 Main St", Decimal('1000'), Decimal('150')),
            ("Sarah's Bakery", "sarah@bakery.com", "555-0102", "456 Oak Ave", Decimal('500'), Decimal('0')),
            ("Mike's Restaurant", "mike@rest.com", "555-0103", "789 Pine Rd", Decimal('2000'), Decimal('300')),
            ("Coffee Shop", None, "555-0104", None, Decimal('500'), Decimal('0')),
            ("Local Market", None, "555-0105", "321 Elm St", Decimal('1500'), Decimal('0')),
        ]
        
        for name, email, phone, address, credit_limit, balance in customers_data:
            customer = Customer(
                name=name,
                email=email,
                phone=phone,
                address=address,
                credit_limit=credit_limit,
                balance=balance
            )
            db.add(customer)
        
        # Create vendors
        vendors_data = [
            ("Flour Supplier", "Bob", "bob@flour.com", "555-1001", "100 Supplier St"),
            ("Dairy Co", "Alice", "alice@dairy.com", "555-1002", "200 Dairy Lane"),
        ]
        
        for name, contact, email, phone, address in vendors_data:
            vendor = Vendor(
                name=name,
                contact=contact,
                email=email,
                phone=phone,
                address=address
            )
            db.add(vendor)
        
        # Create settings
        tax_setting = Setting(key="tax_rate", value="0.10", value_type="number")
        db.add(tax_setting)
        
        db.commit()
        print("Database seeded successfully!")
        print("\nDefault credentials:")
        print("  Admin:   admin / demo123")
        print("  Manager: manager / demo123")
        print("  Cashier: cashier / demo123")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

