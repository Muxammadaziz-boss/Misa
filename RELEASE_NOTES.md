# 🚀 Misa AI v9.0.2 — Rasmiy Reliz Qaydlari (Release Notes)

🎉 **Misa AI v9.0.2 (Autonomous Windows Agent, Authoritative Security & Platform Hardening) rasmiy barqaror relizi e'lon qilindi!**

Misa AI v9.0.2 rasmiy relizi shaxsiy sun'iy intellekt yordamchisini to'liq avtonom, xavfsiz va Windows muhitida barqaror ishlaydigan yangi bosqichga olib chiqdi. Ushbu versiyada masofaviy buyruq bajaruvchi (remote agent lifecycle), markazlashtirilgan asboblar xavfsizlik siyosati, sessiyadan xabardor Windows GUI controller, agent loop verifikatsiyasi va to'liq platforma mustahkamligi joriy etildi.

---

### 📦 Reliz Binar Fayllari va SHA-256 Nazorat Yig'indisi:

| Fayl nomi | Hajmi | Turi | SHA-256 Nazorat Yig'indisi | Yuklab olish |
| :--- | :--- | :--- | :--- | :--- |
| **`Misa-AI-Setup-v9.0.2.exe`** | **13.55 MB** | Windows NSIS O'rnatuvchisi | `30cca0a57f4140dd2e2effbea83751a6299ac9f03179e516ecb2d8facc031319` | [Yuklab olish](https://github.com/Muxammadaziz-boss/Misa/releases/download/v9.0.2/Misa-AI-Setup-v9.0.2.exe) |
| **`Misa-AI-v9.0.2-Portable.zip`** | **236.55 MB** | To'liq Portativ Paket (Backend bilan) | `fb8eb81cf2ad3f039621d8d872a6bb7307f4bd2fb074d2e71466e7e4b4a9b218` | [Yuklab olish](https://github.com/Muxammadaziz-boss/Misa/releases/download/v9.0.2/Misa-AI-v9.0.2-Portable.zip) |
| **`Misa-AI-v9.0.2.exe`** | **5.20 MB** | Standalone Desktop Executable | `fb8a74752175a9d401cced1d5af3783ef20d2397c74f7e9042de476e5a809a5c` | [Yuklab olish](https://github.com/Muxammadaziz-boss/Misa/releases/download/v9.0.2/Misa-AI-v9.0.2.exe) |
| **`Misa-AI-v9.0.2.msi`** | **14.37 MB** | Windows MSI O'rnatuvchisi | `d07688b384327c978320335eba9eae539d5da5e99f3bb1aefd4ec77bdb0576d8` | [Yuklab olish](https://github.com/Muxammadaziz-boss/Misa/releases/download/v9.0.2/Misa-AI-v9.0.2.msi) |
| **`SHA256SUMS.txt`** | **358 B** | Nazorat Summalari | Mustaqil tekshirilgan | [Yuklab olish](https://github.com/Muxammadaziz-boss/Misa/releases/download/v9.0.2/SHA256SUMS.txt) |
| **`version_manifest.json`** | **2.56 KB** | Kriptografik Manifest | Ed25519 & SHA-256 | [Yuklab olish](https://github.com/Muxammadaziz-boss/Misa/releases/download/v9.0.2/version_manifest.json) |

*Barcha reliz fayllari rasmiy [GitHub Releases Sahifasida](https://github.com/Muxammadaziz-boss/Misa/releases/tag/v9.0.2) joylashtirilgan.*

---

### 🌟 Asosiy Yangiliklar (v9.0.2):

1. **🔐 Vakolatli Asboblar Xavfsizlik Siyosati (Authoritative Security Policy)**:
   - Barcha destruktiv va yuqori xavfli amallar (`system_shutdown`, `system_restart`, `delete_file`, `keyboard_type`, `mouse_click`) markaziy xavfsizlik filtri orqali o'tadi.
   - Kriptografik bir martalik `_confirmation_token`: parametrlar SHA-256 xeshi bilan qat'iy bog'langan, cheklangan muddatli (TTL) va takroriy ishlatishdan himoyalangan (`TOKEN_ALREADY_USED`, `TOKEN_EXPIRED`, `PARAMS_MISMATCH`).
   - Lokal API izolyatsiyasi: `127.0.0.1:18420/api/plugins/execute` endpointi begona Origin/Referer yoki tasdiqlanmagan sessiyalarni 403 `UNAUTHORIZED_LOCAL_CALLER` bilan bloklaydi.

2. **🪟 Sessiyadan Xabardor Windows GUI Controller**:
   - `core/gui/controller.py` orqali DPI-aware oyna boshqaruvi va nishon oyna sarlavhasi/sinfi bo'yicha aniqlash (`find_window`).
   - Win32 `AttachThreadInput` va `BringWindowToTop` orqali Windowsning "focus stealing prevention" cheklovini yengib, oynani ishonchli faollashtirish.
   - Qat'iy precondition (nishon oyna fokusdaligi) va postcondition (matn kiritilgach oyna mavjudligi va yaxlitligi) tekshiruvlari.
   - Har qanday favqulodda vaziyatda harakatlarni bir zumda to'xtatuvchi `abort()` mexanizmi.

3. **🤖 Remote Agent Lifecycle & Poller/Executor Integratsiyasi**:
   - `agent/executor.py` dagi `RemoteCommandExecutor` va `CommandPoller` bevosita `agent/lifecycle.py` boshqaruviga to'liq ulandi.
   - Idempotent polling, takroriy startlardan himoya va 32-bayt nonce yordamida replay-hujumlardan to'liq himoyalangan xizmat.
   - To'xtatish (shutdown/restart) va uzilishlarda barcha fon jarayonlari va soketlarni xavfsiz tozalash mexanizmi.

4. **🧠 Agent Loop Verifikatsiyasi & Lokal Vision Maxfiyligi**:
   - Agent rejasini bajarish jarayonida bir xil asbob takrorlanishini (infinite loop) avtomatik aniqlash va cheklash.
   - Rejalarga to'g'ridan-to'g'ri GUI boshqaruv amallari (click, type, screenshot) integratsiya qilindi.
   - Maxfiylik kafolati: foydalanuvchi ekrani tasvirlari tashqi AI bulutlariga yuborilmaydi (to'liq lokal tahlil qilinadi).

5. **⚙️ Desktop Supervisor Handshake & Platform Hardening**:
   - Rust Tauri supervisor va Python backend o'rtasida `GET /api/health` orqali qat'iy versiya mosligi (`version: 9.0.2`, `app: Misa AI`).
   - Audit va telemetriya loglarida foydalanuvchi parollari, API kalitlari va tokenlari avtomatik ravishda `[REDACTED]` holatiga keltiriladi.
   - PortAudio barqarorligi: xotira buzilishlari (0xC0000005) oldini olish uchun xavfsiz audio loop va VAD boshqaruvi.

---

### 🧪 Sinov va Sifat Kafolati Natijalari (100% PASS):

- **Python Backend Testlari:** 345 / 345 test muvaffaqiyatli o'tdi (**100% PASS**).
- **Frontend Testlari:** 33 / 33 test muvaffaqiyatli o'tdi (**100% PASS**).
- **Frontend Production Build:** TypeScript va Vite build 0 xatolik bilan yakunlandi (**✓ built in 2.07s**).
- **Rust / Tauri Shell:** `cargo check --lib` muvaffaqiyatli o'tdi (**Finished in 19.67s**).
- **Real Windows Smoke-Test:** `tests/smoke_test_rc.py` orqali **8 / 8 test muvaffaqiyatli o'tdi**.

---

### 🏛️ Tarixiy Relizlar:
- [Misa AI v9.0.1](https://github.com/Muxammadaziz-boss/Misa/releases/tag/v9.0.1) — Audio loop hardening & anti-leak
- [Misa AI v9.0.0](https://github.com/Muxammadaziz-boss/Misa/releases/tag/v9.0.0) — Rebranding to Misa AI, Tauri 2.0 + React 19
- [Mikasa AI v8.0.0](https://github.com/Muxammadaziz-boss/Misa/releases/tag/v8.0.0) — Supabase Auth, PC Agent Pairing, Ed25519 Auto-Update
