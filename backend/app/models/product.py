import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(200), nullable=False)
    sku = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False)
    current_price = Column(Numeric(10, 2), nullable=False)
    base_price = Column(Numeric(10, 2), nullable=True)   # Original price — never changes, used as drift anchor
    min_price = Column(Numeric(10, 2), nullable=True)    # Floor — minimum selling price (usually cost + small margin)
    mrp = Column(Numeric(10, 2), nullable=True)          # Maximum Retail Price — legal ceiling in India
    cost_price = Column(Numeric(10, 2), nullable=False)
    inventory_count = Column(Integer, nullable=False, default=0)
    margin_threshold = Column(Numeric(5, 2), default=0.15)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
