#!/usr/bin/env python3
"""
🛒 Toko Pandawa — Telegram Bot
Entry point: daftarkan webhook & jalankan Flask
"""

import os
import logging
from flask import Flask, request, abort
import telebot
from dotenv import load_dotenv

from customer import register_customer_handlers
from admin    import register_admin_handlers
from checkout import register_checkout_handlers

# ─── Env ─────────────────────────────────────────────────────────────────────
load_dotenv()

BOT_TOKEN   = os.getenv("BOT_TOKEN", "").strip()
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
SECRET_PATH = os.getenv("SECRET_PATH", "pandawa_webhook").strip()
PORT        = int(os.getenv("PORT", "5000"))

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("pandawa.log"),
    ],
)
logger = logging.getLogger(__name__)

# ─── Bot & App ────────────────────────────────────────────────────────────────
BOT_TOKEN_FOR_INIT = BOT_TOKEN or "0000000000:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
bot = telebot.TeleBot(BOT_TOKEN_FOR_INIT, parse_mode="HTML")
app = Flask(__name__)

# Daftarkan semua handler
register_customer_handlers(bot)
register_checkout_handlers(bot)
register_admin_handlers(bot)

# ─── Webhook Route ───────────────────────────────────────────────────────────
@app.route(f"/{SECRET_PATH}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") != "application/json":
        abort(403)
    bot.process_new_updates(
        [telebot.types.Update.de_json(request.get_data(as_text=True))]
    )
    return "OK", 200

@app.route("/health")
def health():
    return {"status": "ok", "toko": "Pandawa"}, 200

# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN belum di-set di .env!")
    if not WEBHOOK_URL:
        raise RuntimeError("WEBHOOK_URL belum di-set di .env!")

    url = f"{WEBHOOK_URL.rstrip('/')}/{SECRET_PATH}"
    bot.remove_webhook()
    bot.set_webhook(url=url)
    logger.info("Webhook aktif: %s", url)
    app.run(host="127.0.0.1", port=PORT, debug=False)
