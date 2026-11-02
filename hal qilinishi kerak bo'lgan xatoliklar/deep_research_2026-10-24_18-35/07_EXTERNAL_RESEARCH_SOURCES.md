# MISA V9.3 — TASHQI CHUQUR TADQIQOT MANBALARI VA STANDARTLAR REYESTRI
## External Deep Research Sources, Technical Standards & Authoritative References

**Hujjat kodi:** `07_EXTERNAL_RESEARCH_SOURCES.md`  
**Sana va vaqt:** 2026-10-24 18:35  
**Tadqiqotchi:** Mustaqil Deep Research Auditor & Security Researcher  
**Loyiha:** Misa AI v9.3.0 Desktop Assistant  

Ushbu hujjat Misa v9.3 loyihasining Deep Research auditi davomida o'rganilgan, havola qilingan va solishtirilgan barcha xalqaro standartlar, rasmiy xavfsizlik qo'llanmalari, dizayn tizimlari va ilmiy manbalarning to'liq bibliografik reyestridir.

---

## 1. Veb va Desktop Qulayligi Standartlari (Accessibility Standards)

### [EXT-A11Y-01] W3C Web Content Accessibility Guidelines (WCAG) 2.2
- **Tashkilot:** World Wide Web Consortium (W3C) / Accessibility Guidelines Working Group (AG WG)
- **Rasmiy URL:** `https://www.w3.org/TR/WCAG22/`
- **Nashr sanasi:** 2023-yil 5-oktabr (Amaldagi rasmiy W3C Recommendation)
- **Tekshirilgan sana:** 2026-yil 24-oktabr
- **Asosiy qoidalar va Misa komponentlariga tatbiqi:**
  - **SC 1.4.3 Contrast (Minimum) (Level AA):** Oddiy matn va fon o'rtasidagi kontrast kamida `4.5:1`, yirik matnlar uchun `3:1` bo'lishi shart. *Misa'ning Och mavzusidagi (`html.theme-light`) binafsha va kulrang matnlariga tatbiq etildi.*
  - **SC 1.4.11 Non-text Contrast (Level AA):** Interaktiv elementlar chegaralari (input border, icon button) va ularning holatlari kamida `3:1` kontrastga ega bo'lishi shart. *`Misa/src/components/IconButton.tsx` va `Button.tsx` ga tatbiq etildi.*
  - **SC 2.4.7 Focus Visible (Level A):** Har qanday klaviatura fokusi tushgan elementda aniq ko'rinadigan fokus indikatori bo'lishi shart. *`Button.tsx` va `CommandPalette.tsx` dagi focus outline yo'qligiga tatbiq etildi.*
  - **SC 2.4.11 Focus Not Obscured (Minimum) (Level AA):** Yangi WCAG 2.2 qoidasi. Klaviatura fokusi tushgan element boshqa qatlamlar (sticky header, modal) ostida butunlay yashirinib qolmasligi shart.
  - **SC 2.4.13 Focus Appearance (Level AAA):** Fokus indikatori kamida 2px qalinlikda va o'zgarish kontrasti kamida `3:1` bo'lishi lozim.
  - **SC 2.5.8 Target Size (Minimum) (Level AA):** Yangi WCAG 2.2 qoidasi. Har qanday pointer/touch nishoni kamida `24x24px` bo'lishi yoki atrofida yetarli bo'shliq bo'lishi shart. *Misa `IconButton.tsx` (34px) va sidebar piktogrammalariga tatbiq etildi.*
  - **SC 4.1.2 Name, Role, Value (Level A):** Barcha input va modallar ekran o'quvchilari (Screen Reader) uchun aniq nom (`aria-label`, `htmlFor`), rol va holatga ega bo'lishi shart. *`AuthPage.tsx` va `UpdateModal.tsx` ga tatbiq etildi.*

### [EXT-A11Y-02] W3C WAI-ARIA Authoring Practices Guide (APG) — Combobox & Modal Dialog
- **Tashkilot:** W3C Web Accessibility Initiative (WAI)
- **Rasmiy URL:** `https://www.w3.org/WAI/ARIA/apg/patterns/combobox/` va `https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/`
- **Yangilangan sana:** 2024–2025-yillar
- **Asosiy talablar:**
  - Modal oyna ochilganda: `role="dialog"`, `aria-modal="true"`, sarlavhaga `aria-labelledby` bog'lanishi, boshlang'ich fokus birinchi interaktiv elementga o'tishi va klaviatura fokusi modal ichida aylanib qolishi (Focus Trap).
  - Global qidiruv / buyruqlar paneli (Command Palette): `role="combobox"`, `aria-expanded`, `aria-controls="listbox-id"`, `aria-activedescendant` orqali tanlangan elementni e'lon qilish. *`CommandPalette.tsx` ga tatbiq etildi.*

---

## 2. Sun'iy Intellekt va LLM Xavfsizligi Standartlari (AI Security)

### [EXT-SEC-01] OWASP Top 10 for Large Language Model Applications (2025 Edition, v2.0)
- **Tashkilot:** Open Web Application Security Project (OWASP GenAI / LLM Project)
- **Rasmiy URL:** `https://genai.owasp.org/llm-top-10/`
- **Nashr sanasi:** 2024-yil oxiri / 2025-yilgi rasmiy reliz
- **Tekshirilgan sana:** 2026-yil 24-oktabr
- **Tahlil qilingan xatarlar reyestri:**
  - **LLM01:2025 — Prompt Injection:** Foydalanuvchi buyruqlari yoki tashqi ma'lumotlar (ochiq oynalar, clipboard, veb) orqali tizim instruksiyalarini chetlab o'tish (Direct & Indirect Prompt Injection). *`core/ai_engine.py` L217-L225 ga tatbiq etildi.*
  - **LLM02:2025 — Sensitive Information Disclosure:** Model xotirasidagi API kalitlar, PII va shaxsiy suhbatlarning kutilmaganda fosh bo'lishi. *`core/agent_memory.py` va `ai_keys_cache.json` ga tatbiq etildi.*
  - **LLM05:2025 — Improper Output Handling:** Model javoblarini tozalashsiz quyi tizimlarga (PowerShell, brauzer, fayl tizimi) uzatish oqibatida RCE yoki XSS kelib chiqishi. *`core/agent_tools.py` dagi `system_control` ga tatbiq etildi.*
  - **LLM06:2025 — Excessive Agency:** Agentga inson nazoratisiz (Human-in-the-Loop) haddan ortiq yuqori vakolatlar berilishi (jarayonlarni o'ldirish, kompyuterni o'chirish, fayllarni yozish). *`core/intelligence/agent_loop.py` ga tatbiq etildi.*
  - **LLM07:2025 — System Prompt Leakage:** Maxfiy tizim ko'rsatmalari va ichki arxitektura sirlarining model orqali tashqariga sizib chiqishi.
  - **LLM08:2025 — Vector and Embedding / Memory Weaknesses:** RAG konteksti va mahalliy xotirani zararli matnlar bilan zaharlash (Memory Poisoning). *`core/agent_memory.py` bilimlar bazasiga tatbiq etildi.*
  - **LLM09:2025 — Misinformation (Hallucination in Actions):** Model bajarmagan ishini "bajardim" deb e'lon qilishi va tizimning buni tekshirmasdan tasdiqlashi. *`core/intelligence/verifier.py` L114-L121 ga tatbiq etildi.*
  - **LLM10:2025 — Unbounded Consumption:** Cheksiz retry va katta kontekst orqali tokenlar va CPU resurslarini nazoratsiz sarflash. *`core/ai_engine.py` L218 ga tatbiq etildi.*

### [EXT-SEC-02] NIST Artificial Intelligence Risk Management Framework (NIST AI RMF 1.0 / Generative AI Profile NIST AI 600-1)
- **Tashkilot:** National Institute of Standards and Technology (NIST), AQSH
- **Rasmiy URL:** `https://www.nist.gov/itl/ai-risk-management-framework`
- **Nashr sanasi:** 2023–2024-yillar
- **Misa arxitekturasiga tatbiqi:** GOVERN, MAP, MEASURE va MANAGE funksiyalari bo'yicha agentning ishonchlilik (Trustworthiness), shaffoflik va xatoliklarga chidamlilik darajasi baholandi.

---

## 3. Desktop Ilova va Dasturiy Xavfsizlik Standartlari (Desktop Security)

### [EXT-SEC-03] Tauri 2.0 Security Architecture & Best Practices
- **Tashkilot:** Tauri Programme / Commons Conservancy
- **Rasmiy URL:** `https://v2.tauri.app/security/` va `https://v2.tauri.app/security/csp/`
- **Nashr sanasi:** 2024–2025-yillar (Tauri 2.0 Rasmiy hujjatlari)
- **Asosiy qoidalar va Misa tatbiqi:**
  - **Strict CSP:** Hech qachon `'unsafe-eval'` yoki ruxsatsiz HTTP manbalarni ochmaslik. Localhost ulanishlarini faqat belgilangan portlar bilan cheklash. *`Misa/src-tauri/tauri.conf.json` dagi CSP tahlil qilindi.*
  - **The Isolation Pattern:** Frontend XSS xurujlariga uchrasa ham, Rust Core IPC ga zarar yetkazmasligi uchun xavfsiz iframe orqali izolyatsiya qilish. *Misa'da isolation o'chirilganligi qayd etildi.*
  - **Capabilities and Granular Permissions:** Wildcard ruxsatlar o'rniga faqat kerakli fayllar va buyruqlarni qamrovchi (scoped) ruxsatlar berish.
  - **Process Lifecycle Guard:** Bolalar jarayonlari (Python backend) zombi holatda qolmasligi va yopilishda ma'lumotlar buzilmasligi uchun xavfsiz boshqaruv. *`lib.rs` dagi `taskkill /F` muammosiga tatbiq etildi.*

### [EXT-SEC-04] OWASP Application Security Verification Standard (ASVS) v4.0.3
- **Tashkilot:** OWASP Foundation
- **Rasmiy URL:** `https://owasp.org/www-project-application-security-verification-standard/`
- **Standart boblari:**
  - **V2: Authentication Verification:** Tokenlar generatsiyasi, Telegram OTP va Supabase sessiyalari xavfsizligi. *`backendService.ts` va `api_server.py` ga tatbiq etildi.*
  - **V5: Validation, Sanitization and Encoding:** Barcha foydalanuvchi va LLM buyruqlari qobig'iga (shell) tushishidan oldin tozalanishi shart. *`agent_tools.py` ga tatbiq etildi.*
  - **V8: Data Protection:** Maxfiy qiymatlar (API kalitlar) diskda shifrlangan omborlarda (Windows DPAPI) saqlanishi shart. *`ai_keys_cache.json` ga tatbiq etildi.*
  - **V13: API & Web Service:** Mahalliy soket va HTTP API lari (port 18420) soxta so'rovlardan himoyalangan va avtorizatsiyali bo'lishi shart. *`api_server.py` ga tatbiq etildi.*

---

## 4. Foydalanuvchi Tajribasi va Dizayn Tamoyillari (UX & Design Systems)

### [EXT-UX-01] Nielsen Norman Group (NN/g) — 10 Usability Heuristics for User Interface Design
- **Tashkilot:** Nielsen Norman Group
- **Rasmiy URL:** `https://www.nngroup.com/articles/ten-usability-heuristics/`
- **Muallif:** Jakob Nielsen
- **Misa UX auditi uchun qo'llangan evristikalar:**
  1. *Visibility of system status:* Foydalanuvchi agent nima qilayotganini va tizim holatini doim aniq bilishi lozim.
  2. *Match between system and the real world:* Real hayotga mos tushunchalar va atamalar.
  3. *User control and freedom:* Foydalanuvchida bekor qilish (Emergency Exit, barge-in) imkoniyati bo'lishi.
  4. *Consistency and standards:* Barcha sahifalarda tugmalar, modallar va ikonalar bir xil xatti-harakatga ega bo'lishi.
  5. *Error prevention:* Xatolik sodir bo'lishidan oldin uni oldini olish (masalan, xavfli vositalar oldidan tasdiqlash oynasi).
  6. *Recognition rather than recall:* Keraksiz xotira yukini kamaytirish.
  7. *Aesthetic and minimalist design:* Ortiqcha shovqinli vizual elementlar (majburiy intro video) ning bo'lmasligi.
  8. *Help users recognize, diagnose, and recover from errors:* Tushunarli o'zbekcha yechimlar ko'rsatish.

### [EXT-UX-02] Microsoft Windows App Design Guidelines & Fluent Design System
- **Tashkilot:** Microsoft Corporation
- **Rasmiy URL:** `https://learn.microsoft.com/en-us/windows/apps/design/`
- **Misa Desktop tatbiqi:**
  - Windows oynalari chegaralari, High-DPI masshtablash (125%, 150%, 200%), Frameless oynalar boshqaruvi (`WindowControls.tsx`), System Tray xatti-harakati va qorong'u/och mavzularning OS darajasidagi o'zgarishi.

---

## 5. Manbalarning To'liqligi va Cheklovlari

Ushbu tadqiqotda keltirilgan barcha URL manzillar va standart boblari rasmiy manbalarga asoslangan bo'lib, o'ylab topilgan yoki sun'iy sitatalar keltirilmagan. Kelgusi bosqichda tuzatish ishlari olib borilganda, har bir pull request ushbu standart talablari bilan tekshiriladi.
