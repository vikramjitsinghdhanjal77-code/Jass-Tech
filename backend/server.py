from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
import certifi
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError
import uuid
import os
import logging


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(
    mongo_url,
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=20000,
)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production-please")
JWT_ALGO = "HS256"
JWT_EXP_HOURS = 24 * 7

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

app = FastAPI()
api_router = APIRouter(prefix="/api")


# ---------------- Models ----------------

class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class ForgotPassword(BaseModel):
    username: str
    new_password: str


class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str
    description: str
    price: float
    stock: int = 0
    image: str = ""
    badge: Optional[str] = None
    specs: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProductCreate(BaseModel):
    name: str
    category: str
    description: str
    price: float
    stock: int = 0
    image: str = ""
    badge: Optional[str] = None
    specs: List[str] = []


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    image: Optional[str] = None
    badge: Optional[str] = None
    specs: Optional[List[str]] = None


class OrderItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int
    image: str = ""


class OrderCreate(BaseModel):
    items: List[OrderItem]
    shipping: dict
    payment_method: str = "cod"
    notes: Optional[str] = ""


# ---------------- Helpers ----------------

def create_token(user_id: str, username: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXP_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


async def current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def admin_user(user: dict = Depends(current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def order_total(items: List[OrderItem]) -> float:
    return round(sum(i.price * i.quantity for i in items), 2)


# ---------------- Auth ----------------

@api_router.post("/register")
async def register(payload: UserCreate):
    existing = await db.users.find_one({"username": payload.username})
    if existing:
        return {"success": False, "message": "Username already exists"}

    user_id = str(uuid.uuid4())
    doc = {
        "id": user_id,
        "username": payload.username,
        "password_hash": hash_password(payload.password),
        "email": payload.email or "",
        "full_name": payload.full_name or "",
        "phone": "",
        "address": "",
        "city": "",
        "state": "",
        "zip_code": "",
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": None,
    }
    await db.users.insert_one(doc)
    token = create_token(user_id, payload.username, "user")
    return {
        "success": True,
        "message": "Registered successfully",
        "token": token,
        "username": payload.username,
        "role": "user",
    }


@api_router.post("/login")
async def login(credentials: LoginRequest):
    user = await db.users.find_one({"username": credentials.username})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        return {"success": False, "message": "Invalid username or password"}

    await db.users.update_one(
        {"username": credentials.username},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}},
    )
    token = create_token(user["id"], user["username"], user.get("role", "user"))
    return {
        "success": True,
        "message": "Login successful",
        "token": token,
        "username": user["username"],
        "role": user.get("role", "user"),
    }


@api_router.post("/forgot-password")
async def forgot_password(payload: ForgotPassword):
    user = await db.users.find_one({"username": payload.username})
    if not user:
        return {"success": False, "message": "No user with that username"}
    if len(payload.new_password) < 6:
        return {"success": False, "message": "Password must be at least 6 characters"}
    await db.users.update_one(
        {"username": payload.username},
        {"$set": {"password_hash": hash_password(payload.new_password)}},
    )
    return {"success": True, "message": "Password reset successful. Please log in."}


@api_router.get("/me")
async def get_me(user: dict = Depends(current_user)):
    return {"success": True, "user": user}


@api_router.put("/me")
async def update_me(payload: UserUpdate, user: dict = Depends(current_user)):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if update:
        await db.users.update_one({"id": user["id"]}, {"$set": update})
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return {"success": True, "user": fresh}


@api_router.post("/me/change-password")
async def change_password(payload: PasswordChange, user: dict = Depends(current_user)):
    full = await db.users.find_one({"id": user["id"]})
    if not verify_password(payload.current_password, full["password_hash"]):
        return {"success": False, "message": "Current password is incorrect"}
    if len(payload.new_password) < 6:
        return {"success": False, "message": "Password must be at least 6 characters"}
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_password(payload.new_password)}},
    )
    return {"success": True, "message": "Password changed"}


# ---------------- Products ----------------

@api_router.get("/products")
async def list_products(category: Optional[str] = None, search: Optional[str] = None):
    query = {}
    if category and category != "all":
        query["category"] = category
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"category": {"$regex": search, "$options": "i"}},
        ]
    products = await db.products.find(query, {"_id": 0}).to_list(500)
    return {"success": True, "products": products}


@api_router.get("/products/{product_id}")
async def get_product(product_id: str):
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True, "product": product}


@api_router.post("/products")
async def create_product(payload: ProductCreate, _: dict = Depends(admin_user)):
    product = Product(**payload.model_dump())
    doc = product.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.products.insert_one(doc)
    doc.pop("_id", None)
    return {"success": True, "product": doc}


@api_router.put("/products/{product_id}")
async def update_product(product_id: str, payload: ProductUpdate, _: dict = Depends(admin_user)):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update:
        return {"success": False, "message": "Nothing to update"}
    result = await db.products.update_one({"id": product_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    fresh = await db.products.find_one({"id": product_id}, {"_id": 0})
    return {"success": True, "product": fresh}


@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, _: dict = Depends(admin_user)):
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True}


# ---------------- Orders ----------------

@api_router.post("/orders")
async def create_order(payload: OrderCreate, user: dict = Depends(current_user)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="No items in order")

    # Validate stock and decrement atomically (best-effort)
    for item in payload.items:
        prod = await db.products.find_one({"id": item.product_id})
        if not prod:
            raise HTTPException(status_code=400, detail=f"Product {item.name} no longer exists")
        if prod.get("stock", 0) < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {prod['name']} (only {prod.get('stock', 0)} left)",
            )

    for item in payload.items:
        await db.products.update_one(
            {"id": item.product_id},
            {"$inc": {"stock": -item.quantity}},
        )

    order_id = str(uuid.uuid4())
    order_number = f"JT-{datetime.now().strftime('%Y%m%d')}-{order_id[:6].upper()}"
    total = order_total(payload.items)
    tax = round(total * 0.10, 2)

    doc = {
        "id": order_id,
        "order_number": order_number,
        "user_id": user["id"],
        "username": user["username"],
        "items": [i.model_dump() for i in payload.items],
        "shipping": payload.shipping,
        "payment_method": payload.payment_method,
        "notes": payload.notes or "",
        "subtotal": total,
        "tax": tax,
        "total": round(total + tax, 2),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.orders.insert_one(doc)
    doc.pop("_id", None)
    return {"success": True, "order": doc}


@api_router.get("/orders/mine")
async def my_orders(user: dict = Depends(current_user)):
    orders = (
        await db.orders.find({"user_id": user["id"]}, {"_id": 0})
        .sort("created_at", -1)
        .to_list(200)
    )
    return {"success": True, "orders": orders}


@api_router.get("/admin/orders")
async def all_orders(_: dict = Depends(admin_user)):
    orders = await db.orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"success": True, "orders": orders}


@api_router.put("/admin/orders/{order_id}/status")
async def update_order_status(order_id: str, body: dict, _: dict = Depends(admin_user)):
    status = body.get("status")
    if status not in {"pending", "shipped", "delivered", "cancelled"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    await db.orders.update_one({"id": order_id}, {"$set": {"status": status}})
    return {"success": True}


@api_router.get("/admin/stats")
async def admin_stats(_: dict = Depends(admin_user)):
    orders = await db.orders.find({}, {"_id": 0}).to_list(5000)
    revenue = sum(o.get("total", 0) for o in orders if o.get("status") != "cancelled")
    products = await db.products.count_documents({})
    users = await db.users.count_documents({"role": {"$ne": "admin"}})
    low_stock = await db.products.count_documents({"stock": {"$lt": 5}})
    by_status = {}
    for o in orders:
        s = o.get("status", "pending")
        by_status[s] = by_status.get(s, 0) + 1
    return {
        "success": True,
        "revenue": round(revenue, 2),
        "orders": len(orders),
        "products": products,
        "users": users,
        "low_stock": low_stock,
        "by_status": by_status,
    }


# ---------------- Bootstrap ----------------

SEED_PRODUCTS = [
    {
        "name": "NVIDIA GeForce RTX 4090",
        "category": "gpu",
        "description": "24GB GDDR6X, 16384 CUDA Cores, Ray Tracing, DLSS 3.0",
        "price": 294999,
        "stock": 8,
        "image": "https://images.unsplash.com/photo-1591488320449-011701bb6704?w=600&q=80",
        "badge": "Top Seller",
        "specs": ["Boost Clock: 2.52 GHz", "Memory: 24GB GDDR6X", "Power: 450W TDP"],
    },
    {
        "name": "AMD Ryzen 9 7950X",
        "category": "cpu",
        "description": "16 Cores, 32 Threads, 5.7 GHz Max Boost, AM5 Socket",
        "price": 51507,
        "stock": 15,
        "image": "https://images.unsplash.com/photo-1555617981-dac3880eac6e?w=600&q=80",
        "badge": "Best Seller",
        "specs": ["Base Clock: 4.5 GHz", "Cache: 80MB", "TDP: 170W"],
    },
    {
        "name": "Corsair Vengeance DDR5 32GB",
        "category": "ram",
        "description": "6000MHz, RGB Lighting, Dual Channel Kit (2x16GB)",
        "price": 47199,
        "stock": 22,
        "image": "https://images.unsplash.com/photo-1592664474505-c2d3322ccc4f?w=600&q=80",
        "specs": ["Speed: 6000MHz", "Latency: CL36", "RGB: Yes"],
    },
    {
        "name": "ASUS ROG Strix B850-E",
        "category": "motherboard",
        "description": "AMD AM5, PCIe 5.0, DDR5, WiFi 6E, RGB",
        "price": 47000,
        "stock": 10,
        "image": "https://images.unsplash.com/photo-1587202372634-32705e3bf49c?w=600&q=80",
        "specs": ["Socket: AM5", "Memory: DDR5 up to 6400MHz", "WiFi: 6E"],
    },
    {
        "name": "Samsung 990 PRO 2TB",
        "category": "storage",
        "description": "NVMe PCIe 4.0, 7450MB/s Read, 6900MB/s Write",
        "price": 12500,
        "stock": 30,
        "image": "https://images.unsplash.com/photo-1601737487795-dab272f52420?w=600&q=80",
        "badge": "New",
        "specs": ["Read: 7450 MB/s", "Write: 6900 MB/s", "Interface: PCIe 4.0"],
    },
    {
        "name": "Consistent 990 PRO 7TB",
        "category": "storage",
        "description": "NVMe PCIe 4.0, 7450MB/s Read, 6900MB/s Write",
        "price": 37789,
        "stock": 5,
        "image": "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=600&q=80",
        "badge": "New",
        "specs": ["Read: 7450 MB/s", "Write: 6900 MB/s", "Interface: PCIe 4.0"],
    },
    {
        "name": "Corsair RM1000x 1000W",
        "category": "psu",
        "description": "80+ Gold, Fully Modular, Silent Fan, 10 Year Warranty",
        "price": 17900,
        "stock": 12,
        "image": "https://images.unsplash.com/photo-1587831990711-23ca6441447b?w=600&q=80",
        "specs": ["Wattage: 1000W", "Efficiency: 80+ Gold", "Modular: Fully"],
    },
]


@app.on_event("startup")
async def seed_data():
    # Ensure admin
    admin = await db.users.find_one({"username": ADMIN_USERNAME})
    if not admin:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "username": ADMIN_USERNAME,
            "password_hash": hash_password(ADMIN_PASSWORD),
            "email": "admin@jasstech.local",
            "full_name": "Site Administrator",
            "phone": "",
            "address": "",
            "city": "",
            "state": "",
            "zip_code": "",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": None,
        })
        logger.info("Seeded admin user '%s'", ADMIN_USERNAME)
    else:
        # Promote to admin role if missing
        if admin.get("role") != "admin":
            await db.users.update_one({"username": ADMIN_USERNAME}, {"$set": {"role": "admin"}})

    # Seed products if empty
    count = await db.products.count_documents({})
    if count == 0:
        for p in SEED_PRODUCTS:
            doc = Product(**p).model_dump()
            doc["created_at"] = doc["created_at"].isoformat()
            await db.products.insert_one(doc)
        logger.info("Seeded %d products", len(SEED_PRODUCTS))


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


# Mount router and CORS
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)
