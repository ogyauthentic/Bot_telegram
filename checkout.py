"""
Handler alur checkout:
Cart → Isi data → Tampil rekening → Upload bukti → Notif admin
"""
import telebot
from telebot import types

import database as db
import cart as Cart
from config import REKENING, ADMIN_GROUP, TOKO_NAMA, STATUS


def register_checkout_handlers(bot: telebot.TeleBot):

    def _rekening_txt() -> str:
        lines = ["🏦 <b>Rekening Pembayaran:</b>\n"]
        for r in REKENING:
            lines.append(f"• <b>{r['bank']}</b>: <code>{r['no']}</code> a/n {r['nama']}")
        return "\n".join(lines)

    # ── Step 1: mulai checkout ─────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data == "checkout")
    def cb_checkout(call: types.CallbackQuery):
        user_id = call.from_user.id
        if not Cart.get_cart(user_id):
            bot.answer_callback_query(call.id, "Keranjang kosong!", show_alert=True)
            return
        Cart.set_state(user_id, "tunggu_nama")
        bot.send_message(
            call.message.chat.id,
            "📝 <b>Checkout</b>\n\nMasukkan <b>nama lengkap</b> penerima:"
        )
        bot.answer_callback_query(call.id)

    # ── Step 2: terima nama, minta alamat ─────────────────────────────────────
    @bot.message_handler(func=lambda m: (Cart.get_state(m.from_user.id) or {}).get("step") == "tunggu_nama")
    def step_nama(msg: types.Message):
        Cart.set_state(msg.from_user.id, "tunggu_alamat", nama=msg.text.strip())
        bot.send_message(msg.chat.id, "📍 Masukkan <b>alamat lengkap</b> pengiriman:")

    # ── Step 3: terima alamat, buat pesanan, tampil rekening ──────────────────
    @bot.message_handler(func=lambda m: (Cart.get_state(m.from_user.id) or {}).get("step") == "tunggu_alamat")
    def step_alamat(msg: types.Message):
        user_id  = msg.from_user.id
        state    = Cart.get_state(user_id)
        cart     = Cart.get_cart(user_id)

        order = db.create_order(
            user_id  = user_id,
            username = msg.from_user.username or "",
            nama     = state["nama"],
            alamat   = msg.text.strip(),
            cart     = cart,
        )

        Cart.clear_cart(user_id)
        Cart.set_state(user_id, "tunggu_bukti", order_id=order["id"])

        items_txt = "\n".join(f"  • {i['nama']} x{i['qty']} = Rp {i['harga']*i['qty']:,}" for i in order["items"])
        ringkasan = (
            f"✅ <b>Pesanan Dibuat!</b>\n\n"
            f"🧾 ID: <code>{order['id']}</code>\n"
            f"👤 Nama: {order['nama']}\n"
            f"📍 Alamat: {order['alamat']}\n\n"
            f"🛒 <b>Item:</b>\n{items_txt}\n\n"
            f"💰 <b>Total: Rp {order['total']:,}</b>\n\n"
            f"{_rekening_txt()}\n\n"
            "Setelah transfer, kirimkan <b>foto bukti pembayaran</b> di sini."
        )
        bot.send_message(msg.chat.id, ringkasan)

    # ── Step 4: terima foto bukti bayar ───────────────────────────────────────
    @bot.message_handler(
        content_types=["photo"],
        func=lambda m: (Cart.get_state(m.from_user.id) or {}).get("step") == "tunggu_bukti"
    )
    def step_bukti(msg: types.Message):
        user_id  = msg.from_user.id
        state    = Cart.get_state(user_id)
        order_id = state["order_id"]
        file_id  = msg.photo[-1].file_id   # ambil resolusi tertinggi

        db.set_bukti_bayar(order_id, file_id)
        Cart.clear_state(user_id)

        bot.send_message(
            msg.chat.id,
            f"📸 Bukti pembayaran diterima!\n\n"
            f"🧾 Pesanan <code>{order_id}</code> sedang menunggu konfirmasi admin.\n"
            f"Kamu bisa cek status via <b>📦 Pesanan Saya</b>."
        )

        # Notifikasi ke grup admin
        if ADMIN_GROUP:
            order = db.get_order(order_id)
            items_txt = "\n".join(f"  • {i['nama']} x{i['qty']}" for i in order["items"])
            admin_teks = (
                f"🔔 <b>PEMBAYARAN MASUK — {TOKO_NAMA}</b>\n\n"
                f"🧾 ID: <code>{order_id}</code>\n"
                f"👤 {order['nama']} (@{order['username'] or 'N/A'})\n"
                f"📍 {order['alamat']}\n\n"
                f"🛒 Item:\n{items_txt}\n\n"
                f"💰 Total: <b>Rp {order['total']:,}</b>"
            )
            kb = types.InlineKeyboardMarkup()
            kb.row(
                types.InlineKeyboardButton("✅ Konfirmasi", callback_data=f"adm_ok:{order_id}"),
                types.InlineKeyboardButton("❌ Tolak",      callback_data=f"adm_no:{order_id}"),
            )
            kb.add(types.InlineKeyboardButton("⚙️ Tandai Diproses", callback_data=f"adm_proses:{order_id}"))
            kb.add(types.InlineKeyboardButton("🚚 Tandai Dikirim",  callback_data=f"adm_kirim:{order_id}"))

            bot.send_photo(ADMIN_GROUP, file_id, caption=admin_teks, reply_markup=kb)
