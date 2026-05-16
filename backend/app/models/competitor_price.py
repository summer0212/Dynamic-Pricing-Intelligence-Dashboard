import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class CompetitorPrice(Base):
    __tablename__ = "competitor_prices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    competitor_name = Column(String(100), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
