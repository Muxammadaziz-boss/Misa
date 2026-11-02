# MISA V9 — SECURITY AUDIT: APPLICATION & DESKTOP SECURITY REPORT
**Loyiha:** Misa Desktop AI Assistant (v9.0.0 / v9.3)  
**Audit Davri:** 2026-10-24  
**Auditor:** Principal Application Security Engineer & Desktop Security Auditor  
**Katalog:** `hal qilinishi kerak bo'lgan xatoliklar\security_deep_audit_2026-10-24_18-14\`  
**Standartlar:** OWASP ASVS v4.0.3, OWASP Top 10:2021, OWASP API Security Top 10:2023, Tauri 2 Security Guidelines, Microsoft Windows Security API  
**Holat:** Yakunlandi (Read-Only Deep Static Inspection)

---

## 1. IJROCHI XULOSA

Misa v9 ning dasturiy va desktop xavfsizlik arxitekturasi chuqur tahlil qilindi. 
Tekshiruv natijasida tizimda bir nechta yuqori va o‘ta xavfli (Critical) zaifliklar aniqlandi:

1. **Localhost = Trusted xatosi:** Mahalliy aiohttp REST serveri (`core/api_server.py`) desktop rejimida ishlaganda `auth_enforcement_middleware` ichida autentifikatsiyani 100% o‘chirib qo‘ygan.
2. **IPC Orqali ShellExecuteW Zaifligi:** Tauri Rust qatlamida (`Misa/src-tauri/src/lib.rs`) tashqi havolalarni ochuvchi `app_open_external_url` funksiyasi URL protokolini (`http/https`) tekshirmaydi, natijada Windows ShellExecuteW orqali ixtiyoriy `.exe`, `.bat` yoki Windows protokollari ishga tushishi mumkin.
3. **PowerShell Argument Injection:** `core/agent_tools.py` dagi `open_app` amali foydalanuvchi yoki agent kiritgan ilova nomini to‘g‘ridan-to‘g‘ri PowerShell satriga formatlab uzatishi sababli quote-escape orqali kod ijro etish zaifligiga ega.
4. **Shifrlanmagan API Kalitlari:** Foydalanuvchining pullik API kalitlari (Gemini, OpenRouter, Groq, Cerebras, Nvidia) diskda ochiq `data/ai_keys_cache.json` faylida DPAPI shifrlashisiz saqlanmoqda.

---

## 2. TOPILMALAR STATISTIKASI

| ID | Sarlavha | Xavfsizlik Toifasi | Jiddiylik | Ishonchlilik | Fayl va Joylashuv |
|---|---|---|---|---|---|
| **SEC-001** | Desktop Rejimda REST API da Autentifikatsiyaning To‘liq Yo‘qligi | OWASP ASVS V13.1, API2:2023 | **Critical** | Confirmed | `core/api_server.py:7328-7330` |
| **SEC-002** | `ShellExecuteW` da URL Sxemasi Tekshirilmasligi (Native RCE Xavfi) | CWE-78, OWASP ASVS V5.2 | **Critical** | Confirmed | `Misa/src-tauri/src/lib.rs:662-682` |
| **SEC-003** | PowerShell `Start-Process` da Satr Formatlash Orqali Ineksiya | CWE-78, CWE-88, ASVS V5.3 | **High** | Confirmed | `core/agent_tools.py:513-516` |
| **SEC-004** | AI Provayder Kalitlarining Ochiq Plaintext JSON Faylida Saqlanishi | CWE-312, OWASP Top 10 A02 | **High** | Confirmed | `core/v8/ai_key_manager.py:102-118` |
| **SEC-005** | Telegram Sessiya Tokenining Frontendda Sintetik Yaratilishi | CWE-287, OWASP ASVS V2.1 | **High** | Confirmed | `Misa/src/services/backendService.ts:160-170` |
| **SEC-006** | Ma’lum Zaifliklarga Ega `requests` Kutubxonasi va Izolyatsiya Yo‘qligi | CWE-1395, Tauri 2 Security | **Medium** | Confirmed | `requirements.txt`, `tauri.conf.json` |

---

## 3. CHUQUR DALILLANGAN TOPILMALAR

### Finding ID: SEC-001
- **Sarlavha:** Desktop Rejimida Mahalliy REST API da Autentifikatsiyaning To‘liq O‘chirib Qo‘yilishi va `/api/commands/execute` Himoyasizligi
- **Xavfsizlik kategoriyasi:** Identity and Access Control / API Architecture
- **Severity:** Critical
- **Confidence:** Confirmed
- **Fayl va qator raqami:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\core\api_server.py` (Lines: 7328-7330, 1962-2015)
- **Dalil va tegishli kod yo‘li:**
  ```python
  # core/api_server.py L7328-L7330:
  # 3. Desktop rejimda (localhost) — backward-compatibility, auth talab qilinmaydi
  if not _is_production_mode():
      return await handler(request)
  ```
  Shuningdek, `L1962` dagi `handle_commands_execute`:
  ```python
  @app.post("/api/commands/execute")
  async def handle_commands_execute(request):
      body = await request.json()
      cmd_text = body.get("command", "").strip()
      # Har qanday ro'yxatdan o'tgan tool hech qanday token yoki parolsiz chaqiriladi:
      tool = reg.get(candidate)
      res = tool.call(**kwargs)
      ...
  ```
- **Muammoning yuzaga kelish shartlari:** Misa odatiy tarzda kompyuterda ishga tushirilganda (`_is_production_mode() == False`), port `18420` dagi barcha API endpointlar (chat, buyruqlarni bajarish, xotirani tozalash, tizim ma’lumotlarini olish) hech qanday sessiya yoki autentifikatsiya talab qilmaydi.
- **Ta’sir va ehtimoliy zarar:** Agar foydalanuvchi o‘zining Chrome, Firefox yoki Edge brauzerida oddiy bir veb-saytga kirsa, tajovuzkor ushbu sahifadagi JavaScript orqali `fetch('http://127.0.0.1:18420/api/commands/execute', {method: 'POST', body: JSON.stringify({command: 'system_control', parameters: {action: 'open_cmd'}})})` so‘rovini yuborishi mumkin. Bu Drive-by Local Attack orqali foydalanuvchi xabarisiz uning kompyuterida amallarni bajarishga imkon beradi.
- **Root cause:** Ishlab chiquvchilar dastlabki rivojlanish davrida frontend bilan aloqani osonlashtirish uchun "localhost rejimida auth kerak emas" degan qoidani qoldirgan va uni xavfsiz token bilan almashtirmagan.
- **Tegishli rasmiy standart yoki hujjat:**
  - OWASP ASVS v4.0.3 bo‘lim V13.1 (API Verification Requirements)
  - OWASP API Security Top 10:2023 API2:2023 (Broken Authentication)
- **Tavsiya qilinadigan himoya yo‘nalishi:** 
  1. Tauri ishga tushganda dinamik ravishda bir martalik tasodifiy token (`X-Misa-Session-Token` yoki Pre-Shared Key) generatsiya qilsin va uni Rust orqali Python backendga uzatsin.
  2. `auth_enforcement_middleware` desktop rejimida ham ushbu tokenni qat’iy tekshirsin.
- **Kelajakdagi tekshiruv uchun qabul mezoni:** Begona brauzer konsolidan tokensiz `fetch('http://127.0.0.1:18420/api/commands/execute')` yuborilganda `401 Unauthorized` xatosi qaytishi.
- **Cheklovlar va tekshirilmagan jihatlar:** Kod tekshiruvi orqali 100% tasdiqlandi; faol exploit so‘rovi yuborilmadi.

---

### Finding ID: SEC-002
- **Sarlavha:** Tauri Rust Qatlamidagi `ShellExecuteW` da URL Sxemasi Validatsiyasi Yo‘qligi (Ixtiyoriy Fayl va Dasturni Ishga Tushirish Xavfi)
- **Xavfsizlik kategoriyasi:** Desktop & Windows Security / Native IPC Execution
- **Severity:** Critical
- **Confidence:** Confirmed
- **Fayl va qator raqami:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src-tauri\src\lib.rs` (Lines: 662-682)
- **Dalil va tegishli kod yo‘li:**
  ```rust
  // Misa/src-tauri/src/lib.rs L662-L682:
  fn app_open_external_url(url: String) -> Result<(), String> {
      startup_log("OPENER", &format!("Opening external URL via native OS shell: {}", url));
      #[cfg(target_os = "windows")]
      {
          use std::ffi::OsStr;
          use std::os::windows::ffi::OsStrExt;
          extern "system" {
              fn ShellExecuteW(
                  hwnd: isize,
                  lpOperation: *const u16,
                  lpFile: *const u16,
                  lpParameters: *const u16,
                  lpDirectory: *const u16,
                  nShowCmd: i32,
              ) -> isize;
          }
          let op: Vec<u16> = OsStr::new("open").encode_wide().chain(std::iter::once(0)).collect();
          let target: Vec<u16> = OsStr::new(&url).encode_wide().chain(std::iter::once(0)).collect();
          let res = unsafe {
              ShellExecuteW(0, op.as_ptr(), target.as_ptr(), std::ptr::null(), std::ptr::null(), 1)
          };
      }
  }
  ```
- **Muammoning yuzaga kelish shartlari:** Frontenddan `invoke('app_open_external_url', { url: '...' })` chaqirilganda, kiritilgan `url` satri hech qanday tekshiruvsiz Windows OS ning `ShellExecuteW(0, "open", url, ...)` API siga uzatiladi.
- **Ta’sir va ehtimoliy zarar:** Windows da `ShellExecuteW` nafaqat veb-saytlarni ochadi, balki fayllarni ishga tushiradi. Agar argument sifatida `cmd.exe`, `powershell.exe`, `ms-msdt:...`, yoki `.bat` fayl yo‘li berilsa, Windows Shell uni to‘g‘ridan-to‘g‘ri dastur sifatida ishga tushiradi (Arbitrary Code Execution). Agar frontendda chat havolalari render qilinayotganda XSS sodir bo‘lsa, ushbu zaiflik to‘g‘ridan-to‘g‘ri native RCE ga aylanadi.
- **Root cause:** Funksiya faqat tashqi brauzerda veb-sahifa ochish uchun mo‘ljallangan, ammo unda URL faqat `http://` yoki `https://` bilan boshlanishini talab qiluvchi tekshiruv kiritilmagan.
- **Tegishli rasmiy standart yoki hujjat:**
  - Microsoft Windows Dev Center: ShellExecuteW Security Best Practices
  - OWASP ASVS v4.0.3 bo‘lim V5.2 (Sanitization and Sandboxing)
  - CWE-78: Improper Neutralization of Special Elements used in an OS Command
- **Tavsiya qilinadigan himoya yo‘nalishi:** Rust funksiyasi ichida `url` faqat `http://` yoki `https://` bilan boshlanishini tekshirish:
  ```rust
  if !url.starts_with("https://") && !url.starts_with("http://") {
      return Err("Faqat HTTP/HTTPS protokollariga ruxsat berilgan".into());
  }
  ```
- **Kelajakdagi tekshiruv uchun qabul mezoni:** `invoke('app_open_external_url', { url: 'cmd.exe' })` chaqirilganda `Err` qaytishi va komanda bajarilmasligi.
- **Cheklovlar va tekshirilmagan jihatlar:** Kod statik ravishda tekshirildi, Rust xavfsiz kodi tahlil qilindi.

---

### Finding ID: SEC-003
- **Sarlavha:** PowerShell `Start-Process` Amali Orqali Ilova Ochishda Quote-Escape va Argument Injection Zaifligi
- **Xavfsizlik kategoriyasi:** Input Validation & Command Injection
- **Severity:** High
- **Confidence:** Confirmed
- **Fayl va qator raqami:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\core\agent_tools.py` (Lines: 509-519)
- **Dalil va tegishli kod yo‘li:**
  ```python
  # core/agent_tools.py L509-L516:
  app_cmd = APP_ALIASES.get(value.lower().strip(), value)

  try:
      # PowerShell Start-Process — xavfsiz, shell injection yo'q (Dasturchi izohi noto'g'ri!)
      subprocess.Popen(
          ["powershell", "-NoProfile", "-Command", f"Start-Process '{app_cmd}'"],
          creationflags=subprocess.CREATE_NO_WINDOW,
      )
  ```
- **Muammoning yuzaga kelish shartlari:** Foydalanuvchi yoki AI agent `system_control` asbobiga `action="open_app"` va `value` sifatida qiymat berganda. Agar `value` `APP_ALIASES` lug‘atida bo‘lmasa, u to‘g‘ridan-to‘g‘ri f-string orqali `'...'` bittalik qo‘shtirnoq ichiga joylanadi.
- **Ta’sir va ehtimoliy zarar:** PowerShell da bittalik qo‘shtirnoq ichidagi satrni bittalik qo‘shtirnoq va nuqta-vergul bilan yopish mumkin. Masalan, agar `value` qiymati: `test'; Start-Process calc.exe; #` bo‘lsa, PowerShell da bajariladigan komanda quyidagicha bo‘ladi:
  `Start-Process 'test'; Start-Process calc.exe; #'`
  Bu tizimda ixtiyoriy PowerShell komandasining bajarilishiga (Command Injection) olib keladi.
- **Root cause:** Dasturchi "PowerShell Start-Process orqali ochsak, shell injection bo‘lmaydi" deb yanglish o‘ylagan, ammo `f"Start-Process '{app_cmd}'"` satrli formatlash orqali parametrlarni to‘g‘ridan-to‘g‘ri inyeksiya qilishga yo‘l qo‘ygan.
- **Tegishli rasmiy standart yoki hujjat:**
  - CWE-78: OS Command Injection
  - CWE-88: Improper Neutralization of Argument Delimiters in a Command
  - OWASP ASVS v4.0.3 bo‘lim V5.3 (Output Encoding and Injection Prevention)
- **Tavsiya qilinadigan himoya yo‘nalishi:** PowerShell orqali satrli komanda tuzish o‘rniga, faqat ruxsat etilgan ilovalar oq ro‘yxatidan (Allowlist) foydalanish yoki to‘g‘ridan-to‘g‘ri `subprocess.Popen([binary_path], shell=False)` dan foydalanish va hech qachon foydalanuvchi parametrini PowerShell kodiga formatlamaslik.
- **Kelajakdagi tekshiruv uchun qabul mezoni:** Maxsus belgilar (`'`, `;`, `$`, `&`) o‘z ichiga olgan nom kiritilganda ineksiya bajarilmasligi va qat’iy rad etilishi.
- **Cheklovlar va tekshirilmagan jihatlar:** Kod sintaksisi va PowerShell parser qoidalari bo‘yicha to‘liq isbotlandi.

---

### Finding ID: SEC-004
- **Sarlavha:** AI Provayderlarining API Kalitlari (Gemini, OpenRouter, Groq va b.) Shifrlanmagan Plaintext JSON Faylida Saqlanishi
- **Xavfsizlik kategoriyasi:** Cryptographic Storage & Secrets Management
- **Severity:** High
- **Confidence:** Confirmed
- **Fayl va qator raqami:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\core\v8\ai_key_manager.py` (Lines: 102-118)
- **Dalil va tegishli kod yo‘li:**
  ```python
  # core/v8/ai_key_manager.py L106-L116:
  data = {
      "gemini": self._system_keys.get("gemini", []),
      "openrouter": self._system_keys.get("openrouter", []),
      "groq": self._system_keys.get("groq", []),
      "cerebras": self._system_keys.get("cerebras", []),
      "nvidia": self._system_keys.get("nvidia", []),
      "active_models": self._active_models,
      "updated_at": time.time(),
  }
  with open(CACHE_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, indent=2)
  ```
  `CACHE_FILE` manzili esa: `REPO_ROOT / "data" / "ai_keys_cache.json"`.
- **Muammoning yuzaga kelish shartlari:** Dastur har safar kalitlarni o‘rnatganda yoki yangilaganda, barcha API kalitlari oddiy JSON formatida diskka yoziladi.
- **Ta’sir va ehtimoliy zarar:** Kompyuterda ishlovchi istalgan oddiy (imtiyozsiz) dastur, infostealer yoki skript ushbu faylni o‘qib, foydalanuvchining pullik API hisoblari va kvotalarini o‘g‘irlashi mumkin.
- **Root cause:** Kalitlarni saqlashning eng oson yo‘li sifatida oddiy faylga yozish tanlangan, Windows Data Protection API (DPAPI) yoki tizim kalitlar ombori ishlatilmagan.
- **Tegishli rasmiy standart yoki hujjat:**
  - OWASP Top 10:2021 A02: Cryptographic Failures
  - OWASP ASVS v4.0.3 bo‘lim V8.3 (Sensitive Private Data)
  - Microsoft Windows CryptProtectData (DPAPI) API
- **Tavsiya qilinadigan himoya yo‘nalishi:** Python `cryptography` yoki `keyring` moduli orqali kalitlarni Windows Credential Manager'ga joylash yoki Windows foydalanuvchi hisobiga bog‘langan DPAPI bilan shifrlash.
- **Kelajakdagi tekshiruv uchun qabul mezoni:** `data/` katalogida ochiq matnli kalitlar mavjud bo‘lmasligi, fayl faqat shifrlangan baytlarni o‘z ichiga olishi.
- **Cheklovlar va tekshirilmagan jihatlar:** Fayl mavjudligi tekshirildi, maxfiy kalit qiymatlari xavfsizlik maqsadida oshkor etilmadi (`[REDACTED]`).

---

### Finding ID: SEC-005
- **Sarlavha:** Telegram Foydalanuvchi Sessiyasining Frontendda Sintetik Yaratilishi va Backend Imzosi Yo‘qligi
- **Xavfsizlik kategoriyasi:** Identity and Access Control / Session Management
- **Severity:** High
- **Confidence:** Confirmed
- **Fayl va qator raqami:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\services\backendService.ts` (Lines: 155-180)
- **Dalil va tegishli kod yo‘li:**
  ```typescript
  // Misa/src/services/backendService.ts L160-L166:
  public createTelegramSession(telegramId: string, username: string): string {
    const cleanId = telegramId.replace(/[^0-9]/g, '');
    const sessionToken = `tg_token_${cleanId}_${Date.now()}_local`;
    localStorage.setItem('misa_session_token', sessionToken);
    localStorage.setItem('misa_user_role', 'telegram_user');
    return sessionToken;
  }
  ```
- **Muammoning yuzaga kelish shartlari:** Foydalanuvchi Telegram orqali tizimga kirganda, frontend o‘zicha token yasab, `localStorage` ga yozadi. Backenddagi `core/v8/telegram_identity.py` dagi xavfsiz OTP xeshlash zanjiri chetlab o‘tiladi.
- **Ta’sir va ehtimoliy zarar:** Har qanday shaxs brauzer devtools konsolida istalgan boshqa foydalanuvchining raqamli Telegram ID sini kiritib, uning nomidan mahalliy sessiya yarata oladi (Identity Spoofing).
- **Root cause:** Frontend va backend o‘rtasida Telegram sessiyasini to‘liq integratsiya qilish oxiriga yetkazilmagan, vaqtinchalik yechim qoldirilgan.
- **Tegishli rasmiy standart yoki hujjat:**
  - OWASP ASVS v4.0.3 bo‘lim V2.1 va V3.1 (Session Management)
  - Telegram Login Widget Verification: https://core.telegram.org/widgets/login
- **Tavsiya qilinadigan himoya yo‘nalishi:** Frontendda token generatsiya qilishni to‘xtatish. Telegram avtorizatsiyasini faqat backend orqali HMAC-SHA256 imzosi tekshirilgandan so‘ng qabul qilish.
- **Kelajakdagi tekshiruv uchun qabul mezoni:** Frontendda `createTelegramSession` kabi sintetik funksiyalar qolmasligi.
- **Cheklovlar va tekshirilmagan jihatlar:** Kod tahlili orqali tasdiqlandi.

---

### Finding ID: SEC-006
- **Sarlavha:** Ma’lum Xavfsizlik Zaifliklariga Ega `requests==2.31.0` Kutubxonasi va Tauri Izolyatsiya Namunasi Yo‘qligi
- **Xavfsizlik kategoriyasi:** Dependencies & Supply Chain / Platform Security
- **Severity:** Medium
- **Confidence:** Confirmed
- **Fayl va qator raqami:** 
  - `d:\Ishchi stoli\Misa\yordamchi_9.0.0\requirements.txt` (Line 13)
  - `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src-tauri\tauri.conf.json` (Lines: 12-17)
- **Dalil va tegishli kod yo‘li:**
  `requirements.txt` L13:
  `requests==2.31.0`
  `Misa/src-tauri/tauri.conf.json`:
  `"isolation": null` (Mavjud emas)
- **Muammoning yuzaga kelish shartlari:** `requests` 2.31.0 versiyasi CVE-2023-32681 (Proxy-Authorization header leak) va CVE-2024-35195 (TLS Session reuse leak) kabi ma’lum zaifliklarga ega. Shuningdek, Tauri da Isolation Pattern yoqilmagan.
- **Ta’sir va ehtimoliy zarar:** Qayta yo‘naltirilgan proksi so‘rovlarida sarlavhalar sizishi yoki frontenddagi skriptlarning bevosita IPC ga ruxsat olishi xavfi.
- **Root cause:** Kutubxona versiyalarining uzoq vaqt yangilanmagani.
- **Tegishli rasmiy standart yoki hujjat:**
  - CVE-2024-35195: https://nvd.nist.gov/vuln/detail/CVE-2024-35195
  - Tauri 2 Isolation Pattern Documentation
- **Tavsiya qilinadigan himoya yo‘nalishi:** `requests` ni kamida `2.32.3` versiyasiga yangilash va `tauri.conf.json` da qat’iy izolyatsiyani joriy qilish.
- **Kelajakdagi tekshiruv uchun qabul mezoni:** Paketlar xavfsizlik skanerlarida (Safety / Dependabot) 0 ta zaiflik ko‘rsatishi.
- **Cheklovlar va tekshirilmagan jihatlar:** Paketlar yangilanmadi (Read-Only qoidasi).

---

## 4. XULOSA VA TAVSIYALAR
Application va Desktop darajasida Misa zudlik bilan:
1. `ShellExecuteW` chaqiruviga qat’iy `http://`/`https://` protokol filtrini kiritishi,
2. `core/api_server.py` desktop rejimida ham dinamik `X-Misa-Session-Token` talab qilishini ta’minlashi,
3. `open_app` amalini xavfsiz oq ro‘yxat (allowlist) bilan cheklashi shart.
