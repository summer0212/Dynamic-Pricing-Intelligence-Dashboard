from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class ProductCreate(BaseModel):
    name : str
    sku : str
    category : str
    current_price : float
    cost_price : float
    inventory_count : int = 0
    margin_threshold : float = 0.15


class ProductUpdate(BaseModel):
    name : Optional[str] = None
    current_price : Optional[float] = None
    cost_price : Optional[float] = None
    inventory_count : Optional[int] = None
    margin_threshold : Optional[float] = None

class ProductResponse(BaseModel):
    id : str
    name : str
    sku : str
    category : str
    current_price : float
    cost_price : float
    inventory_count : int
    margin_threshold : float
    created_at : datetime

    class Config:
        from_attributes = True
