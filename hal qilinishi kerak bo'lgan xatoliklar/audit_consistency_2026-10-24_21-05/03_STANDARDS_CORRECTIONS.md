# 03 — STANDARDS RECONCILIATION & CITATION CORRECTIONS
## MISA V9 — Xalqaro Standartlar, Versiyalar, Bandlar va Muvofiqlik Mezonlarini To'g'rilash

- **Audit Turi:** Regulatory Standards Verification & Normative Correction (Phase 4.1)
- **Sana:** 2026-10-24
- **Auditor Roli:** Lead Compliance, Standards Architect & WCAG/OWASP Auditor
- **Qamrov:** OWASP ASVS (v4.0.3 vs v5.0), W3C WCAG 2.2 (SC 2.4.7, SC 2.5.8), WAI-ARIA APG, OWASP LLM 2025 (LLM06).
- **Qat'iy Qoida:** 100% READ-ONLY. Hech qanday kod o'zgartirilmadi.

---

## 1. KIRISH VA STANDARTLARNING XOLISLIGI

Avvalgi audit hisobotlarida xalqaro xavfsizlik va accessibility standartlariga havola berishda bir qator chalkashliklar va noto'g'ri band raqamlaridan foydalanilgan. Ushbu hisobot xalqaro standartlarning rasmiy matnlari asosida barcha xatoliklarni to'g'rilaydi va ularning Misa loyihasidagi amaliy ma'nosini belgilab beradi.

---

## 2. OWASP ASVS: v4.0.3 VA v5.0 DRAFT FARQLARI HAMDA CORS BANDI

### A. ASVS v4.0.3 (Amaldagi Rasmiy Versiya)
Loyiha xavfsizligini tekshirishda faqat amaldagi **OWASP ASVS v4.0.3** (2020-yil oktyabr) rasmiy standarti qo'llanilishi shart. ASVS v5.0 hozirda loyiha (draft) bosqichida bo'lib, rasmiy kuchga ega emas.

### B. `V13.1.4` va `V13.2.3` Bandlarining Asl Mazmuni:
- **ASVS v4.0.3 `V13.1.4`:**  
  *Asl matni:* *"Verify that authorization decisions are made at both the URI level (enforced by programmatic or declarative security at the controller or router) and at the resource level (enforced by model-based permissions)."*  
  *Misa'dagi ma'nosi:* Port 18420 dagi har bir endpointda faqat router darajasida emas, balki resurs/foydalanuvchi darajasida ham avtorizatsiya bo'lishi talabi.
- **ASVS v4.0.3 `V13.2.3`:**  
  *Asl matni:* *"Verify that RESTful web services that utilize cookies are protected from Cross-Site Request Forgery (CSRF) via the use of at least one or more of the following: double submit cookie pattern, CSRF nonces, or Origin request header checks."*  
  *Misa'dagi ma'nosi:* Cookie ishlatuvchi REST xizmatlar uchun CSRF himoyasi.

### C. CORS Uchun To'g'ri Band: `V14.5.3`!
Avvalgi hisobotlarda CORS zaifligi (`Access-Control-Allow-Origin: *`) noto'g'ri ravishda `V13.2.3` ga bog'langan. Aslida OWASP ASVS v4.0.3 da CORS talabi **`V14.5.3`** bandida mustahkamlangan:
- **ASVS v4.0.3 `V14.5.3` (Level 1, 2, 3 — CWE-346):**  
  *Asl matni:* *"Verify that the Cross-Origin Resource Sharing (CORS) Access-Control-Allow-Origin header uses a strict allow list of trusted domains and subdomains to match against and does not support the "null" origin."*  
- **Xulosa:** [`core/api_server.py:7351`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/api_server.py#L7351) dagi `*` va reflektiv origin xatosi uchun to'g'ri havola **OWASP ASVS v4.0.3 V14.5.3** deb ko'rsatilishi shart!

---

## 3. W3C WCAG 2.2: FOCUS VISIBLE VA TARGET SIZE TALABLARI

### A. `2.4.7 Focus Visible` Qaysi Darajaga Kiradi?
- **Rasmiy Holat:** WCAG 2.2 da `2.4.7 Focus Visible` **Level A** darajasidagi majburiy mezon hisoblanadi!
- **Tuzatish:** Avvalgi hisobotlarda bu mezon ba'zan "Level AA" deb xato keltirilgan. [`Misa/src/App.css:89`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/App.css#L89) dagi `outline: none` mezoni eng yuqori majburiy talab bo'lgan **WCAG 2.2 SC 2.4.7 (Level A)** ni buzadi.

### B. `2.5.8 Target Size (Minimum)` va 44px HIG Chalkashligi:
- **WCAG 2.2 SC 2.5.8 (Level AA — Yangi mezon):**  
  *Asl talab:* Interaktiv elementlar o'lchami kamida **24 by 24 CSS piksel** bo'lishi kerak (44px EMAS!).
  *5 ta Rasmiy Istisno:*
  1. **Spacing Exception:** Agar 24px doira boshqa tugma yoki boshqa doira bilan kesishmasa, tugma kichikroq bo'lsa ham o'tadi.
  2. **Equivalent Control:** Sahifada xuddi shu amalni bajaruvchi boshqa 24px boshqaruvchi bo'lsa.
  3. **Inline:** Gap ichidagi matn havolalari.
  4. **User Agent Control:** Brauzerning o'zgartirilmagan standart inputlari.
  5. **Essential:** Sxema, xarita yoki texnik jihatdan o'lchamni o'zgartirib bo'lmaydigan holatlar.
- **Tuzatish:** [`Misa/src/components/IconButton.tsx:12`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/IconButton.tsx#L12) komponenti **34x34 CSS piksel** hajmga ega. Demak, u **WCAG 2.2 SC 2.5.8 (Level AA — 24px) mezonini BUZMAYDI**!
- **Haqiqat:** 44x44px me'yori WCAG 2.2 da **SC 2.5.5 Target Size (Enhanced) — Level AAA** talabidir yoki Apple Human Interface Guidelines (HIG) hamda Google Material Design tavsiyasidir. Shuning uchun `IconButton.tsx` ni "WCAG Level AA qoidabuzari" deb atash xato; u Level AA dan o'tadi, biroq sensorli ekranlar uchun Level AAA / HIG bo'yicha tavsiya etiladi.

---

## 4. WAI-ARIA APG VS ME'YORIY WCAG STANDARTLARI

- **WAI-ARIA Authoring Practices Guide (APG):** Bu rasmiy W3C standarti emas, balki **tavsiyaviy yo'riqnoma (Informative Guide)** hisoblanadi.
- **Me'yoriy Buzilish:** `UpdateModal.tsx` va `CommandPalette.tsx` da `role="dialog"` yoki focus-trap yo'qligi APG ga zid keladi, ammo qonuniy me'yor sifatida u quyidagi rasmiy WCAG mezonlarini buzadi:
  - **WCAG SC 2.1.2 No Keyboard Trap (Level A):** Fokus modal orqasiga chiqib ketib, klaviatura aylanib qolishi.
  - **WCAG SC 2.4.3 Focus Order (Level A):** Tab bosilganda fokus mantiqiy ketma-ketlikda yurmasligi.
  - **WCAG SC 4.1.2 Name, Role, Value (Level A):** Elementning roli (`dialog`, `combobox`) va holati e'lon qilinmasligi.

---

## 5. OWASP TOP 10 FOR LLMS 2025: LLM06 (EXCESSIVE AGENCY)

### A. Rasmiy Ta'rifi (OWASP LLM 2025 v2.0):
**LLM06:2025 Excessive Agency** — AI agentga tizim resurslari, fayllar, API va operatsion tizim vositalari bilan ishlashda yetarli cheklovlar, granular ruxsatlar va insoniy tasdiq (Human-In-The-Loop) berilmaganligi sababli yuzaga keluvchi xavflar to'plamidir.

### B. Misa Arxitekturasidagi Amaliy Qo'llanilishi:
- **Backend:** [`core/tools/security_policy.py:184-239`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/tools/security_policy.py#L184) da `POWER_ACTIONS`, `FILE_WRITE_OR_DELETE_ACTIONS`, `PROCESS_CLOSE_ACTIONS` uchun `is_confirmation_required` signali to'g'ri ishlab chiqilgan.
- **Frontend Uzilishi:** Ammo [`Misa/src/pages/ChatPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx) ushbu signalni qabul qilmaydi va foydalanuvchiga tasdiqlash modali chiqarmaydi.
- **Natija:** AI agent murakkab topshiriq bajarayotganda, agar prompt inyeksiya sodir bo'lsa, foydalanuvchining bexabar fayllarni o'chirish yoki tizim jarayonlarini to'xtatish xavfi yuzaga keladi. Bu to'g'ridan-to'g'ri **LLM06:2025** ning amaliy ko'rinishidir.

---

## 6. XULOSAVIY MEZONLAR VA HAVOLALAR REYESTRI

| Standart | To'g'ri Band | Rasmiy Darajasi | Misa'dagi To'g'ri Talqin | Rasmiy Manba (URL) |
|---|---|---|---|---|
| **OWASP ASVS v4.0.3** | **V14.5.3** | Level 1, 2, 3 | CORS `*` va reflektiv origin taqiqlanadi | [OWASP ASVS v4.0.3 V14](https://owasp.org/www-project-application-security-verification-standard/) |
| **OWASP ASVS v4.0.3** | **V13.1.4** | Level 1, 2, 3 | URI va resurs darajasida avtorizatsiya | [OWASP ASVS v4.0.3 V13](https://owasp.org/www-project-application-security-verification-standard/) |
| **W3C WCAG 2.2** | **SC 2.4.7** | **Level A** | Fokus doimo ko'zga ko'rinishi shart (`outline`) | [W3C SC 2.4.7 Focus Visible](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html) |
| **W3C WCAG 2.2** | **SC 2.5.8** | **Level AA** | Minimal 24x24px (34px tugma buni buzmaydi) | [W3C SC 2.5.8 Target Size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) |
| **W3C WCAG 2.2** | **SC 2.5.5** | **Level AAA** | Kengaytirilgan 44x44px (Tavsiyaviy daraja) | [W3C SC 2.5.5 Target Size Enhanced](https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced.html) |
| **W3C WCAG 2.2** | **SC 2.1.2** | **Level A** | Modallarda klaviatura qamalib qolmasligi | [W3C SC 2.1.2 No Keyboard Trap](https://www.w3.org/WAI/WCAG22/Understanding/no-keyboard-trap.html) |
| **OWASP LLM 2025** | **LLM06:2025** | High/Critical | AI tool chaqiruvlarida Human-In-The-Loop | [OWASP Top 10 for LLMs 2025](https://genai.owasp.org/llm-top-10/) |

Ushbu to'g'rilashlar barcha me'yoriy chalkashliklarni bartaraf etadi va Misa loyihasi bo'yicha tuzatiladigan texnik talablarni yuridik va xalqaro jihatdan nuqsonsiz qiladi.
