"""Quick verification that the approval flow updated the product price and created an audit log."""
import sys
sys.path.insert(0, ".")
from app.database import SessionLocal
from app.models.product import Product
from app.models.recommendation import Recommendation
from app.models.audit_log import AuditLog

db = SessionLocal()

print("=== APPROVED RECOMMENDATIONS ===")
approved = db.query(Recommendation).filter(Recommendation.status == "approved").all()
for r in approved:
    product = db.query(Product).filter(Product.id == r.product_id).first()
    print(f"  Rec {str(r.id)[:8]}: recommended ₹{float(r.recommended_price):,.2f}")
    print(f"  Product '{product.name}' current price: ₹{float(product.current_price):,.2f}")
    print(f"  Match: {'YES ✅' if float(product.current_price) == float(r.recommended_price) else 'NO ❌'}")
    print()

print("=== AUDIT LOG ===")
logs = db.query(AuditLog).all()
for log in logs:
    print(f"  {log.action}: ₹{float(log.old_price):,.2f} → ₹{float(log.new_price):,.2f} ({log.reason})")

if not approved:
    print("  (No approved recommendations yet)")
if not logs:
    print("  (No audit logs yet)")

db.close()
