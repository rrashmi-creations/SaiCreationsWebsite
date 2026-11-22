import os, json, secrets, time
from datetime import datetime, timezone
from typing import Optional
import jwt
import cloudinary
from cloudinary.utils import api_sign_request
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import libsql_experimental as libsql

APP_NAME = "Sai Creation API"
JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
JWT_HOURS = int(os.environ.get("JWT_HOURS", "12"))
SETUP_SECRET = os.environ.get("SETUP_SECRET", "")
TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")
FRONTEND_ORIGINS = [x.strip() for x in os.environ.get("FRONTEND_ORIGINS", "*").split(",") if x.strip()]
ph = PasswordHasher()

app = FastAPI(title=APP_NAME, version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"] if FRONTEND_ORIGINS == ["*"] else FRONTEND_ORIGINS,
                   allow_credentials=False, allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
                   allow_headers=["Authorization","Content-Type"])

def db():
    if not TURSO_DATABASE_URL or not TURSO_AUTH_TOKEN:
        raise HTTPException(503, "Turso database is not configured. Add TURSO_DATABASE_URL and TURSO_AUTH_TOKEN.")
    return libsql.create_client(url=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)

def rows(result):
    cols = list(getattr(result, "columns", []) or [])
    return [dict(zip(cols, list(r))) for r in (getattr(result, "rows", []) or [])]

def one(client, sql, args=()):
    result = client.execute(sql, list(args))
    found = rows(result)
    return found[0] if found else None

def run(client, sql, args=()):
    return client.execute(sql, list(args))

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def init_db():
    client = db()
    statements = [
      """CREATE TABLE IF NOT EXISTS admins (id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)""",
      """CREATE TABLE IF NOT EXISTS products (id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, price REAL NOT NULL, offer_price REAL NOT NULL DEFAULT 0, stock INTEGER NOT NULL DEFAULT 0, sizes TEXT DEFAULT '', fabric TEXT DEFAULT '', image_url TEXT DEFAULT '', description TEXT DEFAULT '', is_new INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
      """CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)""",
      """CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, order_number TEXT UNIQUE NOT NULL, customer_name TEXT DEFAULT '', customer_phone TEXT DEFAULT '', items_json TEXT NOT NULL, total REAL NOT NULL, status TEXT NOT NULL DEFAULT 'new', created_at TEXT NOT NULL)""",
      """CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)""",
      """CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at)"""
    ]
    for sql in statements: run(client, sql)
    defaults = {
      "store_name":"Sai Creation","tagline":"Fashion Beyond Boundaries","hero_heading":"Style. Grace. Elegance.",
      "hero_sub":"Discover ethnic fashion for every moment.","hero_button":"Explore collection","whatsapp":"",
      "phone":"","retail_whatsapp":"","wholesale_whatsapp":"","support_whatsapp":"","email":"",
      "instagram":"","facebook":"","youtube":"","hero_image":"","page_size":8
    }
    for k,v in defaults.items():
        run(client, "INSERT OR IGNORE INTO settings(key,value,updated_at) VALUES(?,?,?)", (k,json.dumps(v),now_iso()))
    # Seed the eight demonstration products from the original storefront only on a fresh database.
    existing = one(client, "SELECT id FROM products LIMIT 1")
    if not existing:
        seed = [
          ("k1","Elegant Embroidered Kurti Set","Kurtis",1299,899,12,"S, M, L, XL","Rayon","images/kurties/image1.jpg","Elegant embroidered kurti set for festive and everyday occasions.",1),
          ("k2","Everyday Cotton Kurti","Kurtis",899,649,18,"M, L, XL, XXL","Cotton","images/kurties/image2.jpg","Comfortable cotton kurti with a fresh print.",0),
          ("c1","Chic Co-ord Set","Co-ord Sets",1799,1299,7,"S, M, L, XL","Blend","images/coordsets/image1.jpg","Contemporary co-ord set with an easy, relaxed fit.",1),
          ("c2","Printed Co-ord Set","Co-ord Sets",1499,1099,10,"M, L, XL","Cotton Blend","images/coordsets/image2.jpg","Versatile printed set for day outings.",0),
          ("s1","Classic Occasion Saree","Sarees",2199,1699,5,"Free size","Silk Blend","images/sarees/image1.jpg","Traditional drape with an elegant border.",0),
          ("s2","Soft Festive Saree","Sarees",1899,1399,8,"Free size","Georgette","images/sarees/image2.jpg","A graceful saree for celebrations and gifting.",0),
          ("o1","Festive Sharara Set","Others",2499,1899,4,"S, M, L, XL","Chiffon","images/others/image1.jpg","Statement festive wear with beautiful detailing.",0),
          ("o2","Draped Dupatta Set","Others",1599,1199,9,"M, L, XL","Crepe","images/others/image2.jpg","A versatile ethnic set to style your way.",0),
        ]
        stamp = now_iso()
        for item in seed:
            run(client, "INSERT INTO products(id,name,category,price,offer_price,stock,sizes,fabric,image_url,description,is_new,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (*item,stamp,stamp))
    client.close()

@app.on_event("startup")
def startup():
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        init_db()

class SetupIn(BaseModel):
    setup_secret: str
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    category: str = Field(min_length=1, max_length=80)
    price: float = Field(ge=0)
    offer_price: float = Field(default=0, ge=0)
    stock: int = Field(default=0, ge=0)
    sizes: str = Field(default="", max_length=300)
    fabric: str = Field(default="", max_length=120)
    image_url: str = Field(default="", max_length=2000)
    description: str = Field(default="", max_length=3000)
    is_new: bool = False

class SettingsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    store_name: str = Field(default="Sai Creation", max_length=120)
    tagline: str = Field(default="", max_length=200)
    hero_heading: str = Field(default="", max_length=200)
    hero_sub: str = Field(default="", max_length=300)
    hero_button: str = Field(default="Explore collection", max_length=80)
    whatsapp: str = Field(default="", max_length=40)
    phone: str = Field(default="", max_length=40)
    retail_whatsapp: str = Field(default="", max_length=40)
    wholesale_whatsapp: str = Field(default="", max_length=40)
    support_whatsapp: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=200)
    instagram: str = Field(default="", max_length=500)
    facebook: str = Field(default="", max_length=500)
    youtube: str = Field(default="", max_length=500)
    hero_image: str = Field(default="", max_length=2000)
    page_size: int = Field(default=8, ge=4, le=48)

class OrderItem(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, le=20)

class OrderIn(BaseModel):
    customer_name: str = Field(default="Website customer", max_length=150)
    customer_phone: str = Field(default="", max_length=40)
    items: list[OrderItem] = Field(min_length=1, max_length=30)

class OrderStatusIn(BaseModel):
    status: str

def admin_user(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Please log in as administrator.")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("role") != "admin": raise ValueError("role")
        return payload
    except Exception:
        raise HTTPException(401, "Admin session expired. Please log in again.")

def product_dict(r):
    r["is_new"] = bool(r.get("is_new", 0))
    return r

@app.get("/")
def root():
    return {"service": APP_NAME, "status": "ok", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status":"ok","time":now_iso()}

@app.post("/api/auth/setup")
def setup_admin(data: SetupIn):
    if not SETUP_SECRET or not secrets.compare_digest(data.setup_secret, SETUP_SECRET):
        raise HTTPException(403, "Invalid one-time setup key.")
    client=db()
    existing=one(client,"SELECT id FROM admins LIMIT 1")
    if existing:
        client.close()
        raise HTTPException(409,"Admin account already exists. Setup is disabled.")
    import uuid
    run(client,"INSERT INTO admins(id,email,password_hash,created_at) VALUES(?,?,?,?)",
        (str(uuid.uuid4()),data.email.lower(),ph.hash(data.password),now_iso()))
    client.close()
    return {"message":"Admin account created. Remove SETUP_SECRET from Render after setup."}

@app.post("/api/auth/login")
def login(data: LoginIn):
    if not JWT_SECRET or len(JWT_SECRET)<32: raise HTTPException(503,"JWT_SECRET is not configured securely.")
    client=db(); admin=one(client,"SELECT * FROM admins WHERE email=?",(data.email.lower(),));client.close()
    if not admin: raise HTTPException(401,"Incorrect email or password.")
    try: ph.verify(admin["password_hash"],data.password)
    except VerifyMismatchError: raise HTTPException(401,"Incorrect email or password.")
    token=jwt.encode({"sub":admin["id"],"role":"admin","exp":int(time.time())+JWT_HOURS*3600},JWT_SECRET,algorithm=JWT_ALGORITHM)
    return {"access_token":token,"token_type":"bearer","expires_in":JWT_HOURS*3600}

@app.get("/api/products")
def list_products(category: Optional[str]=None, search: Optional[str]=None):
    client=db()
    if category and category!="All":
        result=client.execute("SELECT * FROM products WHERE category=? ORDER BY created_at DESC",[category])
    else:
        result=client.execute("SELECT * FROM products ORDER BY created_at DESC")
    data=[product_dict(x) for x in rows(result)]
    client.close()
    if search:
        q=search.lower();data=[p for p in data if q in (p["name"]+" "+p["category"]+" "+p.get("description","")).lower()]
    return data

@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    client=db();p=one(client,"SELECT * FROM products WHERE id=?",(product_id,));client.close()
    if not p:raise HTTPException(404,"Product not found.")
    return product_dict(p)

@app.get("/api/settings")
def get_settings():
    client=db();found=rows(client.execute("SELECT key,value FROM settings"));client.close()
    return {x["key"]:json.loads(x["value"]) for x in found}

@app.post("/api/admin/products")
def create_product(data: ProductIn, _=Depends(admin_user)):
    import uuid
    client=db();pid=str(uuid.uuid4());t=now_iso()
    run(client,"INSERT INTO products(id,name,category,price,offer_price,stock,sizes,fabric,image_url,description,is_new,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (pid,data.name,data.category,data.price,data.offer_price,data.stock,data.sizes,data.fabric,data.image_url,data.description,int(data.is_new),t,t))
    p=one(client,"SELECT * FROM products WHERE id=?",(pid,));client.close()
    return product_dict(p)

@app.put("/api/admin/products/{product_id}")
def update_product(product_id: str,data: ProductIn,_=Depends(admin_user)):
    client=db()
    existing=one(client,"SELECT id FROM products WHERE id=?",(product_id,))
    if not existing:client.close();raise HTTPException(404,"Product not found.")
    run(client,"UPDATE products SET name=?,category=?,price=?,offer_price=?,stock=?,sizes=?,fabric=?,image_url=?,description=?,is_new=?,updated_at=? WHERE id=?",
        (data.name,data.category,data.price,data.offer_price,data.stock,data.sizes,data.fabric,data.image_url,data.description,int(data.is_new),now_iso(),product_id))
    p=one(client,"SELECT * FROM products WHERE id=?",(product_id,));client.close()
    return product_dict(p)

@app.delete("/api/admin/products/{product_id}")
def delete_product(product_id: str,_=Depends(admin_user)):
    client=db();existing=one(client,"SELECT id FROM products WHERE id=?",(product_id,))
    if not existing:client.close();raise HTTPException(404,"Product not found.")
    run(client,"DELETE FROM products WHERE id=?",(product_id,));client.close()
    return {"deleted":True,"id":product_id}

@app.put("/api/admin/settings")
def update_settings(data: SettingsIn,_=Depends(admin_user)):
    client=db();t=now_iso()
    for k,v in data.model_dump().items():
        run(client,"INSERT INTO settings(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(k,json.dumps(v),t))
    found=rows(client.execute("SELECT key,value FROM settings"));client.close()
    return {x["key"]:json.loads(x["value"]) for x in found}

@app.post("/api/admin/cloudinary-signature")
def cloudinary_signature(_=Depends(admin_user)):
    if not all([CLOUDINARY_CLOUD_NAME,CLOUDINARY_API_KEY,CLOUDINARY_API_SECRET]):
        raise HTTPException(503,"Cloudinary credentials are not configured.")
    timestamp=int(time.time());folder="sai-creation/products"
    params={"timestamp":timestamp,"folder":folder}
    signature=api_sign_request(params,CLOUDINARY_API_SECRET)
    return {"cloud_name":CLOUDINARY_CLOUD_NAME,"api_key":CLOUDINARY_API_KEY,"timestamp":timestamp,"folder":folder,"signature":signature}

@app.post("/api/orders")
def create_order(data: OrderIn):
    import uuid
    client=db();items=[];total=0.0
    for item in data.items:
        p=one(client,"SELECT id,name,price,offer_price,stock FROM products WHERE id=?",(item.product_id,))
        if not p:client.close();raise HTTPException(400,"One of the selected products is no longer available.")
        if p["stock"]<item.quantity:client.close();raise HTTPException(409,f"Insufficient stock for {p['name']}.")
        price=float(p["offer_price"] or p["price"]);line=price*item.quantity;total+=line
        items.append({"product_id":p["id"],"name":p["name"],"quantity":item.quantity,"unit_price":price,"line_total":line})
    order_id=str(uuid.uuid4());number="SC-"+datetime.now().strftime("%y%m%d")+"-"+secrets.token_hex(3).upper()
    run(client,"INSERT INTO orders(id,order_number,customer_name,customer_phone,items_json,total,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
        (order_id,number,data.customer_name,data.customer_phone,json.dumps(items),total,"new",now_iso()))
    client.close()
    return {"id":order_id,"order_number":number,"total":round(total,2),"status":"new"}

@app.get("/api/admin/orders")
def list_orders(_=Depends(admin_user)):
    client=db();result=rows(client.execute("SELECT * FROM orders ORDER BY created_at DESC"));client.close()
    for x in result:x["items"]=json.loads(x.pop("items_json"))
    return result

@app.patch("/api/admin/orders/{order_id}")
def update_order(order_id: str,data: OrderStatusIn,_=Depends(admin_user)):
    allowed={"new","confirmed","dispatched","completed","cancelled"}
    if data.status not in allowed:raise HTTPException(400,"Invalid order status.")
    client=db();found=one(client,"SELECT id FROM orders WHERE id=?",(order_id,))
    if not found:client.close();raise HTTPException(404,"Order not found.")
    run(client,"UPDATE orders SET status=? WHERE id=?",(data.status,order_id));client.close()
    return {"updated":True,"status":data.status}
