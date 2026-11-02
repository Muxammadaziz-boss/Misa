# 05 — FINAL VALIDATED RISK & MITIGATION REGISTER
## MISA V9 — Qayta Tasdiqlangan va Kalibrlangan Master Xavf-Xatarlar Reyestri

- **Audit Turi:** Final Calibrated Risk Register (Phase 4.1)
- **Sana:** 2026-10-24
- **Auditor Roli:** Chief Risk Officer, Principal Security Architect & Engineering Lead
- **Jami Master Root Causes:** 32 ta (31 CONFIRMED, 1 PARTIALLY_CONFIRMED)
- **Qat'iy Qoida:** 100% READ-ONLY. Hech qanday kod o'zgartirilmadi.

---

## 1. YAKUNIY JIDDIY LIK TAQSIMOTI

Barcha topilmalar real tizim ta'siri, ekspluatatsiya qilinish ehtimoli va me'yoriy standartlar bo'yicha qayta tekshirildi:

```
   Tier 1: CRITICAL [██████] 6 ta (19%) — Tizimni to'xtatuvchi xavflar (RCE, Crash, Secret Leak)
   Tier 2: HIGH     [███████████] 11 ta (34%) — Xavfsizlik, accessibility va agent nazorati
   Tier 3: MEDIUM   [███████████] 11 ta (34%) — Usability, dizayn tizimi va xotira
   Tier 4: LOW      [████] 4 ta (13%) — Estetika, intro va arxitektura tozalash
   ---------------------------------------------------------------------------------------------------
   JAMI MASTER ROOT CAUSE : 32 ta (31 ta CONFIRMED + 1 ta PARTIALLY_CONFIRMED)
```

---

## 2. TIER 1: CRITICAL (O'TA JIDDIY VA ZUDLIK BILAN TUZATILISHI SHART — 6 TA)

### 1. `MISA-ROOT-001`: Port 18420 dagi mahalliy API autentifikatsiyasi yo'qligi va CORS `*`
- **Tasnifi:** `SECURITY_RISK` | **Holati:** `CONFIRMED`
- **Fayl & Qator:** [`core/api_server.py:7328-7330`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/api_server.py#L7328), [`7351`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/api_server.py#L7351)
- **Standart:** OWASP ASVS v4.0.3 V14.5.3, CWE-306
- **Xavf & Sharoit:** Foydalanuvchi oddiy brauzerida zararli sahifaga kirganda, sahifadagi JS `http://127.0.0.1:18420` ga buyruq yuborishi mumkin (`_is_production_mode == False` tufayli token talab qilinmaydi).
- **Tuzatish Chora-tadbiri:** Desktop rejimida ham dinamik `X-Misa-Session-Token` majburiy qilinsin, CORS faqat `tauri://localhost` ga ruxsat etilsin.
- **Qabul Mezoni (Acceptance Criteria):** Tashqi brauzerdan tokensiz yuborilgan har qanday `POST` so'rovi `401 Unauthorized` qaytaradi.

### 2. `MISA-ROOT-002`: NSIS Installerda `_internal` katalogining yo'qligi sababli qulash
- **Tasnifi:** `CONFIRMED_DEFECT` | **Holati:** `CONFIRMED`
- **Fayl & Qator:** [`Misa/src-tauri/tauri.conf.json:37-40`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src-tauri/tauri.conf.json#L37)
- **Xavf & Sharoit:** O'rnatilgan paketda `_internal/` papkasi bo'lmagani sababli `python311.dll` topilmay dastur yangi kompyuterda ishga tushmaydi.
- **Tuzatish Chora-tadbiri:** `tauri.conf.json` dagi `bundle.resources` ga `"backend/**/*"` deb yozilsin.
- **Qabul Mezoni:** Python o'rnatilmagan toza Windows 11 virtual mashinasida NSIS o'rnatuvchisi orqali dastur xatosiz ishga tushadi.

### 3. `MISA-ROOT-003`: Native `ShellExecuteW` da URL protokoli tekshirilmasligi
- **Tasnifi:** `SECURITY_RISK` | **Holati:** `CONFIRMED`
- **Fayl & Qator:** [`Misa/src-tauri/src/lib.rs:681`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src-tauri/src/lib.rs#L681)
- **Standart:** CWE-20, MITRE ATT&CK T1204
- **Xavf & Sharoit:** `app_open_external_url` IPC buyrug'iga `.exe` yoki `.bat` yo'li berilsa, Windows uni to'g'ridan-to'g'ri ishga tushiradi (RCE).
- **Tuzatish Chora-tadbiri:** Rust funksiyasida faqat `http://` va `https://` protokollariga ruxsat beruvchi regex tekshiruvi kiritilsin.
- **Qabul Mezoni:** `app_open_external_url("calc.exe")` chaqirilganda `Err("Invalid URL protocol")` qaytadi va dastur ochilmaydi.

### 4. `MISA-ROOT-004`: `open_app` vositasida PowerShell argument inyeksiyasi
- **Tasnifi:** `SECURITY_RISK` | **Holati:** `CONFIRMED`
- **Fayl & Qator:** [`core/agent_tools.py:514`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/agent_tools.py#L514)
- **Standart:** CWE-78 (OS Command Injection)
- **Xavf & Sharoit:** `value` parametriga `calc'; Start-Process 'cmd.exe` uzatilganda f-string qo'shtirnog'i yopilib, ixtiyoriy buyruq bajariladi.
- **Tuzatish Chora-tadbiri:** f-string bilan buyruq tuzish o'rniga qat'iy parametrli massiv yoki whitelist mapping ishlatilsin.
- **Qabul Mezoni:** Inyeksion qiymat kiritilganda faqat xato xabari qaytadi, qo'shimcha jarayonlar ochilmaydi.

### 5. `MISA-ROOT-005`: API kalitlarning ochiq JSON faylda saqlanishi
- **Tasnifi:** `SECURITY_RISK` | **Holati:** `CONFIRMED`
- **Fayl & Qator:** [`core/v8/ai_key_manager.py:115`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/v8/ai_key_manager.py#L115)
- **Standart:** CWE-312, OWASP ASVS v4.0.3 V8.1
- **Xavf & Sharoit:** `data/ai_keys_cache.json` faylida shaxsiy kalitlar plaintext holatda yozilgan.
- **Tuzatish Chora-tadbiri:** Windows DPAPI (`win32crypt.CryptProtectData`) yoki tizim keyring orqali shifrlab saqlansin.
- **Qabul Mezoni:** Kesh faylini matn muharririda ochganda API kalitlar shifrlangan baytlar ko'rinishida bo'ladi.

### 6. `MISA-ROOT-006`: Destruktiv amallarda Human-In-The-Loop frontend tasdiqlovining yo'qligi
- **Tasnifi:** `SECURITY_RISK` | **Holati:** `CONFIRMED`
- **Fayl & Qator:** [`core/tools/security_policy.py:184`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/tools/security_policy.py#L184), [`Misa/src/pages/ChatPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx)
- **Standart:** OWASP Top 10 for LLMs 2025 LLM06:2025 (Excessive Agency)
- **Xavf & Sharoit:** Agent destruktiv buyruq (`file_delete`, `process_kill`) olganda, frontendda uni tasdiqlovchi dialog yo'qligi sababli jarayon uzilib qoladi yoki nazoratsiz o'tib ketadi.
- **Tuzatish Chora-tadbiri:** `ChatPage.tsx` ga `CONFIRMATION_REQUIRED` signali uchun chiroyli glass modal dialog qo'shilsin.
- **Qabul Mezoni:** Foydalanuvchi "Ruxsat berish" tugmasini bosmaguncha agent destruktiv amalni bajarmaydi.

---

## 3. TIER 2: HIGH (MUHIM FOYDALANISH VA XAVFSIZLIK TO'SIQLARI — 11 TA)

| Master ID | Canonical Sarlavha | Tasnifi | Holati | Asosiy Fayl | Tuzatish Ko'rsatmasi |
|---|---|---|---|---|---|
| **`MISA-ROOT-007`** | Rust `lib.rs` nomzodlarida `v9.3` yo'qligi | `CONFIRMED_DEFECT` | `CONFIRMED` | [`Misa/src-tauri/src/lib.rs:290`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src-tauri/src/lib.rs#L290) | Nomzodlar qatoriga `release/v9.3` yo'lini qo'shish. |
| **`MISA-ROOT-008`** | Global `outline: none` (fokus yo'qolishi) | `CONFIRMED_DEFECT` | `CONFIRMED` | [`Misa/src/App.css:91`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/App.css#L91) | `:focus-visible` uchun 2px binafsha halqa kiritish (WCAG SC 2.4.7 Level A). |
| **`MISA-ROOT-009`** | AuthPage inputlarida `<label>` va `id` yo'qligi | `CONFIRMED_DEFECT` | `CONFIRMED` | [`Misa/src/pages/AuthPage.tsx:1824`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/AuthPage.tsx#L1824) | Har bir inputga `id` va `<label htmlFor="...">` ulash (WCAG SC 1.3.1). |
| **`MISA-ROOT-010`** | Modallarda `role="dialog"` va focus trap yo'qligi | `CONFIRMED_DEFECT` | `CONFIRMED` | [`Misa/src/components/UpdateModal.tsx:150`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/UpdateModal.tsx#L150) | Konteynerga dialog roli berish va fokusni modal ichida ushlash (WCAG SC 2.1.2). |
| **`MISA-ROOT-011`** | High-DPI 150% da 800px oyna qirqilishi | `CONFIRMED_DEFECT` | `CONFIRMED` | [`Misa/src-tauri/src/lib.rs:1310`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src-tauri/src/lib.rs#L1310) | Oyna balandligini monitor ishchi maydoniga mos ravishda dinamik hisoblash. |
| **`MISA-ROOT-012`** | Generatsiyani to'xtatuvchi `[Stop]` tugmasi yo'qligi | `FEATURE_GAP` | `CONFIRMED` | [`Misa/src/pages/ChatPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx) | `AbortController` orqali so'rovni bekor qilish tugmasini joriy qilish. |
| **`MISA-ROOT-013`** | Agent topshiriq rejasining yashirinligi | `FEATURE_GAP` | `CONFIRMED` | [`core/agents/manager_agent.py`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/agents/manager_agent.py) | Chatda qadamlar akordeonini (Task Checklist) ko'rsatish. |
| **`MISA-ROOT-014`** | Ovozli muloqotda AEC va Ducking yo'qligi | `CONFIRMED_DEFECT` | `CONFIRMED` | [`core/audio_service.py:119`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/audio_service.py#L119) | TTS gapirayotganda mikrofon sezgirligini pasaytirish (Audio Ducking). |
| **`MISA-ROOT-015`** | "Salom Misa" neyron wake-word modelining yo'qligi | `FEATURE_GAP` | `CONFIRMED` | [`models/wake_word/`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/models/wake_word/) | OpenWakeWord yoki ONNX modelini joylashtirish. |
| **`MISA-ROOT-016`** | Indirect Prompt Injection (Oyna sarlavhalari) | `SECURITY_RISK` | `CONFIRMED` | [`core/gui/controller.py:123`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/gui/controller.py#L123) | Oyna sarlavhalarini `<untrusted_context>` teglari bilan chegaralash (LLM01). |
| **`MISA-ROOT-017`** | Kirish formasida so'rovlar poygasi (Double-Click) | `CONFIRMED_DEFECT` | `CONFIRMED` | [`Misa/src/pages/AuthPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/AuthPage.tsx) | So'rov ketayotganda tugmani `isSubmitting` flag orqali nofaol qilish. |

---

## 4. TIER 3: MEDIUM (FOYDALANISH QULAYLIGI VA DIZAYN — 11 TA)

| Master ID | Canonical Sarlavha | Tasnifi | Holati | Asosiy Fayl | Tuzatish Ko'rsatmasi |
|---|---|---|---|---|---|
| **`MISA-ROOT-018`** | `Button.tsx` dagi arvoh tokenlar (`--glass-bg`) | `CONFIRMED_DEFECT` | `CONFIRMED` | [`Misa/src/components/Button.tsx:47`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/Button.tsx#L47) | `tokens.css` ga `--glass-bg` va `--radius-pill` qiymatlarini kiritish. |
| **`MISA-ROOT-019`** | Yorug' mavzuda oq fonda oq yozuv qolishi | `CONFIRMED_DEFECT` | `CONFIRMED` | [`Misa/src/styles/tokens.css:101`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/styles/tokens.css#L101) | `theme-light` da qattiq `#FFFFFF` yozuvlarni `--text-primary` ga almashtirish. |
| **`MISA-ROOT-020`** | Sozlamalarning 5 ta sahifaga tarqalishi | `TECHNICAL_DEBT` | `CONFIRMED` | Navigatsiya va Router | Barcha sozlamalarni yagona `/settings` markaziga jamlash. |
| **`MISA-ROOT-021`** | Xotira va Rejalashtiruvchida bo'sh holatlar yo'qligi | `UX_RECOMMENDATION` | `CONFIRMED` | [`Misa/src/pages/MemoryPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/MemoryPage.tsx) | Bo'sh sahifada boy yo'l-yo'riq kartasi va CTA tugmasini chiqarish. |
| **`MISA-ROOT-022`** | Boshlang'ich Prompt chiplari yo'qligi | `UX_RECOMMENDATION` | `CONFIRMED` | [`Misa/src/pages/ChatPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx) | Yangi chatda 4 ta tayyor taklif chipini ko'rsatish. |
| **`MISA-ROOT-023`** | SQLite xotirasida ko'p foydalanuvchili izolyatsiya | `SECURITY_RISK` | `CONFIRMED` | [`core/agent_memory.py`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/agent_memory.py) | Barcha SQLite so'rovlariga `WHERE user_id = ?` shartini majburiy qilish. |
| **`MISA-ROOT-024`** | Command Palette da WAI-ARIA Combobox yo'qligi | `UX_RECOMMENDATION` | `CONFIRMED` | [`Misa/src/components/CommandPalette.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/CommandPalette.tsx) | Qidiruv maydoniga `role="combobox"` va natijalarga `role="option"` qo'shish. |
| **`MISA-ROOT-025`** | `IconButton.tsx` 34px bo'lib, 44px HIG ga mos emasligi | `UX_RECOMMENDATION` | `CONFIRMED` | [`Misa/src/components/IconButton.tsx:12`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/IconButton.tsx#L12) | Sensorli ekranlar uchun klik maydonini (hit target) 44px ga kengaytirish. |
| **`MISA-ROOT-026`** | Web Speech API audio trafigi ruxsatnomasi | `SECURITY_RISK` | `PARTIALLY_CONFIRMED` | [`Misa/src/pages/VoicePage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/VoicePage.tsx) | Ovozli sozlamalarda Google STT ga audio chiqishi haqida shaffof bildirishnoma berish. |
| **`MISA-ROOT-027`** | Xotirani interfeys orqali tahrirlash imkoni yo'qligi | `FEATURE_GAP` | `CONFIRMED` | [`Misa/src/pages/MemoryPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/MemoryPage.tsx) | Faktlarni o'chirish va tahrirlash uchun qalamcha tugmalarini qo'shish. |
| **`MISA-ROOT-028`** | AI Provayder nosozligida zaxira model holati | `FEATURE_GAP` | `CONFIRMED` | [`Misa/src/pages/ChatPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx) | Model alishganda foydalanuvchiga sariq indikator ko'rsatish. |

---

## 5. TIER 4: LOW (ESTETIKA VA KOSMETIK TOZALASH — 4 TA)

| Master ID | Canonical Sarlavha | Tasnifi | Holati | Asosiy Fayl | Tuzatish Ko'rsatmasi |
|---|---|---|---|---|---|
| **`MISA-ROOT-029`** | Xatolik yuz berganda qayta urinish (Retry) tugmasi | `UX_RECOMMENDATION` | `CONFIRMED` | [`Misa/src/pages/ChatPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx) | Xato xabari ostiga [Qayta urinish] tugmasini qo'yish. |
| **`MISA-ROOT-030`** | Monolit "Xudo-fayllar" (`api_server.py`, `backendService`) | `TECHNICAL_DEBT` | `CONFIRMED` | Backend va Frontend servislar | Kelajakda router va kichik servis modullariga bo'lish (Refactoring). |
| **`MISA-ROOT-031`** | Ochilishda majburiy 800ms intro video | `UX_RECOMMENDATION` | `CONFIRMED` | [`Misa/src/components/MisaIntroSplash.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/MisaIntroSplash.tsx) | Sozlamalarga "Kirish videosini o'chirish" tugmasini qo'shish. |
| **`MISA-ROOT-032`** | Brend nomlarida eski `Mikasa` qoldiqlari | `TECHNICAL_DEBT` | `CONFIRMED` | JSX va CSS klasslar | `mikasa-*` klasslarini `misa-*` ga almashtirish. |

---

## 6. XULOSA VA KEYINGI BOSQICHGA TAYYORLIK

Ushbu yakuniy registr:
- 138 ta xom da'vodan tozalangan va 32 ta qat'iy Master vazifaga keltirilgan;
- 31 ta to'liq tasdiqlangan (`CONFIRMED`) va 1 ta qisman tasdiqlangan (`PARTIALLY_CONFIRMED`) holatni qat'iy ko'rsatadi;
- Muhandislik jamoasi uchun navbatdagi tuzatish fazasiga to'liq yo'llanma beradi.
