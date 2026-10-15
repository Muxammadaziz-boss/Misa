# 🛠️ Misa AI — O'rnatish va Sozlash Qo'llanmasi

Ushbu qo'llanma **Misa AI v9.0.2 (Autonomous Desktop Assistant & Intelligence Hub)** tizimini Windows tizimida to'g'ri o'rnatish, sozlash va ishga tushirish bo'yicha to'liq qo'llanmadir.

---

## 1. Tizim Talablari

* **Operatsion tizim**: Windows 10 yoki Windows 11 (64-bit)
* **Python**: 3.11.x (3.11 tavsiya etiladi)
* **Node.js**: 20.x yoki undan yuqori
* **RAM**: Kamida 4 GB (8 GB yoki 16 GB tavsiya etiladi)
* **Mikrofon va Dinamik**: Ovozli boshqaruv va Misa Orb uchun
* **Internet**: Google Gemini, Supabase Auth va Telegram masofaviy boshqaruvi uchun

---

## 2. O'rnatish Usullari

### 🅰️ 1-usul: Tayyor Desktop Reliz (Tavsiya etiladi)
Hech qanday dasturlash muhiti yoki kutubxonalarni o'rnatish shart emas:
1. [GitHub Releases](https://github.com/Muxammadaziz-boss/Misa/releases/tag/v9.0.2) bo'limidan `Misa-AI-Setup-v9.0.2.exe` yoki `Misa-AI-v9.0.2-Portable.zip` faylini yuklab oling.
2. Ilovani ishga tushiring. Portable rejimda `run_portable.bat` fayli orqali bir bosishda backend va frontendni birgalikda ishga tushirishingiz mumkin.

---

### 🅱️ 2-usul: Dasturchilar uchun (Manba kodi orqali)

#### 1-qadam: Repozitoriyani yuklab olish
```bash
git clone https://github.com/Muxammadaziz-boss/Misa.git
cd Misa
git checkout dev-v9.0.0
```

#### 2-qadam: Python 3.11 Virtual Muhiti
```powershell
# Virtual muhit yaratish
py -3.11 -m venv .venv

# Virtual muhitni faollashtirish (PowerShell)
.venv\Scripts\Activate.ps1

# PIP-ni yangilash va bog'liqliklarni o'rnatish
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### 3-qadam: Frontend Interfeysini O'rnatish (Misa)
```bash
cd Misa
npm install
npm run build
cd ..
```

---

## 3. Konfiguratsiya (.env va data/config.json)

Loyiha ildizidagi `.env` faylida quyidagi kalitlarni sozlashingiz mumkin:

```env
# AI Modellari Kalitlari
GEMINI_API_KEY=AIzaSy...sizning_gemini_kalitingiz
OPENROUTER_API_KEY=sk-or-v1-...sizning_openrouter_kalitingiz
OPENROUTER_MODEL=openai/gpt-4o-mini

# Supabase Auth Sozlamalari
SUPABASE_URL=https://sizning-loyiha.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...

# Telegram Bot Masofaviy Boshqaruvi
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
TELEGRAM_WEBHOOK_URL=https://sizning-domen.up.railway.app/telegram/webhook
TELEGRAM_WEBHOOK_SECRET=maxfiy_webhook_token_32_belgi

# Umumiy sozlamalar
PORT=18420
DEBUG=false
```

---

## 4. Dasturni Ishga Tushirish

### 1. Asosiy AI Dvigateli va Backend Server:
```bash
python main.py
```
*Backend avtomatik tarzda `http://127.0.0.1:18420` manzilida ishga tushadi.*

### 2. Desktop Interfeysini Ishga Tushirish (Vite + Tauri):
```bash
cd Misa
npm run desktop
```

### 3. Brauzer / Ishlab chiqish rejimida:
```bash
cd Misa
npm run dev
```

---

## 5. Sinovlar va Sifat Tekshiruvi

Barcha modullar to'liq avtomatlashtirilgan testlar bilan ta'minlangan (100% PASS):

```bash
# 1. Asosiy Backend Testlari (345 ta test)
python -m unittest discover tests/ "test_*.py"

# 2. Frontend Birlik va Stress Testlari (33 ta test)
cd Misa
npm test

# 3. Haqiqiy Windows Smoke Testlari (8 ta test)
python tests/smoke_test_rc.py
```

---

## 6. Muammolarni Bartaraf Etish (Troubleshooting)

1. **Port 18420 band bo'lsa**:
   PowerShell orqali portni tekshiring:
   ```powershell
   Get-NetTCPConnection -LocalPort 18420 -ErrorAction SilentlyContinue
   ```
2. **Audio yoki Mikrofon ishlamasa**:
   Windows Sozlamalari -> Maxfiylik va Xavfsizlik -> Mikrofon bo'limida ilovaga ruxsat berilganligini tekshiring.
3. **Avto-yangilanish holati**:
   Ilova ichida `Hisob va Sozlamalar -> Yangilanishlar` bo'limi orqali yangi relizlar mavjudligini istalgan vaqt tekshirishingiz mumkin.
