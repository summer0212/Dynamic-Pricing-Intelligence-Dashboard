"""
Patch script: injects simulated competitor prices into the competitor_prices table.

SAFE TO RUN MULTIPLE TIMES — deletes and re-inserts rows for each product
so you always get fresh random prices within the product's real min/mrp range.

New logic (Option A):
  - Each product has min_price and mrp stored in the products table
  - Amazon, Flipkart and Meesho each get a random price between min_price and mrp
  - No platform-specific bias — each platform independently draws from the full range
  - This mirrors real Indian e-commerce: any platform can list at any price within the band

Why this is better than the old percentage-band approach:
  - Old: prices anchored to current_price (drifts as you approve recommendations)
  - New: prices anchored to min_price/mrp (fixed product attributes, never drift)

Usage:
    cd backend
    python scripts/patch_competitor_prices.py
"""
import sys
import random
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models.product import Product
from app.models.competitor_price import CompetitorPrice

COMPETITORS = ["Amazon", "Flipkart", "Meesho"]

db = SessionLocal()

try:
    products = db.query(Product).all()
    print(f"Found {len(products)} products. Refreshing competitor prices...\n")

    total_deleted = 0
    total_inserted = 0

    for product in products:
        # Determine bounds
        min_p = float(product.min_price) if product.min_price else float(product.cost_price) * 1.10
        mrp_p = float(product.mrp)       if product.mrp       else float(product.current_price) * 1.35

        if min_p >= mrp_p:
            print(f"  ⚠ Skipping {product.name} — min_price ({min_p}) >= mrp ({mrp_p})")
            continue

        # Delete any existing competitor price rows for this product
        deleted = db.query(CompetitorPrice).filter(
            CompetitorPrice.product_id == product.id
        ).delete()
        total_deleted += deleted

        # Insert one fresh row per competitor, price randomly drawn from [min_price, mrp]
        for competitor_name in COMPETITORS:
            competitor_price = round(random.uniform(min_p, mrp_p), 2)
            row = CompetitorPrice(
                product_id=product.id,
                competitor_name=competitor_name,
                price=competitor_price,
            )
            db.add(row)
            total_inserted += 1

        print(
            f"  ✓ {product.name} ({product.sku}) "
            f"| range: ₹{min_p:,.0f} – ₹{mrp_p:,.0f}"
        )

    db.commit()
    print(
        f"\n✅ Done! Removed {total_deleted} old rows. "
        f"Inserted {total_inserted} fresh competitor price rows."
    )

except Exception as e:
    db.rollback()
    print(f"❌ Error: {e}")
    raise
finally:
    db.close()
