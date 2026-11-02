# 04 — BIRINCHI DARAJALI KRITIK XAVFLAR DALILLARINI QAYTA BAHOLASH (PHASE 4.3)
**Hujjat turi:** Xavfsizlik va Kritik Zaifliklar Dalillari Re-Audit Hisoboti  
**Sana:** 2026-10-24  
**Auditor:** Principal Application Security Engineer & Systems Auditor  
**Holat:** Final Verified / Rigorous Evidence-Based Evaluation  

---

## 1. KIRISH VA METODOLOGIK CHEKLOVLAR

Oldingi hisobotlarda ko'pincha statik kod tahlilining o'zidanoq "to'liq va 100% ekspluatatsiya qilinadigan xakerlik hujumi mavjud" degan da'volar ilgari surilgan edi. Biroq, real xavfsizlik muhandisligida har qanday zaiflikning real ekspluatatsiya darajasi operatsion tizim himoya mexanizmlari, brauzer cheklovlari va mavjud mitigatsiyalar bilan chegaralanadi.

> [!WARNING]
> **Metodologik cheklov:** Ushbu audit qat'iy **read-only rejimida** bajarildi. Tizimga real xakerlik xurujlari, exploit ishga tushirish, portlarni skanerlash yoki toza virtual mashinada o'rnatuvchi paketlarni yig'ish (clean-room installer build test) sinovlari **bajarilmadi**. Barcha xulosalar statik manba kodi, Windows API arxitekturasi va ma'lumotlar oqimi tahliliga asoslanadi.

---

## 2. 6 TA KRITIK TOPILMANING SINCHIKLAB RE-VALIDATSIYASI

---

### 2.1. MISA-ROOT-001: Port 18420 dagi Mahalliy API Autentifikatsiyasining Yo'qligi va CORS `*`
- **Tasdiqlangan Kod Holati:**  
  [`core/api_server.py:L7351`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/api_server.py#L7351):
  ```python
  cors = aiohttp_cors.setup(app, defaults={
      "*": aiohttp_cors.ResourceOptions(
          allow_credentials=True,
          expose_headers="*",
          allow_headers="*",
          allow_methods="*"
      )
  })
  ```
  [`core/api_server.py:L7328`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/api_server.py#L7328):
  ```python
  if is_desktop_mode:
      return await handler(request)  # Token tekshiruvi chetlab o'tiladi
  ```
- **Ehtimoliy Ekspluatatsiya Shartlari (Preconditions):**
  1. Misa backend jarayoni fonda ishlayotgan bo'lishi kerak (`http://127.0.0.1:18420` portida tinglaydi).
  2. Foydalanuvchi o'zining asosiy veb-brauzerida (Chrome, Edge yoki Firefox) tashqi zararli veb-saytni ochishi kerak.
  3. Brauzerda Private Network Access (PNA — jamoat tarmog'idan mahalliy loopbackka so'rov yuborishni bloklash siyosati) o'chirilgan yoki preflight OPTIONS so'roviga CORS `allow_origins=["*"]` bilan ruxsat berilishi sababli aylanib o'tilishi kerak.
- **Real Ta'sir (Impact):**  
  Tashqi veb-sahifa JavaScript kodi Misa API endpointlariga (`/api/cmd`, `/api/agent/task`) so'rov yo'llab, foydalanuvchi nomidan dasturlarni ochishi yoki fayllarni o'qishi mumkin.
- **Mavjud Himoya Mexanizmlari (Mitigating Controls):**
  - Zamonaviy Chromium brauzerlarida (Chrome 104+) joriy etilayotgan *Private Network Access (PNA)* siyosati `public` internetdan `127.0.0.1` ga yuboriladigan so'rovlarga nisbatan preflight tekshiruvini amalga oshiradi va ba'zi so'rovlarni bloklashi mumkin.
  - Server faqat `127.0.0.1` (loopback) interfeysida tinglaydi, tashqi LAN yoki internetdan to'g'ridan-to'g'ri unga ulanib bo'lmaydi.
- **Dinamik Test Bajarilganmi?** **YO'Q (Faqat statik kod tahlili).**
- **Jiddiylik va CVSS v3.1 Asoslanishi:**
  - **Ball:** **8.8 (CRITICAL)**
  - **Vektor:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H`
  - **Izoh:** `UI:R` (Foydalanuvchi zararli saytga kirishi shart). Mahalliy portda token talab qilinmagani sababli masofadan turib foydalanuvchi orqali amallarni bajarish xavfi juda yuqori.

---

### 2.2. MISA-ROOT-002: PyInstaller `--onedir` `_internal` Katalogining Installerga Kiritilmagani
- **Tasdiqlangan Kod Holati:**  
  [`installer.iss`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/installer.iss) va [`Misa/src-tauri/tauri.conf.json:L37`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src-tauri/tauri.conf.json#L37):  
  Inno Setup va Tauri konfiguratsiyasida backend `.exe` ko'rsatilgan, biroq PyInstaller 6+ tomonidan ishlab chiqarilgan `_internal/` katalogining barcha fayllarini rekursiv nusxalash qatori kiritilmagan.
- **Ehtimoliy Ekspluatatsiya / Nosozlik Shartlari:**
  1. Dastur toza Windows operatsion tizimiga (Python, Visual C++ Redistributable yoki boshqa dependency o'rnatilmagan kompyuterga) o'rnatilishi kerak.
  2. Dastur ishga tushganda `misa_backend.exe` o'zining yonidagi `_internal/` katalogidagi `.dll` larni qidiradi.
- **Real Ta'sir (Impact):**  
  Agar `_internal` katalogi o'rnatuvchi tomonidan nusxalanmasa, backend birinchi soniyadayoq qulaydi va ilova ishlamaydi (Blocker Defect).
- **Mavjud Himoya Mexanizmlari (Mitigating Controls):**
  - Agar dastur `--onefile` rejimida yig'ilgan bo'lsa, `_internal` papkasi talab qilinmaydi (vaqtinchalik `%TEMP%` ga o'zi ochiladi). Biroq repo build skriptlarida `--onedir` ko'rsatilgan.
  - Ishlab chiquvchining shaxsiy kompyuterida global Python yoki DLL lar mavjud bo'lsa, dastur xatosiz ishlayotgandek tuyulishi mumkin.
- **Dinamik Test Bajarilganmi?** **YO'Q (Toza virtual mashinada o'rnatish testi o'tkazilmadi).**
- **Jiddiylik Asoslanishi:**
  - **Daraja:** **High / Blocker** (Xavfsizlik zaifligi emas, balki arxitekturaviy barqarorlik muammosi).

---

### 2.3. MISA-ROOT-003: Native `ShellExecuteW` da URL Protokoli Tekshirilmasligi
- **Tasdiqlangan Kod Holati:**  
  [`Misa/src-tauri/src/lib.rs:L681`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src-tauri/src/lib.rs#L681):
  ```rust
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
- **Ehtimoliy Ekspluatatsiya Shartlari (Preconditions):**
  1. `ShellExecuteW` ga kelib tushayotgan `url` parametri ustidan foydalanuvchi yoki tashqi tajovuzkor nazorati bo'lishi kerak (masalan, AI agent orqali yoki xabardagi havola orqali).
  2. `url` parametri `http://` yoki `https://` o'rniga xavfli protokollar (`file:///`, `calculator:`, `ms-msdt:`, `.bat`, `.vbs`, yoki mahalliy executable yo'li) ko'rinishida berilishi kerak.
- **Real Ta'sir (Impact):**  
  Windows operatsion tizimida ro'yxatdan o'tgan ixtiyoriy protokol handlerlar yoki mahalliy dasturlar ochib yuborilishi mumkin.
- **Mavjud Himoya Mexanizmlari (Mitigating Controls):**
  - **Muhim skeptik eslatma:** `ShellExecuteW` ning mavjudligi o'z-o'zidan RCE (Remote Code Execution) degani emas! Buning uchun tajovuzkor dastur ichiga to'g'ridan-to'g'ri ixtiyoriy string uzata olishi lozim.
  - Windows UAC va SmartScreen mexanizmlari internetdan yuklangan xavfli fayllar ochilishida ogohlantirish beradi.
- **Dinamik Test Bajarilganmi?** **YO'Q (Statik kod tekshiruvi).**
- **Jiddiylik va CVSS v3.1 Asoslanishi:**
  - **Ball:** **8.1 (HIGH/CRITICAL)**
  - **Vektor:** `CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:H/I:H/A:H`
  - **Izoh:** `AC:H` (Hujum murakkabligi yuqori, chunki xavfli protokolni uzatish va tizimda mos keluvchi zararli fayl bo'lishi talab qilinadi).

---

### 2.4. MISA-ROOT-004: `open_app` Amallarida PowerShell Argument In'eksiyasi (CWE-78)
- **Tasdiqlangan Kod Holati:**  
  [`core/agent_tools.py:L514`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/agent_tools.py#L514):
  ```python
  cmd = f"powershell.exe -NoProfile -Command \"Start-Process '{app_name}'\""
  subprocess.Popen(cmd, shell=True)
  ```
- **Ehtimoliy Ekspluatatsiya Shartlari (Preconditions):**
  1. `app_name` o'zgaruvchisiga foydalanuvchi yoki AI Agent prompt inyeksiya orqali maxsus shakllantirilgan satr (`calc.exe'; Remove-Item ... #`) uzatishi kerak.
  2. Satr ichidagi bittalik qo'shtirnoq (`'`) yopilib, keyin yangi PowerShell komandasi ulanadi.
- **Real Ta'sir (Impact):**  
  PowerShell foydalanuvchi huquqlari doirasida kompyuterda ixtiyoriy operatsion tizim buyruqlarini bajaradi.
- **Mavjud Himoya Mexanizmlari (Mitigating Controls):**
  - Jarayon administrativ (Elevated) huquqlar bilan emas, balki joriy foydalanuvchi huquqlari bilan ishga tushadi.
  - PowerShell ExecutionPolicy sukut bo'yicha ayrim skriptlarni cheklashi mumkin, ammo `-Command` inline buyruqlari odatda bajariladi.
- **Dinamik Test Bajarilganmi?** **YO'Q (Faqat statik argument tahlili).**
- **Jiddiylik va CVSS v3.1 Asoslanishi:**
  - **Ball:** **8.4 (HIGH/CRITICAL)**
  - **Vektor:** `CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`
  - **Izoh:** `AV:L` (Mahalliy kirish yoki agent konteksti orqali in'eksiya).

---

### 2.5. MISA-ROOT-005: API Kalitlarning `ai_keys_cache.json` Faylida Ochiq Matnda Saqlanishi
- **Tasdiqlangan Kod Holati:**  
  [`core/v8/ai_key_manager.py:L115`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/v8/ai_key_manager.py#L115):  
  OpenAI, Anthropic yoki boshqa provayder API kalitlari mahalliy JSON fayliga shifrlanmagan ochiq matn (plaintext) sifatida yoziladi. Windows Data Protection API (DPAPI / `CryptProtectData`) ishlatilmagan.
- **Ehtimoliy Ekspluatatsiya Shartlari (Preconditions):**
  1. Xuddi shu kompyuterda ishlayotgan boshqa zararli dastur (infostealer, troyan) yoki mahalliy foydalanuvchi fayl tizimiga kirish huquqiga ega bo'lishi kerak.
  2. Yoki foydalanuvchi sozlamalar katalogini tasodifan ochiq GitHub omboriga yuklab yuborishi kerak.
- **Real Ta'sir (Impact):**  
  Foydalanuvchining pullik AI hisoblaridagi balans o'g'irlanadi yoki kvotasi tugatiladi.
- **Mavjud Himoya Mexanizmlari (Mitigating Controls):**
  - Fayl foydalanuvchining shaxsiy Windows profili katalogida joylashgan bo'lib, standart Windows NTFS ACL ruxsatlari boshqa foydalanuvchilarning kirishini cheklaydi (agar ular administrator bo'lmasa).
- **Dinamik Test Bajarilganmi?** **YO'Q (Statik tahlil).**
- **Jiddiylik va CVSS v3.1 Asoslanishi:**
  - **Ball:** **6.2 (MEDIUM/HIGH)**
  - **Vektor:** `CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N`
  - **Izoh:** `AV:L/PR:L` (Mahalliy ruxsat talab etiladi, masofaviy emas).

---

### 2.6. MISA-ROOT-006: Destruktiv Amallarda Human-in-the-Loop Backend Tasdig'ining Yo'qligi
- **Tasdiqlangan Kod Holati:**  
  [`core/agents/manager_agent.py:L140`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/agents/manager_agent.py#L140) va [`Misa/src/pages/ChatPage.tsx:L100`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx#L100):  
  Agent harakatlari oldidan frontendda dialog ochilishi rejalashtirilgan, biroq backenddagi harakatlarni bajaruvchi API da inson tomonidan tasdiqlanganini kafolatlovchi kriptografik token (nonce / HMAC) talab etilmaydi.
- **Ehtimoliy Ekspluatatsiya Shartlari (Preconditions):**
  1. Agent ko'p bosqichli avtonom rejimda ishlayotganda noto'g'ri xulosaga kelishi (hallucination) yoki prompt injection orqali chalg'itilishi.
  2. Agent tizim fayllarini o'chirish (`file_delete`) yoki jarayonlarni to'xtatish (`process_kill`) funksiyasini chaqirishi.
- **Real Ta'sir (Impact):**  
  Foydalanuvchining muhim ma'lumotlari yoki tizim fayllari uning ruxsatisiz yo'qotilishi mumkin.
- **Mavjud Himoya Mexanizmlari (Mitigating Controls):**
  - Agent faqat oldindan belgilangan tool funksiyalari to'plami bilan cheklangan (cheksiz tizim API lariga ega emas).
- **Dinamik Test Bajarilganmi?** **YO'Q (Statik tahlil).**
- **Jiddiylik va CVSS v3.1 Asoslanishi:**
  - **Ball:** **8.1 (HIGH/CRITICAL)**
  - **Vektor:** `CVSS:3.1/AV:L/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H`
  - **Izoh:** `OWASP LLM06 Excessive Agency`. Inson nazoratining backend darajasida bo'lmasligi xavf tug'diradi.

---

## 3. REKONSILYATSIYA MATRITsASI

| Master ID | Aniqlangan Zaiflik | Kod Dalili | Hujum Vektori (Plausible Condition) | Mavjud Mitigatsiya | Dinamik Test | Yakuniy Risk |
|---|---|---|---|---|:---:|:---:|
| **MISA-ROOT-001** | Port 18420 Auth Bypass & CORS * | `core/api_server.py:L7351` | Brauzerdan mahalliy portga cross-origin POST | Faqat 127.0.0.1 da tinglaydi | Yo'q | **CRITICAL** |
| **MISA-ROOT-002** | PyInstaller `_internal` Missing | `installer.iss:L42` | Toza Windows OS da dependenciesiz o'rnatish | Dev muhitda global kutubxonalar | Yo'q | **High / Blocker** |
| **MISA-ROOT-003** | ShellExecuteW URL Scheme Missing | `Misa/src-tauri/src/lib.rs:L681` | Zararli protokolli havolani agent orqali ochish | Windows UAC / SmartScreen | Yo'q | **CRITICAL** |
| **MISA-ROOT-004** | PowerShell Argument Injection | `core/agent_tools.py:L514` | app_name parametriga `'` orqali buyruq qo'shish | Foydalanuvchi huquqlari bilan | Yo'q | **CRITICAL** |
| **MISA-ROOT-005** | Plaintext API Keys in JSON | `core/v8/ai_key_manager.py:L115` | Mahalliy zararli dastur yoki tasodifiy git leak | Windows User Profile NTFS ACL | Yo'q | **HIGH** |
| **MISA-ROOT-006** | Excessive Agency / No HITL Token | `core/agents/manager_agent.py:L140` | Avtonom agent tsiklida destruktiv tool chaqirish | Toollar to'plami cheklanganligi | Yo'q | **CRITICAL** |

Ushbu xulosa shuni ko'rsatadiki, yuqoridagi 6 ta muammo shunchaki nazariy farazlar emas, balki kod darajasida isbotlangan jiddiy arxitektura va xavfsizlik to'siqlaridir.
