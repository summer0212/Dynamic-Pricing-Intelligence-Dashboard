"""
One-time patch: updates min_price and mrp on existing products using raw SQL.
Safe to run multiple times — idempotent UPDATE.

Usage:
    cd backend
    python scripts/patch_product_prices.py
"""
import sys
sys.path.insert(0, ".")

from app.database import engine
from sqlalchemy import text

# Correct min_price and mrp per SKU
PRICE_BOUNDS = {
    "SONY-WH1000": {"min_price": 19800,  "mrp": 29990},
    "SAM-S24":     {"min_price": 61000,  "mrp": 89999},
    "NIKE-AM90":   {"min_price":  8500,  "mrp": 16995},
    "DYS-V15":     {"min_price": 39000,  "mrp": 62990},
    "APL-APP2":    {"min_price": 18900,  "mrp": 29900},
    "LEV-501":     {"min_price":  3200,  "mrp":  6499},
    "IP-DUO":      {"min_price":  6500,  "mrp": 10999},
    "JBL-FL6":     {"min_price":  7500,  "mrp": 12999},
    "BOAT-AD141":  {"min_price":   799,  "mrp":  1999},
    "HM-BTEE":     {"min_price":   499,  "mrp":   999},
    "PRE-IND":     {"min_price":  2200,  "mrp":  3999},
}

with engine.connect() as conn:
    for sku, bounds in PRICE_BOUNDS.items():
        result = conn.execute(
            text("UPDATE products SET min_price = :min_p, mrp = :mrp WHERE sku = :sku"),
            {"min_p": bounds["min_price"], "mrp": bounds["mrp"], "sku": sku}
        )
        if result.rowcount:
            print(f"  ✓ {sku} → min=₹{bounds['min_price']:,} | mrp=₹{bounds['mrp']:,}")
        else:
            print(f"  ⚠ {sku} — not found in DB")
    conn.commit()

print(f"\n✅ Done! min_price and mrp updated for all products.")
