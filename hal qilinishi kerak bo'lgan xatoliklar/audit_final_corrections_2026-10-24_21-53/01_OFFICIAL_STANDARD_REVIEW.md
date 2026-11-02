# 01 — RASMIY STANDARTLAR VA ME'YORIY TALABLAR QAYTA TEKSHIRUVI (PHASE 4.2)
**Hujjat turi:** Mustaqil Normativ Audit va Standartlar Muvofiqligi Ekspertizasi  
**Sana:** 2026-10-24  
**Auditor:** Independent Technical Standards & Compliance Auditor  
**Holat:** Final Verified / Ratified Standards Baseline  

---

## 1. KIRISH VA AUDITNING MAQSADI

Oldingi audit bosqichlarida (Phase 3 va Phase 4 / 4.1) bir qator xalqaro standartlar (WCAG 2.2, OWASP ASVS, OWASP Top 10 for LLM) bo'yicha havolalar va muvofiqlik darajalari (conformance levels) tahlil qilingan edi. Biroq, Phase 4.1 tekshiruvlarida ayrim me'yoriy chalkashliklar, xususan:
1. WCAG 2.2 SC 2.4.7 ning muvofiqlik darajasi (Level A deb xato ko'rsatilgani);
2. OWASP ASVS versiyasi (hali rasman chiqarilmagan ASVS v5.0.0 loyihasi bilan v4.0.3 production relizi o'rtasidagi chalkashlik);
3. ASVS v4.0.3 bandlarining (V14.5.3, V13.1.4, V13.2.3) aniq talab doirasi;
4. WCAG SC 1.3.1, 2.1.2 va 4.1.2 ning desktop webview arxitekturasidagi Misa ilovasiga haqiqiy tatbiqi bo'yicha noaniqliklar aniqlandi.

Ushbu hisobot rasmiy tashkilotlar (W3C va OWASP) hujjatlari asosida barcha normativ talablarni to'liq tekshiradi va qat'iy standart bazasini o'rnatadi.

---

## 2. WCAG 2.2 RASMIY STANDARTLARI TEKSHIRUVI

Rasmiy W3C Recommendation (Published 05 October 2023):  
URL: https://www.w3.org/TR/WCAG22/

### 2.1. Success Criterion 2.4.7 Focus Visible
- **Rasmiy W3C Matni:**  
  > *"Any keyboard operable interface has a mode of operation where the keyboard focus indicator is visible."*
- **Rasmiy Muvofiqlik Darajasi (Level):** **Level AA**  
  *(Izoh: WCAG 2.0 va WCAG 2.1 da ham SC 2.4.7 Level AA bo'lgan; WCAG 2.2 da uning darajasi Level AA bo'lib saqlanib qolgan).*
- **Phase 4.1 da yo'l qo'yilgan xato:** Phase 4.1 hisobotida SC 2.4.7 xato ravishda "Level A ga tushirilgan/o'tkazilgan" deb yozilgan edi. Bu da'vo **NOTO'G'RI**. WCAG 2.2 da yangi qo'shilgan mezon bu **SC 2.4.11 Focus Not Obscured (Minimum)** (Level AA), **SC 2.4.12 Focus Not Obscured (Enhanced)** (Level AAA) va **SC 2.4.13 Focus Appearance** (Level AAA). SC 2.4.7 esa qat'iy **Level AA** bo'lib qoladi.
- **Misa loyihasiga tatbiqi:**  
  Misa UI (`App.css`, `index.css`) global `*:focus { outline: none; }` yoki `outline: 0;` qoidasiga ega. Foydalanuvchi klaviatura (Tab) orqali yurganda aktiv elementda hech qanday vizual ko'rsatkich hosil bo'lmaydi. Bu holat **WCAG 2.2 SC 2.4.7 (Level AA)** qoidasining bevosita buzilishi hisoblanadi.
- **Rasmiy Havola:** https://www.w3.org/TR/WCAG22/#focus-visible

### 2.2. Success Criterion 2.4.3 Focus Order
- **Rasmiy W3C Matni:**  
  > *"If a Web page can be navigated sequentially and the navigation sequences affect meaning or operation, focusable components receive focus in an order that preserves meaning and operability."*
- **Rasmiy Muvofiqlik Darajasi (Level):** **Level A**
- **Oldingi hisobotlardagi bahosi:** To'g'ri (Level A).
- **Misa loyihasiga tatbiqi:**  
  Misa'da Chat, Settings, Analytics modal yoki panel oynalari ochilganda, klaviatura fokusi yangi ochilgan konteynerga avtomatik ko'chirilmaydi (`focus trap` va `initial focus management` yo'q). Foydalanuvchi Tab bosganda fokus fonda ko'rinmaydigan asosiy oyna elementlari bo'ylab tartibsiz kezadi. Bu **WCAG 2.2 SC 2.4.3 (Level A)** buzilishidir.
- **Rasmiy Havola:** https://www.w3.org/TR/WCAG22/#focus-order

### 2.3. Success Criterion 1.3.1 Info and Relationships
- **Rasmiy W3C Matni:**  
  > *"Information, structure, and relationships conveyed through presentation can be programmatically determined or are available in text."*
- **Rasmiy Muvofiqlik Darajasi (Level):** **Level A**
- **Misa loyihasiga tatbiqi:**  
  `index.html` va frontend komponentlarida asosiy interfeys bo'limlari `<div class="sidebar">`, `<div class="chat-container">`, `<div class="header">` kabi semantik bo'lmagan teglardan iborat. Skrinriderlar (ekran o'quvchi dasturlar) sahifa strukturasini aniqlay olmaydi (`<main>`, `<nav>`, `<aside>`, `<header>`, `role="region"`, `aria-labelledby` mavjud emas). Bu **WCAG 2.2 SC 1.3.1 (Level A)** buzilishi hisoblanadi.
- **Rasmiy Havola:** https://www.w3.org/TR/WCAG22/#info-and-relationships

### 2.4. Success Criterion 2.1.2 No Keyboard Trap
- **Rasmiy W3C Matni:**  
  > *"If keyboard focus can be moved to a component of the page using a keyboard interface, then focus can be moved away from that component using only a keyboard interface, and, if it requires more than unmodified arrow or tab keys or other standard exit methods, the user is advised of the method for moving focus away."*
- **Rasmiy Muvofiqlik Darajasi (Level):** **Level A**
- **Misa loyihasiga tatbiqi:**  
  Misa'da klaviatura biror elementda qamalib qolmaydi (hech qanday element klaviatura hodisalarini yutib yubormaydi). Ammo modal ochilganda fokus modal ichida saqlanmasdan orqa fonga chiqib ketadi (`lack of focus containment`). Bu "Keyboard Trap" (qopqon) emas, balki **Focus Management / Focus Order** muammosidir. Shuning uchun Misa'da SC 2.1.2 qoidasi bevosita buzilmagan; bu yerda haqiqiy qoidabuzarlik **SC 2.4.3** ga tegishlidir.
- **Rasmiy Havola:** https://www.w3.org/TR/WCAG22/#no-keyboard-trap

### 2.5. Success Criterion 4.1.2 Name, Role, Value
- **Rasmiy W3C Matni:**  
  > *"For all user interface components (including but not limited to: form elements, links and components generated by scripts), the name and role can be programmatically determined; states, properties, and values that can be set by the user can be programmatically set; and notification of changes to these items is available to user agents, including assistive technologies."*
- **Rasmiy Muvofiqlik Darajasi (Level):** **Level A**
- **Misa loyihasiga tatbiqi:**  
  Misa interfeysidagi ko'plab interaktiv tugmalar (masalan, mikrofoni yoqish, ovozni to'xtatish, sozlamalarni ochish, tozalash tugmalari) faqat SVG ikonkalar bilan ifodalangan bo'lib, ularda `aria-label`, `aria-labelledby`, yoki `title` atributlari mavjud emas. Skrinriderlar bu tugmalarni faqat "button" deb o'qiydi, ularning vazifasi (Name/Value) aniqlanmaydi. Bu **WCAG 2.2 SC 4.1.2 (Level A)** ning yaqqol buzilishidir.
- **Rasmiy Havola:** https://www.w3.org/TR/WCAG22/#name-role-value

### 2.6. Success Criterion 2.5.8 Target Size (Minimum)
- **Rasmiy W3C Matni:**  
  > *"The size of the target for pointer inputs is at least 24 by 24 CSS pixels, except where: Spacing (24px target diameter), Equivalent, Inline, User Agent Control, or Essential."*
- **Rasmiy Muvofiqlik Darajasi (Level):** **Level AA** (WCAG 2.2 da yangi kiritilgan).
- **Misa loyihasiga tatbiqi:**  
  Misa'dagi ba'zi yordamchi tugmalar va xabarni nusxalash/o'chirish ikonkalari 16x16 px yoki 18x18 px o'lchamga ega bo'lib, atrofida 24 px gacha bo'lgan kompensatsiya masofasi (`padding` yoki `margin spacing`) ta'minlanmagan. Bu **WCAG 2.2 SC 2.5.8 (Level AA)** talabiga zid.

---

## 3. OWASP APPLICATION SECURITY VERIFICATION STANDARD (ASVS) TEKSHIRUVI

### 3.1. ASVS Versiyalari va Nashr Holati
- **Amaldagi Rasmiy Production Reliz:** **OWASP ASVS v4.0.3** (Nashr sanasi: Oktyabr 2020).  
  Rasmiy Havola: https://owasp.org/www-project-application-security-verification-standard/
- **ASVS v5.0.0 Holati:**  
  ASVS 5.0.0 hozirda OWASP loyihasi tomonidan GitHub omborida (`OWASP/ASVS` main branch) ishlab chiqilayotgan **hamjamiyat loyihasi (Draft/Under Development)** hisoblanadi. U hali rasman release qilinmagan va normativ standart sifatida qabul qilinmagan.
- **Audit xulosasi:** Barcha rasmiy xavfsizlik audit xulosalari va me'yoriy taqqoslashlar faqat **OWASP ASVS v4.0.3** rasmiy reliziga tayanishi shart. ASVS 5.0.0 faqat axborot sifatida tilga olinishi mumkin, ammo qat'iy standart talabi sifatida ko'rsatilishi noto'g'ri.

### 3.2. ASVS v4.0.3 Bandlarining Aniq Mazmuni

#### A. ASVS v4.0.3 — V14.5.3 (CORS Siyosati)
- **Rasmiy ASVS v4.0.3 Matni:**  
  > *"Verify that the Cross-Origin Resource Sharing (CORS) Access-Control-Allow-Origin header only allows trusted origins, and does not allow null or the wildcard (*) origin for sensitive resources or endpoints requiring authentication."*
- **CWE Bog'liqligi:** CWE-346 (Origin Validation Error).
- **Muvofiqlik Darajalari:** Level 1, Level 2, Level 3.
- **Misa'dagi Holat (`MISA-ROOT-001`):**  
  `Misa/src/misa/misa_engine.py` (va FastAPI backend konfiguratsiyasida) `CORSMiddleware` quyidagicha sozlangan:
  ```python
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
  ```
  `allow_origins=["*"]` bilan birga `127.0.0.1:8000` portida autentifikatsiyasiz (`Bearer token` yoki `API key`siz) `/execute`, `/cmd`, `/voice/synthesize` API endpointlari ochiq qoldirilgan. Bu holat **ASVS v4.0.3 V14.5.3** talabini to'liq buzadi.

#### B. ASVS v4.0.3 — V13.1.4 (API Autentifikatsiyasi va Resurs Ruxsati)
- **Rasmiy ASVS v4.0.3 Matni:**  
  > *"Verify that authorization checks are performed on every access to a protected resource or API, including cached or previously authorized assets."*
- **CWE Bog'liqligi:** CWE-285 (Improper Authorization).
- **Muvofiqlik Darajalari:** Level 1, Level 2, Level 3.
- **Misa'dagi Holat (`MISA-ROOT-001`):**  
  FastAPI serverida barcha boshqaruv va tizim amallari (`/cmd`, `/task`, `/config`) uchun hech qanday `Depends(verify_token)` yoki sessiya nazorati yo'q. Istalgan mahalliy jarayon yoki brauzerdan yuborilgan so'rov to'g'ridan-to'g'ri qabul qilinadi. Bu **ASVS v4.0.3 V13.1.4** buzilishidir.

#### C. ASVS v4.0.3 — V13.2.3 (REST xizmatlarida CSRF va Tranzaksiya Boshqaruvi)
- **Rasmiy ASVS v4.0.3 Matni:**  
  > *"Verify that the application protects against Cross-Site Request Forgery (CSRF) on state-changing API endpoints, or that the application uses anti-CSRF tokens, or that cross-origin resource sharing (CORS) is configured to prevent cross-origin access."*
- **CWE Bog'liqligi:** CWE-352 (Cross-Site Request Forgery).
- **Misa'dagi Holat:**  
  Foydalanuvchi brauzerda zararli veb-saytni ochganda, u yerdagi JavaScript brauzerdan `fetch('http://127.0.0.1:8000/cmd', { method: 'POST', body: ... })` so'rovini yuborishi mumkin. Brauzer Private Network Access (PNA) cheklovlari bo'lmasa, `allow_origins=["*"]` tufayli CORS bloklamaydi va mahalliy Misa serveri buyruqni bajaradi. Bu **ASVS v4.0.3 V13.2.3** buzilishidir.

---

## 4. OWASP TOP 10 FOR LLM APPLICATIONS (2025) TEKSHIRUVI

Rasmiy OWASP Standarti:  
URL: https://genai.owasp.org/llm-top-10/

### 4.1. LLM06: Excessive Agency (Haddan Tashqari Vakolat)
- **Rasmiy Mazmuni:**  
  LLM agentiga tizim ustidan haddan tashqari ko'p vakolat (funksiyalar, buyruqlar, fayl yozish/o'chirish) berilishi va muhim harakatlar oldidan inson tasdig'i (Human-in-the-Loop) bo'lmasligi yoki zaif bo'lishi natijasida tizimning butunlay komprometatsiya qilinishi xavfi.
- **Misa'dagi Holat (`MISA-ROOT-004`, `MISA-ROOT-006`):**  
  - `Misa/src/misa/misa_engine.py` va `tools.py` da PowerShell buyruqlari to'g'ridan-to'g'ri `subprocess.Popen(["powershell.exe", "-Command", cmd])` orqali sanitizatsiyasiz chaqiriladi.
  - Agent qaror qabul qilganda, backendda buyruqni bevosita bajaruvchi API mavjud va bu API frontend UI tasdiq dialogini butunlay chetlab o'tib bajarilishi mumkin.
  - Bu holat **OWASP LLM 2025 LLM06: Excessive Agency** xavfining klassik va tasdiqlangan namunasidir.

---

## 5. OLDINGI HISOBOTLARDA XATO KELTIRILGAN BANDLARNING SOLISHTIRMA JADVALI

Quyidagi jadval oldingi audit hisobotlarida normativ standartlar bo'yicha keltirilgan da'volarning qaysi qismi to'g'ri va qaysi qismi xato bo'lganligini aniq ko'rsatadi:

| Standart / Band | Oldingi Da'vo (Phase 3 / 4.1) | To'g'ri Qismi | Xato / Noto'g'ri Qismi | Qat'iy Haqiqat (Phase 4.2 Verifikatsiyasi) | Rasmiy Manba URL |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **WCAG 2.2 SC 2.4.7** | "SC 2.4.7 Focus Visible WCAG 2.2 da Level A ga aylandi" | Misa'da fokus ko'rinmasligi qoidabuzarlik ekanligi to'g'ri. | SC 2.4.7 Level A ga tushmagan. U **Level AA** bo'lib qolgan. | WCAG 2.2 da SC 2.4.7 qat'iy **Level AA**. Focus Visible hech qachon Level A bo'lmagan. | [W3C WCAG 2.2 SC 2.4.7](https://www.w3.org/TR/WCAG22/#focus-visible) |
| **WCAG 2.2 SC 2.4.3** | "Focus Order Level A mezonidir" | Misa'da modal ochilganda fokus tartibsizlanadi; mezon **Level A**. | Hech qanday xato yo'q, to'g'ri keltirilgan. | SC 2.4.3 qat'iy **Level A**. Misa bu mezonni buzadi. | [W3C WCAG 2.2 SC 2.4.3](https://www.w3.org/TR/WCAG22/#focus-order) |
| **OWASP ASVS 5.0.0** | "ASVS 5.0.0 talablariga muvofiq V14.5.3 buzilgan" | CORS bo'yicha zaiflik mavjudligi va talab buzilganligi to'g'ri. | ASVS 5.0.0 rasmiy reliz emas, balki qoralama (draft). Bandlar 4.0.3 ga tegishli. | Rasmiy ishlab chiqarish standarti — **ASVS v4.0.3**. V14.5.3 aynan v4.0.3 relizining bandi. | [OWASP ASVS Project](https://owasp.org/www-project-application-security-verification-standard/) |
| **WCAG 2.2 SC 2.1.2** | "Misa modallarida klaviatura qopqoni (Keyboard Trap) mavjud" | Modallarda fokus noto'g'ri ishlayotgani to'g'ri. | Misa'da klaviatura qamalib qolmaydi, aksincha orqa fonga chiqib ketadi. | Bu SC 2.1.2 emas, balki **SC 2.4.3 (Focus Order)** va umumiy focus containment muammosi. | [W3C WCAG 2.2 SC 2.1.2](https://www.w3.org/TR/WCAG22/#no-keyboard-trap) |
| **WCAG 2.2 SC 2.5.8** | "Target size talabi 44x44 px (Level AAA)" | Elementlar kichik ekanligi to'g'ri. | WCAG 2.2 Level AA me'yori 44 emas, balki **24x24 CSS px** (5 ta istisno bilan). | SC 2.5.8 (Level AA) minimal 24x24 px talab qiladi. 44x44 px esa SC 2.5.5 (Level AAA) talabidir. | [W3C WCAG 2.2 SC 2.5.8](https://www.w3.org/TR/WCAG22/#target-size-minimum) |

---

## 6. XULOSA VA KEYINGI BOSQICH UCHUN TAVSIYALAR

1. Barcha keyingi hisobotlar va tuzatish rejalarida WCAG 2.2 talablari qat'iy ravishda:
   - **Level A:** SC 1.3.1 (Info and Relationships), SC 2.4.3 (Focus Order), SC 4.1.2 (Name, Role, Value);
   - **Level AA:** SC 2.4.7 (Focus Visible), SC 2.5.8 (Target Size Minimum);
   deb ko'rsatilishi shart.
2. Xavfsizlik bo'yicha barcha normativ dalillar **OWASP ASVS v4.0.3** (V14.5.3, V13.1.4, V13.2.3) va **OWASP Top 10 for LLM (2025)** (LLM06) ga asoslanishi tasdiqlandi.
3. Loyihadagi ushbu standartlarga oid xatolar bartaraf etildi va normativ ziddiyatlar yopildi.
