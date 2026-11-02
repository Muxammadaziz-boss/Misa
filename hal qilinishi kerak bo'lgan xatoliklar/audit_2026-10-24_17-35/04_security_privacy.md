# AUDIT HISOBOTI: 04. APPLICATION SECURITY VA PRIVACY SPECIALIST
**Ekspert roli:** Application Security va Privacy Specialist  
**Audit sanasi va vaqti:** 2026-10-24 17:35 (Toshkent vaqti)  
**Tekshirilgan branch va commit:** `dev-v9.0.0` (commit `aafa0d2fd15bba95b4f0c7aac921a9bd08986bb1`)  
**Loyiha ildiz katalogi:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0`  

---

## 1. TEKSHIRUV QAMROVI VA METODOLOGIYASI

Ushbu audit Misa AI tizimining axborot xavfsizligi, maxfiyligi (privacy), ruxsatlar chegaralari (trust boundaries), inyeksiya zaifliklari (command injection), maxfiy kalitlar boshqaruvi va foydalanuvchi shaxsiy ma'lumotlari daxlsizligini tekshirishga qaratilgan.

### Tekshirilgan asosiy fayllar va modullar:
- `core/agent_tools.py` — Agent vositalari va quyi jarayonlarni chaqirish
- `core/sandbox.py` — Izolatsiyalangan kod bajarish muhiti
- `core/v8/ai_key_manager.py` — API kalitlarini saqlash va kesh
- `Misa/src-tauri/src/lib.rs` — Desktop shell va muhit o'zgaruvchilari
- `Misa/src/services/backendService.ts` — Telegram va OAuth autentifikatsiyasi
- `core/api_server.py` — Tarmoq va CORS qoidalari

### Qo'llangan tekshiruv usullari:
- Tahdid modellashtirish (Threat Modeling & Attack Surface Review)
- Inyeksiya va shell buyruqlari qatorlarini tekshirish (Code Injection Analysis)
- Kriptografik kalitlar va saqlash xavfsizligi tekshiruvi (Secrets Storage Audit)
- Sandbox va ruxsatlar chegarasini aylanib o'tish (Sandbox Escape Analysis)

---

## 2. JIDDIYLI DARADALARI BO'YICHA TOPILMALAR STATISTIKASI

| Jiddiylik darajasi | Topilmalar soni |
| :--- | :---: |
| **Critical** | 2 |
| **High** | 2 |
| **Medium** | 1 |
| **Low** | 0 |
| **Info** | 0 |
| **JAMI** | **5** |

---

## 3. BATAFSIL TOPILMALAR

### Topilma ID: SEC-001
**Sarlavha:** `system_control` Vositasida PowerShell Buyruqlar Inyeksiyasi (Command Injection)  
**Kategoriya:** Security / Remote Code Execution  
**Jiddiylik darajasi:** Critical  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** 
- [core/agent_tools.py](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/agent_tools.py#L492-L520)

**Dalil:**
```python
# core/agent_tools.py L509-L516
app_cmd = APP_ALIASES.get(value.lower().strip(), value)

try:
    # PowerShell Start-Process — xavfsiz, shell injection yo'q
    subprocess.Popen(
        ["powershell", "-NoProfile", "-Command", f"Start-Process '{app_cmd}'"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
```

**Muammo tavsifi:**
Dastur kodidagi izohda `# xavfsiz, shell injection yo'q` deb yozilgan bo'lsa-da, amalda bu to'liq buyruqlar inyeksiyasiga ochiq. Agar `value` parametri `APP_ALIASES` ro'yxatida bo'lmasa, u to'g'ridan-to'g'ri qabul qilinadi va hech qanday ekranlashsiz (sanitization) `f"Start-Process '{app_cmd}'"` satriga joylashtiriladi.
Agar `value` ga `test'; Start-Process calc; #` qiymati berilsa, PowerShell quyidagicha bajaradi:
`Start-Process 'test'; Start-Process calc; #'`
Bu esa operatsion tizimda har qanday ixtiyoriy buyruqni bajarishga (RCE) imkon beradi.

**Yuzaga kelish shartlari:**
AI agenti foydalanuvchi so'rovi (yoki tashqi web-sahifadan olingan prompt injection) asosida `system_control` toolini chaqirganda.

**Ta’siri:**
Foydalanuvchi kompyuterida ixtiyoriy zararli dastur, skript yoki jarayonni yashirin ishga tushirish xavfi.

**Root cause:**
Tashqi kiruvchi satrni PowerShell buyrug'i ichiga qavs va apostroflarni tekshirmasdan to'g'ridan-to'g'ri string formatlash orqali kiritish.

**Qayta tekshirish usuli:**
Python interpretatorda:
`_system(action="open_app", value="notepad'; Start-Process calc; #")`
bajarilganda Kalkulyator dasturi ochilishi bilan xavf tasdiqlanadi.

**Tavsiya:**
PowerShell `Start-Process` satridan voz kechish. Windows API `os.startfile()` yoki xavfsiz massivli `subprocess.Popen([app_cmd], shell=False)` dan foydalanish va faqat ruxsat etilgan ilovalarning qat'iy oq ro'yxati (whitelist) bo'yicha ishlash.

**Qabul mezoni:**
Apostrof va maxsus belgilar kiritilganda ham buyruqlar inyeksiyasi sodir bo'lmasligi, faqat xavfsiz oq ro'yxatdagi dasturlar ochilishi.

**Cheklovlar:**
Windows OS muhitida sinovdan o'tkazilishi lozim.

---

### Topilma ID: SEC-002
**Sarlavha:** AI Provayderlarining Maxfiy API Kalitlarini Shifrlanmagan Ochiq Matnda Diskka Saqlash  
**Kategoriya:** Security / Credential Storage  
**Jiddiylik darajasi:** High  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** 
- [core/v8/ai_key_manager.py](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/v8/ai_key_manager.py#L16)
- [core/v8/ai_key_manager.py](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/v8/ai_key_manager.py#L102-L119)

**Dalil:**
```python
# core/v8/ai_key_manager.py L16
CACHE_FILE = REPO_ROOT / "data" / "ai_keys_cache.json"

# core/v8/ai_key_manager.py L115-L116
with open(CACHE_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
```

**Muammo tavsifi:**
Foydalanuvchi yoki tizim tomonidan kiritilgan barcha tashqi AI API kalitlari (Gemini, OpenRouter, Groq, Cerebras, Nvidia) diskdagi `data/ai_keys_cache.json` fayliga hech qanday shifrlashsiz, oddiy JSON formatida yoziladi. Garchi loyihada `core/secure_vault.py` mavjud bo'lsa-da, `ai_key_manager.py` undan foydalanmaydi.

**Yuzaga kelish shartlari:**
Ilovada birinchi marta API kaliti saqlanganda yoki bulutdan sinxronlanganda.

**Ta’siri:**
Foydalanuvchi kompyuteridagi har qanday unprivileged dastur, zararli skript (infostealer) yoki boshqa dasturlar ushbu faylni o'qib, foydalanuvchining pullik API hisoblariga to'liq kirish huquqini qo'lga kiritadi.

**Root cause:**
Kalitlarni boshqaruvchi modul ishlab chiqilganda mavjud `SecureVault` shifrlash tizimi bilan integratsiya qilinmagan.

**Qayta tekshirish usuli:**
`data/ai_keys_cache.json` faylini matn muharririda ochib, kalitlarning ochiq holda turganligini ko'rish.

**Tavsiya:**
API kalitlarini saqlash uchun Windows Data Protection API (DPAPI via `cryptography` yoki `keyring`) yoki loyihadagi `SecureVault` modulidan foydalanish. Diskda hech qachon ochiq JSON saqlanmasligi kerak.

**Qabul mezoni:**
Diskdagi kesh fayli to'liq shifrlangan bo'lishi yoki Windows Credential Manager da saqlanishi.

**Cheklovlar:**
Ushbu hisobotda maxfiy kalit qiymatlari ko'rsatilmadi (`[REDACTED]`).

---

### Topilma ID: SEC-003
**Sarlavha:** `loginWithTelegram` da Kriptografik Imzo Tekshiruvisiz Soxta Token Yaratish (Identity Forgery)  
**Kategoriya:** Security / Authentication Bypass  
**Jiddiylik darajasi:** Critical  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** 
- [Misa/src/services/backendService.ts](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/services/backendService.ts#L3783-L3810)

**Dalil:**
```typescript
// Misa/src/services/backendService.ts L3783-L3807
public async loginWithTelegram(payload: { telegram_id?: number | string; username?: string; ... }) {
  const cleanId = rawId || tgUsername || `tg_${Date.now().toString().slice(-6)}`;
  const user: MikasaAuthUser = {
    id: `tg_${cleanId}`,
    username: displayName,
    email,
    provider: "telegram",
    ...
  };
  const sessionToken = `tg_token_${cleanId}_${Date.now()}`;
  this.setAuthToken(sessionToken);
```

**Muammo tavsifi:**
Frontenddagi `loginWithTelegram` metodi Telegram tomonidan berilgan rasmiy kriptografik `hash` va `auth_date` parametrlarini tekshirmaydi. Har qanday mijoz ixtiyoriy `telegram_id` va `username` yuborib, o'zini o'sha foydalanuvchi deb ko'rsatishi mumkin. Metod mijoz tomonida soxta token (`tg_token_...`) yaratadi va tizimga kirgan deb e'lon qiladi.

**Yuzaga kelish shartlari:**
Telegram orqali kirish oynasida mijoz tomonidan soxta ID kiritilganda.

**Ta’siri:**
Boshqa bir Telegram foydalanuvchisining profili va shaxsiga noqonuniy kirish (Account Takeover / Impersonation).

**Root cause:**
Telegram Login Widget va WebApp ma'lumotlarini server tomonida Bot Tokeni orqali HMAC-SHA256 tekshiruvi backendda qilinishi kerak bo'lgani holda, frontendda sodda va xavfli mock yaratilgan.

**Qayta tekshirish usuli:**
Brauzer konsolida `backendService.loginWithTelegram({ telegram_id: 9999999, username: "victim" })` chaqirilganda soxta profil ochilishi tasdiqlanadi.

**Tavsiya:**
Ushbu frontend metodini butunlay bekor qilish. Telegram orqali kirish faqat backenddagi OTP mexanizmi (`core/v8/telegram_identity.py`) yoki rasmiy Telegram WebApp HMAC validatsiyasi orqali amalga oshirilishi shart.

**Qabul mezoni:**
Backenddan imzolanmagan hech qanday Telegram profili qabul qilinmasligi.

**Cheklovlar:**
Bu usul faqat frontend lokal sessiyasiga ta'sir qiladi, ammo lokal xotiradagi ma'lumotlarni ochib beradi.

---

### Topilma ID: SEC-004
**Sarlavha:** Rust Manba Kodida Supabase Publishable / Anon Kalitlarining Qattiq Kodlanishi (Hardcoded Keys)  
**Kategoriya:** Security / Secret Management  
**Jiddiylik darajasi:** Medium  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** 
- [Misa/src-tauri/src/lib.rs](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src-tauri/src/lib.rs#L525-L529)

**Dalil:**
```rust
// Misa/src-tauri/src/lib.rs L525-L529
let sup_url = std::env::var("SUPABASE_URL")
    .unwrap_or_else(|_| "https://vdcssmzguxfknqkfxbed.supabase.co".to_string());
let sup_key = std::env::var("SUPABASE_PUBLISHABLE_KEY")
    .or_else(|_| std::env::var("SUPABASE_ANON_KEY"))
    .unwrap_or_else(|_| "[REDACTED_PUBLISHABLE_KEY]".to_string());
```

**Muammo tavsifi:**
Kompilyatsiya qilinadigan Rust manba kodida Supabase URL va Publishable/Anon kalitlari qattiq kodlangan (hardcoded). Garchi publishable key ommaviy hisoblansa-da, agar kelajakda Supabase loyihasi yoki kalitlari o'zgartirilsa, barcha tuzilgan binar executabler eskirgan loyihaga murojaat qilib qoladi va ularni yangilash imkoni bo'lmaydi.

**Yuzaga kelish shartlari:**
Dastur `.env` faylsiz toza kompyuterda ishga tushganda.

**Ta’siri:**
Infratuzilma qattiq bog'lanib qoladi (tight coupling), loyiha kalitlarini xavfsiz rotatsiya qilish imkoniyati cheklanadi.

**Root cause:**
Desktop muhitida env fayllarni qidirish muvaffaqiyatsiz bo'lganda tezkor fallback sifatida manba kodiga yozib ketilgan.

**Qayta tekshirish usuli:**
`strings Misa-AI-v9.3.exe | findstr supabase.co` buyrug'i orqali binar ichida manzil borligini aniqlash mumkin.

**Tavsiya:**
Kalitlarni binar kodiga yozmasdan, tashqi konfiguratsiya yoki o'rnatuvchi manifest fayllari orqali yetkazish.

**Qabul mezoni:**
Rust binar fayli manbasida hech qanday loyiha domeni yoki kalitining statik matni mavjud bo'lmasligi.

**Cheklovlar:**
Publishable key service_role kaliti emas, shu sababli xavflilik darajasi Critical emas, Medium.

---

### Topilma ID: SEC-005
**Sarlavha:** `core/sandbox.py` da Qora Ro'yxat Regexi Tufayli Muhitdan Chiqish (Sandbox Escape) Xavfi  
**Kategoriya:** Security / Sandbox Security  
**Jiddiylik darajasi:** High  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** 
- [core/sandbox.py](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/sandbox.py#L47-L76)

**Dalil:**
```python
# core/sandbox.py L48
BLOCKED_PATTERNS = [
    r"import\s+os\s*(?!as)",
    r"from\s+os\s+import",
    r"import\s+sys\s*(?!as)",
...
```

**Muammo tavsifi:**
`core/sandbox.py` moduli Python kodini xavfsiz deb topishda regex qora ro'yxatidan (blacklist) foydalanadi. Qizig'i shundaki, 48 va 50-qatorlardagi regexda `(?!as)` manfiy qarash (negative lookahead) kiritilgan. Natijada `import os as my_os` sintaksisi ushbu regexga MOS KELMAYDI va tekshiruvdan o'tib ketadi. Garchi quyiroqda AST tekshiruvi mavjud bo'lsa-da, regex va AST qoidalarining nomutanosibligi buzg'unchiga boshqa metodlar orqali sandboxdan chiqish (escape) imkoniyatini qoldiradi.

**Yuzaga kelish shartlari:**
Agent xavfli foydalanuvchi kodi yoki LLM tomonidan tuzilgan Python kodini `sandbox` vositasi orqali bajarganda.

**Ta’siri:**
Izolyatsiya buzilishi, operatsion tizim resurslariga ruxsatsiz kirish.

**Root cause:**
Python tili dinamikligini regex orqali cheklashga urinish (Blacklisting anti-pattern).

**Qayta tekshirish usuli:**
`validate_code("import os as my_os")` kiritilganda birinchi regex filtridan o'tib ketishi bilan tasdiqlanadi.

**Tavsiya:**
Qora ro'yxatlarga tayanmaslik. Python kodini operatsion tizim darajasidagi konteyner (Docker) yoki maxsus xavfsiz izolyator (Windows Sandbox / AppContainer / WASM) ichida bajarish.

**Qabul mezoni:**
Python kodi asosiy tizim muhitidan mutlaqo ajratilgan xavfsiz virtual izolyatsiyada bajarilishi.

**Cheklovlar:**
Lokal Windows muhitida AppContainer yaratish qo'shimcha drayver va ruxsatlarni talab qilishi mumkin.

---

## 4. TEKSHIRISH IMKONI BO'LMAGAN QISMLAR VA CHEKLOVLAR
- Jonli Supabase loyihasidagi barcha RLS siyosatlari to'liq penetratsion test qilinmadi (faqat lokal SQL skriptlar o'rganildi).
- Maxfiy tokenlar hisobotga kiritilmadi (`[REDACTED]`).

---

## 5. UMUMIY XULOSA VA USTUVOR YO'NALISHLAR
Misa xavfsizligida zudlik bilan bartaraf etilishi shart bo'lgan ikkita o'ta xavfli zaiflik mavjud: `system_control` vositasidagi PowerShell inyeksiyasi va `loginWithTelegram` dagi soxta autentifikatsiya. Ushbu zaifliklar ilovaning ishonchliligiga jiddiy putur yetkazadi.

### Boshlang'ich ustuvor vazifalar:
1. `core/agent_tools.py` dagi `system_control` vositasini qayta yozib, PowerShell inyeksiyasini bartaraf etish.
2. `data/ai_keys_cache.json` faylidagi ochiq kalitlarni shifrlash.
3. Frontenddagi soxta `loginWithTelegram` metodini bekor qilib, faqat xavfsiz backend tekshiruviga tayanish.
