from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User, UserRole
from app.models.product import Product
from app.models.competitor_price import CompetitorPrice
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.competitor_agent import scrape_competitor_prices

router = APIRouter(
    prefix="/api/products",
    tags=["Products"])

@router.get("/", response_model=List[ProductResponse])
def get_products(
    db : Session = Depends(get_db),
    user : User = Depends(get_current_user)):

    '''Get all the products for the user from his organization'''

    products = db.query(Product).filter(Product.org_id == user.org_id).all()

    return [ProductResponse(
        id=str(p.id), name=p.name, sku=p.sku, category=p.category,
        current_price=float(p.current_price), cost_price=float(p.cost_price),
        inventory_count=p.inventory_count, margin_threshold=float(p.margin_threshold),
        created_at=p.created_at
    ) for p in products]

@router.post("/", response_model=ProductResponse)
def create_product(
    product : ProductCreate,
    db : Session = Depends(get_db),
    user : User = Depends(get_current_user)):

    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can create products")

    new_product = Product(
        org_id = user.org_id,
        name = product.name,
        sku = product.sku,
        category = product.category,
        current_price = product.current_price,
        cost_price = product.cost_price,
        inventory_count = product.inventory_count,
        margin_threshold = product.margin_threshold
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return ProductResponse(
        id=str(new_product.id), name=new_product.name, sku=new_product.sku,
        category=new_product.category, current_price=float(new_product.current_price),
        cost_price=float(new_product.cost_price), inventory_count=new_product.inventory_count,
        margin_threshold=float(new_product.margin_threshold), created_at=new_product.created_at
    )

@router.get("/{product_id}",response_model = ProductResponse)
def get_product(
    product_id : str,
    db :Session = Depends(get_db),
    user : User = Depends(get_current_user)):

    product = db.query(Product).filter(Product.id == product_id, Product.org_id == user.org_id).first()

    if not product:
       raise HTTPException(status_code=404, detail="Product not found")

    return  ProductResponse(
        id=str(product.id), name=product.name, sku=product.sku,
        category=product.category, current_price=float(product.current_price),
        cost_price=float(product.cost_price), inventory_count=product.inventory_count,
        margin_threshold=float(product.margin_threshold), created_at=product.created_at
    )

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    updates: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Update a product. Admin only."""
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can update products")
    
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.org_id == user.org_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Only update fields that were provided
    update_data = updates.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    
    db.commit()
    db.refresh(product)
    
    return ProductResponse(
        id=str(product.id), name=product.name, sku=product.sku,
        category=product.category, current_price=float(product.current_price),
        cost_price=float(product.cost_price), inventory_count=product.inventory_count,
        margin_threshold=float(product.margin_threshold), created_at=product.created_at
    )

    

@router.delete("/{product_id}")
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Delete a product. Admin only."""
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can delete products")
    
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.org_id == user.org_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return {"detail": "Product deleted"}


@router.post("/{product_id}/scrape-competitors")
def scrape_and_save_competitors(
    product_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Trigger the Competitor Agent to find live prices on the web. Admin only."""
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can scrape competitors")
    
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.org_id == user.org_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 1. Trigger Agent
    extracted_prices = scrape_competitor_prices(product.name)
    
    if not extracted_prices:
        return {"detail": "Agent could not find any clear competitor prices on the web."}

    # 2. Save to database
    saved_records = []
    for comp in extracted_prices:
        new_comp = CompetitorPrice(
            product_id=product.id,
            competitor_name=comp["competitor_name"],
            price=comp["price"]
        )
        db.add(new_comp)
        saved_records.append(new_comp)
        
    db.commit()
    
    return {
        "detail": f"Agent successfully found {len(saved_records)} competitor prices.",
        "data": extracted_prices
    }