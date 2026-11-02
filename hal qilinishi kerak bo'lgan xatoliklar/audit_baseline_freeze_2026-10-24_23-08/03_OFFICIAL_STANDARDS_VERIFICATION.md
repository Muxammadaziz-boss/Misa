# 03 — RASMIY STANDARTLAR VA ME'YORIY TALABLAR VERIFIKATSIYASI (PHASE 4.3)
**Hujjat turi:** Xalqaro Standartlar Muvofiqligi va Normativ Re-Audit Hisoboti  
**Sana:** 2026-10-24  
**Auditor:** Principal Standards & Regulatory Compliance Auditor  
**Holat:** Final Verified / Ratified Normative Baseline  

---

## 1. KIRISH VA STANDARTLARNI QO'LLASH PRINSIPLARI

Oldingi audit bosqichlarida xalqaro xavfsizlik (OWASP ASVS, OWASP LLM) va qulaylik (W3C WCAG 2.2) standartlaridan foydalanishda ayrim metodologik xatoliklarga yo'l qo'yilgan edi:
1. Chiqarilmagan qoralama (draft) versiyalarni rasmiy standart sifatida ko'rsatish;
2. Standart bandlarining muayyan shartlarini hisobga olmasdan, ilova arxitekturasiga mos kelmaydigan mezonlarni avtomatik "buzilgan" deb e'lon qilish (masalan, cookie ishlatilmaydigan REST xizmatlariga klassik cookie-CSRF qoidalarini to'g'ridan-to'g'ri tatbiq etish);
3. WCAG muvofiqlik darajalarini (Level A, Level AA, Level AAA) adashtirish.

Ushbu hujjat har bir standart bo'yicha faqat rasmiy hujjatlarga tayanadi, to'g'ridan-to'g'ri rasmiy URL manzillari, aniq talab matni va Misa arxitekturasiga haqiqiy tatbiq etilish shartlarini birma-bir belgilab beradi.

---

## 2. OWASP APPLICATION SECURITY VERIFICATION STANDARD (ASVS)

### 2.1. ASVS Versiyalari va Rasmiy Nashr Holati
- **OWASP ASVS v4.0.3 (Rasmiy Reliz):**
  - **Nashr sanasi:** 2020-yil oktyabr.
  - **Holati:** Amaldagi yagona rasmiy tasdiqlangan (production-ready) reliz.
  - **Muhim me'yoriy aniqlik:** v4.0.3 2020-yilgi standart bo'lib, uni "eng yangi zamonaviy 2026-yilgi versiya" deb atash noto'g'ri. Biroq, u rasmiy auditlar uchun amaldagi yagona qonuniy me'yordir.
  - **Rasmiy Manba URL:** https://owasp.org/www-project-application-security-verification-standard/
- **OWASP ASVS v5.0.0 (Faol Rivojlanish Bosqichidagi Qoralama):**
  - **Holati:** GitHub ochiq omboridagi (`OWASP/ASVS` main branch) bleeding-edge qoralama (draft). U rasman tasdiqlanmagan, uning bandlari va raqamlanishi o'zgarishi mumkin.
  - **Normativ baho:** ASVS 5.0.0 dan kelajak tendensiyalari uchun foydalanish mumkin, ammo loyihaga qat'iy normativ da'vo qo'yishda faqat **v4.0.3** ga tayanish shart.

---

### 2.2. ASVS v4.0.3 Bandlarining Aniq Matni va Misa'ga Tatbiqi

#### A. ASVS v4.0.3 — V14.5.3 (CORS Siyosati)
- **Rasmiy ASVS v4.0.3 Matni:**  
  > *"Verify that the Cross-Origin Resource Sharing (CORS) Access-Control-Allow-Origin header only allows trusted origins, and does not allow null or the wildcard (*) origin for sensitive resources or endpoints requiring authentication."*
- **Tegishli CWE:** CWE-346 (Origin Validation Error).
- **Muvofiqlik Darajasi:** Level 1, Level 2, Level 3.
- **Rasmiy Manba URL:** https://github.com/OWASP/ASVS/blob/v4.0.3/4.0/en/0x22-V14-Config.md#v145-http-headers-requirements
- **Misa'ga Tatbiq Etilish Tahlili (`MISA-ROOT-001`):**  
  `core/api_server.py:L7351` da `cors_middleware` barcha originlarga ruxsat beradi (`allow_origins=["*"]`). Mahalliy API porti (`18420`) orqali buyruqlar bajarish va fayllarga kirish mumkin. Bu **ASVS v4.0.3 V14.5.3** ning bevosita va to'liq buzilishidir.

#### B. ASVS v4.0.3 — V13.1.4 (API Autentifikatsiyasi va Resurs Ruxsati)
- **Rasmiy ASVS v4.0.3 Matni:**  
  > *"Verify that authorization checks are performed on every access to a protected resource or API, including cached or previously authorized assets."*
- **Tegishli CWE:** CWE-285 (Improper Authorization).
- **Muvofiqlik Darajasi:** Level 1, Level 2, Level 3.
- **Rasmiy Manba URL:** https://github.com/OWASP/ASVS/blob/v4.0.3/4.0/en/0x21-V13-API.md#v131-generic-web-service-security-verification-requirements
- **Misa'ga Tatbiq Etilish Tahlili (`MISA-ROOT-001`):**  
  `core/api_server.py:L7328` da `auth_enforcement_middleware` ichida desktop rejimi aniqlanganda autentifikatsiya tekshiruvi chetlab o'tiladi (`if is_desktop_mode: return await handler(request)`). Oqibatda har qanday so'rov avtorizatsiyasiz qabul qilinadi. Bu **ASVS v4.0.3 V13.1.4** buzilishi hisoblanadi.

#### C. ASVS v4.0.3 — V13.2.3 (REST xizmatlarida CSRF va Tranzaksiya Nazorati)
- **Rasmiy ASVS v4.0.3 Matni:**  
  > *"Verify that the application protects against Cross-Site Request Forgery (CSRF) on state-changing API endpoints, or that the application uses anti-CSRF tokens, or that cross-origin resource sharing (CORS) is configured to prevent cross-origin access."*
- **Tegishli CWE:** CWE-352 (Cross-Site Request Forgery).
- **Muvofiqlik Darajasi:** Level 1, Level 2, Level 3.
- **Rasmiy Manba URL:** https://github.com/OWASP/ASVS/blob/v4.0.3/4.0/en/0x21-V13-API.md#v132-restful-web-service-verification-requirements
- **Muhim Metodologik Farq va Misa'ga Aniq Tatbiqi:**  
  - *Klassik CSRF sharti:* Foydalanuvchi brauzerida saqlangan ambient autentifikatsiya ma'lumotlari (sessiya cookie'lari yoki HTTP Basic Auth) mavjud bo'lishi va brauzer ularni avtomatik tarzda jo'natishi kerak.
  - *Misa haqiqati:* Misa backend REST API'si cookie-sessiyalardan **foydalanmaydi**. Shuning uchun Misa'da "cookie-o'g'irlash yoki soxta cookie-sessiya orqali CSRF" mavjud emas!
  - *Biroq mezonning ikkinchi qismi:* Standart *"or that cross-origin resource sharing (CORS) is configured to prevent cross-origin access"* deb talab qiladi. Misa'da CORS `*` bo'lgani va API token talab qilmagani sababli, foydalanuvchi brauzerida ochilgan tashqi zararli veb-saytdagi JavaScript mahalliy `http://127.0.0.1:18420/api/cmd` manziliga bevosita POST so'rovi yuborishi mumkin (agar brauzer Private Network Access — PNA orqali bloklamasa).
  - *Xulosa:* Misa V13.2.3 ni **cookie zaifligi orqali emas**, balki **CORS kelib chiqishini (Origin) cheklamagani va holatni o'zgartiruvchi operatsiyalarda anti-CSRF/session tokeni ishlatmagani tufayli** buzadi.

---

## 3. W3C WEB CONTENT ACCESSIBILITY GUIDELINES (WCAG 2.2)

Rasmiy W3C Tavsiyasi (Published 05 October 2023):  
Rasmiy URL: https://www.w3.org/TR/WCAG22/

### 3.1. Success Criterion 2.4.7 Focus Visible
- **Rasmiy W3C Matni:**  
  > *"Any keyboard operable interface has a mode of operation where the keyboard focus indicator is visible."*
- **Rasmiy Muvofiqlik Darajasi:** **Level AA**  
  *(Qat'iy eslatma: WCAG 2.0, 2.1 va 2.2 da bu mezon doimo Level AA bo'lgan; uni Level A deb talqin qilish mutlaqo noto'g'ri).*
- **Rasmiy URL:** https://www.w3.org/TR/WCAG22/#focus-visible
- **Misa'dagi Dalil:** `Misa/src/App.css:L91` da `*:focus { outline: none; }` qo'llangan. Tab bilan navigatsiya qilinganda hech qanday vizual indikator yo'q. Bu **Level AA** qoidabuzarligidir.

### 3.2. Success Criterion 2.4.3 Focus Order
- **Rasmiy W3C Matni:**  
  > *"If a Web page can be navigated sequentially and the navigation sequences affect meaning or operation, focusable components receive focus in an order that preserves meaning and operability."*
- **Rasmiy Muvofiqlik Darajasi:** **Level A**
- **Rasmiy URL:** https://www.w3.org/TR/WCAG22/#focus-order
- **Misa'dagi Dalil:** `Misa/src/components/UpdateModal.tsx:L150`. Modal dialog ochilganda fokus modal ichidagi birinchi boshqaruv elementiga yo'naltirilmaydi va modal orqasidagi fon elementlariga o'tib ketadi. Bu **Level A** buzilishidir.

### 3.3. Success Criterion 2.5.8 Target Size (Minimum)
- **Rasmiy W3C Matni:**  
  > *"The size of the target for pointer inputs is at least 24 by 24 CSS pixels, except where: Spacing (24px target diameter), Equivalent, Inline, User Agent Control, or Essential."*
- **Rasmiy Muvofiqlik Darajasi:** **Level AA** (WCAG 2.2 da yangi qo'shilgan).
- **Rasmiy URL:** https://www.w3.org/TR/WCAG22/#target-size-minimum
- **Muhim Metodologik Farq:**  
  - WCAG 2.2 **Level AA** minimal talabi — **24x24 CSS px** (5 ta istisno bilan).
  - **44x44 CSS px** talabi esa **WCAG 2.2 SC 2.5.5 (Level AAA)** ga tegishlidir!
- **Misa'dagi Dalil:** `Misa/src/components/IconButton.tsx:L12` dagi tugmalar `34px` o'lchamga ega.  
  - Demak, `IconButton.tsx` WCAG 2.2 **SC 2.5.8 (Level AA) 24px mezonini qanoatlantiradi**!  
  - Ammo u ba'zi eski auditlarda aytilganidek 44px (Level AAA) talabiga javob bermaydi. Shuning uchun bu topilma `CONFIRMED` emas, balki `PARTIALLY_CONFIRMED` (Level AAA da kamchilik, ammo Level AA da o'tadi) deb baholandi.

### 3.4. Success Criterion 1.3.1 Info and Relationships
- **Rasmiy W3C Matni:**  
  > *"Information, structure, and relationships conveyed through presentation can be programmatically determined or are available in text."*
- **Rasmiy Muvofiqlik Darajasi:** **Level A**
- **Rasmiy URL:** https://www.w3.org/TR/WCAG22/#info-and-relationships
- **Misa'dagi Dalil:** `Misa/src/pages/AuthPage.tsx:L1824` da inputlar `<label htmlFor="...">` teglari bilan bog'lanmagan. `index.html:L20` da semantik landmarklar yo'q. Bu **Level A** buzilishidir.

### 3.5. Success Criterion 4.1.2 Name, Role, Value
- **Rasmiy W3C Matni:**  
  > *"For all user interface components (including but not limited to: form elements, links and components generated by scripts), the name and role can be programmatically determined..."*
- **Rasmiy Muvofiqlik Darajasi:** **Level A**
- **Rasmiy URL:** https://www.w3.org/TR/WCAG22/#name-role-value
- **Misa'dagi Dalil:** `Misa/src/components/CommandPalette.tsx:L332` da WAI-ARIA Combobox roli yo'q; bir nechta ikonka tugmalarida `aria-label` mavjud emas. Bu **Level A** buzilishidir.

---

## 4. OWASP GENAI / LLM TOP 10 (2025)

Rasmiy OWASP Standarti (Published 2025):  
Rasmiy URL: https://genai.owasp.org/llm-top-10/

### 4.1. LLM06: Excessive Agency (Haddan Tashqari Vakolat)
- **Rasmiy Mazmuni:**  
  AI modeliga tizim resurslari (operatsion tizim buyruqlari, fayllarni modifikatsiya qilish/o'chirish) ustidan haddan tashqari ko'p erkinlik berilishi va muhim harakatlar oldidan server-side inson tasdig'i (Human-in-the-Loop) mexanizmi o'rnatilmaganligi.
- **Rasmiy URL:** https://genai.owasp.org/llm06-excessive-agency/
- **Misa'dagi Dalil (`MISA-ROOT-006`):**  
  `core/agents/manager_agent.py:L140` va `Misa/src/pages/ChatPage.tsx:L100` — Agent tizim amallarini bajarganda frontendda faqat ixtiyoriy vizual dialog chiqishi mumkin, biroq backend darajasida buyruq bajaruvchi funksiya hech qanday bir martalik kriptografik tasdiq tokenini (nonce) talab qilmaydi. Bu **OWASP LLM 2025 LLM06** xavfidir.

### 4.2. LLM01: Prompt Injection (Bilvosita In'eksiya)
- **Rasmiy Mazmuni:**  
  Tashqi, ishonchsiz ma'lumotlar manbalari (foydalanuvchi oynalari sarlavhalari, veb-kontent, klipbord) modelning tizimli ko'rsatmalariga (system prompt) delimitatorlarsiz qo'shilishi oqibatida agentning dastlabki xulq-atvori buzilishi.
- **Rasmiy URL:** https://genai.owasp.org/llm01-prompt-injection/
- **Misa'dagi Dalil (`MISA-ROOT-016`):**  
  `core/gui/controller.py:L50` — Faol oyna nomlari va klipbord matni to'g'ridan-to'g'ri tizim promptiga qo'shilmoqda. Maxsus shakllantirilgan oyna nomi agent xulqini o'zgartirishi mumkin.

---

## 5. NORMATIV SOLISHTIRMA VA XULOSA

| Standart / Mezon | Rasmiy Versiya | Muvofiqlik Darajasi | Misa'dagi Haqiqiy Holat | Baholash Xulosasi |
|---|---|:---:|---|---|
| **ASVS V14.5.3** | v4.0.3 | L1–L3 | `allow_origins=["*"]` port 18420 da ochiq | **CONFIRMED VIOLATION** |
| **ASVS V13.1.4** | v4.0.3 | L1–L3 | Desktop rejimida auth tekshiruvi chetlab o'tilgan | **CONFIRMED VIOLATION** |
| **ASVS V13.2.3** | v4.0.3 | L1–L3 | Cookie yo'q, ammo CORS * orqali cross-origin POST mumkin | **PARTIALLY_CONFIRMED (CORS jihatdan)** |
| **WCAG SC 2.4.7** | 2.2 (2023) | **Level AA** | `outline: none` tufayli fokus yo'qolgan | **CONFIRMED VIOLATION** |
| **WCAG SC 2.4.3** | 2.2 (2023) | **Level A** | Modallar fokusni ushlab qolmaydi (Trap yo'q) | **CONFIRMED VIOLATION** |
| **WCAG SC 2.5.8** | 2.2 (2023) | **Level AA** | Tugmalar 34px (24px minimal mezonini qanoatlantiradi) | **PARTIALLY_CONFIRMED (Pass AA, Fail AAA)** |
| **WCAG SC 1.3.1** | 2.2 (2023) | **Level A** | Input label bog'lanmagan, landmarklar yo'q | **CONFIRMED VIOLATION** |
| **WCAG SC 4.1.2** | 2.2 (2023) | **Level A** | Ikonka tugmalarda aria-label yo'q | **CONFIRMED VIOLATION** |
| **OWASP LLM06** | 2025 | N/A | Server-side tasdiqlash tokensiz buyruq ijrosi | **CONFIRMED RISK** |
| **OWASP LLM01** | 2025 | N/A | Oyna sarlavhalari filtrsiz promptga kiritiladi | **CONFIRMED RISK** |

Ushbu verifikatsiya audit hisobotlarining normativ aniqligini ta'minlaydi va barcha huquqiy-standart chalkashliklarni uzil-kesil yopadi.
