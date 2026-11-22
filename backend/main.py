import os
import io
import json
import time
import uuid
import secrets
import base64
from datetime import datetime, timezone
from typing import Optional

import jwt
import libsql_experimental as libsql
from PIL import Image
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import (
    FastAPI, HTTPException, Depends, Header,
    UploadFile, File
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, EmailStr


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

APP_NAME = "Sai Creation API"

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_HOURS = int(os.getenv("JWT_HOURS", "12"))
JWT_ALGORITHM = "HS256"

SETUP_SECRET = os.getenv("SETUP_SECRET", "")

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")

FRONTEND_ORIGINS = [
    x.strip()
    for x in os.getenv(
        "FRONTEND_ORIGINS",
        "https://rrashmi-creations.github.io"
    ).split(",")
    if x.strip()
]

password_hasher = PasswordHasher()

app = FastAPI(
    title=APP_NAME,
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def db():
    if not TURSO_DATABASE_URL or not TURSO_AUTH_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Turso database credentials are missing."
        )

    # Correct connection method for libsql-experimental
    return libsql.connect(
        TURSO_DATABASE_URL,
        auth_token=TURSO_AUTH_TOKEN
    )


def execute(conn, sql, params=()):
    return conn.execute(sql, list(params))


def fetch_all(conn, sql, params=()):
    cursor = execute(conn, sql, params)

    if not cursor.description:
        return []

    columns = [column[0] for column in cursor.description]

    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def fetch_one(conn, sql, params=()):
    result = fetch_all(conn, sql, params)
    return result[0] if result else None


def write(conn, sql, params=()):
    execute(conn, sql, params)
    conn.commit()


def now():
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

def init_db():
    conn = db()

    try:
        statements = [

            """
            CREATE TABLE IF NOT EXISTS admins (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                offer_price REAL NOT NULL DEFAULT 0,
                stock INTEGER NOT NULL DEFAULT 0,
                sizes TEXT DEFAULT '',
                fabric TEXT DEFAULT '',
                image_url TEXT DEFAULT '',
                description TEXT DEFAULT '',
                is_new INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS product_images (
                id TEXT PRIMARY KEY,
                product_id TEXT NOT NULL,
                image_data BLOB NOT NULL,
                content_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(product_id)
                    REFERENCES products(id)
                    ON DELETE CASCADE
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                order_number TEXT UNIQUE NOT NULL,
                customer_name TEXT DEFAULT '',
                customer_phone TEXT DEFAULT '',
                items_json TEXT NOT NULL,
                total REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL
            )
            """,

            """
            CREATE INDEX IF NOT EXISTS idx_products_category
            ON products(category)
            """,

            """
            CREATE INDEX IF NOT EXISTS idx_orders_created
            ON orders(created_at)
            """,

            """
            CREATE INDEX IF NOT EXISTS idx_images_product
            ON product_images(product_id)
            """
        ]

        for statement in statements:
            write(conn, statement)

        defaults = {
            "store_name": "Sai Creation",
            "tagline": "Fashion Beyond Boundaries",
            "hero_heading": "Style. Grace. Elegance.",
            "hero_sub": "Discover ethnic fashion for every moment.",
            "hero_button": "Explore collection",
            "whatsapp": "",
            "phone": "",
            "retail_whatsapp": "",
            "wholesale_whatsapp": "",
            "support_whatsapp": "",
            "email": "",
            "instagram": "",
            "facebook": "",
            "youtube": "",
            "hero_image": "",
            "page_size": 8
        }

        for key, value in defaults.items():
            write(
                conn,
                """
                INSERT OR IGNORE INTO settings
                (key, value, updated_at)
                VALUES (?, ?, ?)
                """,
                (key, json.dumps(value), now())
            )

        # No demo products are inserted.

    finally:
        conn.close()


@app.on_event("startup")
def startup():
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        init_db()


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class SetupIn(BaseModel):
    setup_secret: str
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    category: str = Field(min_length=1, max_length=80)
    price: float = Field(ge=0)
    offer_price: float = Field(default=0, ge=0)
    stock: int = Field(default=0, ge=0)
    sizes: str = ""
    fabric: str = ""
    image_url: str = ""
    description: str = ""
    is_new: bool = False


class SettingsIn(BaseModel):
    store_name: str = "Sai Creation"
    tagline: str = ""
    hero_heading: str = ""
    hero_sub: str = ""
    hero_button: str = "Explore collection"
    whatsapp: str = ""
    phone: str = ""
    retail_whatsapp: str = ""
    wholesale_whatsapp: str = ""
    support_whatsapp: str = ""
    email: str = ""
    instagram: str = ""
    facebook: str = ""
    youtube: str = ""
    hero_image: str = ""
    page_size: int = Field(default=8, ge=4, le=48)


class OrderItem(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, le=20)


class OrderIn(BaseModel):
    customer_name: str = "Website customer"
    customer_phone: str = ""
    items: list[OrderItem] = Field(min_length=1, max_length=30)


class OrderStatusIn(BaseModel):
    status: str


# --------------------------------------------------
# ADMIN AUTHENTICATION
# --------------------------------------------------

def admin_user(
    authorization: Optional[str] = Header(default=None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Admin login required.")

    try:
        token = authorization[7:]

        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

        if payload.get("role") != "admin":
            raise ValueError()

        return payload

    except Exception:
        raise HTTPException(
            401,
            "Admin session expired. Please log in again."
        )


@app.post("/api/auth/setup")
def setup_admin(data: SetupIn):

    if not SETUP_SECRET or not secrets.compare_digest(
        data.setup_secret,
        SETUP_SECRET
    ):
        raise HTTPException(403, "Invalid setup secret.")

    conn = db()

    try:
        existing = fetch_one(
            conn,
            "SELECT id FROM admins LIMIT 1"
        )

        if existing:
            raise HTTPException(
                409,
                "Admin already exists."
            )

        admin_id = str(uuid.uuid4())

        write(
            conn,
            """
            INSERT INTO admins
            (id, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                admin_id,
                data.email.lower(),
                password_hasher.hash(data.password),
                now()
            )
        )

        return {
            "message": "Admin account created successfully."
        }

    finally:
        conn.close()


@app.post("/api/auth/login")
def login(data: LoginIn):

    if not JWT_SECRET or len(JWT_SECRET) < 32:
        raise HTTPException(
            503,
            "JWT_SECRET must contain at least 32 characters."
        )

    conn = db()

    try:
        admin = fetch_one(
            conn,
            "SELECT * FROM admins WHERE email = ?",
            (data.email.lower(),)
        )

    finally:
        conn.close()

    if not admin:
        raise HTTPException(401, "Invalid email or password.")

    try:
        password_hasher.verify(
            admin["password_hash"],
            data.password
        )

    except VerifyMismatchError:
        raise HTTPException(401, "Invalid email or password.")

    token = jwt.encode(
        {
            "sub": admin["id"],
            "role": "admin",
            "exp": int(time.time()) + JWT_HOURS * 3600
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": JWT_HOURS * 3600
    }


# --------------------------------------------------
# HEALTH AND PUBLIC INFORMATION
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "service": APP_NAME,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "time": now()
    }


# --------------------------------------------------
# PUBLIC PRODUCTS
# --------------------------------------------------

def clean_product(product):
    if product:
        product["is_new"] = bool(product.get("is_new", 0))
    return product


@app.get("/api/products")
def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None
):
    conn = db()

    try:
        if category and category != "All":
            products = fetch_all(
                conn,
                """
                SELECT * FROM products
                WHERE category = ?
                ORDER BY created_at DESC
                """,
                (category,)
            )
        else:
            products = fetch_all(
                conn,
                "SELECT * FROM products ORDER BY created_at DESC"
            )

        for product in products:
            product["is_new"] = bool(product.get("is_new", 0))

    finally:
        conn.close()

    if search:
        term = search.lower()

        products = [
            p for p in products
            if term in (
                p["name"] + " " +
                p["category"] + " " +
                p.get("description", "")
            ).lower()
        ]

    return products


@app.get("/api/products/{product_id}")
def get_product(product_id: str):

    conn = db()

    try:
        product = fetch_one(
            conn,
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        )

        if not product:
            raise HTTPException(404, "Product not found.")

        product["is_new"] = bool(product.get("is_new", 0))

        return product

    finally:
        conn.close()


# --------------------------------------------------
# ADMIN PRODUCT MANAGEMENT
# --------------------------------------------------

@app.post("/api/admin/products")
def create_product(
    data: ProductIn,
    _=Depends(admin_user)
):

    product_id = str(uuid.uuid4())
    timestamp = now()

    conn = db()

    try:
        write(
            conn,
            """
            INSERT INTO products
            (
                id, name, category, price, offer_price,
                stock, sizes, fabric, image_url,
                description, is_new, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                data.name,
                data.category,
                data.price,
                data.offer_price,
                data.stock,
                data.sizes,
                data.fabric,
                data.image_url,
                data.description,
                int(data.is_new),
                timestamp,
                timestamp
            )
        )

        product = fetch_one(
            conn,
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        )

        return clean_product(product)

    finally:
        conn.close()


@app.put("/api/admin/products/{product_id}")
def update_product(
    product_id: str,
    data: ProductIn,
    _=Depends(admin_user)
):

    conn = db()

    try:
        existing = fetch_one(
            conn,
            "SELECT id FROM products WHERE id = ?",
            (product_id,)
        )

        if not existing:
            raise HTTPException(404, "Product not found.")

        write(
            conn,
            """
            UPDATE products SET
                name = ?,
                category = ?,
                price = ?,
                offer_price = ?,
                stock = ?,
                sizes = ?,
                fabric = ?,
                image_url = ?,
                description = ?,
                is_new = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                data.name,
                data.category,
                data.price,
                data.offer_price,
                data.stock,
                data.sizes,
                data.fabric,
                data.image_url,
                data.description,
                int(data.is_new),
                now(),
                product_id
            )
        )

        product = fetch_one(
            conn,
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        )

        return clean_product(product)

    finally:
        conn.close()


@app.delete("/api/admin/products/{product_id}")
def delete_product(
    product_id: str,
    _=Depends(admin_user)
):

    conn = db()

    try:
        existing = fetch_one(
            conn,
            "SELECT id FROM products WHERE id = ?",
            (product_id,)
        )

        if not existing:
            raise HTTPException(404, "Product not found.")

        write(
            conn,
            "DELETE FROM product_images WHERE product_id = ?",
            (product_id,)
        )

        write(
            conn,
            "DELETE FROM products WHERE id = ?",
            (product_id,)
        )

        return {
            "deleted": True,
            "id": product_id
        }

    finally:
        conn.close()


# --------------------------------------------------
# PRODUCT IMAGE STORAGE - TURSO BLOB
# --------------------------------------------------

@app.post("/api/admin/products/{product_id}/images")
async def upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    _=Depends(admin_user)
):

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp"
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            400,
            "Only JPG, PNG and WEBP images are supported."
        )

    raw = await file.read()

    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(
            413,
            "Image must be smaller than 10 MB."
        )

    try:
        image = Image.open(io.BytesIO(raw))
        image = image.convert("RGB")
        image.thumbnail((1400, 1400))

        output = io.BytesIO()
        image.save(
            output,
            format="JPEG",
            quality=82,
            optimize=True
        )

        image_bytes = output.getvalue()

    except Exception:
        raise HTTPException(400, "Invalid image file.")

    conn = db()

    try:
        product = fetch_one(
            conn,
            "SELECT id FROM products WHERE id = ?",
            (product_id,)
        )

        if not product:
            raise HTTPException(404, "Product not found.")

        image_id = str(uuid.uuid4())

        write(
            conn,
            """
            INSERT INTO product_images
            (id, product_id, image_data, content_type, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                image_id,
                product_id,
                image_bytes,
                "image/jpeg",
                now()
            )
        )

        return {
            "id": image_id,
            "product_id": product_id,
            "url": f"/api/product-images/{image_id}"
        }

    finally:
        conn.close()


@app.get("/api/products/{product_id}/images")
def list_product_images(product_id: str):

    conn = db()

    try:
        images = fetch_all(
            conn,
            """
            SELECT id FROM product_images
            WHERE product_id = ?
            ORDER BY created_at
            """,
            (product_id,)
        )

        return [
            {
                "id": image["id"],
                "url": f"/api/product-images/{image['id']}"
            }
            for image in images
        ]

    finally:
        conn.close()


@app.get("/api/product-images/{image_id}")
def get_product_image(image_id: str):

    conn = db()

    try:
        image = fetch_one(
            conn,
            """
            SELECT image_data, content_type
            FROM product_images
            WHERE id = ?
            """,
            (image_id,)
        )

        if not image:
            raise HTTPException(404, "Image not found.")

        return Response(
            content=image["image_data"],
            media_type=image["content_type"],
            headers={
                "Cache-Control": "public, max-age=86400"
            }
        )

    finally:
        conn.close()


@app.delete("/api/admin/product-images/{image_id}")
def delete_product_image(
    image_id: str,
    _=Depends(admin_user)
):

    conn = db()

    try:
        image = fetch_one(
            conn,
            "SELECT id FROM product_images WHERE id = ?",
            (image_id,)
        )

        if not image:
            raise HTTPException(404, "Image not found.")

        write(
            conn,
            "DELETE FROM product_images WHERE id = ?",
            (image_id,)
        )

        return {"deleted": True}

    finally:
        conn.close()


# --------------------------------------------------
# STORE SETTINGS
# --------------------------------------------------

@app.get("/api/settings")
def get_settings():

    conn = db()

    try:
        settings = fetch_all(
            conn,
            "SELECT key, value FROM settings"
        )

        return {
            item["key"]: json.loads(item["value"])
            for item in settings
        }

    finally:
        conn.close()


@app.put("/api/admin/settings")
def update_settings(
    data: SettingsIn,
    _=Depends(admin_user)
):

    conn = db()

    try:
        for key, value in data.model_dump().items():

            write(
                conn,
                """
                INSERT INTO settings
                (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key)
                DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, json.dumps(value), now())
            )

        settings = fetch_all(
            conn,
            "SELECT key, value FROM settings"
        )

        return {
            item["key"]: json.loads(item["value"])
            for item in settings
        }

    finally:
        conn.close()


# --------------------------------------------------
# CUSTOMER ORDERS
# --------------------------------------------------

@app.post("/api/orders")
def create_order(data: OrderIn):

    conn = db()

    try:
        items = []
        total = 0.0

        for item in data.items:

            product = fetch_one(
                conn,
                """
                SELECT id, name, price, offer_price, stock
                FROM products WHERE id = ?
                """,
                (item.product_id,)
            )

            if not product:
                raise HTTPException(
                    400,
                    "A selected product is unavailable."
                )

            if product["stock"] < item.quantity:
                raise HTTPException(
                    409,
                    f"Insufficient stock for {product['name']}."
                )

            price = float(
                product["offer_price"] or product["price"]
            )

            line_total = price * item.quantity
            total += line_total

            items.append({
                "product_id": product["id"],
                "name": product["name"],
                "quantity": item.quantity,
                "unit_price": price,
                "line_total": line_total
            })

        order_id = str(uuid.uuid4())

        order_number = (
            "SC-" +
            datetime.now().strftime("%y%m%d") +
            "-" +
            secrets.token_hex(3).upper()
        )

        write(
            conn,
            """
            INSERT INTO orders
            (
                id, order_number, customer_name,
                customer_phone, items_json, total,
                status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                order_number,
                data.customer_name,
                data.customer_phone,
                json.dumps(items),
                total,
                "new",
                now()
            )
        )

        return {
            "id": order_id,
            "order_number": order_number,
            "total": round(total, 2),
            "status": "new"
        }

    finally:
        conn.close()


@app.get("/api/admin/orders")
def list_orders(_=Depends(admin_user)):

    conn = db()

    try:
        orders = fetch_all(
            conn,
            "SELECT * FROM orders ORDER BY created_at DESC"
        )

        for order in orders:
            order["items"] = json.loads(
                order.pop("items_json")
            )

        return orders

    finally:
        conn.close()


@app.patch("/api/admin/orders/{order_id}")
def update_order(
    order_id: str,
    data: OrderStatusIn,
    _=Depends(admin_user)
):

    allowed = {
        "new",
        "confirmed",
        "dispatched",
        "completed",
        "cancelled"
    }

    if data.status not in allowed:
        raise HTTPException(400, "Invalid order status.")

    conn = db()

    try:
        order = fetch_one(
            conn,
            "SELECT id FROM orders WHERE id = ?",
            (order_id,)
        )

        if not order:
            raise HTTPException(404, "Order not found.")

        write(
            conn,
            "UPDATE orders SET status = ? WHERE id = ?",
            (data.status, order_id)
        )

        return {
            "updated": True,
            "status": data.status
        }

    finally:
        conn.close()
