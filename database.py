"""
Database sederhana berbasis file JSON
Untuk skala besar ganti dengan SQLite / PostgreSQL
"""
import json
import os
import uuid
from datetime import datetime
from typing import Optional
from config import PRODUCTS_FILE, ORDERS_FILE, DATA_DIR

# ─── Helpers ─────────────────────────────────────────────────────────────────
def _resolve_path(path: str) -> str:
    if os.path.exists(path):
        return path
    fallback = os.path.join(os.path.dirname(__file__), os.path.basename(path))
    if os.path.exists(fallback):
        return fallback
    return path


def _load(path: str) -> dict | list:
    path = _resolve_path(path)
    if not os.path.exists(path):
        return {} if path.endswith("orders.json") else []

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return {} if path.endswith("orders.json") else []
        return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return {} if path.endswith("orders.json") else []


def _save(path: str, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ══════════════════════════════════════════════════════════════════════════════
#  PRODUK
# ══════════════════════════════════════════════════════════════════════════════

def get_products() -> list:
    return _load(PRODUCTS_FILE)

def get_product(product_id: str) -> Optional[dict]:
    return next((p for p in get_products() if p["id"] == product_id), None)

def get_categories() -> list[str]:
    return sorted({p["kategori"] for p in get_products()})

def get_products_by_category(kategori: str) -> list:
    return [p for p in get_products() if p["kategori"] == kategori]

def add_product(nama: str, kategori: str, harga: int, stok: int, deskripsi: str = "") -> dict:
    products = get_products()
    prod = {
        "id"       : str(uuid.uuid4())[:8],
        "nama"     : nama,
        "kategori" : kategori,
        "harga"    : harga,
        "stok"     : stok,
        "deskripsi": deskripsi,
        "aktif"    : True,
    }
    products.append(prod)
    _save(PRODUCTS_FILE, products)
    return prod

def update_product(product_id: str, **kwargs) -> bool:
    products = get_products()
    for p in products:
        if p["id"] == product_id:
            p.update(kwargs)
            _save(PRODUCTS_FILE, products)
            return True
    return False

def delete_product(product_id: str) -> bool:
    return update_product(product_id, aktif=False)

# ══════════════════════════════════════════════════════════════════════════════
#  PESANAN
# ══════════════════════════════════════════════════════════════════════════════

def get_orders() -> dict:
    return _load(ORDERS_FILE)

def get_order(order_id: str) -> Optional[dict]:
    return get_orders().get(order_id)

def get_user_orders(user_id: int) -> list:
    return [o for o in get_orders().values() if o["user_id"] == user_id]

def create_order(user_id: int, username: str, nama: str,
                 alamat: str, cart: list) -> dict:
    orders = get_orders()
    order_id = f"PWD-{str(uuid.uuid4())[:6].upper()}"
    total = sum(i["harga"] * i["qty"] for i in cart)
    order = {
        "id"         : order_id,
        "user_id"    : user_id,
        "username"   : username,
        "nama"       : nama,
        "alamat"     : alamat,
        "items"      : cart,
        "total"      : total,
        "status"     : "MENUNGGU_BAYAR",
        "bukti_bayar": None,
        "catatan"    : "",
        "dibuat"     : datetime.now().isoformat(),
        "diupdate"   : datetime.now().isoformat(),
    }
    orders[order_id] = order
    _save(ORDERS_FILE, orders)

    # Kurangi stok sesuai qty yang dipesan
    for item in cart:
        product = get_product(item["product_id"])
        if product is None:
            continue
        new_stock = max(product.get("stok", 0) - item["qty"], 0)
        update_product(item["product_id"], stok=new_stock)

    return order

def update_order_status(order_id: str, status: str, catatan: str = "") -> bool:
    orders = get_orders()
    if order_id not in orders:
        return False
    orders[order_id]["status"]   = status
    orders[order_id]["diupdate"] = datetime.now().isoformat()
    if catatan:
        orders[order_id]["catatan"] = catatan
    _save(ORDERS_FILE, orders)
    return True

def set_bukti_bayar(order_id: str, file_id: str) -> bool:
    orders = get_orders()
    if order_id not in orders:
        return False
    orders[order_id]["bukti_bayar"] = file_id
    orders[order_id]["status"]      = "MENUNGGU_KONFIRM"
    orders[order_id]["diupdate"]    = datetime.now().isoformat()
    _save(ORDERS_FILE, orders)
    return True

def get_orders_by_status(status: str) -> list:
    return [o for o in get_orders().values() if o["status"] == status]
