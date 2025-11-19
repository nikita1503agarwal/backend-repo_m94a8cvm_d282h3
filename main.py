import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Restaurant, MenuItem, CartItem, Cart, Order

app = FastAPI(title="Food Delivery API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Food Delivery API is running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    return response


# ---------- Helper ----------

def to_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id format")


# ---------- Seed Sample Data ----------

@app.post("/api/seed", response_model=dict)
async def seed_sample_data():
    if db["restaurant"].count_documents({}) > 0:
        return {"status": "ok", "message": "Data already exists"}

    r1 = Restaurant(
        name="Sunset Pizzeria",
        cuisine="Italian",
        image_url="https://images.unsplash.com/photo-1604382354936-07c5d9983bd3",
        rating=4.6,
        delivery_time_min=30,
        delivery_fee=2.99,
        address="123 Main St"
    )
    r2 = Restaurant(
        name="Spice Garden",
        cuisine="Indian",
        image_url="https://images.unsplash.com/photo-1544025162-d76694265947",
        rating=4.7,
        delivery_time_min=40,
        delivery_fee=3.49,
        address="55 Curry Ave"
    )

    r1_id = create_document("restaurant", r1)
    r2_id = create_document("restaurant", r2)

    items = [
        MenuItem(restaurant_id=r1_id, name="Margherita Pizza", description="Classic with fresh basil", price=12.5, image_url="https://images.unsplash.com/photo-1548365328-9f547fb09556", is_veg=True),
        MenuItem(restaurant_id=r1_id, name="Pepperoni Pizza", description="Spicy pepperoni, mozzarella", price=14.0, image_url="https://images.unsplash.com/photo-1601924582971-b6e100ca9b3a", is_veg=False),
        MenuItem(restaurant_id=r2_id, name="Butter Chicken", description="Creamy and rich", price=13.75, image_url="https://images.unsplash.com/photo-1567188040759-fb8a883dc6d8", is_veg=False, spicy_level=1),
        MenuItem(restaurant_id=r2_id, name="Paneer Tikka", description="Grilled cottage cheese", price=11.0, image_url="https://images.unsplash.com/photo-1604908176997-43162d71db00", is_veg=True, spicy_level=2),
    ]
    for it in items:
        create_document("menuitem", it)

    return {"status": "ok", "message": "Seeded"}


# ---------- Restaurants ----------

@app.post("/api/restaurants", response_model=dict)
async def create_restaurant(restaurant: Restaurant):
    inserted_id = create_document("restaurant", restaurant)
    return {"id": inserted_id}


@app.get("/api/restaurants", response_model=List[dict])
async def list_restaurants():
    docs = get_documents("restaurant", {}, limit=50)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs


# ---------- Menu Items ----------

@app.post("/api/menu", response_model=dict)
async def create_menu_item(item: MenuItem):
    rid = to_object_id(item.restaurant_id)
    if not db["restaurant"].find_one({"_id": rid}):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    inserted_id = create_document("menuitem", item)
    return {"id": inserted_id}


@app.get("/api/menu/{restaurant_id}", response_model=List[dict])
async def get_menu_for_restaurant(restaurant_id: str):
    to_object_id(restaurant_id)
    docs = list(db["menuitem"].find({"restaurant_id": restaurant_id}))
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs


# ---------- Cart (simple per-user) ----------

@app.get("/api/cart/{user_id}", response_model=dict)
async def get_cart(user_id: str):
    cart = db["cart"].find_one({"user_id": user_id})
    if not cart:
        cart = {"user_id": user_id, "items": [], "created_at": None, "updated_at": None}
        db["cart"].insert_one(cart)
    cart["id"] = str(cart.pop("_id"))
    return cart


@app.post("/api/cart/{user_id}/add", response_model=dict)
async def add_to_cart(user_id: str, item: CartItem):
    if item.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")
    mid = to_object_id(item.menu_item_id)
    mi = db["menuitem"].find_one({"_id": mid})
    if not mi:
        raise HTTPException(status_code=404, detail="Menu item not found")

    db["cart"].update_one(
        {"user_id": user_id},
        {"$setOnInsert": {"user_id": user_id},
         "$push": {"items": item.model_dump()}},
        upsert=True
    )
    return await get_cart(user_id)


@app.post("/api/cart/{user_id}/clear", response_model=dict)
async def clear_cart(user_id: str):
    db["cart"].update_one({"user_id": user_id}, {"$set": {"items": []}})
    return await get_cart(user_id)


# ---------- Orders ----------

@app.post("/api/orders", response_model=dict)
async def place_order(order: Order):
    to_object_id(order.restaurant_id)
    inserted_id = create_document("order", order)
    db["cart"].update_one({"user_id": order.user_id}, {"$set": {"items": []}})
    return {"id": inserted_id, "status": "placed"}


@app.get("/api/orders/{user_id}", response_model=List[dict])
async def list_orders(user_id: str):
    docs = list(db["order"].find({"user_id": user_id}).sort("created_at", -1))
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
