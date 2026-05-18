from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class PredictionRequest(BaseModel):
    """Trigger prediction for a single product or all products."""
    product_id: Optional[str] = None  # None = generate for ALL products


class RecommendationReview(BaseModel):
    """Approve or reject a recommendation."""
    status: str  # "approved" or "rejected"
    review_note: Optional[str] = None


class RecommendationResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    product_sku: str
    recommended_price: float
    current_price: float
    price_change_pct: float
    confidence_score: float
    status: str
    rationale: Optional[str] = None
    agent_outputs: Optional[dict] = None
    reviewed_by: Optional[str] = None
    review_note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
