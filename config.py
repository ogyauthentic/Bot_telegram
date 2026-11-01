"""
Konfigurasi global Toko Pandawa
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Telegram ─────────────────────────────────────────────────────────────────
BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
ADMIN_IDS    = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
ADMIN_GROUP  = int(os.getenv("ADMIN_GROUP_ID", "0"))   # Chat ID grup/channel admin

# ─── Toko ─────────────────────────────────────────────────────────────────────
TOKO_NAMA    = "Toko Pandawa"
TOKO_TAGLINE = "Belanja Lengkap, Harga Bersahabat 🛒"

# Rekening pembayaran (bisa lebih dari satu)
REKENING = [
    {"bank": "BCA",     "no": "1234567890", "nama": "Pandawa Store"},
    {"bank": "Mandiri", "no": "0987654321", "nama": "Pandawa Store"},
    {"bank": "GoPay",   "no": "0812-3456-7890", "nama": "Pandawa Store"},
]

# ─── Paths ────────────────────────────────────────────────────────────────────
DATA_DIR     = os.path.join(os.path.dirname(__file__), "data")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
ORDERS_FILE   = os.path.join(DATA_DIR, "orders.json")

# ─── Status Pesanan ───────────────────────────────────────────────────────────
STATUS = {
    "MENUNGGU_BAYAR" : "⏳ Menunggu Pembayaran",
    "MENUNGGU_KONFIRM": "🔍 Menunggu Konfirmasi Admin",
    "DIPROSES"       : "⚙️ Sedang Diproses",
    "DIKIRIM"        : "🚚 Sedang Dikirim",
    "SELESAI"        : "✅ Selesai",
    "DIBATALKAN"     : "❌ Dibatalkan",
}
