"""Seed script: populates the database with demo products for 2 organizations."""
import sys
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.product import Product
from app.models.org_settings import OrgSettings
from app.models.competitor_price import CompetitorPrice
from app.utils.security import hash_password

db = SessionLocal()

# --- Org 1: TechCorp ---
org1 = Organization(name="TechCorp", invite_code="TECH2026")
db.add(org1)
db.flush()

settings1 = OrgSettings(org_id=org1.id, auto_execute_threshold=0.85)
db.add(settings1)

admin1 = User(email="admin@techcorp.com", password_hash=hash_password("admin123"),
              name="Admin TechCorp", org_id=org1.id, role=UserRole.admin)
analyst1 = User(email="analyst@techcorp.com", password_hash=hash_password("analyst123"),
                name="Analyst TechCorp", org_id=org1.id, role=UserRole.analyst)
db.add_all([admin1, analyst1])

products_data = [
    ("Sony WH-1000XM5", "SONY-WH1000", "electronics", 24990, 18000, 150, 0.15),
    ("Samsung Galaxy S24", "SAM-S24", "electronics", 79999, 55000, 80, 0.20),
    ("Nike Air Max 90", "NIKE-AM90", "apparel", 12995, 7000, 200, 0.25),
    ("Dyson V15 Detect", "DYS-V15", "home_goods", 52990, 35000, 45, 0.15),
    ("Apple AirPods Pro", "APL-APP2", "electronics", 24900, 17000, 120, 0.18),
    ("Levi's 501 Jeans", "LEV-501", "apparel", 4999, 2500, 300, 0.20),
    ("Instant Pot Duo", "IP-DUO", "home_goods", 8999, 5500, 90, 0.15),
    ("JBL Flip 6", "JBL-FL6", "electronics", 9999, 6000, 175, 0.18),
]

for name, sku, cat, price, cost, inv, margin in products_data:
    p = Product(org_id=org1.id, name=name, sku=sku, category=cat,
                current_price=price, cost_price=cost, inventory_count=inv,
                margin_threshold=margin)
    db.add(p)

# --- Org 2: RetailHub ---
org2 = Organization(name="RetailHub", invite_code="RETAIL26")
db.add(org2)
db.flush()

settings2 = OrgSettings(org_id=org2.id, auto_execute_threshold=0.75)
db.add(settings2)

admin2 = User(email="admin@retailhub.com", password_hash=hash_password("admin123"),
              name="Admin RetailHub", org_id=org2.id, role=UserRole.admin)
db.add(admin2)

products_data2 = [
    ("Boat Airdopes 141", "BOAT-AD141", "electronics", 1299, 600, 500, 0.30),
    ("H&M Basic Tee", "HM-BTEE", "apparel", 799, 300, 1000, 0.25),
    ("Prestige Induction", "PRE-IND", "home_goods", 2999, 1800, 60, 0.15),
]

for name, sku, cat, price, cost, inv, margin in products_data2:
    p = Product(org_id=org2.id, name=name, sku=sku, category=cat,
                current_price=price, cost_price=cost, inventory_count=inv,
                margin_threshold=margin)
    db.add(p)

db.commit()
print("✅ Seed data created!")
print(f"   TechCorp: invite_code=TECH2026, admin=admin@techcorp.com/admin123")
print(f"   RetailHub: invite_code=RETAIL26, admin=admin@retailhub.com/admin123")
db.close()
