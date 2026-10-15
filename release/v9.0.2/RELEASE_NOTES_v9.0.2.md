# Misa AI v9.0.2 — Autonomous Windows Agent, Authoritative Security & Platform Hardening

Misa AI v9.0.2 rasmiy relizi shaxsiy sun'iy intellekt yordamchisini to'liq avtonom, xavfsiz va Windows muhitida barqaror ishlaydigan yangi bosqichga olib chiqdi. Ushbu versiyada masofaviy buyruq bajaruvchi (remote agent lifecycle), markazlashtirilgan asboblar xavfsizlik siyosati, sessiyadan xabardor Windows GUI controller, agent loop verifikatsiyasi va to'liq platforma mustahkamligi joriy etildi.

---

### 🌟 Asosiy Yangiliklar va Imkoniyatlar

#### 1. Remote Agent Lifecycle & Poller/Executor Integratsiyasi
- `agent/executor.py` dagi `RemoteCommandExecutor` va `CommandPoller` bevosita `agent/lifecycle.py` boshqaruviga to'liq ulandi.
- Idempotent polling, takroriy startlardan xavfsiz himoya va 32-bayt nonce yordamida replay-hujumlardan to'liq kafolatlangan xavfsizlik.
- To'xtatish (shutdown/restart) va uzilishlarda barcha fon jarayonlari va soketlarni xavfsiz tozalash mexanizmi.

#### 2. Vakolatli Asboblar Xavfsizlik Siyosati (Authoritative Security Policy)
- Barcha yuqori xavfli amallar (`system_shutdown`, `delete_file`, `keyboard_type`, `mouse_click`, `clear_memory`) markaziy xavfsizlik dvigateli orqali tekshiriladi.
- Kriptografik bir martalik tasdiqlash tokenlari (`ConfirmationTokenManager`): parametrlar SHA-256 xeshi bilan bog'langan, cheklangan muddatli (TTL) va takroriy sarflashdan himoyalangan (`TOKEN_ALREADY_USED`, `TOKEN_EXPIRED`, `PARAMS_MISMATCH`).
- Lokal API izolyatsiyasi: `127.0.0.1:18420/api/plugins/execute` endpointi begona Origin/Referer yoki sessiya tokensiz so'rovlarni qat'iy 403 `UNAUTHORIZED_LOCAL_CALLER` bilan rad etadi.

#### 3. Sessiyadan Xabardor Windows GUI Controller
- `core/gui/controller.py` orqali DPI-aware oyna boshqaruvi va nishon oyna sarlavhasi/sinfi bo'yicha aniqlash (`find_window`).
- Win32 `AttachThreadInput` va `BringWindowToTop` orqali Windowsning "focus stealing prevention" cheklovini yengib, oynani ishonchli faollashtirish.
- Qat'iy precondition (nishon oyna fokusdaligi) va postcondition (matn kiritilgach oyna tirikligi va yaxlitligi) tekshiruvlari.
- Har qanday favqulodda vaziyatda input amallarini bir zumda to'xtatuvchi `abort()` nazorati.

#### 4. Agent Loop Verifikatsiyasi & Lokal Vision Maxfiyligi
- Agent rejasini bajarish jarayonida bir xil asbob takrorlanishini (infinite loop) avtomatik aniqlash va cheklash.
- Rejalarga to'g'ridan-to'g'ri GUI boshqaruv amallari (click, type, screenshot) integratsiya qilindi.
- Maxfiylik kafolati: foydalanuvchi ekrani tasvirlari hech qanday tashqi AI bulutlariga yuborilmaydi (to'liq lokal tahlil qilinadi).

#### 5. Desktop Supervisor Handshake & Platform Hardening
- Rust Tauri supervisor va Python backend o'rtasida `GET /api/health` orqali qat'iy versiya mosligi (`version: 9.0.2`, `app: Misa AI`). Versiya mos kelmasa, eskirgan jarayon avtomatik xavfsiz tozalanadi.
- `BrowserAutomationAdapter`: Chrome, Brave, Edge va boshqa brauzer tablarini boshqarish va DOM amallari interfeysi.
- Screenshot xatosi yuz berganda soxta `captured: true` qaytmasligi ta'minlandi.
- Audit va telemetriya loglarida foydalanuvchi parollari, API kalitlari va tokenlari avtomatik ravishda `[REDACTED]` holatiga keltiriladi.

---

### 🧪 Sinov va Sifat Kafolati Natijalari

- **Python Testlari:** 345 / 345 test muvaffaqiyatli o'tdi (**100% PASS**).
- **Frontend Testlari:** 33 / 33 test muvaffaqiyatli o'tdi (**100% PASS**).
- **Frontend Production Build:** TypeScript va Vite build 0 xatolik bilan yakunlandi (**✓ built in 2.07s**).
- **Rust / Tauri Shell:** `cargo check --lib` muvaffaqiyatli o'tdi (**Finished in 19.67s**).
- **Real Windows Smoke-Test:**
  - Backend Handshake: HTTP 200, `version: 9.0.2`, `app: Misa AI` (`✓ PASS`)
  - Remote Agent Lifecycle: start, duplicate start protection, stop (`✓ PASS`)
  - Unconfirmed GUI Action: tasdiqsiz bloklanish va challenge yaratilishi (`✓ PASS`)
  - Real Windows Notepad Sandbox: ochish, fokuslash, xavfsiz yozish, postcondition tekshirish va tozalash (`✓ PASS`)
  - Screenshot Hardening: soxta true yo'qligi (`✓ PASS`)
  - Local API Security: 403 `UNAUTHORIZED_LOCAL_CALLER` (`✓ PASS`)
  - Replay & Expiry: `TOKEN_ALREADY_USED`, `TOKEN_EXPIRED` (`✓ PASS`)
  - Destructive Actions: quvvat, o'chirish va input amallarining tasdiqsiz bloklanishi (`✓ PASS`)

---

### 📦 Reliz Artefaktlari va SHA-256 Nazorat Summalari

| Fayl nomi | Tavsif | Hajmi | SHA-256 Checksum |
|---|---|---|---|
| `Misa-AI-v9.0.2.exe` | Mustaqil ishga tushuvchi ilova | 5.20 MB (5,449,216 bayt) | `fb8a74752175a9d401cced1d5af3783ef20d2397c74f7e9042de476e5a809a5c` |
| `Misa-AI-Setup-v9.0.2.exe` | Windows NSIS O'rnatuvchisi | 13.55 MB (14,203,721 bayt) | `30cca0a57f4140dd2e2effbea83751a6299ac9f03179e516ecb2d8facc031319` |
| `Misa-AI-v9.0.2.msi` | Windows MSI O'rnatuvchisi | 14.37 MB (15,065,088 bayt) | `d07688b384327c978320335eba9eae539d5da5e99f3bb1aefd4ec77bdb0576d8` |
| `Misa-AI-v9.0.2-Portable.zip` | To'liq portativ paket (Backend bilan) | 236.55 MB (248,041,699 bayt) | `fb8eb81cf2ad3f039621d8d872a6bb7307f4bd2fb074d2e71466e7e4b4a9b218` |
| `SHA256SUMS.txt` | Mustaqil tekshirilgan checksumlar | 355 B | `2f98642a8a8167f5e3bf739097e3f847ffb58cfaf44321b7952a819d9b04f7f6` |
