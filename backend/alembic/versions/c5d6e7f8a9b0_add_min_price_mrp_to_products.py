"""add min_price and mrp to products

Revision ID: c5d6e7f8a9b0
Revises: a3f2c1d4e5b6
Create Date: 2026-05-25 00:44:00.000000

Adds two new columns to the products table:
  - min_price : the floor price — minimum the product should ever be sold for
  - mrp       : Maximum Retail Price — the legal ceiling (common in Indian e-commerce)

Existing rows are backfilled with sensible defaults:
  - min_price = cost_price * 1.10  (10% above cost — basic margin floor)
  - mrp       = current_price * 1.35  (35% above current price as a default MRP)
"""
from alembic import op
import sqlalchemy as sa


revision = 'c5d6e7f8a9b0'
down_revision = 'a3f2c1d4e5b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('products', sa.Column('min_price', sa.Numeric(10, 2), nullable=True))
    op.add_column('products', sa.Column('mrp', sa.Numeric(10, 2), nullable=True))

    # Backfill existing rows with sensible defaults
    op.execute("""
        UPDATE products
        SET
            min_price = ROUND(cost_price * 1.10, 2),
            mrp       = ROUND(current_price * 1.35, 2)
        WHERE min_price IS NULL OR mrp IS NULL
    """)


def downgrade() -> None:
    op.drop_column('products', 'mrp')
    op.drop_column('products', 'min_price')
