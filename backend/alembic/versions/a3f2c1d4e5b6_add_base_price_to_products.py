"""add base_price to products

Revision ID: a3f2c1d4e5b6
Revises: 17613b87962d
Create Date: 2026-05-24 17:55:00.000000

Adds a base_price column to the products table.
This is the original/anchor price set at product creation.
It never changes — used by the pricing engine to cap drift at ±25%.
Existing rows are backfilled so base_price = current_price.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3f2c1d4e5b6'
down_revision = '17613b87962d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add column as nullable first so existing rows don't fail
    op.add_column(
        'products',
        sa.Column('base_price', sa.Numeric(10, 2), nullable=True)
    )
    # Backfill: for all existing products, set base_price = current_price
    op.execute("UPDATE products SET base_price = current_price WHERE base_price IS NULL")


def downgrade() -> None:
    op.drop_column('products', 'base_price')
