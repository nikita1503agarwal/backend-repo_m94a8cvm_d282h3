"""
Database Schemas for Food Delivery App

Each Pydantic model represents a collection in MongoDB. The collection name is the
lowercased class name by convention in this project.

Collections:
- restaurant
- menuitem
- cart
- order
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class Restaurant(BaseModel):
    name: str = Field(..., description="Restaurant name")
    cuisine: str = Field(..., description="Cuisine type, e.g., Italian, Indian")
    image_url: Optional[str] = Field(None, description="Cover image URL")
    rating: float = Field(4.5, ge=0, le=5, description="Average rating")
    delivery_time_min: int = Field(30, ge=5, le=120, description="Estimated delivery time in minutes")
    delivery_fee: float = Field(2.99, ge=0, description="Delivery fee in dollars")
    address: Optional[str] = Field(None, description="Restaurant address")


class MenuItem(BaseModel):
    restaurant_id: str = Field(..., description="Linked restaurant id as string")
    name: str = Field(..., description="Dish name")
    description: Optional[str] = Field(None, description="Dish description")
    price: float = Field(..., ge=0, description="Price in dollars")
    image_url: Optional[str] = Field(None, description="Dish image URL")
    is_veg: bool = Field(False, description="Vegetarian dish flag")
    spicy_level: int = Field(0, ge=0, le=3, description="Spice level 0-3")


class CartItem(BaseModel):
    restaurant_id: str
    menu_item_id: str
    name: str
    price: float
    quantity: int = Field(1, ge=1)


class Cart(BaseModel):
    user_id: str
    items: List[CartItem] = []


class Order(BaseModel):
    user_id: str
    restaurant_id: str
    items: List[CartItem]
    total: float
    status: str = Field("placed", description="placed | preparing | on-the-way | delivered")
    address: str
