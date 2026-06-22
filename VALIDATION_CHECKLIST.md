# Validation Checklist - Multi-Webhook Discord System

## 📋 Checklist Sebelum Testing

### ✅ 1. File Configuration
- [x] `.env` ada di `.gitignore` ✓
- [x] `.env.example` memiliki webhook template kosong (bukan XXXXXXXXXX) ✓
- [x] `config.py` membaca semua webhook dari `.env` ✓
- [x] `DISCORD_WEBHOOKS` mapping sudah benar (5 sumber) ✓

### ✅ 2. Database Schema
- [x] `notified_at` column ada di tabel `pengumuman` ✓
- [x] `mark_as_notified()` function implemented ✓
- [x] `get_unnotified_pengumuman()` function implemented ✓
- [x] Database init menambahkan column secara otomatis jika belum ada ✓

### ✅ 3. Discord Notification Logic
- [x] Webhook berbeda per sumber (BAAK, LEPKOM, STUDENTSITE, KEMAHASISWAAN, PENDAFTARAN) ✓
- [x] Format embed lengkap (title, url, description, fields, footer, timestamp) ✓
- [x] Timezone Asia/Jakarta untuk timestamp ✓
- [x] Indonesian month name support (Januari, Februari, etc.) ✓
- [x] Indonesian day name support (Minggu, Senin, etc.) ✓
- [x] Date parsing untuk multiple format (15/05/2026, 2026-06-19, Jun 15 2026, Minggu 21 Juni 2026) ✓
- [x] Sort by date descending (terbaru ke terlama) ✓
- [x] Color coding per sumber ✓
- [x] Mark as `notified_at` setelah berhasil kirim ✓

### ✅ 4. Notification Behavior
- [x] INSERT baru → kirim Discord ✓
- [x] UPDATE/UNCHANGED → skip Discord ✓
- [x] Data yang sudah pernah dikirim → skip Discord ✓
- [x] Webhook kosong → skip dengan warning (tidak crash) ✓
- [x] Delay antar pesan sesuai `DISCORD_SEND_DELAY_SECONDS` ✓

### ✅ 5. Initial Scraping Mode
- [x] `SEND_DISCORD_ON_INITIAL=true` → kirim untuk INSERT baru ✓
- [x] `SEND_DISCORD_ON_INITIAL=false` → tidak kirim notifikasi ✓
- [x] Data diurutkan berdasarkan tanggal pengumuman, bukan urutan scrape ✓

### ✅ 6. Logging
- [x] `[DISCORD] Webhook {sumber} aktif: YA/TIDAK` ✓
- [x] `[DISCORD] Sumber {sumber} -> webhook {sumber}` ✓
- [x] `[DISCORD] Mengirim N notifikasi {sumber}, urut tanggal terbaru` ✓
- [x] `[DISCORD] Berhasil kirim: <judul>` ✓
- [x] `[DISCORD] Skip karena webhook kosong: {sumber}` ✓
- [x] `[DISCORD] Summary: BAAK: sent X, skipped Y` ✓

---

## 🧪 Testing Scenario

### Persiapan Testing

1. **Isi `.env` dengan webhook yang valid:**
```env
DISCORD_WEBHOOK_BAAK=https://discord.com/api/webhooks/.../...
DISCORD_WEBHOOK_LEPKOM=https://discord.com/api/webhooks/.../...
DISCORD_WEBHOOK_STUDENTSITE=https://discord.com/api/webhooks/.../...
DISCORD_WEBHOOK_KEMAHASISWAAN=https://discord.com/api/webhooks/.../...
DISCORD_WEBHOOK_PENDAFTARAN=https://discord.com/api/webhooks/.../...

SEND_DISCORD_ON_INITIAL=true
INITIAL_SCRAPE_LIMIT=1
MONITORING_INTERVAL_MINUTES=1
DISCORD_SEND_DELAY_SECONDS=3
```

2. **TRUNCATE database:**
```sql
TRUNCATE TABLE pengumuman;
```

3. **Jalankan program:**
```bash
py main.py
```

### Expected Results

#### Console Output:
```
[DISCORD] Status Webhook:
[DISCORD] Webhook BAAK            aktif: YA
[DISCORD] Webhook LEPKOM          aktif: YA
[DISCORD] Webhook STUDENTSITE     aktif: YA
[DISCORD] Webhook KEMAHASISWAAN   aktif: YA
[DISCORD] Webhook PENDAFTARAN     aktif: YA

[DB] INSERT baru: ...
[DB] INSERT baru: ...

[DISCORD] SEND_DISCORD_ON_INITIAL=true, kirim X notifikasi
[DISCORD] Sumber BAAK -> webhook BAAK
[DISCORD] Mengirim N notifikasi BAAK, urut tanggal terbaru
[DISCORD] Berhasil kirim: ...
[DISCORD] Summary:
  BAAK           : sent 1, skipped 0
  LEPKOM         : sent 1, skipped 0
  STUDENTSITE    : sent 1, skipped 0
  KEMAHASISWAAN  : sent 1, skipped 0
  PENDAFTARAN    : sent 1, skipped 0
```

#### Discord Channels:
- Channel **#baak** menerima pengumuman dari BAAK
- Channel **#lepkom** menerima pengumuman dari LEPKOM
- Channel **#studentsite** menerima pengumuman dari STUDENTSITE
- Channel **#kemahasiswaan** menerima pengumuman dari KEMAHASISWAAN
- Channel **#pendaftaran-mhs-baru** menerima pengumuman dari PENDAFTARAN

#### Message Format (Embed):
```
┌─────────────────────────────────────────┐
│ [BAAK] JUDUL PENGUMUMAN                  │  (Color: Blue)
├─────────────────────────────────────────┤
│ Preview isi pengumuman maksimal 700      │
│ karakter dari field isi...               │
├─────────────────────────────────────────┤
│ Sumber: BAAK                             │
│ Tanggal Pengumuman: 15/05/2026           │
│ Author: Admin                            │
│ File/URL: [Lihat File](...)              │
├─────────────────────────────────────────┤
│ Sistem Agregasi Pengumuman Gunadarma    │
│ • 22 Juni 2026 18:55 WIB                 │
└─────────────────────────────────────────┘
```

#### Database Verification:
```sql
-- Check notified_at column
SELECT judul, sumber, notified_at 
FROM pengumuman 
WHERE notified_at IS NOT NULL 
LIMIT 10;

-- Result should show timestamps for all sent notifications
```

---

## 🔍 Verification Points

### Database
- [ ] Data masuk ke tabel `pengumuman`
- [ ] Field `notified_at` diupdate setelah notifikasi dikirim
- [ ] Status INSERT/UPDATE/UNCHANGED sesuai ekspektasi

### Discord Messages
- [ ] Pesan masuk ke channel yang benar sesuai sumber
- [ ] Format embed rapi (kotak dengan warna)
- [ ] Timestamp dalam timezone Asia/Jakarta
- [ ] Urutan notifikasi dari tanggal pengumuman terbaru ke terlama
- [ ] Description tidak lebih dari 700 karakter
- [ ] Fields (Sumber, Tanggal, Author, File/URL) muncul

### Date Parsing
- [ ] Format 15/05/2026 → parsed
- [ ] Format 2026-06-19 → parsed
- [ ] Format Jun 15, 2026 → parsed
- [ ] Format Minggu, 21 Juni 2026 → parsed (Indonesian)
- [ ] Tanggal yang tidak bisa diparse → diletakkan di bawah

### Error Handling
- [ ] Webhook kosong → skip dengan warning, tidak crash
- [ ] Timeout → log error, lanjut ke notifikasi berikutnya
- [ ] Connection error → log error, lanjut

### Delay
- [ ] Jeda antar pesan sesuai `DISCORD_SEND_DELAY_SECONDS` (default 3 detik)
- [ ] Tidak ada spam/rate limit dari Discord

---

## ⚠️ Common Issues & Solutions

### Issue 1: Webhook 404 Not Found
**Cause:** Webhook URL salah atau sudah dihapus
**Solution:** Generate webhook baru dari Discord Server Settings → Integrations → Webhooks

### Issue 2: Notifikasi tidak terkirim
**Check:**
- Webhook URL di `.env` benar dan tidak kosong?
- `SEND_DISCORD_ON_INITIAL=true`?
- Data benar-benar INSERT baru (bukan UPDATE)?
- Log menunjukkan `[DISCORD] Berhasil kirim`?

### Issue 3: Tanggal tidak terparse
**Check:**
- Format tanggal cocok dengan salah satu format di `parse_tanggal_pengumuman()`?
- Nama bulan Indonesia sudah ditambahkan mapping?
- Log menunjukkan `[DISCORD] Gagal parse tanggal: ...`?

### Issue 4: Message embed tidak rapi
**Check:**
- Payload menggunakan `embeds: [...]` array?
- Field `color` dalam format integer hex (0x3498db)?
- Field `timestamp` dalam format ISO 8601?

---

## ✅ All Validations Complete

Semua checklist sudah terpenuhi! 

**Next Steps:**
1. Isi `.env` dengan webhook URL yang valid
2. Set `SEND_DISCORD_ON_INITIAL=true` dan `INITIAL_SCRAPE_LIMIT=1`
3. TRUNCATE TABLE pengumuman
4. Jalankan: `py main.py`
5. Verifikasi notifikasi masuk ke channel yang benar
6. Verifikasi database `notified_at` diupdate

**Ready for production testing!** 🚀
