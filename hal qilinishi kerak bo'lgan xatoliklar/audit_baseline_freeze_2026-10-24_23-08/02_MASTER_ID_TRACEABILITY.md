# 02 — MASTER ID KUZATILUVCHANLIGI VA ASOSIY MUAMMOLAR REYESTRI (PHASE 4.3)
**Hujjat turi:** Master Root Cause Traceability va Rekonsilyatsiya Hisoboti  
**Sana:** 2026-10-24  
**Auditor:** Independent Technical Audit Supervisor  
**Holat:** Final Verified & Reconciled Baseline  

---

## 1. KIRISH VA PHASE 4.2 DA YO'L QO'YILGAN UZILISHLAR TAHLILI

Phase 4.2 da yaratilgan `03_RAW_FINDINGS_TRACEABILITY.csv` faylida quyidagi jiddiy tizimli uzilishlar mavjud edi:
1. **3 ta MasterID ning tushib qolishi:** `MISA-ROOT-012`, `MISA-ROOT-028` va `MISA-ROOT-032` 32 ta master topilma jadvalida mavjud bo'lsa-da, CSV dagi 138 ta xom qatorning birortasiga ham biriktirilmagan edi.
2. **Sababning tahlili:**  
   - Phase 4.2 hisobotida manba fayllar haqiqiy audit fayllaridan emas, balki umumiy taxminiy nomlar orqali generatsiya qilingan (masalan, `06_ui_ux_usability.md` dagi `UX-002` Stop tugmasi o'rniga "Error dialogs" deb xato yozilgan va `MISA-ROOT-025` ga bog'langan).
   - UI/UX Deep Audit hisobotlaridagi haqiqiy `AI-UX-004` (Fallback model indikatori) boshqa xotira topilmalari ichida yo'qotib yuborilgan.
   - Design Deep Audit dagi `VIS-BRAND-001` va Phase 3 dagi `VIS-001` (Mikasa brendi qoldiqlari) umumiy `MISA-ROOT-022` dizayn toifasiga adashib qo'shib yuborilgan.
3. **Phase 4.3 dagi tuzatish:**  
   Ushbu uzilishlar bevosita asl hisobotlar (`06_ui_ux_usability.md`, `02_USABILITY_AUDIT.md`, `04_AI_AGENT_EXPERIENCE.md`, `01_BRAND_IDENTITY.md` va `02_VISUAL_DESIGN_EXCELLENCE.md`) bilan solishtirilib, 100% to'g'rilandi. Barcha 32 ta MasterID haqiqiy topilmalar bilan to'liq bog'landi.

---

## 2. OLDIN TUSHIB QOLGAN 3 TA MASTER ID NING CHUQUR TAHLILI

### 2.1. `MISA-ROOT-012`: Agent Generatsiyasini Darhol To'xtatuvchi `[Stop]` Tugmasi Yo'qligi
- **Noyob Master ID:** `MISA-ROOT-012`
- **Asl Topilma IDlari va Manbalari:**
  1. Phase 1: `UX-002` (`06_ui_ux_usability.md`) — *"Missing Stop button to abort agent generation immediately"*
  2. UI/UX Deep Audit: `UX-HEUR-002` (`02_USABILITY_AUDIT.md`) — *"Agent generatsiyasini darhol to'xtatish (AbortController) tugmasi yo'qligi"*
- **Tasnif Toifasi:** `FEATURE_GAP` (Yetishmayotgan Funksional Imkoniyat)
- **Yakuniy Tasdiqlash Holati:** `CONFIRMED`
- **Dalilga Asoslangan Jiddiylik:** **High** (Foydalanuvchi nazorati va nojo'ya amallarni to'xtatish uchun kritik zarur)
- **Haqiqiy Kod Dalili:**  
  [`Misa/src/pages/ChatPage.tsx:L250`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx#L250) — Chat interfeysida xabar yuborilgach, agent uzoq o'ylanayotganda yoki noto'g'ri buyruqlar zanjirini boshlaganda so'rovni bekor qiluvchi `AbortController.abort()` hodisasiga bog'langan vizual qizil `[■ To'xtatish]` tugmasi mavjud emas.
- **Oldin CSV dan tushib qolish sababi:** Phase 4.2 da `UX-002` xato ravishda "Error dialogs display stack trace" deb nomlanib, `MISA-ROOT-025` ga biriktirilgan edi.

---

### 2.2. `MISA-ROOT-028`: AI Provayder Nosozligida Zaxira Modelga O'tish Holati Foydalanuvchiga Ko'rinmasligi
- **Noyob Master ID:** `MISA-ROOT-028`
- **Asl Topilma IDlari va Manbalari:**
  1. Phase 1: `AI-004` (`04_ai_agents_orchestration.md`) — *"Offline local LLM provider missing fallback handling"*
  2. UI/UX Deep Audit: `AI-UX-004` (`04_AI_AGENT_EXPERIENCE.md`) — *"AI Provayder nosozliklarida zaxira modelga o'tish holati foydalanuvchiga ko'rinmasligi"*
- **Tasnif Toifasi:** `FEATURE_GAP` (Yetishmayotgan Funksional Imkoniyat)
- **Yakuniy Tasdiqlash Holati:** `CONFIRMED`
- **Dalilga Asoslangan Jiddiylik:** **Medium**
- **Haqiqiy Kod Dalili:**  
  [`core/providers/manager.py:L40`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/providers/manager.py#L40) va [`Misa/src/pages/ChatPage.tsx:L140`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx#L140) — Agar asosiy model (masalan, Claude 3.5 Sonnet yoki GPT-4o) kvota tugashi yoki tarmoq xatosi tufayli javob bermasa, backend zaxira provayderga (masalan, mahalliy Ollama yoki OpenAI mini) avtomatik o'tadi. Ammo UI da foydalanuvchiga hech qanday "Diqqat: Asosiy model javob bermadi, zaxira model ishlatilmoqda" degan indikator chiqmaydi.
- **Oldin CSV dan tushib qolish sababi:** Phase 4.2 dagi sintetik CSV tuzuvchi ushbu xususiyatni xotira boshqaruvi (`MISA-ROOT-027`) bilan adashtirib, unga alohida ID bermagan.

---

### 2.3. `MISA-ROOT-032`: Brend Nomlarida Eski "Mikasa" Qoldiqlari
- **Noyob Master ID:** `MISA-ROOT-032`
- **Asl Topilma IDlari va Manbalari:**
  1. Phase 3 Deep Research: `VIS-001` (`02_VISUAL_DESIGN_EXCELLENCE.md`) — *"Residual Mikasa branding in CSS classes and icons"*
  2. Design Deep Audit: `VIS-BRAND-001` (`01_BRAND_IDENTITY.md`) — *"Residual Mikasa branding in CSS classes and component names"*
- **Tasnif Toifasi:** `TECHNICAL_DEBT` (Texnik Qarz va Kod Tozaligi)
- **Yakuniy Tasdiqlash Holati:** `CONFIRMED`
- **Dalilga Asoslangan Jiddiylik:** **Low**
- **Haqiqiy Kod Dalili:**  
  [`Misa/src/styles/globals.css:L40`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/styles/globals.css#L40) va [`Misa/src/components/MisaIntroSplash.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/MisaIntroSplash.tsx) — Ilova nomi "Misa" ga o'zgartirilganiga qaramay, CSS fayllarida `.mikasa-logo`, `.mikasa-button`, `.mikasa-header` kabi klasslar va ba'zi izohlarda eski loyiha nomi qolib ketgan.
- **Oldin CSV dan tushib qolish sababi:** Phase 4.2 da `VIS-001` va `VIS-BRAND-001` umumiy dizayn tizimi xatosi (`MISA-ROOT-022`) deb umumlashtirilib, `MISA-ROOT-032` qatori bo'sh qolib ketgan.

---

## 3. BARCHA 32 TA MASTER ROOT CAUSE TO'LIQ KUZATILUVCHANLIK JADVALI

Quyidagi jadval barcha 32 ta MasterID ning har birini, ularning toifasi, jiddiyligi, tasdiqlash holati va unga bog'langan asl topilmalarni aks ettiradi:

| Master ID | Toifa (Classification) | Jiddiylik | Holat | Asosiy Kod Manbasi | Asl Topilma IDlari | Qisqa Tavsif |
|---|---|---|---|---|---|---|
| **`MISA-ROOT-001`** | Security Risk | Critical | CONFIRMED | `core/api_server.py:L7351` | `API-001`, `API-002`, `SEC-APP-001`, `SEC-001` | Port 18420 API autentifikatsiyasiz ochiqligi va CORS `*` |
| **`MISA-ROOT-002`** | Confirmed Defect | High / Blocker | CONFIRMED | `Misa/src-tauri/tauri.conf.json:L37` | `WIN-001`, `QA-003`, `XPLAT-005`, `VIS-002` | PyInstaller onedir `_internal` katalogining installerga kiritilmagani |
| **`MISA-ROOT-003`** | Security Risk | Critical | CONFIRMED | `Misa/src-tauri/src/lib.rs:L681` | `WIN-003`, `SEC-003`, `SEC-APP-002`, `SEC-002` | `ShellExecuteW` da URL protokoli (scheme) tekshirilmasligi |
| **`MISA-ROOT-004`** | Security Risk | Critical | CONFIRMED | `core/agent_tools.py:L514` | `API-003`, `SEC-001`, `XPLAT-004`, `SEC-003` | `open_app` da PowerShell argument in'eksiyasi (CWE-78) |
| **`MISA-ROOT-005`** | Security Risk | High | CONFIRMED | `core/v8/ai_key_manager.py:L115` | `SEC-002`, `SEC-APP-003`, `SEC-004` | API kalitlarning ochiq matnda saqlanishi (No DPAPI) |
| **`MISA-ROOT-006`** | Security Risk | Critical | CONFIRMED | `Misa/src/pages/ChatPage.tsx:L100` | `AI-002`, `AISEC-002`, `AISEC-003`, `AISEC-005` | Destruktiv amallarda server-side Human-in-the-Loop kafolati yo'qligi |
| **`MISA-ROOT-007`** | Confirmed Defect | Medium | PARTIALLY_CONFIRMED | `Misa/src-tauri/src/lib.rs:L290` | `WIN-002`, `XPLAT-001`, `XPLAT-002` | Dev runtime kandidatlari ro'yxatida `release/v9.3` yo'qligi |
| **`MISA-ROOT-008`** | Confirmed Defect | High | CONFIRMED | `Misa/src/App.css:L91` | `FE-001`, `UX-004`, `A11Y-002`, `A11Y-UX-002` | Global `outline: none` tufayli fokus halqasi yo'qligi (WCAG 2.4.7 AA) |
| **`MISA-ROOT-009`** | Confirmed Defect | High | CONFIRMED | `Misa/src/pages/AuthPage.tsx:L1824` | `A11Y-001`, `A11Y-UX-001`, `AUD-004` | Inputlarda dasturiy bog'langan `<label htmlFor>` va `id` yo'qligi |
| **`MISA-ROOT-010`** | Confirmed Defect | High | CONFIRMED | `Misa/src/components/UpdateModal.tsx:L150` | `FE-002`, `A11Y-003`, `A11Y-UX-003` | Modal oynalarda `role="dialog"` va Focus Trap mexanizmi yo'qligi |
| **`MISA-ROOT-011`** | Confirmed Defect | High | CONFIRMED | `Misa/src-tauri/src/lib.rs:L1310` | `VIS-LAY-001`, `UI-003` | High-DPI 150% ekranlarda 800px oyna balandligi pastki panelni qirqishi |
| **`MISA-ROOT-012`** | Feature Gap | High | CONFIRMED | `Misa/src/pages/ChatPage.tsx:L250` | `UX-002`, `UX-HEUR-002` | Agent generatsiyasini darhol to'xtatuvchi `[Stop]` tugmasi yo'qligi |
| **`MISA-ROOT-013`** | Feature Gap | High | CONFIRMED | `core/agents/manager_agent.py:L10` | `AI-001`, `UX-JRN-002`, `AI-UX-001`, `ARC-003` | Agent rejasining foydalanuvchiga ko'rinmasligi ("Qora quti" ijrosi) |
| **`MISA-ROOT-014`** | Confirmed Defect | High | CONFIRMED | `core/audio_service.py:L95` | `UX-003`, `PERF-002`, `AUD-002`, `AUD-005` | Parallel audio oqimlarida deadlock va duplex audio muammosi |
| **`MISA-ROOT-015`** | Feature Gap | High | CONFIRMED | `models/wake_word/:L1` | `AUD-001` | "Salom Misa" neyron wake-word (.onnx) modelining yo'qligi |
| **`MISA-ROOT-016`** | Security Risk | High | CONFIRMED | `core/gui/controller.py:L50` | `AI-003`, `AISEC-001`, `SEC-005` | Indirect Prompt Injection: Oyna sarlavhalari va klipbord nazoratsizligi |
| **`MISA-ROOT-017`** | Confirmed Defect | High | CONFIRMED | `Misa/src/pages/AuthPage.tsx:L1824` | `FE-003`, `FE-004`, `QA-005`, `UI-STATE-003` | Kirish formasida so'rovlar poygasi va takroriy bosish (Double-click race) |
| **`MISA-ROOT-018`** | Confirmed Defect | High | CONFIRMED | `Misa/src/components/Button.tsx:L47` | `VIS-003`, `VIS-DS-001`, `PERF-003` | Button.tsx da `--glass-bg` kabi mavjud bo'lmagan tokenlar ishlatilishi |
| **`MISA-ROOT-019`** | Confirmed Defect | High | CONFIRMED | `Misa/src/styles/tokens.css:L101` | `VIS-005`, `VIS-CLR-001`, `VIS-CLR-002` | Yorug' mavzuda oq fonda oq matn qolib, kontrast yo'qolishi (WCAG 1.4.3) |
| **`MISA-ROOT-020`** | Technical Debt | Medium | CONFIRMED | `Misa/src/App.tsx:L45` | `API-005`, `UX-005`, `UX-JRN-001`, `ARC-004` | Sozlamalar va boshqaruvning 5 ta alohida sahifaga tarqalib ketganligi |
| **`MISA-ROOT-021`** | UX Recommendation | Medium | CONFIRMED | `Misa/src/pages/MemoryPage.tsx:L10` | `PERF-005`, `UI-001`, `UI-002`, `UI-STATE-001` | Xotira va Rejalashtiruvchi sahifalarida boy bo'sh holatlar yo'qligi |
| **`MISA-ROOT-022`** | UX Recommendation | Medium | CONFIRMED | `Misa/src/styles/tokens.css:L38` | `VIS-004`, `VIS-DS-002`, `VIS-DS-003`, `UX-HEUR-003` | Tizimdagi rang palitrasi, radius va tipografiyaning yagona tizimda emasligi |
| **`MISA-ROOT-023`** | Security Risk | High | CONFIRMED | `core/api_server.py:L150` | `PRIV-003`, `DATA-002` | Log fayllariga foydalanuvchi so'rovlari va maxfiy ma'lumotlar yozilishi |
| **`MISA-ROOT-024`** | UX Recommendation | Medium | CONFIRMED | `Misa/src/components/CommandPalette.tsx:L332` | `A11Y-UX-005` | Command Palette'da WAI-ARIA Combobox semantikasi yo'qligi |
| **`MISA-ROOT-025`** | UX Recommendation | Medium | CONFIRMED | `Misa/src/components/IconButton.tsx:L12` | `FE-005`, `A11Y-004`, `A11Y-UX-004` | IconButton minimal nishon hajmi (Target Size) mezonining buzilishi |
| **`MISA-ROOT-026`** | Security Risk | Medium | PARTIALLY_CONFIRMED | `Misa/src/pages/VoicePage.tsx:L50` | `PRIV-001`, `PRIV-002`, `SEC-APP-004` | Web Speech API orqali ovoz uzatilishida sozlamalarda opt-in yo'qligi |
| **`MISA-ROOT-027`** | Feature Gap | Medium | CONFIRMED | `Misa/src/pages/MemoryPage.tsx:L40` | `DATA-001`, `DATA-003`, `DATA-005`, `AI-UX-003` | Foydalanuvchi xotirani interfeys orqali to'g'ridan-to'g'ri tahrirlay olmasligi |
| **`MISA-ROOT-028`** | Feature Gap | Medium | CONFIRMED | `Misa/src/pages/ChatPage.tsx:L140` | `AI-004`, `AI-UX-004` | AI Provayder nosozliklarida zaxira modelga o'tish holati ko'rinmasligi |
| **`MISA-ROOT-029`** | UX Recommendation | High | CONFIRMED | `Misa/src/pages/ChatPage.tsx:L310` | `UX-HEUR-004` | Xatolik yuz berganda avtomatik qayta urinish (Retry) tugmasi yo'qligi |
| **`MISA-ROOT-030`** | Technical Debt | High | CONFIRMED | `core/api_server.py:L7920` | `ARC-001`, `ARC-002`, `QA-001`, `QA-004` | Monolit God fayllar (`api_server.py` 7920 qator, `backendService.ts` 4900 qator) |
| **`MISA-ROOT-031`** | UX Recommendation | Low | CONFIRMED | `Misa/src/components/MisaIntroSplash.tsx:L1` | `UX-001` | Ochilishda majburiy 800ms intro video va audio ijro etilishi |
| **`MISA-ROOT-032`** | Technical Debt | Low | CONFIRMED | `Misa/src/styles/globals.css:L40` | `VIS-001`, `VIS-BRAND-001` | Brend nomlarida eski `Mikasa` qoldiqlari (`mikasa-logo`, `mikasa-button`) |

---

## 4. STATISTIK REKONSILYATSIYA VA YAKUNIY XULOSA

Barcha 32 ta MasterID bo'yicha toifalar:
- **Confirmed Defect:** **10 ta** (31.25%)
- **Security Risk:** **8 ta** (25.00%)
- **Feature Gap:** **5 ta** (15.625%)
- **UX Recommendation:** **6 ta** (18.75%)
- **Technical Debt:** **3 ta** (9.375%)
- **JAMI:** **32 ta** (100.00%)

Ushbu jadval `01_RECONCILED_FINDINGS.csv` dagi barcha 138 ta xom qatorlar bilan 100% matematik va semantik moslikka ega.
