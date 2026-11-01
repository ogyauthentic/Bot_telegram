"""
Konfigurasi global Toko Pandawa
"""
import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency in runtime env
    def load_dotenv(*_args, **_kwargs):
        return False


load_dotenv()


def _read_int(name: str, default: int = 0) -> int:
    raw = os.getenv(name, "")
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _read_admin_ids() -> list[int]:
    raw = os.getenv("ADMIN_IDS", "")
    if not raw:
        return []
    ids: list[int] = []
    for item in raw.split(","):
        value = item.strip()
        if not value:
            continue
        try:
            ids.append(int(value))
        except ValueError:
            continue
    return ids


# ─── Telegram ─────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = _read_admin_ids()
ADMIN_GROUP = _read_int("ADMIN_GROUP_ID", 0)  # Chat ID grup/channel admin

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
