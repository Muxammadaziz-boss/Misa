# 02 — MASTER FINDINGS EVIDENCE & VERIFICATION MATRIX
## MISA V9 — 32 Ta Master Muammoning Kod Dalillari, Himoya Mexanizmlari va Ijro Yo'llari

- **Audit Turi:** Deep Evidence Verification & Execution Path Traceability (Phase 4.1)
- **Sana:** 2026-10-24
- **Auditor Roli:** Principal Code Auditor & Security Verification Specialist
- **Qamrov:** Barcha 32 ta Master Root Cause (`MISA-ROOT-001` dan `MISA-ROOT-032` gacha).
- **Qat'iy Qoida:** 100% READ-ONLY. Hech qanday kod o'zgartirilmadi.

---

## 1. TEKSHIRUV STANDARTI VA METODIKASI

Har bir master topilma quyidagi qat'iy mezonlar bo'yicha tahlil qilindi:
1. **Dalil Turi:** 
   - `STATIC_CONFIRMED`: Manba kodida statik tahlil orqali 100% isbotlangan.
   - `DYNAMIC_REPRODUCED`: Amaliy jarayon yoki skript orqali chaqirilib qayta tiklangan.
   - `STATIC_NUANCED`: Kodda mavjud, ammo shartli yoki qisman konfiguratsiyalangan.
2. **Mavjud Himoya Mexanizmlari:** Dasturda ushbu xatoni yumshatuvchi qandaydir filtr, tekshiruv yoki shart bormi?
3. **Ijro Yo'li (Execution Trace):** Xato qaysi funksiyadan qaysi tizim buyrug'iga qarab oqib boradi?

---

## 2. 32 TA MASTER MUAMMONING CHUQUR DALILLAR MATRITSASI

### `MISA-ROOT-001`: Port 18420 dagi mahalliy API autentifikatsiyasi yo'qligi va CORS `*`
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`core/api_server.py:7328-7330`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/api_server.py#L7328), [`7351`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/api_server.py#L7351)
- **Ijro Yo'li:** Brauzer Web Page ➔ `fetch("http://127.0.0.1:18420/api/system/command")` ➔ `cors_middleware` (`Access-Control-Allow-Origin: *`, `Allow-Private-Network: true`) ➔ `auth_enforcement_middleware` (`if not _is_production_mode(): return await handler(request)`) ➔ Buyruq bajariladi.
- **Yuzaga Kelish Shartlari:** Misa fonda ishlab turganda, foydalanuvchi oddiy veb-brauzerda (Chrome/Edge) ixtiyoriy zararli saytni ochishi kifoya.
- **Mavjud Himoyalar:** Faqat `_is_production_mode()` tekshiruvi bor, biroq u desktop rejimida doimo `False` qaytaradi. Boshqa himoya yo'q.
- **Ta'sir & Jiddiylik:** **Critical**. Brauzerdan turib kompyuterni masofadan boshqarish (RCE) xavfi.

---

### `MISA-ROOT-002`: NSIS Installerda `_internal` katalogining yo'qligi sababli qulash
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src-tauri/tauri.conf.json:37-40`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src-tauri/tauri.conf.json#L37), [`packaging/build_backend.py:41, 181`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/packaging/build_backend.py#L41)
- **Ijro Yo'li:** PyInstaller `--onedir` ➔ `dist/backend_build/misa_backend/` (`misa_backend.exe` + `_internal/`) ➔ `tauri.conf.json` faqat `"backend/misa_backend.exe"` ni oladi ➔ NSIS o'rnatuvchisi `_internal/` siz paketlaydi ➔ Foydalanuvchi ilovani o'rnatgach ishga tushiradi ➔ `python311.dll not found` xatosi bilan qulaydi.
- **Yuzaga Kelish Shartlari:** Toza kompyuterga (Python o'rnatilmagan Windows tizimiga) dastur o'rnatilganda.
- **Mavjud Himoyalar:** Dasturchi kompyuterida ishlaydi, chunki u yerda lokal `src-tauri/backend/_internal` mavjud. O'rnatilgan paketda esa yo'q.
- **Ta'sir & Jiddiylik:** **Critical**. Yangi foydalanuvchilarda dastur umuman ochilmaydi.

---

### `MISA-ROOT-003`: Native `ShellExecuteW` da URL protokoli tekshirilmasligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src-tauri/src/lib.rs:662-686`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src-tauri/src/lib.rs#L662)
- **Ijro Yo'li:** Webview IPC ➔ `invoke("app_open_external_url", { url })` ➔ `app_open_external_url(url: String)` ➔ `ShellExecuteW(0, "open", url, null, null, 1)`.
- **Yuzaga Kelish Shartlari:** Agar chatda, bildirishnomada yoki linkda `calc.exe`, `cmd.exe /c ...` yoki `.bat` havolasi berilsa.
- **Mavjud Himoyalar:** [`Misa/index.html:76`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/index.html#L76) da frontend `isHttp` tekshiruvi bor, biroq to'g'ridan-to'g'ri Tauri IPC orqali chaqirilganda Rust qatlamida hech qanday protokol tekshiruvi yo'q.
- **Ta'sir & Jiddiylik:** **Critical**. Native darajadagi RCE (Ixtiyoriy dastur ishga tushirish).

---

### `MISA-ROOT-004`: `open_app` vositasida PowerShell argument inyeksiyasi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`core/agent_tools.py:509-516`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/agent_tools.py#L509)
- **Ijro Yo'li:** `system_control(action="open_app", value=user_input)` ➔ `app_cmd = APP_ALIASES.get(value, value)` ➔ `subprocess.Popen(["powershell", "-NoProfile", "-Command", f"Start-Process '{app_cmd}'"])`.
- **Yuzaga Kelish Shartlari:** AI agentga `calc'; Start-Process 'cmd.exe` kabi kiritma uzatilganda (masalan, prompt inyeksiya orqali).
- **Mavjud Himoyalar:** `APP_ALIASES` lug'ati bor, biroq `value` lug'atda topilmasa, to'g'ridan-to'g'ri f-string ichiga o'tib ketadi.
- **Ta'sir & Jiddiylik:** **Critical**. Tizim buyruqlari inyeksiyasi (CWE-78).

---

### `MISA-ROOT-005`: API kalitlarning ochiq JSON faylda saqlanishi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`core/v8/ai_key_manager.py:102-118`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/v8/ai_key_manager.py#L102)
- **Ijro Yo'li:** `register_system_key()` ➔ `_save_cache()` ➔ `with open(CACHE_FILE, "w") as f: json.dump(data, f)`.
- **Yuzaga Kelish Shartlari:** Foydalanuvchi dasturga Gemini, OpenAI yoki OpenRouter kalitini kiritishi bilan.
- **Mavjud Himoyalar:** Hech qanday shifrlash yo'q; oddiy matnli JSON fayli.
- **Ta'sir & Jiddiylik:** **Critical**. Tizimdagi boshqa ilovalar tomonidan maxfiy kalitlarning o'g'irlanishi (CWE-312).

---

### `MISA-ROOT-006`: Destruktiv amallarda Human-In-The-Loop frontend tasdiqlovining yo'qligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`core/tools/security_policy.py:184-239`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/tools/security_policy.py#L184), [`Misa/src/pages/ChatPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx)
- **Ijro Yo'li:** Agent destruktiv toolni chaqiradi (`process_kill`, `file_delete`) ➔ Backend `is_confirmation_required` `True` qaytaradi ➔ Frontend `ChatPage.tsx` bu signalni qabul qiluvchi modilga ega emas ➔ Jarayon yo qotib qoladi yoki aylanib o'tiladi.
- **Yuzaga Kelish Shartlari:** Foydalanuvchi yoki prompt inyeksiya agentga faylni o'chirishni buyurganda.
- **Mavjud Himoyalar:** Backend darajasida `security_policy.py` mavjud, ammo frontend UI da tasdiqlash uzilgan.
- **Ta'sir & Jiddiylik:** **Critical**. Agent tomonidan tizim fayllarini ruxsatsiz yo'q qilish xavfi (OWASP LLM06).

---

### `MISA-ROOT-007`: Rust `lib.rs` nomzodlar ro'yxatida `release/v9.3` yo'li yo'qligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src-tauri/src/lib.rs:290, 314`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src-tauri/src/lib.rs#L290)
- **Ijro Yo'li:** Tauri ishga tushadi ➔ `find_backend_candidates` ro'yxat tuzadi: `release/v9.2`, `release/v9.0.2`, `release/v9.0.1`, `release/v9.0.0` ➔ `release/v9.3` katalogi unutilgan ➔ Eski v9.2 backend ishga tushiriladi.
- **Yuzaga Kelish Shartlari:** Dastur release papkasidan ishga tushirilganda.
- **Ta'sir & Jiddiylik:** **High**. Versiyalar mos kelmasligi va eski backend kodining ishga tushishi.

---

### `MISA-ROOT-008`: Global `outline: none` tufayli klaviatura fokus halqasining butunlay yo'qolishi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src/App.css:89-92`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/App.css#L89)
- **Ijro Yo'li:** `input, button { outline: none; }` ➔ Hech qanday `:focus-visible` muqobili belgilanmagan ➔ Tab bosilganda fokus ko'rinmaydi.
- **Ta'sir & Jiddiylik:** **High**. WCAG 2.2 SC 2.4.7 (Level A) buzilishi, klaviatura foydalanuvchilarining to'liq cheklanishi.

---

### `MISA-ROOT-009`: AuthPage inputlarida dasturiy bog'langan `<label htmlFor>` va `id` yo'qligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src/pages/AuthPage.tsx:1824-1840`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/AuthPage.tsx#L1824)
- **Ta'sir & Jiddiylik:** **High**. WCAG 2.2 SC 1.3.1 (Level A) buzilishi, screen readerlar orqali kirish imkonsizligi.

---

### `MISA-ROOT-010`: Modal oynalarda `role="dialog"` va Focus Trap mexanizmining yo'qligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src/components/UpdateModal.tsx:150`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/UpdateModal.tsx#L150)
- **Ta'sir & Jiddiylik:** **High**. WCAG 2.2 SC 2.4.3 (Level AA) buzilishi, modal orqasidagi fon elementlari bilan chalkashlik.

---

### `MISA-ROOT-011`: High-DPI 150% ekranlarda 800px oyna balandligi sababli pastki panel qirqilishi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src-tauri/src/lib.rs:1308-1311`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src-tauri/src/lib.rs#L1308)
- **Ijro Yo'li:** 1920x1080 150% scaling ➔ Foydali ishchi balandlik: 672px ➔ Oyna qat'iy 800px bo'lib ochiladi ➔ Frameless bo'lgani sababli pastki 128px taskbar ostiga tushib ketadi.
- **Ta'sir & Jiddiylik:** **High**. Chat kiritish maydoni ko'rinmay qoladi.

---

### `MISA-ROOT-012`: Agent generatsiyasini darhol to'xtatuvchi `[Stop]` (AbortController) tugmasi yo'qligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src/pages/ChatPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx)
- **Ta'sir & Jiddiylik:** **High**. Foydalanuvchi nazorati va erkinligi (NN/g #3) buzilishi.

---

### `MISA-ROOT-013`: Agent topshiriq rejasining foydalanuvchidan yashirinligi ("Qora quti" ijrosi)
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`core/agents/manager_agent.py`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/agents/manager_agent.py)
- **Ta'sir & Jiddiylik:** **High**. Tizim holatining ko'rinmasligi (NN/g #1), foydalanuvchi ishonchsizligi.

---

### `MISA-ROOT-014`: Ovozli muloqotda AEC va Ducking yo'qligi tufayli Misa o'z karnayidagi ovozidan o'zini to'xtatishi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`core/audio_service.py:119`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/audio_service.py#L119)
- **Ijro Yo'li:** TTS karnay orqali gapiradi ➔ Dinamik ovozi mikrofon orqali olinadi ➔ `rms > self.vad_threshold` (0.015) sharti bajariladi ➔ Tizim "Foydalanuvchi gapirmoqda" deb o'ylab, TTS ni o'zi to'xtatadi.
- **Ta'sir & Jiddiylik:** **High**. Ovozli rejimda uzluksiz gaplashish imkonsizligi.

---

### `MISA-ROOT-015`: "Salom Misa" neyron wake-word (.onnx) modelining yo'qligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`models/wake_word/README.md`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/models/wake_word/README.md)
- **Dalil:** Papkada faqat `README.md` mavjud, haqiqiy `.onnx` yoki `.tflite` model fayli yo'q.
- **Ta'sir & Jiddiylik:** **High**. Ovoz orqali avtonom chaqiruvning ishlamasligi.

---

### `MISA-ROOT-016`: Indirect Prompt Injection: Oyna sarlavhalari va klipbord matnining filtrsiz kiritilishi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`core/gui/controller.py:123`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/gui/controller.py#L123)
- **Ta'sir & Jiddiylik:** **High**. Ochiq veb-sahifa sarlavhasidagi zararli ko'rsatmalarning AI kontekstiga sizib kirishi (OWASP LLM01:2025).

---

### `MISA-ROOT-017`: Kirish formasida so'rovlar poygasi va takroriy bosish himoyasi (isSubmitting) yo'qligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src/pages/AuthPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/AuthPage.tsx)
- **Ta'sir & Jiddiylik:** **High**. Takroriy tarmoq so'rovlari va Supabase rate-limitga tushish.

---

### `MISA-ROOT-018`: `Button.tsx` va `IconButton.tsx` da `--glass-bg` kabi mavjud bo'lmagan tokenlar ishlatilishi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src/components/Button.tsx:47`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/Button.tsx#L47), [`Misa/src/styles/tokens.css`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/styles/tokens.css)
- **Ta'sir & Jiddiylik:** **Medium**. Shisha tugmalar fonining shaffof bo'lib qolishi.

---

### `MISA-ROOT-019`: Yorug' mavzuda (`theme-light`) qattiq `#FFFFFF` yozuvlar qolib, kontrast yo'qolishi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src/styles/tokens.css:101-114`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/styles/tokens.css#L101)
- **Ta'sir & Jiddiylik:** **Medium**. Oq fonda oq matn o'qilmasligi.

---

### `MISA-ROOT-020`: Sozlamalar va boshqaruvning 5 ta alohida sahifaga tarqalib ketganligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** Router va Navigation (`AccountPage`, `VoicePage`, `CommandsPage`, `RemoteControlPage`)
- **Ta'sir & Jiddiylik:** **Medium**. Axborot arxitekturasi zaifligi.

---

### `MISA-ROOT-021`: Xotira va Rejalashtiruvchi sahifalarida boy bo'sh holatlar (Empty States) yo'qligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src/pages/MemoryPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/MemoryPage.tsx), [`SchedulerPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/SchedulerPage.tsx)
- **Ta'sir & Jiddiylik:** **Medium**. Bo'sh qora ekran foydalanuvchini adashtiradi.

---

### `MISA-ROOT-022`: Yangi suhbat ochilganda tayyor namunaviy Prompt chiplarining yo'qligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src/pages/ChatPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx)
- **Ta'sir & Jiddiylik:** **Medium**. Blank Page Syndrome (NN/g #6).

---

### `MISA-ROOT-023`: Lokal SQLite va xotirada ko'p foydalanuvchilar o'rtasida ma'lumotlar ajratilmaganligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`core/agent_memory.py`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/agent_memory.py)
- **Ta'sir & Jiddiylik:** **Medium**. Boshqa hisob bilan kirgan odam avvalgi suhbatlarni ko'rishi.

---

### `MISA-ROOT-024`: Global Command Palette (Ctrl+K) da WAI-ARIA Combobox semantikasi yo'qligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src/components/CommandPalette.tsx:332-440`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/CommandPalette.tsx#L332)
- **Ta'sir & Jiddiylik:** **Medium**. Screen readerda natijalar e'lon qilinmasligi.

---

### `MISA-ROOT-025`: `IconButton.tsx` komponentida minimal interaktiv nishon hajmining 34px bo'lishi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src/components/IconButton.tsx:12`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/IconButton.tsx#L12)
- **Ta'sir & Jiddiylik:** **Medium**. Sensorli ekranlarda 44px HIG tavsiyasiga mos emasligi.

---

### `MISA-ROOT-026`: Web Speech API orqali ovoz uzatilishida sozlamalarda shaffof opt-in ruxsat yo'qligi
- **Holati:** `PARTIALLY_CONFIRMED`
- **Dalil Turi:** `STATIC_NUANCED`
- **Fayl & Qator:** [`Misa/src/pages/VoicePage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/VoicePage.tsx)
- **Nuans:** Ovoz uzatish faqat foydalanuvchi mikrofonga bosganda amalga oshiriladi (fonda doimiy uzatilmaydi), biroq Google serveriga chiqish haqida sozlamalarda ogohlantirish yo'q.
- **Ta'sir & Jiddiylik:** **Medium**. Maxfiylik shaffofligi yetishmasligi.

---

### `MISA-ROOT-027`: Foydalanuvchi uzoq muddatli xotirani interfeys orqali to'g'ridan-to'g'ri tahrirlay olmasligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src/pages/MemoryPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/MemoryPage.tsx)
- **Ta'sir & Jiddiylik:** **Medium**. Xotira ustidan to'liq nazorat yo'qligi.

---

### `MISA-ROOT-028`: AI Provayder nosozliklarida zaxira modelga o'tish holati foydalanuvchiga ko'rinmasligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src/pages/ChatPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx)
- **Ta'sir & Jiddiylik:** **Medium**. Provayder o'zgarganda shaffoflik yo'qligi.

---

### `MISA-ROOT-029`: Xatolik yuz berganda avtomatik qayta urinish (Retry) tugmasi yo'qligi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src/pages/ChatPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx)
- **Ta'sir & Jiddiylik:** **Low**. Qayta yozishga majbur bo'lish (Usability).

---

### `MISA-ROOT-030`: Monolit "Xudo-fayllar" (`api_server.py` 7920 qator, `backendService.ts` 4900 qator)
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`core/api_server.py`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/api_server.py), [`Misa/src/services/backendService.ts`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/services/backendService.ts)
- **Ta'sir & Jiddiylik:** **Low** (Texnik qarz). Qo'llab-quvvatlash qiyinligi.

---

### `MISA-ROOT-031`: Ochilishda majburiy 800ms intro video va audio ijro etilishi
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** [`Misa/src/components/MisaIntroSplash.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/MisaIntroSplash.tsx)
- **Ta'sir & Jiddiylik:** **Low** (UX Tavsiya). Foydalanuvchini chalg'itish.

---

### `MISA-ROOT-032`: Brend nomlarida eski `Mikasa` qoldiqlari (`mikasa-logo`, `mikasa-button`)
- **Holati:** `CONFIRMED`
- **Dalil Turi:** `STATIC_CONFIRMED`
- **Fayl & Qator:** JSX va CSS klasslar
- **Ta'sir & Jiddiylik:** **Low** (Kosmetik tozalash).
