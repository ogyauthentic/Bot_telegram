"""
Handler untuk pelanggan Toko Pandawa:
/start, katalog, keranjang, cek pesanan
"""
import telebot
from telebot import types

import database as db
import cart as Cart
from config import TOKO_NAMA, TOKO_TAGLINE, STATUS


def register_customer_handlers(bot: telebot.TeleBot):

    # ── Keyboard utama ────────────────────────────────────────────────────────
    def main_kb():
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🛍️ Katalog", "🛒 Keranjang")
        kb.row("📦 Pesanan Saya", "❓ Bantuan")
        return kb

    # ── /start ────────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["start"])
    def cmd_start(msg: types.Message):
        nama = msg.from_user.first_name or "Kak"
        bot.send_message(
            msg.chat.id,
            f"👋 Halo, <b>{nama}</b>!\n\n"
            f"Selamat datang di <b>{TOKO_NAMA}</b>\n"
            f"<i>{TOKO_TAGLINE}</i>\n\n"
            "Pilih menu di bawah untuk mulai belanja:",
            reply_markup=main_kb(),
        )

    # ── Bantuan ───────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "❓ Bantuan")
    def btn_bantuan(msg: types.Message):
        bot.send_message(
            msg.chat.id,
            "📖 <b>Cara Belanja di Toko Pandawa</b>\n\n"
            "1️⃣ Ketuk <b>🛍️ Katalog</b> → pilih kategori → pilih produk\n"
            "2️⃣ Tambahkan produk ke keranjang\n"
            "3️⃣ Ketuk <b>🛒 Keranjang</b> → lanjut ke checkout\n"
            "4️⃣ Isi nama & alamat pengiriman\n"
            "5️⃣ Transfer ke rekening yang tertera\n"
            "6️⃣ Upload bukti transfer\n"
            "7️⃣ Pesanan diproses oleh admin ✅\n\n"
            "Cek status pesanan via <b>📦 Pesanan Saya</b>",
            reply_markup=main_kb(),
        )

    # ── Katalog: pilih kategori ───────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🛍️ Katalog")
    def btn_katalog(msg: types.Message):
        kategori_list = db.get_categories()
        if not kategori_list:
            bot.send_message(msg.chat.id, "Katalog masih kosong. Coba lagi nanti.")
            return
        kb = types.InlineKeyboardMarkup()
        for kat in kategori_list:
            kb.add(types.InlineKeyboardButton(f"📂 {kat}", callback_data=f"kat:{kat}"))
        bot.send_message(msg.chat.id, "🗂️ <b>Pilih Kategori:</b>", reply_markup=kb)

    # ── Katalog: list produk per kategori ────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("kat:"))
    def cb_kategori(call: types.CallbackQuery):
        kat = call.data.split(":", 1)[1]
        produk_list = [p for p in db.get_products_by_category(kat) if p.get("aktif")]
        if not produk_list:
            bot.answer_callback_query(call.id, "Tidak ada produk di kategori ini.")
            return
        kb = types.InlineKeyboardMarkup()
        for p in produk_list:
            stok_info = f"(stok {p['stok']})" if p["stok"] > 0 else "⛔ Habis"
            kb.add(types.InlineKeyboardButton(
                f"{p['nama']} — Rp {p['harga']:,} {stok_info}",
                callback_data=f"prod:{p['id']}"
            ))
        kb.add(types.InlineKeyboardButton("« Kembali", callback_data="katalog"))
        bot.edit_message_text(
            f"📂 <b>Kategori: {kat}</b>\nPilih produk:",
            call.message.chat.id, call.message.message_id,
            reply_markup=kb,
        )

    # Kembali ke daftar kategori
    @bot.callback_query_handler(func=lambda c: c.data == "katalog")
    def cb_back_katalog(call: types.CallbackQuery):
        kategori_list = db.get_categories()
        kb = types.InlineKeyboardMarkup()
        for kat in kategori_list:
            kb.add(types.InlineKeyboardButton(f"📂 {kat}", callback_data=f"kat:{kat}"))
        bot.edit_message_text(
            "🗂️ <b>Pilih Kategori:</b>",
            call.message.chat.id, call.message.message_id,
            reply_markup=kb,
        )

    # ── Detail produk ─────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("prod:"))
    def cb_produk(call: types.CallbackQuery):
        prod_id = call.data.split(":", 1)[1]
        p = db.get_product(prod_id)
        if not p:
            bot.answer_callback_query(call.id, "Produk tidak ditemukan.")
            return

        stok_txt = f"Stok: {p['stok']}" if p["stok"] > 0 else "⛔ Stok Habis"
        teks = (
            f"🏷️ <b>{p['nama']}</b>\n"
            f"📂 Kategori: {p['kategori']}\n"
            f"💰 Harga: <b>Rp {p['harga']:,}</b>\n"
            f"📦 {stok_txt}\n"
        )
        if p.get("deskripsi"):
            teks += f"\n📝 {p['deskripsi']}"

        kb = types.InlineKeyboardMarkup()
        if p["stok"] > 0:
            kb.row(
                types.InlineKeyboardButton("➕ +1", callback_data=f"add:{prod_id}:1"),
                types.InlineKeyboardButton("➕ +3", callback_data=f"add:{prod_id}:3"),
                types.InlineKeyboardButton("➕ +5", callback_data=f"add:{prod_id}:5"),
            )
        kb.add(types.InlineKeyboardButton("« Kembali", callback_data=f"kat:{p['kategori']}"))

        bot.edit_message_text(
            teks, call.message.chat.id, call.message.message_id, reply_markup=kb
        )

    # ── Tambah ke keranjang ───────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("add:"))
    def cb_add_cart(call: types.CallbackQuery):
        _, prod_id, qty_str = call.data.split(":")
        p = db.get_product(prod_id)
        if not p:
            bot.answer_callback_query(call.id, "Produk tidak ditemukan.")
            return
        ok = Cart.add_to_cart(call.from_user.id, p, int(qty_str))
        if ok:
            bot.answer_callback_query(
                call.id, f"✅ {p['nama']} x{qty_str} ditambahkan ke keranjang!", show_alert=False
            )
        else:
            bot.answer_callback_query(call.id, "⛔ Stok tidak mencukupi!", show_alert=True)

    # ── Keranjang ─────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🛒 Keranjang")
    def btn_keranjang(msg: types.Message):
        user_id = msg.from_user.id
        cart = Cart.get_cart(user_id)
        if not cart:
            bot.send_message(msg.chat.id, "🛒 Keranjangmu kosong.\nYuk belanja dulu via <b>🛍️ Katalog</b>!")
            return

        kb = types.InlineKeyboardMarkup()
        for item in cart:
            kb.add(types.InlineKeyboardButton(
                f"🗑️ Hapus: {item['nama']}",
                callback_data=f"rm:{item['product_id']}"
            ))
        kb.add(types.InlineKeyboardButton("✅ Checkout Sekarang", callback_data="checkout"))
        kb.add(types.InlineKeyboardButton("🗑️ Kosongkan Semua", callback_data="clear_cart"))

        bot.send_message(
            msg.chat.id,
            f"🛒 <b>Keranjang Kamu</b>\n\n{Cart.cart_summary(user_id)}",
            reply_markup=kb,
        )

    # Hapus satu item
    @bot.callback_query_handler(func=lambda c: c.data.startswith("rm:"))
    def cb_remove(call: types.CallbackQuery):
        prod_id = call.data.split(":", 1)[1]
        Cart.remove_from_cart(call.from_user.id, prod_id)
        bot.answer_callback_query(call.id, "Item dihapus dari keranjang.")
        # Refresh tampilan keranjang
        cart = Cart.get_cart(call.from_user.id)
        if not cart:
            bot.edit_message_text("🛒 Keranjang sudah kosong.", call.message.chat.id, call.message.message_id)
            return
        kb = types.InlineKeyboardMarkup()
        for item in cart:
            kb.add(types.InlineKeyboardButton(
                f"🗑️ Hapus: {item['nama']}", callback_data=f"rm:{item['product_id']}"
            ))
        kb.add(types.InlineKeyboardButton("✅ Checkout Sekarang", callback_data="checkout"))
        kb.add(types.InlineKeyboardButton("🗑️ Kosongkan Semua",  callback_data="clear_cart"))
        bot.edit_message_text(
            f"🛒 <b>Keranjang Kamu</b>\n\n{Cart.cart_summary(call.from_user.id)}",
            call.message.chat.id, call.message.message_id, reply_markup=kb
        )

    @bot.callback_query_handler(func=lambda c: c.data == "clear_cart")
    def cb_clear(call: types.CallbackQuery):
        Cart.clear_cart(call.from_user.id)
        bot.edit_message_text("🛒 Keranjang dikosongkan.", call.message.chat.id, call.message.message_id)

    # ── Cek pesanan saya ──────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📦 Pesanan Saya")
    def btn_pesanan(msg: types.Message):
        orders = db.get_user_orders(msg.from_user.id)
        if not orders:
            bot.send_message(msg.chat.id, "📦 Kamu belum memiliki pesanan.")
            return
        # 5 pesanan terbaru
        for o in sorted(orders, key=lambda x: x["dibuat"], reverse=True)[:5]:
            status_label = STATUS.get(o["status"], o["status"])
            items_txt = "\n".join(f"  • {i['nama']} x{i['qty']}" for i in o["items"])
            teks = (
                f"🧾 <b>{o['id']}</b>\n"
                f"📅 {o['dibuat'][:10]}\n"
                f"Status: {status_label}\n"
                f"Items:\n{items_txt}\n"
                f"💰 Total: <b>Rp {o['total']:,}</b>"
            )
            if o.get("catatan"):
                teks += f"\n📝 Catatan: {o['catatan']}"
            bot.send_message(msg.chat.id, teks)
