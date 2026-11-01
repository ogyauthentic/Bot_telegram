"""
Manajemen keranjang belanja & state sesi pengguna (in-memory)
"""
from typing import Optional

# ─── Keranjang: {user_id: [{"product_id", "nama", "harga", "qty", "stok_sisa"}]}
_carts: dict[int, list] = {}

# ─── State checkout: {user_id: {"step", "nama", "alamat", "order_id"}}
_states: dict[int, dict] = {}


# ══════════════════════════════════════════════════════════════════════════════
#  KERANJANG
# ══════════════════════════════════════════════════════════════════════════════

def get_cart(user_id: int) -> list:
    return _carts.get(user_id, [])

def add_to_cart(user_id: int, product: dict, qty: int = 1) -> bool:
    """Tambah produk ke keranjang. Kembalikan False jika stok tidak cukup."""
    cart = _carts.setdefault(user_id, [])
    existing = next((i for i in cart if i["product_id"] == product["id"]), None)
    current_qty = existing["qty"] if existing else 0
    if current_qty + qty > product["stok"]:
        return False
    if existing:
        existing["qty"] += qty
        existing["stok_sisa"] = product["stok"] - existing["qty"]
    else:
        cart.append({
            "product_id": product["id"],
            "nama"      : product["nama"],
            "harga"     : product["harga"],
            "qty"       : qty,
            "stok_sisa" : product["stok"] - qty,
        })
    return True

def remove_from_cart(user_id: int, product_id: str):
    cart = _carts.get(user_id, [])
    _carts[user_id] = [i for i in cart if i["product_id"] != product_id]

def clear_cart(user_id: int):
    _carts.pop(user_id, None)

def cart_total(user_id: int) -> int:
    return sum(i["harga"] * i["qty"] for i in get_cart(user_id))

def cart_summary(user_id: int) -> str:
    cart = get_cart(user_id)
    if not cart:
        return "Keranjang kosong."
    lines = []
    for item in cart:
        subtotal = item["harga"] * item["qty"]
        lines.append(
            f"• {item['nama']} x{item['qty']} "
            f"= <b>Rp {subtotal:,}</b>"
        )
    lines.append(f"\n💰 <b>Total: Rp {cart_total(user_id):,}</b>")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  STATE SESI
# ══════════════════════════════════════════════════════════════════════════════

def set_state(user_id: int, step: str, **data):
    _states[user_id] = {"step": step, **data}

def get_state(user_id: int) -> Optional[dict]:
    return _states.get(user_id)

def clear_state(user_id: int):
    _states.pop(user_id, None)
