# 🛒 Panduan Setup Bot Toko Pandawa di VPS

Bot toko Telegram lengkap dengan katalog produk, keranjang belanja,
checkout, pembayaran transfer, konfirmasi admin — semua lewat Telegram.

---

## 📁 Struktur Proyek

```
pandawa-bot/
├── bot.py                    # Entry point Flask + webhook
├── config.py                 # Konfigurasi global & konstanta
├── database.py               # Database JSON (produk & pesanan)
├── cart.py                   # Manajemen keranjang & state sesi
├── handlers/
│   ├── customer.py           # Handler pelanggan (katalog, keranjang, pesanan)
│   ├── checkout.py           # Alur checkout & upload bukti bayar
│   └── admin.py              # Panel admin (konfirmasi, produk, laporan)
├── data/
│   ├── products.json         # Data produk (bisa diedit langsung)
│   └── orders.json           # Data pesanan (otomatis terisi)
├── requirements.txt
├── .env.example
├── nginx-pandawa.conf        # Konfigurasi Nginx
├── pandawa-bot.service       # Systemd service
└── SETUP.md                  # Panduan ini
```

---

## 📋 Prasyarat

| Item | Keterangan |
|------|-----------|
| VPS | Ubuntu 22.04 / Debian 12 |
| Domain | A record → IP VPS, contoh: `pandawa.example.com` |
| Akses | SSH sebagai root / sudo |
| Bot Token | Dari [@BotFather](https://t.me/BotFather) |
| Admin Telegram ID | Cek via [@userinfobot](https://t.me/userinfobot) |

---

## ⚙️ Langkah Setup

### 1. Buat User & Install Paket

```bash
# Buat user khusus
adduser botuser
su - botuser

# Install dependensi
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git
```

### 2. Upload File Bot

```bash
# Dari komputer lokal:
scp -r ./pandawa-bot botuser@IP_VPS:/home/botuser/

# Atau via git:
git clone https://github.com/kamu/pandawa-bot.git /home/botuser/pandawa-bot
```

### 3. Virtual Environment

```bash
cd /home/botuser/pandawa-bot
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Konfigurasi `.env`

```bash
cp .env.example .env
nano .env
```

Isi semua variabel:

```env
BOT_TOKEN=TOKEN_DARI_BOTFATHER

WEBHOOK_URL=https://pandawa.example.com

# Generate SECRET_PATH:
# openssl rand -hex 20
SECRET_PATH=abc123def456ghi789jkl012mno345pq

PORT=5000

# User ID Telegram admin (pisah koma jika >1)
ADMIN_IDS=111111111,222222222

# Chat ID grup admin untuk notifikasi pesanan
# Cara dapat ID grup: tambahkan bot ke grup, lihat via getUpdates
ADMIN_GROUP_ID=-1001234567890
```

> 💡 **Cara dapat ADMIN_GROUP_ID:**
> 1. Tambahkan bot ke grup admin
> 2. Kirim pesan sembarang di grup
> 3. Buka: `https://api.telegram.org/botTOKEN/getUpdates`
> 4. Cari `"chat":{"id":-100xxxxxxxxxx}` — itulah Group ID-nya

### 5. Setup SSL

Pastikan DNS A record sudah mengarah ke IP VPS:

```bash
dig +short pandawa.example.com   # Harus tampil IP VPS kamu
```

Lalu jalankan Certbot:

```bash
sudo certbot --nginx -d pandawa.example.com
```

### 6. Konfigurasi Nginx

```bash
sudo cp /home/botuser/pandawa-bot/nginx-pandawa.conf \
        /etc/nginx/sites-available/pandawa-bot
sudo nano /etc/nginx/sites-available/pandawa-bot
```

Ganti **dua hal** di file tersebut:
- `pandawa.example.com` → domain kamu
- `ganti_string_acak_panjang_di_sini` → nilai `SECRET_PATH` dari `.env`

Aktifkan dan reload:

```bash
sudo ln -s /etc/nginx/sites-available/pandawa-bot \
           /etc/nginx/sites-enabled/
sudo nginx -t          # Harus: "syntax is ok"
sudo systemctl reload nginx
```

### 7. Jalankan sebagai Service

```bash
sudo cp /home/botuser/pandawa-bot/pandawa-bot.service \
        /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pandawa-bot
sudo systemctl start pandawa-bot
sudo systemctl status pandawa-bot   # Harus: active (running)
```

### 8. Daftarkan Webhook

```bash
source /home/botuser/pandawa-bot/venv/bin/activate
cd /home/botuser/pandawa-bot

# Jalankan sekali untuk set webhook, lalu Ctrl+C
python bot.py
```

Atau via curl langsung:

```bash
BOT_TOKEN="ISI_TOKEN"
SECRET="ISI_SECRET_PATH"
DOMAIN="pandawa.example.com"

curl -s "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=https://${DOMAIN}/${SECRET}"
```

### 9. Verifikasi

```bash
# Cek webhook terdaftar
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo" | python3 -m json.tool

# Cek health endpoint
curl https://pandawa.example.com/health
# → {"status": "ok", "toko": "Pandawa"}

# Cek log bot
sudo journalctl -u pandawa-bot -f
```

---

## 🤖 Cara Pakai Bot

### Untuk Pelanggan

| Menu | Fungsi |
|------|--------|
| 🛍️ Katalog | Lihat produk per kategori, tambah ke keranjang |
| 🛒 Keranjang | Lihat & edit keranjang, lanjut ke checkout |
| 📦 Pesanan Saya | Cek status semua pesanan |
| ❓ Bantuan | Panduan cara belanja |

**Alur Belanja:**
```
Katalog → Pilih Produk → Tambah Keranjang
→ Checkout → Isi Nama & Alamat
→ Transfer ke Rekening → Upload Foto Bukti
→ Tunggu Konfirmasi Admin ✅
```

### Untuk Admin

Ketik `/admin` di chat bot untuk masuk panel admin.

| Menu | Fungsi |
|------|--------|
| 📋 Pesanan Masuk | Lihat pesanan menunggu konfirmasi + foto bukti |
| ➕ Tambah Produk | Tambah produk baru lewat percakapan |
| 📦 Kelola Produk | Lihat & nonaktifkan produk |
| 📊 Laporan | Ringkasan total pesanan & pendapatan |

**Alur Konfirmasi Pesanan:**
- Bot otomatis kirim notifikasi + foto bukti ke grup admin
- Admin klik **✅ Konfirmasi** atau **❌ Tolak**
- Pelanggan otomatis dapat notifikasi update status

---

## 🏦 Konfigurasi Rekening Pembayaran

Edit file `config.py`, bagian `REKENING`:

```python
REKENING = [
    {"bank": "BCA",     "no": "NOMOR_REKENING", "nama": "Nama Pemilik"},
    {"bank": "Mandiri", "no": "NOMOR_REKENING", "nama": "Nama Pemilik"},
    {"bank": "GoPay",   "no": "08xx-xxxx-xxxx", "nama": "Nama Pemilik"},
]
```

Setelah edit, restart bot:

```bash
sudo systemctl restart pandawa-bot
```

---

## 🏷️ Kelola Produk via File

Untuk edit produk massal, edit langsung `data/products.json`:

```json
[
  {
    "id": "p001",
    "nama": "Nama Produk",
    "kategori": "Nama Kategori",
    "harga": 50000,
    "stok": 10,
    "deskripsi": "Deskripsi produk",
    "aktif": true
  }
]
```

Set `"aktif": false` untuk menyembunyikan produk tanpa menghapusnya.

---

## 🔄 Perintah Harian

```bash
# Restart bot
sudo systemctl restart pandawa-bot

# Lihat log live
sudo journalctl -u pandawa-bot -f

# Lihat log akses Nginx
sudo tail -f /var/log/nginx/pandawa-bot.access.log

# Perbarui SSL (Certbot auto-renew, tapi bisa test manual)
sudo certbot renew --dry-run

# Backup data pesanan
cp /home/botuser/pandawa-bot/data/orders.json \
   /home/botuser/backup/orders_$(date +%Y%m%d).json
```

---

## 🛠️ Troubleshooting

### Bot tidak merespons pesan
```bash
sudo systemctl status pandawa-bot
sudo journalctl -u pandawa-bot -n 50 --no-pager
curl https://pandawa.example.com/health
```

### Notifikasi tidak masuk ke grup admin
- Pastikan bot sudah dijadikan **admin** di grup
- Pastikan `ADMIN_GROUP_ID` di `.env` sudah benar (diawali `-100`)
- Restart bot setelah edit `.env`

### Error 502 dari Nginx
- Gunicorn tidak berjalan, cek: `sudo journalctl -u pandawa-bot -n 20`

### Foto bukti tidak terkirim ke admin
- Pastikan `client_max_body_size 10M` ada di `nginx-pandawa.conf`
- Reload Nginx: `sudo systemctl reload nginx`

---

## 🔐 Tips Keamanan

- Jangan commit file `.env` ke Git — sudah ada di `.gitignore`
- Aktifkan firewall: `sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable`
- Ganti `SECRET_PATH` secara berkala jika diperlukan
- Backup folder `data/` secara rutin (berisi semua data produk & pesanan)

---

> 🏪 **Toko Pandawa** — Sistem bot siap pakai, selamat berjualan!
