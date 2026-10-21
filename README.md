# 🔷 MISA AI (sobiq Mikasa AI) — Autonomous Desktop Assistant & Intelligence Hub

> **📢 MUHIM E'LON (v9.0.0 Rebranding & v9.3.0 Release): 9-versiyadan boshlab "Mikasa AI" loyihasi rasmiy ravishda "Misa" (`Misa AI`) deb yuritiladi!**  
> *1.0.0 dan 8.0.0 gacha bo'lgan barcha barqaror versiyalarda loyiha **Mikasa AI** nomi bilan ishlab chiqilgan va arxivlangan (`main` / `dev-v8.0.0`). **9.0.0 versiyadan (`dev-v9.0.0`) boshlab** loyiha yadrosi, desktop interfeysi (`Misa/`), ovozli chaqiruv tizimi ("Salom Misa"), Windows PC agenti va barcha hujjatlar **Misa AI** nomi ostida davom ettiriladi.*

> **O'zbek tilidagi birinchi professional avtonom AI desktop yordamchisi va aqlli orkestratori (v9.3.0 Barqaror Reliz)**  
> React 19 + Tauri 2.0 zamonaviy aero-shisha interfeysi, Model Context Protocol (MCP) ko'prigi, Stitch UI generatori, Multi-Provider AI (Gemini 3.8 Flash, Groq Llama 3.3, Cerebras, OpenRouter), Neural RVC (Retrieval-based Voice Conversion) va Edge-TTS ovoz dvigatellari, Supabase Auth ko'p foydalanuvchili (multi-tenant) xavfsiz autentifikatsiyasi, Google OAuth 2.0, Ed25519 kriptografik PC Agent Enrollment & Pairing, Universal Telegram Bot (`@Mikasa_ai_agent_bot`) orqali masofaviy boshqaruv, Wake-on-LAN, ko'p bosqichli intellektual boshqaruv (Agent Loop 2.0), Authoritative Tool Security, Session-Aware Windows GUI Controller va Ed25519 imzolangan xavfsiz auto-update tizimi.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-Tauri%202.0%20%7C%20React%2019-61DAFB?style=flat&logo=react&logoColor=black)](Misa/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows)](https://microsoft.com/windows)
[![Stable Release](https://img.shields.io/badge/Stable%20Release-v9.3.0-success)](https://github.com/Muxammadaziz-boss/Misa/releases/tag/v9.3.0)
[![Active Branch](https://img.shields.io/badge/Active%20Branch-dev--v9.0.0-blueviolet)](https://github.com/Muxammadaziz-boss/Misa/tree/dev-v9.0.0)
[![CI Checks](https://img.shields.io/badge/CI%20Checks-9%2F9%20Passing%20%7C%20100%25%20Green-brightgreen)](https://github.com/Muxammadaziz-boss/Misa/actions)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🏷️ Loyiha Nomi Evolyutsiyasi: Mikasa AI ➔ Misa AI (v9.0.0+)

| Versiya davri | Rasmiy nom | Git Branch | Frontend Katalogi | Izoh |
| :--- | :--- | :--- | :--- | :--- |
| **v1.0.0 – v8.0.0** | **Mikasa AI** | `main`, `dev-v8.0.0` | `mikasa-7/` | 8-versiyagacha bo'lgan barcha relizlar va tarixiy arxitektura o'z holicha saqlanadi. |
| **v9.0.0 – v9.0.2** | **Misa AI** | `dev-v9.0.0` | `Misa/` | Yangi Tauri 2.0 + React 19 interfeysi, ovozli boshqaruv ("Salom Misa") va PC Agent. |
| **v9.2** | **Misa AI** | `dev-v9.0.0` | `Misa/` | 9.2 Versiya sinxronizatsiyasi, yangi relizlar paketi va to'liq platforma barqarorligi. |
| **v9.3.0 (Eng so'nggi barqaror reliz)** | **Misa AI** | `dev-v9.0.0` | `Misa/` | **Model Context Protocol (MCP)** arxitekturasi, **Stitch UI Generator**, **Multi-Provider AI Key Manager** (Gemini, Groq, Cerebras, OpenRouter), **Neural RVC & Edge-TTS** ovozli dvigateli, 56 ta tizim vositalari, 100% Portativ binar relizlar va to'liq yashil CI (GitHub Actions 9/9). |

---

## 📸 Ilovaning Haqiqiy Interfeysi (Visual Showcase)

### 🪐 1. Bosh Sahifa va Interaktiv Misa Orb
*Haqiqiy vaqt rejimida yordamchi holatini (10 xil jonli holat: idle, listening, thinking, speaking, executing va h.k.) ko'rsatuvchi vizual yadro, jonli apparat telemetriyasi (CPU/RAM), tezkor AI harakatlari va to'liq ovozli boshqaruv.*
![Bosh sahifa va AI Orb](docs/assets/landing_preview.png)

---

### ⚡ 2. Buyruqlar Markazi — 56 ta Tizim Vositalari (Tool System 2.0)
*Klaviatura orqali tezkor boshqaruv (`Ctrl+K`), tizim asboblarini toifalash (Tizim, Ilovalar, Utilitlar, Dasturlash, Multimedia, Xotira, Rejalashtirish), interaktiv parametrlar va xavfsiz ijro.*
![Buyruqlar markazi](docs/assets/commands_preview.png)

---

### 💬 3. Intellektual AI Suhbat va Zamonaviy Glassmorphism
*Fikrlovchi Gemini, Groq, Cerebras va OpenRouter modellari, kontekstni to'liq saqlash, avtonom agent rejalari, rasm va kod tahlili hamda silliq aero-shisha vizual effektlari.*
![AI Suhbat](docs/assets/chat_preview.png)

---

### ⚙️ 4. Shaxsiy Profil, Ovoz va AI Dvigatellari (Quiet Intelligence Hub)
*Ovozli dvigatellar (Neural RVC HuBERT & Microsoft Edge-TTS), jonli apparat audio monitori (Loopback), ko'p modelli AI kalitlari boshqaruvi va profil sozlamalari.*
![Sozlamalar va Ovoz Dvigatellari](docs/assets/settings_preview.png)

---

### 🎨 5. Quiet Intelligence — Maxsus Vektor Ikonkalar Tizimi
*Matnli emojilardan butunlay xoli, 26 ta kanonik SVG piktogrammalar va premium qora dizayn karkasi.*
![Misa AI Vektor Ikonkalar Tizimi](docs/assets/icon_showcase.png)

---

## 🌟 9.3-Versiyadagi Asosiy Imkoniyatlar (v9.3.0 — Eng So'nggi Barqaror Reliz)

1. **🤖 Multi-Provider AI va Standart API Kalitlari**:
   - **Gemini 3.8 Flash**, **Groq (Llama 3.3 70B Versatile)**, **Cerebras (Llama 3.3 70B Ultra-fast)** va **OpenRouter** tizimga standart integratsiya qilingan va dastur ishga tushishi bilanoq darhol AI bilan ishlashga tayyor.
   - Dynamic Key Manager: Foydalanuvchi Sozlamalar sahifasida o'zining shaxsiy API kalitini kiritishi mumkin va shaxsiy kalit standart tizim kalitidan ustun turadi (priority override).

2. **🎙️ Neural RVC & Yangilangan Edge-TTS Ovoz Tizimi**:
   - Microsoft Edge-TTS yangi `Sec-MS-GEC v2` token protokoli bilan to'liq yangilandi (`edge-tts 7.3.1`). Madina (Ayol) va Sardor (Erkak) milliy ovozlari to'liq tiklandi.
   - Lokal RVC (Retrieval-based Voice Conversion) tizimi: `torch`, `torchaudio`, `faiss-cpu` va `hubert_base.pt` modeli (189.5 MB) integratsiyasi.
   - 6 xil ovoz modeli (`ayol`, `erkak`, `fish_yigit`, `fish_anime`, `ashley`, `yukari`) va ovoz to'xtab qolmasligi uchun Madinaga avtomatik xavfsiz fallback.

3. **🔌 Model Context Protocol (MCP) ko'prigi & Stitch UI Generator**:
   - Anthropic Model Context Protocol (MCP) standartiga mos asboblar va tashqi servislar integratsiyasi ko'prigi.
   - Stitch UI generatori: foydalanuvchi so'rovi asosida dinamik, chiroyli va interaktiv vizual vidjetlar generatsiya qilish.

4. **🔐 Vakolatli Asboblar Xavfsizlik Siyosati (Authoritative Security Policy)**:
   - 56 ta tizim va lokal vositalar (`system_shutdown`, `system_restart`, `delete_file`, `keyboard_type`, `mouse_click`, `file_manager` va h.k.) uchun markaziy xavfsizlik nazorati.
   - Kriptografik bir martalik `_confirmation_token`: parametrlar SHA-256 xeshi bilan qat'iy bog'langan, 60s TTL va takroriy ishlatishdan himoyalangan (`TOKEN_ALREADY_USED`, `PARAMS_MISMATCH`).
   - Lokal API izolyatsiyasi: `127.0.0.1:18420/api/plugins/execute` endpointi begona Origin/Referer yoki tasdiqlanmagan sessiyalarni 403 `UNAUTHORIZED_LOCAL_CALLER` bilan bloklaydi.

5. **🪟 Sessiyadan Xabardor Windows GUI Controller**:
   - `core/gui/controller.py` orqali DPI-aware oyna boshqaruvi va sarlavha/sinf bo'yicha oynalarni aniqlash (`find_window`).
   - Win32 `AttachThreadInput` va `BringWindowToTop` orqali Windowsning "focus stealing prevention" cheklovini yengib, oynani ishonchli faollashtirish.
   - Qat'iy precondition (nishon oyna fokusdaligi) va postcondition (matn kiritilgach oyna mavjudligi) tekshiruvlari.
   - Favqulodda vaziyatlarda harakatlarni bir zumda to'xtatuvchi `abort()` nazorati.

6. **🤖 Remote Agent Lifecycle & Poller/Executor**:
   - `agent/executor.py` dagi `RemoteCommandExecutor` va `CommandPoller` bevosita `agent/lifecycle.py` boshqaruviga to'liq ulangan.
   - Idempotent polling, takroriy startlardan himoya va 32-bayt nonce yordamida replay-hujumlardan to'liq himoyalangan xizmat.
   - Shutdown/restart va uzilishlarda barcha fon jarayonlari va soketlarni xavfsiz tozalash mexanizmi.

7. **🧠 Agent Loop 2.0 & Lokal Vision Maxfiyligi**:
   - Agent rejasini bajarish jarayonida cheksiz sikllardan (infinite loop) himoya.
   - Rejalarga bevosita GUI amallari (click, type, screenshot) integratsiya qilingan.
   - Foydalanuvchi ekrani tasvirlari hech qanday tashqi AI bulutlariga yuborilmaydi (to'liq lokal tahlil qilinadi).

8. **⚙️ Desktop Supervisor Handshake & Platform Hardening**:
   - Rust Tauri supervisor va Python backend o'rtasida `GET /api/health` orqali qat'iy versiya mosligi (`version: 9.3.0`, `app: MISA AI`).
   - Telemetriya va loglarda foydalanuvchi parollari va API kalitlari avtomatik `[REDACTED]` holatiga keltiriladi.

---

## 🏛️ 8-Versiyadagi Barcha Yangiliklar va To'liq Arxitektura (v8.0.0 / Phases 35–48)

* **🌐 Masofaviy Boshqaruv & Wake-on-LAN**: UDP Magic Packet orqali kompyuterni masofadan uyg'otish va kriptografik `RemoteCommandEnvelope` (120s TTL).
* **🔐 Masofaviy Sessiya Autentifikatsiyasi**: 3 darajali ruxsat profillari (`SAFE_READONLY`, `STANDARD_CONTROL`, `FULL_ADMIN`) va 15+ masofaviy vositalar.
* **🤖 Universal Telegram Bot (`@Mikasa_ai_agent_bot`)**: 6-xonali OTP kod orqali Telegram akkauntni xavfsiz bog'lash va brute-force himoyasi.
* **🖥️ Ko'p Qurilmali Boshqaruv (Multi-Device)**: Bitta hisobga bir nechta kompyuterni ulash va alohida izolyatsiyalangan sessiyalar yuritish.
* **🛡️ Supabase Auth, JWT & Multi-Tenant RLS**: Zero backend password storage, ES256/RS256 JWKS va HS256 tekshiruvi, ma'lumotlar bazasi darajasida RLS izolyatsiyasi.
* **🔑 Kriptografik PC Agent Enrollment & Ed25519 Pairing**: Asimmetrik Ed25519 kalitlar juftligi, Windows DPAPI shifrlash va 32-bayt nonce challenge-response.
* **🔗 Google OAuth 2.0**: Desktop Tauri ilovasi va mahalliy listener o'rtasida mustahkam OAuth ko'prigi.
* **⚙️ Mustaqil PC Agent & Sandboxed Tool Execution**: `PathSecurityValidator` orqali tizim kataloglari va maxfiy ma'lumotlarni (`C:\Windows`, `.ssh`, `.env`) qat'iy bloklash.
* **🔄 Secure Auto-Update & Crash-Safe Rollback Engine**: Ed25519 raqamli imzosi va SHA-256 bilan himoyalangan yangilanishlar.

---

## 📦 Rasmiy Windows Relizlar (v9.3.0 — Eng So'nggi Barqaror Reliz / Latest)

Barcha reliz fayllari mustaqil kriptografik SHA-256 xeshlari bilan tekshirilgan va rasmiy [GitHub Releases Sahifasida](https://github.com/Muxammadaziz-boss/Misa/releases/tag/v9.3.0) joylashtirilgan:

| Fayl nomi | Tavsif | Hajmi | SHA-256 Checksum | Yuklab olish |
| :--- | :--- | :---: | :--- | :---: |
| **`Misa-AI-v9.3-Portable.zip`** | 📦 **To'liq Portativ Paket (Backend + Python Runtime + RVC HuBERT bilan)** | **470.45 MB** | `008f1f159dd8357c63b470281086ca479d9d79d7d530c4b7c00841ec8a94cbc9` | [Yuklab olish](https://github.com/Muxammadaziz-boss/Misa/releases/download/v9.3.0/Misa-AI-v9.3-Portable.zip) |
| **`Misa-AI-v9.3.exe`** | 🚀 **Mustaqil Standalone Desktop Executable** | **5.24 MB** | `9d7d3e8122181176354c35e92854f7b8780926b0ededc649a231c6da5d58982f` | [Yuklab olish](https://github.com/Muxammadaziz-boss/Misa/releases/download/v9.3.0/Misa-AI-v9.3.exe) |
| **`MicrosoftEdgeWebview2Setup.exe`** | 🌐 **Offline Windows WebView2 Bootstrapper** | **1.77 MB** | `87ad3fe4e3faa1b48bad79de1b9269e5eb30574545bb6f5f7c37d51035748caf` | [Yuklab olish](https://github.com/Muxammadaziz-boss/Misa/releases/download/v9.3.0/MicrosoftEdgeWebview2Setup.exe) |
| **`run_portable.bat`** | ⚡ **Portativ Ishga Tushirish Skripti** | **360 B** | Bir bosishda ishga tushirish | [Yuklab olish](https://github.com/Muxammadaziz-boss/Misa/releases/download/v9.3.0/run_portable.bat) |
| **`SHA256SUMS.txt`** | 🔐 **Kriptografik Nazorat Summalari** | **175 B** | Mustaqil tekshirilgan | [Yuklab olish](https://github.com/Muxammadaziz-boss/Misa/releases/download/v9.3.0/SHA256SUMS.txt) |
| **`version_manifest.json`** | ⚙️ **Avto-Yangilanish Rasmiy Manifesti** | **1.00 KB** | Ed25519 imzolangan | [Yuklab olish](https://github.com/Muxammadaziz-boss/Misa/releases/download/v9.3.0/version_manifest.json) |

### 🏛️ Tarixiy Relizlar Arxivi
- [Misa AI v9.2 Release](https://github.com/Muxammadaziz-boss/Misa/releases/tag/v9.2) — Platform stability & version synchronization
- [Misa AI v9.0.2 Release](https://github.com/Muxammadaziz-boss/Misa/releases/tag/v9.0.2) — Production hardening & installer packages
- [Misa AI v9.0.1 Release](https://github.com/Muxammadaziz-boss/Misa/releases/tag/v9.0.1) — Audio loop & anti-leak hardening
- [Misa AI v9.0.0 Release](https://github.com/Muxammadaziz-boss/Misa/releases/tag/v9.0.0) — Misa AI Rebranding & Tauri 2.0 UI
- [Mikasa AI v8.0.0 Release](https://github.com/Muxammadaziz-boss/Misa/releases/tag/v8.0.0) — Sobiq Mikasa AI arxivi

---

## 🚀 O'rnatish va Ishga Tushirish

### 1-usul: Tayyor Portativ Desktop Ilovani Ishlatish (Foydalanuvchilar uchun — Tavsiya etiladi)
1. [Misa-AI-v9.3-Portable.zip](https://github.com/Muxammadaziz-boss/Misa/releases/download/v9.3.0/Misa-AI-v9.3-Portable.zip) arxivini yuklab oling va istalgan papkaga chiqaring.
2. `run_portable.bat` faylini ikki marta bosing. Dastur backend serverini va Tauri interfeysini avtomatik sozlaydi va ishga tushiradi.
3. Standalone foydalanish uchun to'g'ridan-to'g'ri [Misa-AI-v9.3.exe](https://github.com/Muxammadaziz-boss/Misa/releases/download/v9.3.0/Misa-AI-v9.3.exe) ni ochishingiz mumkin.

### 2-usul: Dasturchilar uchun (Manba kodi orqali)
```bash
# 1. Repozitoriyani klonlash va dev-v9.0.0 branchiga o'tish
git clone https://github.com/Muxammadaziz-boss/Misa.git
cd Misa
git checkout dev-v9.0.0

# 2. Python 3.11+ virtual muhiti va bog'liqliklar
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. Frontend (Misa)
cd Misa
npm install
npm run build
cd ..

# 4. Tizimni ishga tushirish
python main.py
```

---

## 📁 Loyiha Kataloglar Tuzilmasi (v9.3 — Misa AI)

```
Misa/ (yordamchi_9.0.0)
├── agent/                      # Windows PC Agent, Lifecycle & Secure Tools Execution
│   ├── auth.py                 # Agent autentifikatsiyasi & Ed25519 Challenge-Response
│   ├── config.py               # Agent konfiguratsiyasi & DPAPI kalit saqlash
│   ├── executor.py             # Masofaviy buyruqlar ijrochisi va CommandPoller
│   ├── heartbeat.py            # FSM holat mashinasi va jonli signallar
│   ├── lifecycle.py            # Agent hayot sikli boshqaruvi
│   ├── tools.py                # 15 ta tizim asboblari & PathSecurityValidator
│   └── transport.py            # Kriptografik imzolangan HTTP transport
├── core/                       # Intellektual yadro va backend xizmatlari
│   ├── v8/                     # Supabase Auth, UpdateService, Telegram Gateway, OAuth
│   ├── intelligence/           # Agent Loop 2.0, Planner DAG, Verifier, PermissionEngine
│   ├── tools/                  # Tool System 2.0 (56 ta lokal va tizim asboblari, Confirmation Tokens)
│   ├── mcp/                    # Model Context Protocol (MCP) integratsiya ko'prigi
│   ├── stitch/                 # Stitch UI dinamik vizual komponentlar generatori
│   ├── voice/                  # Ovozli dvigatellar: RVC (HuBERT), Edge-TTS va qurilmalar boshqaruvi
│   ├── gui/                    # Session-Aware Windows GUI Controller (controller.py)
│   ├── api_server.py           # Asinxron REST & WebSocket server (18420-port)
│   └── audio_service.py        # VAD, ovozli monitor va audio oqimlar boshqaruvi
├── docs/                       # Loyiha arxitekturasi, qo'llanmalar va rasmlar
│   └── assets/                 # README uchun yuqori sifatli yangi UI skrinshotlar
├── Misa/                       # Tauri 2.0 + React 19 Desktop UI
│   ├── src/                    # Zamonaviy React komponentlari (Orb, Dashboard, Chat, Auth, Settings)
│   ├── src-tauri/              # Rust Tauri 2.0 desktop qobig'i va Backend Supervisor
│   └── dist/                   # Ishlab chiqarish uchun yig'ilgan statik fayllar
├── packaging/                  # PyInstaller backend/agent bundler va Ed25519 reliz imzolash
├── release/                    # Yig'ilgan desktop ilovalar arxivi (v9.3 Latest)
├── supabase/                   # Supabase PostgreSQL migratsiyalari va RLS siyosatlari
├── tests/                      # Avtomatlashtirilgan backend, xavfsizlik va mikrofon testlari
├── main.py                     # Asosiy Misa AI tizim boshqaruvchisi
├── requirements.txt            # Python bog'liqliklari
├── SETUP.md                    # To'liq sozlash qo'llanmasi
├── RELEASE_NOTES.md            # Rasmiy reliz qaydlari
└── README.md                   # Loyiha bosh sahifasi
```

---

## 🧪 Sifat Kafolati va Sinov Ko'rsatkichlari (100% Yashil CI)

Loyiha to'liq integratsion, kriptografik, multi-tenant RLS, mikrofon va Windows sandbox testlari bilan qamrab olingan hamda GitHub Actions CI tekshiruvlaridan 100% muvaffaqiyatli o'tgan:

* **GitHub Actions CI**: `9 / 9 Passing (100% Green)`
  - `Misa AI CI / Backend Tests (Python 3.11)`: ✅ Success
  - `Misa AI CI / Backend Tests (Python 3.12)`: ✅ Success
  - `Python Package using Conda`: ✅ Success
  - `Django CI / Framework Check (Python 3.11 & 3.12)`: ✅ Success
  - `Misa AI CI / Frontend Test & Build (Node 20)`: ✅ Success
  - `Pylint / Code Analysis`: ✅ Success
  - `Python application / App Lint & Test`: ✅ Success
  - `Railway deployment health`: ✅ Success
* **Kriptografiya & Xavfsizlik**: Ed25519, ES256/RS256 JWKS, SHA-256 confirmation token, Windows DPAPI, Constant-time verification

---

## 📄 Litsenziya va Muallif

* **Muallif:** Muxammadaziz ([@Muxammadaziz-boss](https://github.com/Muxammadaziz-boss))
* **Repozitoriya:** [https://github.com/Muxammadaziz-boss/Misa](https://github.com/Muxammadaziz-boss/Misa)
* **Litsenziya:** MIT License
