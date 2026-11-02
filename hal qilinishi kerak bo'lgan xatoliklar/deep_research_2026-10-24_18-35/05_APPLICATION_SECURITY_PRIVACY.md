# EKSPERT 05 — APPLICATION SECURITY, PRIVACY & THREAT MODELING REPORT
**Loyiha:** Misa Desktop AI Assistant (v9.0.0 / v9.3)  
**Sana:** 2026-10-24  
**Auditor:** Ekspert 05 — Application Security & Privacy Deep Researcher  
**Standartlar:** OWASP ASVS v4.0.3, OWASP Top 10:2021, Tauri 2 Security Architecture, Microsoft Windows Desktop Security Best Practices, NIST Privacy Framework (CSWP 029)  
**Holat:** Yakunlandi (Read-Only Deep Inspection & Threat Modeling)

---

## 1. IJROCHI XULOSA VA XAVFSIZLIK POSTURASI

Misa desktop arxitekturasi TypeScript/React frontend (Tauri 2 webview orqali) va Python lokal backend/agent tizimidan (`api_server.py`, `agent_loop.py`, `core/`) tashkil topgan gibrid tizimdir.

Xavfsizlik auditining eng jiddiy xulosasi:
> **Tizimda "Localhost = Trusted" xato paradigmasi hukmronlik qilmoqda.** 
> Localhostda ishlovchi Python REST API serveri (port 18420) tashqi dunyodan va mahalliy tarmoq/brauzerdan yetarli himoyalanmagan. Har qanday brauzer sahifasi (Chrome/Edge orqali ochilgan oddiy veb-sayt) CSRF/CORS bypass orqali Misa REST API'siga murojaat qilib, foydalanuvchi nomidan buyruqlar berishi yoki ma'lumotlarni o‘g‘irlashi mumkin.

Bundan tashqari, maxfiy API kalitlarining shifrlanmagan holda fayllarda saqlanishi, Telegram sessiyasining faqat mijoz tomonida token yaratishi va maxfiylik siyosatidagi nomuvofiqliklar aniqlandi.

---

## 2. TOPILMALAR RO‘YXATI VA STATISTIKA

| ID | Sarlavha | Xavfsizlik Standarti | Jiddiylik | Ishonchlilik | Joylashuv |
|---|---|---|---|---|---|
| **SEC-APP-001** | Port 18420 dagi Autentifikatsiyasiz REST API va Wildcard CORS | OWASP ASVS V13.1, V13.2 | **Critical** | Confirmed | `api_server.py` |
| **SEC-APP-002** | Shifrlanmagan Plaintext API Kalitlari Keshi | OWASP ASVS V8.3, CWE-312 | **High** | Confirmed | `ai_keys_cache.json`, `ai_engine.py` |
| **SEC-APP-003** | Telegram Sessiya Tokenining Mijoz Tomonida Soxtalashtirilishi | OWASP ASVS V2.1, CWE-287 | **High** | Confirmed | `backendService.ts` |
| **SEC-APP-004** | Tauri 2 Izolyatsiya Namunasi (Isolation Pattern) Yo‘qligi | Tauri 2 Security Architecture | **Medium** | Confirmed | `src-tauri/tauri.conf.json` |
| **SEC-APP-005** | Maxfiylik Siyosati Zidligi: Google Web Speech API Oqimi | NIST Privacy Framework (CT.PO-P) | **Medium** | Confirmed | `audio_service.py` |

---

## 3. CHUQUR DALILLANGAN TOPILMALAR

### Finding ID: SEC-APP-001
- **Sarlavha:** Localhost REST API (Port 18420) Autentifikatsiyasiz Ochiqligi va Wildcard CORS (`*`) Orqali RCE / Ma’lumot Sizishi Xavfi
- **Kategoriya:** Application Security / Trust Boundary Violation
- **Jiddiylik:** Critical
- **Ishonchlilik:** Confirmed
- **Tekshiruv turi:** Code inspection & Architecture analysis
- **Aniq joylashuv:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\core\api_server.py` (Lines: 65-110, 240-280)
- **Dalillar:**
  ```python
  # api_server.py L68-L78:
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ...
  # L245: /api/chat va boshqa endpointlar hech qanday Depends(verify_token) talab qilmaydi
  @app.post("/api/chat")
  async def chat_endpoint(request: ChatRequest):
      return await process_chat(request)
  ```
- **Amaldagi holat:** Python FastAPI serveri `127.0.0.1:18420` manzilida ishga tushadi. Unga `CORSMiddleware` orqali `allow_origins=["*"]` o‘rnatilgan va endpointlar hech qanday Bearer token, session cookie yoki mahalliy maxfiy kalit (pre-shared token) talab qilmaydi.
- **Kutiladigan holat:** OWASP ASVS V13.1 va V13.2 (API Architecture & Cross-Origin Resource Sharing) standartlariga ko‘ra, lokal desktop xizmatlari faqat ruxsat etilgan kelib chiqish manbalariga (`tauri://localhost`, `http://localhost:5173`) ruxsat berishi, har bir so‘rovda Tauri frontend tomonidan uzatiladigan vaqtinchalik xavfsiz token (session handshake token) tekshirilishi shart.
- **Kamchilik yoki xavf:** Agar foydalanuvchi Chrome yoki Edge brauzerida zararli veb-saytga (masalan, `attacker.com`) kirsa, ushbu sahifadagi JavaScript kod orqa fonda `fetch('http://localhost:18420/api/chat', {method: 'POST', body: JSON.stringify({message: 'System shutdown'})})` kabi so‘rovlarni erkin yubora oladi. Zararli sayt foydalanuvchining shaxsiy chat tarixini o‘qishi va mahalliy tizimga buyruqlar uzatishi mumkin (Drive-by Local Attack).
- **Foydalanuvchiga ta’sir:** Foydalanuvchining kompyuteri to‘liq masofaviy boshqaruv xavfi ostida qoladi, shaxsiy suhbatlar va ma’lumotlar tashqi tajovuzkor qo‘liga o‘tishi mumkin.
- **Root cause:** Desktop ilovalarida "server faqat kompyuterim ichida ishlaydi, begona kishi kirolmaydi" degan yanglish ishonch.
- **Tashqi manba:**
  - OWASP ASVS 4.0.3 Section V13 API and Web Service: https://owasp.org/www-project-application-security-verification-standard/
  - Tauri 2 Security Guide: https://v2.tauri.app/security/
- **Tavsiya:**
  1. CORS da `allow_origins` qiymatini qat’iy ravishda faqat ilova domenlari bilan cheklash.
  2. Dastur har safar ishga tushganda Tauri tomonidan dinamik generatsiya qilinadigan `X-Misa-Auth-Token` (UUIDv4) talab qilish.
- **Qabul mezoni:** Begona brauzer konsolidan `fetch('http://localhost:18420/api/chat')` chaqirilganda `401 Unauthorized` yoki `CORS Blocked` xatosi qaytishi.
- **Cheklovlar:** Faol tarmoq xuruji (exploit injection) bajarilmadi, faqat kod oqimi va xavfsizlik konfiguratsiyasi tahlil qilindi.

---

### Finding ID: SEC-APP-002
- **Sarlavha:** Foydalanuvchining AI Provayder API Kalitlari (Gemini, OpenAI, Anthropic) Shifrlanmagan Plaintext JSON Faylida Saqlanishi
- **Kategoriya:** Cryptographic Storage & Secrets Management
- **Jiddiylik:** High
- **Ishonchlilik:** Confirmed
- **Tekshiruv turi:** Code inspection & File system analysis
- **Aniq joylashuv:** 
  - `d:\Ishchi stoli\Misa\yordamchi_9.0.0\data\ai_keys_cache.json`
  - `d:\Ishchi stoli\Misa\yordamchi_9.0.0\core\ai_engine.py` (Lines: 145-180)
- **Dalillar:**
  ```python
  # ai_engine.py L152-L165:
  def save_api_keys(keys_dict):
      with open("data/ai_keys_cache.json", "w", encoding="utf-8") as f:
          json.dump(keys_dict, f, indent=2)
  ```
- **Amaldagi holat:** Foydalanuvchi kiritgan barcha tashqi AI API kalitlari (`gemini_api_key`, `openai_api_key`, `claude_api_key`, `groq_api_key`) to‘g‘ridan-to‘g‘ri loyiha ildizidagi `data/ai_keys_cache.json` fayliga oddiy ochiq matn (plaintext JSON) shaklida yoziladi.
- **Kutiladigan holat:** OWASP ASVS V8.3 (Sensitive Private Data) va Microsoft Windows Security Guidelines talabiga muvofiq, foydalanuvchining uchinchi tomon hisoblash kvotalariga ega qimmatli API kalitlari Windows Data Protection API (DPAPI - `CryptProtectData`) yoki tizimning xavfsiz kalitlar omborida (Windows Credential Manager) shifrlangan holda saqlanishi kerak.
- **Kamchilik yoki xavf:** Kompyuterda ishlayotgan har qanday past darajali skript, zararli dastur (infostealer) yoki boshqa dasturlar ushbu faylni o‘qib, foydalanuvchining pullik API balanslarini o‘g‘irlashi mumkin.
- **Foydalanuvchiga ta’sir:** Moliyaviy yo‘qotishlar va shaxsiy API kalitlarining qora bozorda tarqalishi.
- **Root cause:** Kalitlarni saqlash uchun eng oson va tezkor usul (JSON fayl) tanlangan, DPAPI yoki `keyring` kutubxonasi integratsiya qilinmagan.
- **Tashqi manba:**
  - OWASP Top 10 A02:2021 Cryptographic Failures: https://owasp.org/Top10/A02_2021-Cryptographic_Failures/
  - Microsoft DPAPI Documentation: https://learn.microsoft.com/en-us/windows/win32/seccrypto/c-and-cpp-crypto-samples
- **Tavsiya:** Python `keyring` kutubxonasi yordamida kalitlarni Windows Credential Manager'ga saqlash yoki `cryptography.fernet` bilan Windows user SID ga asoslangan kalit bilan shifrlash.
- **Qabul mezoni:** `data/ai_keys_cache.json` fayli diskda ochiq qolmasligi yoki uning ichidagi ma’lumotlar kuchli shifrlangan holatda bo‘lishi.
- **Cheklovlar:** Fayl o‘qildi, unda haqiqiy kalitlar bor-yo‘qligi xavfsizlik nuqtayi nazaridan oshkor qilinmadi (`[REDACTED]`).

---

### Finding ID: SEC-APP-003
- **Sarlavha:** Telegram Orqali Avtorizatsiya Sessiyasining Frontendda Kriptografik Imzosiz Soxtalashtirilishi (Client-Side Token Synthesis)
- **Kategoriya:** Authentication & Session Integrity
- **Jiddiylik:** High
- **Ishonchlilik:** Confirmed
- **Tekshiruv turi:** Code inspection
- **Aniq joylashuv:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\services\backendService.ts` (Lines: 155-185)
- **Dalillar:**
  ```typescript
  // backendService.ts L160-L170:
  public createTelegramSession(telegramId: string, username: string): string {
    const cleanId = telegramId.replace(/[^0-9]/g, '');
    const sessionToken = `tg_token_${cleanId}_${Date.now()}_local`;
    localStorage.setItem('misa_session_token', sessionToken);
    localStorage.setItem('misa_user_role', 'telegram_user');
    return sessionToken;
  }
  ```
- **Amaldagi holat:** Telegram orqali kirishda brauzer (webview) `localStorage` ichiga shunchaki Telegram ID va joriy vaqtni qo‘shib sintetik token yozib qo‘ymoqda. Hech qanday server tomonida HMAC-SHA256 imzosi tekshirilmaydi.
- **Kutiladigan holat:** Telegram Login Widget / WebApp standartiga binoan, Telegram bergan `auth_date`, `hash` va foydalanuvchi ma’lumotlari backendda Bot Token yordamida HMAC-SHA256 orqali to‘liq validatsiyadan o‘tishi shart.
- **Kamchilik yoki xavf:** Agar tajovuzkor webview konsoliga yoki `localStorage` ga kirish imkoniga ega bo‘lsa, u ixtiyoriy foydalanuvchining Telegram ID raqamini qo‘yib, uning nomidan xotira va ma’lumotlarga kirishi mumkin.
- **Foydalanuvchiga ta’sir:** Foydalanuvchilararo izolyatsiyaning buzilishi (Identity Spoofing).
- **Root cause:** Telegram bot backend webhook integratsiyasining to‘liq tugallanmagani va vaqtinchalik "mock" mantiqning qolib ketgani.
- **Tashqi manba:** Telegram Authentication Data Verification Guide: https://core.telegram.org/widgets/login#checking-authorization
- **Tavsiya:** Mijoz tomonidagi token generatsiyasini bekor qilish; faqat Supabase yoki Misa Python backend orqali imzolangan JWT tokenlardan foydalanish.
- **Qabul mezoni:** Sessiya tokenlari faqat server tomonidan kriptografik imzolanib berilishi va frontendda sun’iy yaratilmasligi.
- **Cheklovlar:** Faqat frontend auth oqimi tekshirildi.

---

### Finding ID: SEC-APP-004
- **Sarlavha:** Tauri 2 Konfiguratsiyasida Izolyatsiya Namunasi (Isolation Pattern) Yoqilmagani va Kengaytirilgan Imtiyozlar
- **Kategoriya:** Platform Security / Attack Surface
- **Jiddiylik:** Medium
- **Ishonchlilik:** Confirmed
- **Tekshiruv turi:** Configuration inspection
- **Aniq joylashuv:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\src-tauri\tauri.conf.json` (Lines: 35-70)
- **Dalillar:**
  ```json
  // tauri.conf.json:
  "app": {
    "security": {
      "csp": null,
      "isolation": null
    }
  }
  ```
- **Amaldagi holat:** `csp` (Content Security Policy) `null` va `isolation` bloki mavjud emas. Bu degani, agar frontend kutubxonalarida (masalan, `npm` paketlarida) XSS zaifligi yuzaga kelsa, zararlangan JavaScript to‘g‘ridan-to‘g‘ri Tauri IPC chaqiriqlariga va native OS buyruqlariga kirish huquqiga ega bo‘ladi.
- **Kutiladigan holat:** Tauri 2 Security Architecture bo‘yicha yuqori xavfsizlik darajasidagi ilovalar:
  - Qat’iy Content Security Policy (CSP) ga ega bo‘lishi kerak (`script-src 'self'`).
  - Tashqi skriptlar IPC komandalarini soxtalashtirmasligi uchun Tauri Isolation Pattern (maxsus xavfsiz iframe proksi) qo‘llanilishi lozim.
- **Kamchilik yoki xavf:** Frontenddagi har qanday XSS to‘g‘ridan-to‘g‘ri OS darajasidagi RCE (Remote Code Execution) ga aylanadi.
- **Foydalanuvchiga ta’sir:** Ta’minot zanjiri (supply chain) yoki chatdagi HTML renderlash xatolari orqali tizimning to‘liq buzilishi.
- **Root cause:** Dasturni ishlab chiqishda xavfsizlik sozlamalarini soddalashtirish uchun standart konfiguratsiyada qoldirilgan.
- **Tashqi manba:** Tauri 2 Isolation Pattern Documentation: https://v2.tauri.app/security/isolation/
- **Tavsiya:** `tauri.conf.json` ichida qat’iy CSP belgilash va nozik fayl/shell amallari uchun ruxsatlarni granular cheklash.
- **Qabul mezoni:** Brauzer devtools konsolidan inline xavfli skriptlar ishga tushmasligi (CSP block).
- **Cheklovlar:** IPC kanallari xavfsizligi statik tahlil qilindi.

---

### Finding ID: SEC-APP-005
- **Sarlavha:** Maxfiylik Siyosatidagi Ziddiyat: "Zero-Leak Local AI" Va'dasi va Orqa Fondagi Google Web Speech API Oqimi
- **Kategoriya:** Privacy & Data Flow Discrepancy
- **Jiddiylik:** Medium
- **Ishonchlilik:** Confirmed
- **Tekshiruv turi:** Code inspection & Privacy audit
- **Aniq joylashuv:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\core\audio_service.py` (Lines: 185-215)
- **Dalillar:**
  ```python
  # audio_service.py L192-L198:
  try:
      # Offline vosita ishlamasa yoki tanlanmagan bo'lsa:
      text = recognizer.recognize_google(audio_data, language="uz-UZ")
  except sr.RequestError:
      ...
  ```
- **Amaldagi holat:** Misa hujjatlarida ("Zero-Leak", "To‘liq mahalliy maxfiylik") audio ma’lumotlar qurilmadan tashqariga chiqmaydi deb ko‘rsatilgan. Biroq `audio_service.py` ichida `recognize_google` (Google Cloud Speech API) zaxira variant sifatida chaqiriladi. Foydalanuvchi mikrofonidan yozib olingan ovoz Google serverlariga yuboriladi.
- **Kutiladigan holat:** NIST Privacy Framework (CT.PO-P Data Processing Transparency) talabiga ko‘ra, foydalanuvchining shaxsiy biometrik/ovozli ma’lumotlari uchinchi tomon bulutli servislariga yuborilayotgan bo‘lsa, bu haqda sozlamalarda ochiq ogohlantirish berilishi va alohida ruxsat (opt-in consent) so‘ralishi shart.
- **Kamchilik yoki xavf:** Foydalanuvchi o‘z suhbatlari faqat kompyuterida qolayapti deb o‘ylagan paytda, uning nozik audio yozuvlari Google serverlariga uzatiladi.
- **Foydalanuvchiga ta’sir:** Maxfiylik va ishonchning buzilishi, korxona xavfsizlik qoidalariga (masalan, GDPR / maxfiy suhbatlar) zid kelish.
- **Root cause:** O‘zbek tili uchun mahalliy offline STT (masalan, Whisper) o‘rniga oson yechim sifatida Google Web Speech tanlangan va bu interfeysda ko‘rsatilmagan.
- **Tashqi manba:** NIST Privacy Framework: https://www.nist.gov/privacy-framework
- **Tavsiya:** UI sozlamalarida "Ovozni aniqlash provayderi" (Mahalliy Whisper yoki Google Cloud) tanlovini qo‘shish va ogohlantirish berish.
- **Qabul mezoni:** Foydalanuvchi rozilik bermaguncha mikrofon ma’lumotlari tashqi tarmoqqa yuborilmasligi.
- **Cheklovlar:** Tarmoq trafigi tahlil qilindi; Google tomonidan qaysi ma’lumotlar saqlanishi tekshirilmadi.

---

## 4. STRIDE THREAT MODELING MATRIX

Misa Desktop AI Assistant uchun to‘liq tahdid modeli tuzildi:

| STRIDE Toifasi | Aniqlangan Xavf / Hujum Yo‘li | Ta’sirlangan Tizim Qismi | Mavjud Himoya | Qoldiq Xavf Darajasi |
|---|---|---|---|---|
| **S**poofing (Soxtalashtirish) | Telegram ID ni frontendda qo‘lda yozib sessiyani soxtalashtirish | `backendService.ts` | Yo‘q (faqat mahalliy saqlash) | **High** |
| **T**ampering (O‘zgartirish) | Port 18420 dagi ochiq REST API orqali tizim parametrlarini o‘zgartirish | `api_server.py` | Yo‘q (Wildcard CORS) | **Critical** |
| **R**epudiation (Inkor etish) | Agent tomonidan o‘chirilgan fayllar yoki xatti-harakatlarning imzolangan audit logi yo‘qligi | `agent_loop.py` | Faqat oddiy matnli log | **Medium** |
| **I**nformation Disclosure (Axborot sizishi) | API kalitlarining plaintext JSON da qolishi, audio oqimining Google ga chiqishi | `data/ai_keys_cache.json`, `audio_service.py` | Yo‘q | **High** |
| **D**enial of Service (Xizmatdan to‘xtatish) | Mahalliy port 18420 ni cheksiz so‘rovlar bilan to‘ldirib ilovani qotirib qo‘yish | FastAPI Server | Rate limit mavjud emas | **Medium** |
| **E**levation of Privilege (Huquqlarni oshirish) | `system_control` orqali ixtiyoriy PowerShell komandalarini chaqirish | `agent_tools.py` | Administrator huquqi talab qilinishi mumkin | **Critical** |

---

## 5. XULOSA VA TAVSIYALAR
Misa ilovasi xavfsiz desktop AI mahsulotiga aylanishi uchun:
1. `api_server.py` ga darhol qat’iy mahalliy xavfsizlik kaliti (Shared Local Secret Token) va CORS cheklovi kiritilishi shart.
2. API kalitlari Windows DPAPI orqali shifrlanishi kerak.
3. Maxfiylik va audio oqimlari sozlamalarda to‘liq shaffof qilinishi lozim.
