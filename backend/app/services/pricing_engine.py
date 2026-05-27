"""
AI Pricing Engine — LangChain + Groq powered pricing recommendations.

Uses ChatGroq (llama-3.1-8b-instant) with structured output to analyze
product data, competitor prices, and org margin settings, then generate
intelligent pricing recommendations.

Falls back to simple heuristic logic if the LLM call fails.
"""
import random
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.models.product import Product
from app.models.competitor_price import CompetitorPrice
from app.models.org_settings import OrgSettings

logger = logging.getLogger(__name__)


# ─── Structured Output Schema ────────────────────────────────────────

class PricingRecommendation(BaseModel):
    """Structured output the LLM must return."""
    recommended_price: float = Field(
        description="The recommended selling price in the same currency as the current price"
    )
    confidence_score: float = Field(
        description="Confidence in this recommendation from 0.60 to 0.95"
    )
    direction: str = Field(
        description="Either 'increase' or 'decrease' or 'maintain'"
    )
    rationale: str = Field(
        description="A detailed 2-3 sentence explanation of why this price is recommended, "
                    "referencing specific factors like inventory, margin, competitors"
    )
    factors_analyzed: List[str] = Field(
        description="List of factors that were considered in the analysis"
    )


# ─── Prompt Template ─────────────────────────────────────────────────

PRICING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a senior pricing intelligence analyst for an e-commerce platform.
Your job is to analyze product data and recommend an OPTIMIZED price that maximizes revenue.

PRICING STRATEGY RULES:
1. The recommended price MUST always be above cost price × (1 + margin_threshold/100)
2. Price changes should be between 2% and 15% of the current price — NEVER more than 15%
3. You MUST stay within the PRICE DRIFT GUARDRAIL — see below
4. Recommend 'maintain' when the price is already near its optimal range or near the guardrail ceiling

INVENTORY-BASED PRICING SIGNALS:
- Under 50 units (low stock): INCREASE price by 5-12% (scarcity pricing)
- 50-150 units (moderate stock): Consider a small increase of 2-6% to optimize margins
- 150-250 units (adequate stock): Evaluate based on margin — if margin is high, small decrease to drive volume
- Over 250 units (excess stock): DECREASE price by 3-10% to accelerate turnover

MARGIN ANALYSIS:
- If current margin is well above the threshold, there is room to decrease price to drive volume
- If current margin is close to the threshold, consider increasing price to protect margin
- The minimum margin threshold for this org is: {margin_threshold_pct}%

PRICE DRIFT GUARDRAIL (MOST IMPORTANT RULE):
- The base/original price of this product is: ₹{base_price}
- Your recommended price MUST be between ₹{min_allowed_price} and ₹{max_allowed_price}
- If the current price is ALREADY above the base price, prefer 'maintain' or a small decrease
- If the current price equals or exceeds the max allowed, you MUST recommend 'decrease' or 'maintain'
- Never recommend pushing the price higher if it is already near or above ₹{max_allowed_price}

CONFIDENCE SCORING:
- 0.85-0.95: Strong signal (competitor data available OR clear inventory signal)
- 0.70-0.84: Moderate signal (good margin data but no competitor info)
- 0.60-0.69: Low signal (limited data available)

All prices are in Indian Rupees (₹). Recommend a specific numeric price, not a range."""),

    ("human", """Analyze this product and recommend an optimal price:

PRODUCT INFORMATION:
- Name: {product_name}
- SKU: {product_sku}
- Category: {category}
- Original / Base Price: ₹{base_price}
- Current Selling Price: ₹{current_price}
- Price vs Base: {price_vs_base}
- Cost Price: ₹{cost_price}
- Current Margin: {current_margin_pct}%
- Inventory: {inventory_count} units
- Minimum Margin Threshold: {margin_threshold_pct}%
- Allowed Price Range: ₹{min_allowed_price} — ₹{max_allowed_price}

{competitor_section}

{org_rules_section}

Recommend a specific optimized price. Explain which factors drove your decision.""")
])


# ─── LLM Setup ───────────────────────────────────────────────────────

def _get_llm():
    """Create the ChatGroq LLM with structured output."""
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.2,
        api_key=settings.GROQ_API_KEY,
    )
    return llm.with_structured_output(PricingRecommendation)


# ─── Helpers ──────────────────────────────────────────────────────────

def _round(value: float) -> Decimal:
    """Round to 2 decimal places."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _build_competitor_section(competitor_prices: List[CompetitorPrice]) -> str:
    """Build the competitor pricing section for the prompt."""
    if not competitor_prices:
        return "COMPETITOR PRICES:\nNo competitor pricing data available. Base your analysis on inventory levels and margins."

    lines = ["COMPETITOR PRICES:"]
    for cp in competitor_prices:
        lines.append(f"- {cp.competitor_name}: ₹{float(cp.price):,.2f}")
    return "\n".join(lines)


def _build_org_rules_section(org_settings: Optional[OrgSettings], category: str) -> str:
    """Build org-specific rules section."""
    if not org_settings:
        return "ORGANIZATION RULES:\nNo specific org-level rules configured."

    lines = ["ORGANIZATION RULES:"]
    lines.append(f"- Auto-execute threshold: {float(org_settings.auto_execute_threshold) * 100:.0f}% confidence")

    if org_settings.margin_floors and isinstance(org_settings.margin_floors, dict):
        floor = org_settings.margin_floors.get(category)
        if floor:
            lines.append(f"- Category '{category}' minimum margin floor: {float(floor) * 100:.0f}%")

    return "\n".join(lines)


# ─── Main Function (Real AI) ─────────────────────────────────────────

def generate_prediction(
    product: Product,
    competitor_prices: Optional[List[CompetitorPrice]] = None,
    org_settings: Optional[OrgSettings] = None,
) -> dict:
    """
    Generate a pricing recommendation using the Groq LLM.

    Args:
        product: The Product ORM object to analyze
        competitor_prices: Optional list of CompetitorPrice records for this product
        org_settings: Optional OrgSettings for the user's organization

    Returns:
        dict with keys: recommended_price, confidence_score, rationale, agent_outputs
    """
    current = float(product.current_price)
    cost = float(product.cost_price)
    # Use base_price as the anchor; fall back to current_price for legacy rows without it
    base = float(product.base_price) if product.base_price else current
    margin_pct = ((current - cost) / current * 100) if current > 0 else 0
    margin_threshold = float(product.margin_threshold) * 100

    # ── Drift guardrail bounds (±25% from base_price) ────────────────
    DRIFT_CAP = 0.25
    min_margin_price = cost * (1 + float(product.margin_threshold))
    max_allowed = round(base * (1 + DRIFT_CAP), 2)
    min_allowed = round(max(base * (1 - DRIFT_CAP), min_margin_price), 2)

    # Human-readable drift label for the prompt
    drift_pct = ((current - base) / base * 100) if base > 0 else 0
    if drift_pct > 0:
        price_vs_base = f"+{drift_pct:.1f}% above base (drifting UP — caution on further increases)"
    elif drift_pct < 0:
        price_vs_base = f"{drift_pct:.1f}% below base (drifting DOWN — room to increase)"
    else:
        price_vs_base = "At base price (no drift yet)"

    try:
        structured_llm = _get_llm()

        # Build prompt inputs
        prompt_inputs = {
            "product_name": product.name,
            "product_sku": product.sku,
            "category": product.category,
            "base_price": f"{base:,.2f}",
            "current_price": f"{current:,.2f}",
            "price_vs_base": price_vs_base,
            "cost_price": f"{cost:,.2f}",
            "current_margin_pct": f"{margin_pct:.1f}",
            "inventory_count": product.inventory_count,
            "margin_threshold_pct": f"{margin_threshold:.0f}",
            "max_allowed_price": f"{max_allowed:,.2f}",
            "min_allowed_price": f"{min_allowed:,.2f}",
            "competitor_section": _build_competitor_section(competitor_prices or []),
            "org_rules_section": _build_org_rules_section(org_settings, product.category),
        }

        # Invoke the chain
        chain = PRICING_PROMPT | structured_llm
        result: PricingRecommendation = chain.invoke(prompt_inputs)

        # ── Post-LLM validation: enforce drift cap hard ───────────────
        recommended = result.recommended_price

        if recommended > max_allowed:
            logger.warning(
                f"LLM recommended ₹{recommended:.2f} exceeds drift ceiling ₹{max_allowed:.2f} "
                f"for {product.name}. Capping."
            )
            recommended = max_allowed

        if recommended < min_allowed:
            logger.warning(
                f"LLM recommended ₹{recommended:.2f} below drift floor ₹{min_allowed:.2f} "
                f"for {product.name}. Flooring."
            )
            recommended = min_allowed

        recommended_price = _round(recommended)
        confidence = _round(max(0.60, min(0.95, result.confidence_score)))

        agent_outputs = {
            "model": "llama-3.1-8b-instant",
            "provider": "groq",
            "factors_analyzed": result.factors_analyzed,
            "direction": result.direction,
            "competitor_data_available": bool(competitor_prices),
            "competitor_count": len(competitor_prices) if competitor_prices else 0,
            "base_price": base,
            "max_allowed_price": max_allowed,
            "min_allowed_price": min_allowed,
            "drift_pct_from_base": round(drift_pct, 2),
            "price_capped": recommended != result.recommended_price,
        }

        logger.info(
            f"AI prediction for {product.name}: "
            f"₹{current:,.0f} → ₹{float(recommended_price):,.0f} "
            f"({result.direction}, conf={float(confidence):.0%}, "
            f"base=₹{base:,.0f}, drift={drift_pct:+.1f}%)"
        )

        return {
            "recommended_price": recommended_price,
            "confidence_score": confidence,
            "rationale": result.rationale,
            "agent_outputs": agent_outputs,
        }

    except Exception as e:
        logger.error(f"LLM call failed for {product.name}: {e}. Falling back to heuristic.")
        return _fallback_prediction(product, base, max_allowed, min_allowed)


# ─── Fallback (Heuristic) ────────────────────────────────────────────

def _fallback_prediction(
    product: Product,
    base: float,
    max_allowed: float,
    min_allowed: float,
) -> dict:
    """
    Simple heuristic fallback when the LLM is unavailable.
    Now also respects the ±25% drift guardrail from base_price.
    """
    current = float(product.current_price)
    inventory = product.inventory_count

    if inventory < 50:
        pct_change = random.uniform(0.05, 0.12)
        direction = "increase"
        reason = f"Low inventory ({inventory} units) — scarcity pricing applied"
    elif inventory > 250:
        pct_change = random.uniform(0.03, 0.10)
        direction = "decrease"
        reason = f"High inventory ({inventory} units) — clearance discount applied"
    else:
        pct_change = random.uniform(0.02, 0.08)
        direction = random.choice(["increase", "decrease"])
        reason = f"Moderate inventory — {direction} of ~{pct_change*100:.1f}% applied"

    if direction == "increase":
        recommended = current * (1 + pct_change)
    else:
        recommended = current * (1 - pct_change)

    # Apply the same ±25% drift guardrail as the main AI path
    recommended = max(min_allowed, min(max_allowed, recommended))

    recommended_price = _round(recommended)
    confidence = _round(random.uniform(0.60, 0.75))  # Lower confidence for fallback

    drift_pct = ((current - base) / base * 100) if base > 0 else 0

    return {
        "recommended_price": recommended_price,
        "confidence_score": confidence,
        "rationale": f"[Fallback heuristic] {reason}. Category: {product.category}.",
        "agent_outputs": {
            "model": "heuristic-fallback",
            "provider": "local",
            "factors_analyzed": ["inventory_level", "cost_margin"],
            "direction": direction,
            "competitor_data_available": False,
            "base_price": base,
            "max_allowed_price": max_allowed,
            "min_allowed_price": min_allowed,
            "drift_pct_from_base": round(drift_pct, 2),
            "fallback_reason": "LLM unavailable",
        },
    }
