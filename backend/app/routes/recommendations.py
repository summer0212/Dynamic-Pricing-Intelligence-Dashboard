from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User, UserRole
from app.models.product import Product
from app.models.recommendation import Recommendation, RecommendationStatus
from app.models.audit_log import AuditLog
from app.models.competitor_price import CompetitorPrice
from app.models.org_settings import OrgSettings
from app.schemas.recommendation import (
    PredictionRequest,
    RecommendationResponse,
    RecommendationReview,
)
from app.services.pricing_engine import generate_prediction

router = APIRouter(
    prefix="/api/recommendations",
    tags=["Recommendations"],
)


def _to_response(rec: Recommendation, product: Product) -> RecommendationResponse:
    """Convert a Recommendation ORM object + its Product into a response schema."""
    current = float(rec.current_price)
    recommended = float(rec.recommended_price)
    pct_change = ((recommended - current) / current * 100) if current else 0

    return RecommendationResponse(
        id=str(rec.id),
        product_id=str(rec.product_id),
        product_name=product.name,
        product_sku=product.sku,
        recommended_price=recommended,
        current_price=current,
        price_change_pct=round(pct_change, 2),
        confidence_score=float(rec.confidence_score),
        status=rec.status.value,
        rationale=rec.rationale,
        agent_outputs=rec.agent_outputs,
        reviewed_by=str(rec.reviewed_by) if rec.reviewed_by else None,
        review_note=rec.review_note,
        created_at=rec.created_at,
    )


# ─── Generate Predictions ────────────────────────────────────────────

@router.post("/generate", response_model=List[RecommendationResponse])
def generate_recommendations(
    request: PredictionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Trigger the AI pricing engine (LangChain + Groq).
    - If product_id is given → generate for that product only.
    - Otherwise → generate for ALL products in the user's org.
    Admin only.
    """
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can generate predictions")

    if request.product_id:
        products = db.query(Product).filter(
            Product.id == request.product_id,
            Product.org_id == user.org_id,
        ).all()
        if not products:
            raise HTTPException(status_code=404, detail="Product not found")
    else:
        products = db.query(Product).filter(Product.org_id == user.org_id).all()

    if not products:
        raise HTTPException(status_code=404, detail="No products found for this organization")

    # Load org settings once for all products
    org_settings = db.query(OrgSettings).filter(
        OrgSettings.org_id == user.org_id
    ).first()

    created = []
    for product in products:
        # Load competitor prices for this product
        competitor_prices = db.query(CompetitorPrice).filter(
            CompetitorPrice.product_id == product.id
        ).all()

        prediction = generate_prediction(product, competitor_prices, org_settings)

        rec = Recommendation(
            org_id=user.org_id,
            product_id=product.id,
            recommended_price=prediction["recommended_price"],
            current_price=product.current_price,
            confidence_score=prediction["confidence_score"],
            status=RecommendationStatus.pending,
            rationale=prediction["rationale"],
            agent_outputs=prediction["agent_outputs"],
        )
        db.add(rec)
        created.append((rec, product))

    db.commit()

    # Refresh all to get server-generated fields (id, created_at)
    results = []
    for rec, product in created:
        db.refresh(rec)
        results.append(_to_response(rec, product))

    return results


# ─── List Recommendations ────────────────────────────────────────────

@router.get("/", response_model=List[RecommendationResponse])
def list_recommendations(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all recommendations for the user's org, optionally filtered by status."""
    query = db.query(Recommendation).filter(Recommendation.org_id == user.org_id)

    if status:
        try:
            status_enum = RecommendationStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        query = query.filter(Recommendation.status == status_enum)

    recs = query.order_by(Recommendation.created_at.desc()).all()

    # Batch-load products for efficiency
    product_ids = list({rec.product_id for rec in recs})
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    product_map = {p.id: p for p in products}

    return [_to_response(rec, product_map[rec.product_id]) for rec in recs]


# ─── Get Single Recommendation ───────────────────────────────────────

@router.get("/{recommendation_id}", response_model=RecommendationResponse)
def get_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a single recommendation by ID."""
    rec = db.query(Recommendation).filter(
        Recommendation.id == recommendation_id,
        Recommendation.org_id == user.org_id,
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    product = db.query(Product).filter(Product.id == rec.product_id).first()
    return _to_response(rec, product)


# ─── Review (Approve / Reject) ───────────────────────────────────────

@router.put("/{recommendation_id}/review", response_model=RecommendationResponse)
def review_recommendation(
    recommendation_id: str,
    review: RecommendationReview,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Approve or reject a recommendation. Admin only.

    On APPROVE:
      1. Updates the product's current_price to the recommended_price
      2. Creates an AuditLog entry recording the price change
      3. Marks the recommendation as approved

    On REJECT:
      1. Marks the recommendation as rejected with the review note
    """
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can review recommendations")

    # Validate status value
    if review.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")

    rec = db.query(Recommendation).filter(
        Recommendation.id == recommendation_id,
        Recommendation.org_id == user.org_id,
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    if rec.status != RecommendationStatus.pending:
        raise HTTPException(status_code=400, detail=f"Recommendation already {rec.status.value}")

    product = db.query(Product).filter(Product.id == rec.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Associated product not found")

    # --- Update recommendation ---
    rec.status = RecommendationStatus(review.status)
    rec.reviewed_by = user.id
    rec.review_note = review.review_note

    if review.status == "approved":
        old_price = product.current_price

        # Update product price
        product.current_price = rec.recommended_price

        # Create audit log
        audit = AuditLog(
            org_id=user.org_id,
            product_id=product.id,
            recommendation_id=rec.id,
            action="price_approved",
            old_price=old_price,
            new_price=rec.recommended_price,
            performed_by=user.id,
            reason=review.review_note or "Recommendation approved",
        )
        db.add(audit)

    db.commit()
    db.refresh(rec)
    db.refresh(product)

    return _to_response(rec, product)
