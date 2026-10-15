# Misa AI (sobiq Mikasa AI) — Loyiha O'zgarishlar Tarixi (Changelog)

Barcha o'zgarishlar va relizlar Semantic Versioning (SemVer) qoidalariga muvofiq yuritiladi.

## [9.0.2] — 2026-10-15 (Autonomous Windows Agent, Authoritative Security & Platform Hardening)

- **Masofaviy Windows Agent Lifecycle & Poller/Executor Integratsiyasi**: `agent/executor.py` dagi `RemoteCommandExecutor` va `CommandPoller` bevosita `agent/lifecycle.py` ga xavfsiz ulandi. Idempotent polling, takroriy startlardan himoya, 32-bayt nonce orqali replay-attack nazorati va avtomatik resurs tozalash joriy etildi.
- **Vakolatli Asboblar Xavfsizlik Siyosati (Authoritative Security Policy) & Confirmation Tokenlari**: Barcha yuqori xavfli vositalar (`system_shutdown`, `delete_file`, `keyboard_type`, `mouse_click`, `clear_memory`) uchun markazlashtirilgan xavfsizlik filtri o'rnatildi. Kriptografik SHA-256 parametrlari bilan bog'langan bir martalik tasdiqlash tokenlari (TTL va bir martalik sarflash kafolati) joriy etildi.
- **Lokal API Himoyasi va Izolyatsiyasi (127.0.0.1 Anti-Hijack)**: `/api/plugins/execute` endpointi begona Origin/Referer yoki sessiya tokensiz kelgan chaqiruvlarni 403 `UNAUTHORIZED_LOCAL_CALLER` bilan qat'iy rad etadi.
- **Sessiyadan Xabardor Windows GUI Controller**: `core/gui/controller.py` orqali DPI-aware oyna boshqaruvi, nishon oynani aniqlash (`find_window`), Win32 `AttachThreadInput` orqali ishonchli faollashtirish, qat'iy precondition/postcondition tekshiruvlari va har qanday favqulodda vaziyatda darhol to'xtatuvchi `abort` mexanizmi yaratildi.
- **Agent Loop Verifikatsiyasi & Maxfiy Lokal Vision**: Agent rejasini bajarish jarayonida bir xil vosita qayta-qayta takrorlanishini (infinite loop) avtomatik aniqlash va xavfsiz to'xtatish yo'lga qo'yildi. GUI qadamlari (click, type, screenshot) integratsiya qilindi; foydalanuvchi ekrani tasvirlari hech qanday tashqi AI bulutlariga yuborilmaydi (to'liq lokal qayta ishlanadi).
- **Desktop Handshake, Brauzer Adapteri & Screenshot/Audit Hardening**: Rust supervisor va Python backend o'rtasidagi handshake qat'iylashtirildi (`version: 9.0.2`, `app: Misa AI`). Versiya mos kelmasa eskirgan jarayon avtomatik tozalanadi. Brauzer oynalarini boshqaruvchi `BrowserAutomationAdapter`, xato yuz berganda soxta `captured: true` bermaydigan skrinshot tizimi hamda telemetriyada parollar va maxfiy kalitlarni avtomatik `[REDACTED]` qiluvchi audit mexanizmi ishga tushirildi.
- **To'liq Regression va Sifat Kafolati**: Barcha 345 ta Python testlari, 33 ta Frontend testlari, TypeScript/Vite production buildi, `cargo check --lib` va Windows Notepad sandbox smoke-testi muvaffaqiyatli yakunlandi.

---

## [9.0.1] — 2026-10-15 (Autonomous Windows Agent, Authoritative Security & Platform Hardening)

- **Masofaviy Windows Agent Lifecycle & Poller/Executor Integratsiyasi**: `agent/executor.py` dagi `RemoteCommandExecutor` va `CommandPoller` bevosita `agent/lifecycle.py` ga xavfsiz ulandi. Idempotent polling, takroriy startlardan himoya, 32-bayt nonce orqali replay-attack nazorati va avtomatik resurs tozalash joriy etildi.
- **Vakolatli Asboblar Xavfsizlik Siyosati (Authoritative Security Policy) & Confirmation Tokenlari**: Barcha yuqori xavfli vositalar (`system_shutdown`, `delete_file`, `keyboard_type`, `mouse_click`, `clear_memory`) uchun markazlashtirilgan xavfsizlik filtri o'rnatildi. Kriptografik SHA-256 parametrlari bilan bog'langan bir martalik tasdiqlash tokenlari (TTL va bir martalik sarflash kafolati) joriy etildi.
- **Lokal API Izolyatsiyasi (127.0.0.1 Anti-Hijack)**: `/api/plugins/execute` endpointi begona Origin/Referer yoki sessiya tokensiz kelgan chaqiruvlarni 403 `UNAUTHORIZED_LOCAL_CALLER` bilan qat'iy rad etadi.
- **Sessiyadan Xabardor Windows GUI Controller**: `core/gui/controller.py` orqali DPI-aware oyna boshqaruvi, nishon oynani aniqlash (`find_window`), Win32 `AttachThreadInput` orqali ishonchli faollashtirish, qat'iy precondition/postcondition tekshiruvlari va har qanday favqulodda vaziyatda darhol to'xtatuvchi `abort` mexanizmi yaratildi.
- **Agent Loop Takomillashuvi & Maxfiy Lokal Vision**: Agent rejasini bajarish jarayonida bir xil vosita qayta-qayta takrorlanishini (infinite loop) avtomatik aniqlash va xavfsiz to'xtatish yo'lga qo'yildi. GUI qadamlari (click, type, screenshot) integratsiya qilindi; foydalanuvchi ekrani tasvirlari hech qanday tashqi AI bulutlariga yuborilmaydi (to'liq lokal qayta ishlanadi).
- **Desktop Supervisor Handshake & Platform Hardening**: Rust supervisor va Python backend o'rtasidagi handshake qat'iylashtirildi (`version: 9.0.1`, `app: Misa AI`). Versiya mos kelmasa eskirgan jarayon avtomatik tozalanadi. Brauzer oynalarini boshqaruvchi `BrowserAutomationAdapter`, xato yuz berganda soxta `captured: true` bermaydigan skrinshot tizimi hamda telemetriyada parollar va maxfiy kalitlarni avtomatik `[REDACTED]` qiluvchi audit mexanizmi ishga tushirildi.
- **Ovozli Muloqot va Ijro Sinxronizatsiyasi (Voice & TTS Fix)**: Ovoz tugmasi bosilganda 1 soniyadan so'ng o'chib qolish muammosi tuzatildi (`continuous = true`, sukut taymeri va suhbat to'liq yakunlanishini kutish). Edge-TTS audio oqimi va brauzer sintezi Misa yuzi/orb holati bilan to'liq sinxronlashtirildi.
- **Ilova Ochilganda Tizim Holati Xabarnomasi (Startup Briefing)**: Misa ochilganda avtomatik ravishda server ulanishi, Gemini AI kaliti holati va barcha tizim modullari diagnostikasini o'tkazadi hamda ovozli va vizual tarzda foydalanuvchiga to'liq hisobot beradi.
- **Frontend Code Splitting**: `Misa/src/App.tsx` barcha 12 ta sahifasi `React.lazy()` va `<Suspense>` ga o'tkazilib, boshlang'ich yuklanish hajmi 70 KB gacha qisqartirildi.
- **To'liq Test va Sifat Kafolati**: 284 ta Python unit/integration testlari, 33 ta Frontend testlari, TypeScript/Vite production buildi va Real Windows Notepad sandbox smoke-testi 100% muvaffaqiyatli yakunlandi.

---

## [9.0.0] — 2026-09-29 (Misa AI Rebranding & Level 9 Foundation)

- **Rasmiy Rebranding (`Mikasa AI` ➔ `Misa AI`)**: 9.0.0 versiyadan boshlab loyiha, desktop interfeysi (`Misa/`), ovozli yordamchi chaqiruvi ("Salom Misa"), tizim yadrosi va hujjatlar **Misa (`Misa AI`)** nomi bilan yuritiladi. Oldingi versiyalar (v8.0.0 va undan avvalgilar) tarixiy **Mikasa AI** nomi ostida o'zgarishsiz saqlab qolindi.

---

## [8.0.0] — 2026-09-21 (Level 8 Autonomous Desktop & Release System)

Mikasa AI 8.0.0 — loyihaning to'liq 48 bosqichli evolyutsiyasi natijasi bo'lib, ilovani yagona mustaqil dasturdan **ko'p qurilmali, masofadan xavfsiz boshqariladigan, Supabase Auth bilan himoyalangan va avtonom kriptografik auto-update tizimiga ega sun'iy intellekt platformasiga** aylantirdi.

### 🌟 Yangi Imkoniyatlar va Arxitektura (Phases 35–48):
- **Phase 35–37 — Masofaviy Boshqaruv Protokoli va Sessiyalar**: Asinxron buyruq konvertlari (`RemoteCommandEnvelope`), 32-bayt nonce orqali replay-hujumlardan himoya, sessiya muddatlari (TTL) va xavfsiz token boshqaruvi.
- **Phase 38 — Masofaviy Ruxsatlar Markazi (Permission Engine)**: Xavfli va nozik buyruqlar (fayllarni o'chirish, tizimni o'chirish) uchun foydalanuvchi roziligini so'rash (approval flows) va xavfsizlik chegaralari.
- **Phase 39 — Universal Telegram Gateway**: Telegram bot orqali kompyuter bilan to'g'ridan-to'g'ri bog'lanish, masofadan status olish, skrinshot so'rash va Wake-on-LAN (WoL) orqali kompyuterni uyg'otish.
- **Phase 40 & 41 — Supabase Auth & Multi-Tenant Xavfsizlik**: `auth.users.id` yagona identifikator, email/parol, email tasdiqlash, parol tiklash va ma'lumotlar bazasi darajasida qat'iy Row Level Security (RLS) izolyatsiyasi.
- **Phase 42–44 — Kriptografik PC Agent Enrollment**: 6-xonali qisqa muddatli pairing kodlari (5 min TTL), bruteforce cheklovi (maksimal 5 urinish), Ed25519 ochiq/yopiq kalitlar juftligi va Windows DPAPI xavfsiz shifrlash.
- **Phase 45–47 — Windows Agent & Real Tizim Asboblari**: Mustaqil Windows Agent jarayoni, `PathSecurityValidator` orqali sandboxlangan fayl tizimi boshqaruvi, ekran tahlili, klaviatura/sichqoncha simulyatsiyasi va audio monitoring.
- **Phase 48 — Secure Auto-Update & Crash-Safe Rollback Engine**: SemVer 2.0.0 versiya boshqaruvi, Ed25519 raqamli imzolari (`DEFAULT_TRUSTED_PUBLIC_KEY`) va SHA-256 xeshlari bilan har bir yangilanishni verifikatsiya qilish (fail-closed), atomik staging, avtomatik zaxira va nosozlikda tezkor rollback.
- **Production Desktop Release**: `release/v8.0.0/` katalogida rasmiy reliz paketlari (`Mikasa-AI-v8.0.0.exe`, `Mikasa-AI-Setup-v8.0.0.exe`, `Mikasa-AI-v8.0.0.msi`, `run_portable.bat`, `version_manifest.json`).

---

## [7.1.0] — 2026-09-13 (Production Native Desktop Release)

Mikasa AI 7.1.0 — loyihaning to'liq 27 bosqichli Master Rejasi asosida tubdan yangilangan, Windows 10/11 uchun moslashgan ishlab chiqarish (production) darajasidagi sun'iy intellektli shaxsiy yordamchisi.

### 🌟 Yangi Imkoniyatlar va Arxitektura:
- **Phase 0 — To'liq Loyiha Auditi**: Barcha mavjud kodlar, yo'llar va bog'liqliklar tahlil qilinib, portativ arxitektura poydevori yaratildi.
- **Phase 1 & 2 — Native Tauri 2.0 Desktop Shell**: Rust asosidagi xavfsiz va tezkor desktop qobiq, maxsus oynani boshqarish (minimize, toggle maximize, clean close) va frameless silliq oyna dizayni.
- **Phase 3 & 4 — Python Backend Lifecycle & Portability**: Zero hardcoded paths tamoyili, aiohttp asinxron REST & WebSocket serveri (`127.0.0.1:18420`), fondagi o'rnatilgan Python boshqaruvi va avtomatik resurs tozalash.
- **Phase 5 & 6 — Quiet Intelligence Dizayn Tizimi**: Matnli emojilardan butunlay voz kechildi; to'liq vektorli SVG piktogrammalar, `#0E1422` solid quyuq yuzalar, nozik shisha (glassmorphism) va `#10B981` zumrad yorug'lik effektlari.
- **Phase 7 — Responsive Desktop AppShell**: 1024x700 minimal o'lchamdan boshlab 4K gacha avtomatik moslashuvchi qatlam, tor ekranlarda 68px ixcham yon panel.
- **Phase 8 — Home / Landing**: Real apparat telemetriyasi (soxta ma'lumotlarsiz real CPU/RAM/Disk), tezkor AI harakatlari kartochkalari.
- **Phase 9 — AI Chat**: Fikrlovchi Gemini va universal modellar, ko'p qatorli avtomatik kattalashuvchi yozish maydoni, suhbat tozalash va to'liq kontekstli javoblar.
- **Phase 10 — Ovozli Muloqot & Mikasa Orb**: 7 xil jonli holatga ega (idle, listening, thinking, speaking, loading, offline, error) audio sfera, Edge-TTS Sardor va Madina ovozlari.
- **Phase 11 — Buyruqlar Markazi**: 29 ta haqiqiy ToolRegistry vositasi, tezkor qisqartmalar, parametrlarni interaktiv sozlash modali va natijalarni nusxalash.
- **Phase 12 — Xotira Maydoni**: Shaxsiy bilimlar bazasi (CRUD), suhbatlar konteksti va profil sozlamalari.
- **Phase 13 — Rejalashtiruvchi**: 5 ta holatli (active, repeating, completed, failed, cancelled) eslatmalar va vazifalar tizimi, fon oqimida 1ms da to'xtovchi signal mexanizmi.
- **Phase 14 — Plaginlar Markazi**: O'rnatilgan, mavjud, o'chirilgan va yangilanish holatidagi plaginlar katalogi, JSON shablonlar asosida yangi plagin qo'shish.
- **Phase 15 — Hisob va Sozlamalar**: 7 ta bo'lim (Profil, Ovoz, AI modeli, Ko'rinish, Bildirishnomalar, Maxfiylik, Dastur haqida), dinamik avatar va mavzular.
- **Phase 16 — Global Buyruqlar Palitrasi (`Ctrl+K`)**: WAI-ARIA 1.2 standartiga mos to'liq klaviatura orqali boshqariluvchi global qidiruv va navigatsiya.
- **Phase 17 — Responsive Desktop**: Grid kartochkalarining avtomatik to'lishi (`repeat(auto-fit, minmax(...))`) va tor ekranlarda tugmalar siqilishining oldini olish.
- **Phase 18 — Foydalanish Qulayligi (a11y)**: Yuqori kontrastli fokus halqalari (`:focus-visible`), harakatni kamaytirish (`prefers-reduced-motion`) va ekran o'quvchilari uchun maxsus belgilar.
- **Phase 19 — Ishlash Tezligi (Performance)**: `mountedRef` orqali eskirgan holatlarni tozalash, fonda xotira oqishini (memory leak) bartaraf etish.
- **Phase 20 — Xavfsizlik (Security)**: Qat'iy CORS oq ro'yxati (Tauri va localhost), begona veb-saytlar va tashqi tarmoq IP-laridan kelgan so'rovlarni bloklash (403), plagin nomlarida path traversal himoyasi va Tauri CSP direktivalari.
- **Phase 21 — Xatoliklarni Boshqarish (Error Handling)**: Global React `ErrorBoundary`, "Nima bo'ldi — Nega bo'ldi — Nima qilish kerak" 3 qismli intuitiv xatolik ko'rinishi va barcha sahifalarda qayta urinish mexanizmi.
- **Phase 22 — Ishlab Chiqarish Loglari (Logging)**: `logs/mikasa.log`, `logs/backend.log`, `logs/crash.log` fayllari, aylanuvchi (rotating) hajmlar va API kalitlari/parollarni avtomatik maskalash.
- **Phase 23 — Sinovlar (Testing)**: Frontend `node --test` birlik testlari va to'liq E2E hayotiy tsikl (Launch -> Chat -> Voice -> Commands -> Memory -> Scheduler -> Plugins -> Account) integratsiya testlari.
- **Phase 24 — Yuklama Sinovlari (Stress Testing)**: 100, 500 va 1000 ta buyruqlar yuklamasi (1,730 req/s, o'rtacha 1.15ms kechikish), 10,000 marshrut almashinuvi va barqaror RAM.
- **Phase 25 — Windows QA**: Windows 10 va 11 qo'llab-quvvatlovi, 100%-200% High-DPI masshtabi, jarayonlarni toza o'chirish.
- **Phase 26 — Production Build**: `Mikasa-AI-v7.1.0.exe`, MSI va NSIS o'rnatuvchilari, sha256 tekshiruv fayllari.
- **Phase 27 — Reliz Muhandisligi**: Portativ ishga tushiruvchi (`run_portable.bat`), to'liq hujjatlar va reliz qaydlari.

---

## [6.0.0] — Avvalgi Avlod
- CustomTkinter asosidagi ish stoli ko'rinishi (`gui/` katalogida to'liq zaxira sifatida saqlab qolingan).
