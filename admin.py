"""
Handler panel admin Toko Pandawa:
Konfirmasi pesanan, kelola produk, lihat laporan
"""
import telebot
from telebot import types

import database as db
import cart as Cart
from config import ADMIN_IDS, STATUS


def register_admin_handlers(bot: telebot.TeleBot):

    def is_admin(user_id: int) -> bool:
        return user_id in ADMIN_IDS

    def admin_only(func):
        """Dekorator: tolak jika bukan admin."""
        def wrapper(msg_or_call, *args, **kwargs):
            uid = (msg_or_call.from_user.id
                   if isinstance(msg_or_call, types.Message)
                   else msg_or_call.from_user.id)
            if not is_admin(uid):
                if isinstance(msg_or_call, types.CallbackQuery):
                    bot.answer_callback_query(msg_or_call.id, "⛔ Akses ditolak.", show_alert=True)
                else:
                    bot.send_message(msg_or_call.chat.id, "⛔ Kamu bukan admin.")
                return
            return func(msg_or_call, *args, **kwargs)
        return wrapper

    def admin_kb():
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("📋 Pesanan Masuk", "📊 Laporan")
        kb.row("➕ Tambah Produk",  "📦 Kelola Produk")
        kb.row("🏠 Menu Utama")
        return kb

    # ── /admin ────────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["admin"])
    @admin_only
    def cmd_admin(msg: types.Message):
        bot.send_message(
            msg.chat.id,
            "🔐 <b>Panel Admin Toko Pandawa</b>\n\nSelamat datang, Admin!",
            reply_markup=admin_kb(),
        )

    # ── Pesanan masuk (menunggu konfirmasi) ───────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📋 Pesanan Masuk" and is_admin(m.from_user.id))
    def btn_pesanan_masuk(msg: types.Message):
        orders = db.get_orders_by_status("MENUNGGU_KONFIRM")
        if not orders:
            bot.send_message(msg.chat.id, "✅ Tidak ada pesanan yang menunggu konfirmasi.")
            return
        for o in orders:
            items_txt = "\n".join(f"  • {i['nama']} x{i['qty']}" for i in o["items"])
            teks = (
                f"🧾 <b>{o['id']}</b>\n"
                f"👤 {o['nama']} (@{o['username'] or 'N/A'})\n"
                f"📍 {o['alamat']}\n"
                f"🛒 Item:\n{items_txt}\n"
                f"💰 Total: <b>Rp {o['total']:,}</b>"
            )
            kb = types.InlineKeyboardMarkup()
            kb.row(
                types.InlineKeyboardButton("✅ Konfirmasi", callback_data=f"adm_ok:{o['id']}"),
                types.InlineKeyboardButton("❌ Tolak",      callback_data=f"adm_no:{o['id']}"),
            )
            kb.add(types.InlineKeyboardButton("⚙️ Tandai Diproses", callback_data=f"adm_proses:{o['id']}"))
            kb.add(types.InlineKeyboardButton("🚚 Tandai Dikirim",  callback_data=f"adm_kirim:{o['id']}"))

            if o.get("bukti_bayar"):
                bot.send_photo(msg.chat.id, o["bukti_bayar"], caption=teks, reply_markup=kb)
            else:
                bot.send_message(msg.chat.id, teks, reply_markup=kb)

    # ── Tombol konfirmasi / tolak / update status ─────────────────────────────
    def _notify_customer(order_id: str, status_key: str, catatan: str = ""):
        """Kirim notifikasi ke pelanggan."""
        order = db.get_order(order_id)
        if not order:
            return
        status_label = STATUS.get(status_key, status_key)
        teks = (
            f"🔔 <b>Update Pesanan</b>\n\n"
            f"🧾 ID: <code>{order_id}</code>\n"
            f"Status: {status_label}"
        )
        if catatan:
            teks += f"\n📝 Catatan: {catatan}"
        try:
            bot.send_message(order["user_id"], teks)
        except Exception:
            pass  # User mungkin blokir bot

    @bot.callback_query_handler(func=lambda c: c.data.startswith("adm_ok:"))
    def cb_konfirmasi(call: types.CallbackQuery):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "⛔ Bukan admin.", show_alert=True)
            return
        order_id = call.data.split(":", 1)[1]
        db.update_order_status(order_id, "DIPROSES", "Pembayaran dikonfirmasi")
        _notify_customer(order_id, "DIPROSES", "Pembayaran dikonfirmasi ✅")
        bot.answer_callback_query(call.id, f"✅ Pesanan {order_id} dikonfirmasi!")
        bot.edit_message_caption(
            caption=f"✅ <b>DIKONFIRMASI</b> — {order_id}\noleh @{call.from_user.username}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
        )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("adm_no:"))
    def cb_tolak(call: types.CallbackQuery):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "⛔ Bukan admin.", show_alert=True)
            return
        order_id = call.data.split(":", 1)[1]
        Cart.set_state(call.from_user.id, "tunggu_alasan_tolak", order_id=order_id,
                       chat_id=call.message.chat.id, msg_id=call.message.message_id)
        bot.send_message(call.message.chat.id,
                         f"✏️ Masukkan alasan penolakan pesanan <code>{order_id}</code>:")
        bot.answer_callback_query(call.id)

    @bot.message_handler(func=lambda m: (Cart.get_state(m.from_user.id) or {}).get("step") == "tunggu_alasan_tolak" and is_admin(m.from_user.id))
    def step_alasan_tolak(msg: types.Message):
        state    = Cart.get_state(msg.from_user.id)
        order_id = state["order_id"]
        alasan   = msg.text.strip()
        db.update_order_status(order_id, "DIBATALKAN", alasan)
        _notify_customer(order_id, "DIBATALKAN", alasan)
        Cart.clear_state(msg.from_user.id)
        bot.send_message(msg.chat.id, f"❌ Pesanan <code>{order_id}</code> ditolak.\nAlasan: {alasan}")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("adm_proses:"))
    def cb_proses(call: types.CallbackQuery):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "⛔ Bukan admin.", show_alert=True)
            return
        order_id = call.data.split(":", 1)[1]
        db.update_order_status(order_id, "DIPROSES")
        _notify_customer(order_id, "DIPROSES")
        bot.answer_callback_query(call.id, f"⚙️ {order_id} ditandai Diproses.")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("adm_kirim:"))
    def cb_kirim(call: types.CallbackQuery):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "⛔ Bukan admin.", show_alert=True)
            return
        order_id = call.data.split(":", 1)[1]
        db.update_order_status(order_id, "DIKIRIM")
        _notify_customer(order_id, "DIKIRIM")
        bot.answer_callback_query(call.id, f"🚚 {order_id} ditandai Dikirim.")

    # ── Tambah produk ─────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "➕ Tambah Produk" and is_admin(m.from_user.id))
    def btn_tambah_produk(msg: types.Message):
        Cart.set_state(msg.from_user.id, "adm_prod_nama")
        bot.send_message(msg.chat.id,
            "➕ <b>Tambah Produk Baru</b>\n\nMasukkan <b>nama produk</b>:")

    @bot.message_handler(func=lambda m: (Cart.get_state(m.from_user.id) or {}).get("step") == "adm_prod_nama" and is_admin(m.from_user.id))
    def adm_prod_nama(msg: types.Message):
        Cart.set_state(msg.from_user.id, "adm_prod_kat", nama=msg.text.strip())
        bot.send_message(msg.chat.id, "📂 Masukkan <b>kategori</b> produk (contoh: Fashion, Elektronik):")

    @bot.message_handler(func=lambda m: (Cart.get_state(m.from_user.id) or {}).get("step") == "adm_prod_kat" and is_admin(m.from_user.id))
    def adm_prod_kat(msg: types.Message):
        state = Cart.get_state(msg.from_user.id)
        Cart.set_state(msg.from_user.id, "adm_prod_harga", nama=state["nama"], kat=msg.text.strip())
        bot.send_message(msg.chat.id, "💰 Masukkan <b>harga</b> (angka, contoh: 50000):")

    @bot.message_handler(func=lambda m: (Cart.get_state(m.from_user.id) or {}).get("step") == "adm_prod_harga" and is_admin(m.from_user.id))
    def adm_prod_harga(msg: types.Message):
        try:
            harga = int(msg.text.strip().replace(".", "").replace(",", ""))
        except ValueError:
            bot.send_message(msg.chat.id, "⚠️ Harga harus berupa angka. Coba lagi:")
            return
        state = Cart.get_state(msg.from_user.id)
        Cart.set_state(msg.from_user.id, "adm_prod_stok", nama=state["nama"], kat=state["kat"], harga=harga)
        bot.send_message(msg.chat.id, "📦 Masukkan jumlah <b>stok</b> awal:")

    @bot.message_handler(func=lambda m: (Cart.get_state(m.from_user.id) or {}).get("step") == "adm_prod_stok" and is_admin(m.from_user.id))
    def adm_prod_stok(msg: types.Message):
        try:
            stok = int(msg.text.strip())
        except ValueError:
            bot.send_message(msg.chat.id, "⚠️ Stok harus berupa angka. Coba lagi:")
            return
        state = Cart.get_state(msg.from_user.id)
        Cart.set_state(msg.from_user.id, "adm_prod_desc",
                       nama=state["nama"], kat=state["kat"], harga=state["harga"], stok=stok)
        bot.send_message(msg.chat.id, "📝 Masukkan <b>deskripsi</b> produk (atau ketik <code>-</code> untuk skip):")

    @bot.message_handler(func=lambda m: (Cart.get_state(m.from_user.id) or {}).get("step") == "adm_prod_desc" and is_admin(m.from_user.id))
    def adm_prod_desc(msg: types.Message):
        state = Cart.get_state(msg.from_user.id)
        desc  = "" if msg.text.strip() == "-" else msg.text.strip()
        prod  = db.add_product(state["nama"], state["kat"], state["harga"], state["stok"], desc)
        Cart.clear_state(msg.from_user.id)
        bot.send_message(
            msg.chat.id,
            f"✅ <b>Produk berhasil ditambahkan!</b>\n\n"
            f"ID: <code>{prod['id']}</code>\n"
            f"Nama: {prod['nama']}\n"
            f"Kategori: {prod['kategori']}\n"
            f"Harga: Rp {prod['harga']:,}\n"
            f"Stok: {prod['stok']}",
        )

    # ── Kelola produk (lihat daftar) ──────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📦 Kelola Produk" and is_admin(m.from_user.id))
    def btn_kelola_produk(msg: types.Message):
        products = [p for p in db.get_products() if p.get("aktif")]
        if not products:
            bot.send_message(msg.chat.id, "Belum ada produk aktif.")
            return
        kb = types.InlineKeyboardMarkup()
        for p in products:
            kb.add(types.InlineKeyboardButton(
                f"{p['nama']} | Rp {p['harga']:,} | Stok: {p['stok']}",
                callback_data=f"adm_prod:{p['id']}"
            ))
        bot.send_message(msg.chat.id, "📦 <b>Daftar Produk Aktif:</b>", reply_markup=kb)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("adm_prod:"))
    def cb_adm_prod(call: types.CallbackQuery):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "⛔ Bukan admin.", show_alert=True)
            return
        prod_id = call.data.split(":", 1)[1]
        p = db.get_product(prod_id)
        if not p:
            bot.answer_callback_query(call.id, "Produk tidak ditemukan.")
            return
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🗑️ Nonaktifkan Produk", callback_data=f"adm_del:{prod_id}"))
        bot.send_message(
            call.message.chat.id,
            f"📦 <b>{p['nama']}</b>\n"
            f"ID: <code>{p['id']}</code>\n"
            f"Harga: Rp {p['harga']:,}\n"
            f"Stok: {p['stok']}\n"
            f"Kategori: {p['kategori']}",
            reply_markup=kb,
        )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("adm_del:"))
    def cb_adm_del(call: types.CallbackQuery):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "⛔ Bukan admin.", show_alert=True)
            return
        prod_id = call.data.split(":", 1)[1]
        db.delete_product(prod_id)
        bot.answer_callback_query(call.id, "Produk dinonaktifkan.")
        bot.edit_message_text("🗑️ Produk telah dinonaktifkan.", call.message.chat.id, call.message.message_id)

    # ── Laporan ringkas ───────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📊 Laporan" and is_admin(m.from_user.id))
    def btn_laporan(msg: types.Message):
        orders = list(db.get_orders().values())
        total_order   = len(orders)
        total_revenue = sum(o["total"] for o in orders if o["status"] == "SELESAI")
        by_status     = {}
        for o in orders:
            label = STATUS.get(o["status"], o["status"])
            by_status[label] = by_status.get(label, 0) + 1

        status_lines = "\n".join(f"  • {k}: {v}" for k, v in by_status.items())
        produk_aktif = len([p for p in db.get_products() if p.get("aktif")])

        bot.send_message(
            msg.chat.id,
            f"📊 <b>Laporan Toko Pandawa</b>\n\n"
            f"📦 Total Pesanan: <b>{total_order}</b>\n"
            f"💰 Total Pendapatan (Selesai): <b>Rp {total_revenue:,}</b>\n"
            f"🏷️ Produk Aktif: <b>{produk_aktif}</b>\n\n"
            f"<b>Pesanan per Status:</b>\n{status_lines if status_lines else '  —'}",
        )

    # ── Kembali ke menu utama ─────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🏠 Menu Utama" and is_admin(m.from_user.id))
    def btn_home(msg: types.Message):
        from telebot.types import ReplyKeyboardMarkup
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("🛍️ Katalog", "🛒 Keranjang")
        kb.row("📦 Pesanan Saya", "❓ Bantuan")
        bot.send_message(msg.chat.id, "🏠 Kembali ke menu utama.", reply_markup=kb)
