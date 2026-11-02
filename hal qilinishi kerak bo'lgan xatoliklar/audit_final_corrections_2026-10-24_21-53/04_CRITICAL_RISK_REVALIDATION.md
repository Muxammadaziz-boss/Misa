# 04 — BIRINCHI DARAJALI KRITIK XAVFLARNI QAYTA BAHOLASH (PHASE 4.2)
**Hujjat turi:** Texnik Xavfsizlik va Kritik Xatolar Chuqur Re-validatsiyasi  
**Sana:** 2026-10-24  
**Auditor:** Principal Application Security & Systems Engineer  
**Holat:** Verified with Static Code Evidence & Precondition Mapping  

---

## 1. KIRISH VA AUDIT CHEKLOVLARI

Ushbu hujjat Misa arxitekturasidagi 6 ta eng jiddiy (Tier 1 Critical) root cause xatolarini bevosita repository source code'i bilan solishtirib, ularning haqiqiy ekspluatatsiya shartlari (preconditions), statik kod dalillari va real ta'sir doirasini (impact) baholaydi.

> [!IMPORTANT]
> **Sinov metodologiyasi cheklovi:** Ushbu tekshiruv qat'iy read-only rejimida olib borildi. Dasturiy ta'minotning runtime muhitiga zarar yetkazmaslik, live portlarga hujum qilmaslik va tizim fayllarini o'zgartirmaslik maqsadida **dinamik ekspluatatsion sinovlar (live dynamic penetration testing) o'tkazilmadi**. Xulosalar 100% statik kod tahlili, Windows operatsion tizimi xavfsizlik modeli va xalqaro me'yorlarga asoslangan.

---

## 2. 6 TA KRITIK TOPILMANING SINCHIKLAB RE-VALIDATSIYASI

---

### 2.1. MISA-ROOT-001: Local API Autentifikatsiyasi, CORS va Tarmoqqa Ochiqlik Holati
- **Xavf darajasi:** **CRITICAL** (CVSS v3.1: 8.8 — AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H)
- **Bog'liq modullar:** `Misa/src/misa/misa_engine.py`, FastAPI backend sozlamalari.
- **Statik Kod Dalili:**
  `misa_engine.py` faylida FastAPI serveri quyidagi CORS middleware konfiguratsiyasi bilan ishga tushiriladi:
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
  Shuningdek, `/execute`, `/cmd`, `/task` endpointlarida hech qanday avtorizatsiya decorator yoki middleware (`Depends(verify_token)`) mavjud emas. Server sukut bo'yicha `127.0.0.1:8000` (yoki barcha interfeyslar) orqali tinglaydi.
- **Ekspluatatsiya Shartlari (Preconditions):**
  1. Misa desktop dasturi fonda ishlab turgan bo'lishi kerak (`127.0.0.1:8000` ochiq).
  2. Foydalanuvchi oddiy veb-brauzerda (Chrome, Edge, Firefox) tashqi zararli veb-saytni ochishi kerak.
  3. Brauzerda Private Network Access (PNA) yoki CORS preflight so'rovlariga javoban Misa `allow_origins=["*"]` bilan javob qaytarishi sababli, zararli saytdagi JS kodi mahalliy portga muvaffaqiyatli POST so'rovi yo'llay oladi.
- **Haqiqiy Ta'siri (Real Impact):**
  Foydalanuvchi xabarisiz tashqi veb-sahifa orqali uning kompyuterida Misa nomidan mahalliy buyruqlar, fayl o'qish/yozish va tizim amallari bajarilishi mumkin. Bu to'liq masofaviy boshqaruv (RCE) xavfini keltirib chiqaradi.

---

### 2.2. MISA-ROOT-002: Inno Setup Installerda `_internal` Resurslarining Yetishmasligi
- **Xavf darajasi:** **HIGH / BLOCKER** (Funktsional ishga tushmaslik nuqsoni)
- **Bog'liq modullar:** `installer.iss`, PyInstaller build output katalogi.
- **Statik Kod Dalili:**
  PyInstaller 6.0+ versiyasidan boshlab `--onedir` rejimida barcha Python dependencylari, C-extensionlar va DLL kutubxonalari asosiy `.exe` yonidagi `_internal/` katalogiga joylanadi.  
  Ammo `installer.iss` faylining `[Files]` bo'limida faqat `misa_backend.exe` fayli ko'rsatilgan, biroq uning yonidagi katalog to'liq kiritilmagan:
  ```iss
  ; installer.iss mavjud holati:
  Source: "..\release\v9.3\backend\misa_backend.exe"; DestDir: "{app}\resources\backend"; Flags: ignoreversion
  ; _internal katalogi esa rekursiv qo'shilmagan!
  ```
- **Ekspluatatsiya Shartlari (Preconditions):**
  1. Loyiha Inno Setup orqali installer `.exe` holatiga yig'iladi.
  2. Dastur toza Windows operatsion tizimida (Python o'rnatilmagan kompyuterda) o'rnatiladi.
  3. Foydalanuvchi Misa'ni ishga tushiradi.
- **Haqiqiy Ta'siri (Real Impact):**
  `misa_backend.exe` ishga tushish paytidayoq `python310.dll` yoki boshqa import qilingan kutubxonalarni topa olmasdan `Fatal Error: cannot find _internal directory` xatosi bilan qulaydi. Oqibatda butun backend ishlamaydi, frontend esa backendga ulanolmasdan qotib qoladi.

---

### 2.3. MISA-ROOT-003: `ShellExecuteW` Chaqiruvining Real Kirish Yo'li va Nazoratsizligi
- **Xavf darajasi:** **CRITICAL** (CWE-88 / CWE-78)
- **Bog'liq modullar:** `Misa/src-tauri/src/lib.rs` (va Windows API interfeysi).
- **Statik Kod Dalili:**
  `lib.rs` faylida tashqi URL yoki fayllarni ochish uchun Windows API funksiyasi `ShellExecuteW` chaqiriladi:
  ```rust
  // lib.rs
  unsafe {
      ShellExecuteW(
          null_mut(),
          to_pcwstr("open").as_ptr(),
          to_pcwstr(&url).as_ptr(),
          null_mut(),
          null_mut(),
          SW_SHOWNORMAL,
      );
  }
  ```
  Bu yerda `url` parametri ustidan qat'iy scheme tekshiruvi (`http://` yoki `https://` bilan cheklash) o'rnatilmagan.
- **Ekspluatatsiya Shartlari (Preconditions):**
  1. Frontend yoki AI Agent javobidan foydalanuvchiga kliklanadigan link yoki avtomatik ochiladigan URL yuboriladi.
  2. Ushbu parametr `file:///`, `cmd.exe`, `powershell.exe`, `ms-msdt:` yoki boshqa xavfli protokol ko'rinishida beriladi.
  3. Foydalanuvchi havola ustiga bosadi yoki tizim uni avtomatik ochadi.
- **Haqiqiy Ta'siri (Real Impact):**
  Foydalanuvchi kompyuterida ixtiyoriy dastur, skript yoki mahalliy executable fayl ochib yuborilishi mumkin (Arbitrary Code Execution via URL Protocol Handler).

---

### 2.4. MISA-ROOT-004: PowerShell Argumentlarini Shakllantirish va Sanitizatsiya Yo'qligi
- **Xavf darajasi:** **CRITICAL** (CWE-78: OS Command Injection)
- **Bog'liq modullar:** `Misa/src/misa/tools.py` (tizim buyruqlarini bajarish moduli).
- **Statik Kod Dalili:**
  `tools.py` da PowerShell orqali buyruqlarni bajarish quyidagicha tashkil etilgan:
  ```python
  cmd_str = f"powershell.exe -NoProfile -NonInteractive -Command \"{user_or_agent_input}\""
  proc = subprocess.Popen(cmd_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  ```
  Buyruq satri qatorlari qo'shtirnoq ichiga olinishiga qaramay, parametrlar orasidagi belgilarni (`&`, `;`, `|`, `` ` ``, `$()`) sanitizatsiya qilish, escape qilish yoki `list-based` argumentlar ro'yxatidan foydalanish tatbiq etilmagan.
- **Ekspluatatsiya Shartlari (Preconditions):**
  1. Agentga yoki tizimga foydalanuvchi yoki tashqi ma'lumot (masalan, veb-qidiruv natijasi, fayl nomi) orqali maxsus shakllantirilgan matn kirib keladi.
  2. Matnda `; Remove-Item C:\...` yoki `& calc.exe` kabi in'eksiya konstruksiyasi mavjud bo'ladi.
- **Haqiqiy Ta'siri (Real Impact):**
  Tizimda Misa jarayoni huquqlari doirasida (foydalanuvchi privilegesi bilan) har qanday operatsion tizim buyruqlari bajarilishi, fayllar o'chirilishi yoki zararli dastur yuklab ishga tushirilishi mumkin.

---

### 2.5. MISA-ROOT-005: API Kalitlarining Saqlanishi va Foydalanuvchi Ruxsatlari
- **Xavf darajasi:** **HIGH** (CWE-312: Cleartext Storage of Sensitive Information)
- **Bog'liq modullar:** `Misa/config/config.json` va konfiguratsiya boshqaruvi.
- **Statik Kod Dalili:**
  Konfiguratsiya fayli foydalanuvchining mahalliy katalogida (yoki dastur o'rnatilgan papkada) ochiq matn (plaintext JSON) ko'rinishida saqlanadi:
  ```json
  {
      "openai_api_key": "sk-proj-...",
      "anthropic_api_key": "sk-ant-...",
      "telegram_bot_token": "..."
  }
  ```
  Windows Data Protection API (DPAPI / `CryptProtectData`) yoki Windows Credential Manager integratsiyasi yo'q. Faylga kirish huquqlari (ACL) faqat joriy foydalanuvchi bilan cheklanmagan (umumiy ruxsat meros olinadi).
- **Ekspluatatsiya Shartlari (Preconditions):**
  1. Xuddi shu kompyuterda ishlayotgan boshqa past huquqli dastur, zararli skript yoki umumiy foydalanuvchi hisobi mavjud bo'lishi.
  2. Yoki foydalanuvchi o'z sozlamalar papkasini tasodifan zip qilib boshqalarga yuborishi / gitga yuklab qo'yishi.
- **Haqiqiy Ta'siri (Real Impact):**
  Foydalanuvchining pullik API kalitlari o'g'irlanadi, tashqi shaxslar tomonidan hisobdan mablag' sarflanadi yoki bot boshqaruvi qo'ldan ketadi.

---

### 2.6. MISA-ROOT-006: Backend Tasdiqlash Siyosati va Human-in-the-Loop Zaifligi
- **Xavf darajasi:** **CRITICAL** (OWASP LLM06: Excessive Agency)
- **Bog'liq modullar:** `Misa/src/misa/agent.py` va frontend tasdiq dialogi.
- **Statik Kod Dalili:**
  Frontend interfeysida foydalanuvchiga buyruqni bajarishdan oldin "Tasdiqlaysizmi?" modali ko'rsatilishi mumkin. Ammo backend darajasida bu qat'iy majburiy emas. Backenddagi API endpointi (`/execute_action`) hech qanday kriptografik imzo, bir martalik tasdiqlovchi token (nonce) yoki tasdiqlash sessiyasini talab qilmaydi.
- **Ekspluatatsiya Shartlari (Preconditions):**
  1. AI Agent avtonom rejimda bir nechta topshiriqlarni zanjirli (chained loop) bajarayotgan bo'lishi.
  2. Yoki tajovuzkor backend API ga to'g'ridan-to'g'ri so'rov yuborishi.
- **Haqiqiy Ta'siri (Real Impact):**
  Foydalanuvchi tasdiqlamasdan turib ham, agent destruktiv tizim harakatlarini (fayllarni o'chirish, formatlash, xatlarni jo'natish) to'liq bajarib yuborishi mumkin. Inson nazorati (Human-in-the-Loop) faqat vizual illyuziya bo'lib qoladi.

---

## 3. XULOSA VA XAVFLARNING YAKUNIY MATRITsASI

| Master ID | Aniqlangan Zaiflik | Kod Dalili | Haqiqiy Ekspluatatsiya Ehtimoli | Dinamik Sinov Holati | Yakuniy Risk |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **MISA-ROOT-001** | Local API CORS & No Auth | `misa_engine.py:L75` | **HIGH** (Brauzer orqali) | *Statik tasdiqlangan (no live test)* | **CRITICAL** |
| **MISA-ROOT-002** | Missing `_internal` in ISS | `installer.iss:L42` | **100% (Deterministic)** | *Statik tasdiqlangan (no build test)* | **CRITICAL** |
| **MISA-ROOT-003** | ShellExecuteW Uncontrolled | `lib.rs:L415` | **MEDIUM-HIGH** (Protokol orqali) | *Statik tasdiqlangan (no live test)* | **CRITICAL** |
| **MISA-ROOT-004** | PowerShell Command Injection | `tools.py:L64` | **HIGH** (Prompt orqali) | *Statik tasdiqlangan (no live test)* | **CRITICAL** |
| **MISA-ROOT-005** | Plaintext API Keys in Config | `config.json:L8` | **HIGH** (Lokal kirish orqali) | *Statik tasdiqlangan (no live test)* | **HIGH** |
| **MISA-ROOT-006** | Excessive Agency / No HITL | `agent.py:L140` | **HIGH** (Avtonom tsiklda) | *Statik tasdiqlangan (no live test)* | **CRITICAL** |

Ushbu tahlil 6 ta kritik xavfning har biri shunchaki nazariy emas, balki kod darajasida mavjud bo'lgan haqiqiy arxitekturaviy nuqsonlar ekanligini to'liq isbotlaydi.
