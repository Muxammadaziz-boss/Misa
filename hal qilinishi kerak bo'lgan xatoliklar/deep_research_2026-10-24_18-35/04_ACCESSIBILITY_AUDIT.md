# EKSPERT 04 — ACCESSIBILITY & INCLUSIVE DESIGN AUDIT REPORT
**Loyiha:** Misa Desktop AI Assistant (v9.0.0 / v9.3)  
**Sana:** 2026-10-24  
**Auditor:** Ekspert 04 — Accessibility & Inclusive Design Specialist  
**Standartlar:** W3C WCAG 2.2 (Level A & AA), W3C WAI-ARIA Authoring Practices Guide (APG) 1.2, Microsoft Accessibility Guidelines for Windows Applications  
**Holat:** Yakunlandi (Read-Only Deep Inspection)

---

## 1. MAVZU VA QAMROV

Ushbu audit Misa desktop interfeysining imkoniyati cheklangan, faqat klaviaturadan foydalanuvchi, ko‘rish qobiliyati zaiflashgan yoki screen reader (ekran o‘quvchi dasturlar: Windows Narrator, NVDA, JAWS) orqali ishlovchi foydalanuvchilar uchun qulaylik darajasini baholaydi.

WCAG 2.2 ning to‘rtta asosiy ustuni bo‘yicha chuqur tahlil o‘tkazildi:
1. **Perceivable (Idrok etiladigan):** Kontrast, masshtab, matnli alternativlar, vizual indikatorlar.
2. **Operable (Boshqariladigan):** Klaviatura orqali to‘liq boshqaruv, fokus indikatorlari, fokus qopqoni (focus trap), maqsadli bosish maydoni (target size).
3. **Understandable (Tushunarli):** Formalar etiketkalari (labels), xatoliklarni aniqlash va bog‘lash.
4. **Robust (Mustahkam):** Semantik HTML, ARIA rollari va holatlari, yordamchi texnologiyalar bilan muvofiqlik.

---

## 2. TOPILMALARNING UMUMIY STATISTIKASI

| ID | Sarlavha | WCAG 2.2 Mezoni | Jiddiylik | Ishonchlilik | Joylashuv |
|---|---|---|---|---|---|
| **A11Y-001** | Form Inputlarida Dasturiy Label (`htmlFor`/`id`) Yo‘qligi | SC 1.3.1 (A), SC 4.1.2 (A) | **High** | Confirmed | `AuthPage.tsx` |
| **A11Y-002** | Command Palette ARIA Combobox Semantikasi Yo‘qligi | SC 2.1.1 (A), SC 4.1.2 (A) | **High** | Confirmed | `CommandPalette.tsx` |
| **A11Y-003** | Modallarda Fokus Qopqoni (Focus Trap) va `dialog` Roli Yo‘qligi | SC 2.1.2 (A), SC 2.4.3 (A) | **Critical** | Confirmed | `UpdateModal.tsx`, `ServerDiagnosticModal.tsx` |
| **A11Y-004** | Interaktiv Tugmalarning Yetarli Bo‘lmagan Hajmi (Target Size < 44px) | SC 2.5.8 (AA) | **Medium** | Confirmed | `IconButton.tsx` |
| **A11Y-005** | Klaviatura Fokus Indikatori (`:focus-visible`) Yo‘qligi | SC 2.4.7 (A), SC 2.4.13 (AAA) | **High** | Confirmed | `Button.tsx`, `IconButton.tsx` |

---

## 3. CHUQUR DALILLANGAN TOPILMALAR

### Finding ID: A11Y-001
- **Sarlavha:** Form Inputlarida Dasturiy Label (`htmlFor` / `id`) Yo‘qligi Sababli Screen Readerlarda "Unlabeled Edit Box" Bo‘lib Qolishi
- **Kategoriya:** Accessibility & Assistive Technology
- **Jiddiylik:** High
- **Ishonchlilik:** Confirmed
- **Tekshiruv turi:** Code inspection & Accessibility Tree Analysis
- **Aniq joylashuv:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\pages\AuthPage.tsx` (Lines: 1824-1835, 1920-1932, 2131-2145, 2170-2185)
- **Dalillar:**
  ```tsx
  // AuthPage.tsx L1824-L1835:
  <div className="input-group">
    <label className="auth-label">Elektron pochta</label>
    <input
      type="email"
      value={email}
      onChange={(e) => setEmail(e.target.value)}
      placeholder="nom@domain.com"
      className="auth-input"
    />
  </div>
  ```
  `<label>` tegi mavjud, ammo uning `htmlFor` atributi yo‘q, va unga mos `<input>` elementida `id` atributi belgilanmagan. Shuningdek, `aria-label` yoki `aria-labelledby` ham ishlatilmagan.
- **Amaldagi holat:** Vizual foydalanuvchi "Elektron pochta" yozuvini input tepasida ko‘radi. Biroq, Windows Narrator yoki NVDA bilan ushbu maydonga `Tab` orqali kelganda, u: *"Edit, type in text, blank"* deb o‘qiydi. Foydalanuvchi bu maydon elektron pochta, parol yoki kod kiritish maydoni ekanini eshitmaydi.
- **Kutiladigan holat:** W3C WCAG 2.2 Success Criterion 1.3.1 (Info and Relationships) va 4.1.2 (Name, Role, Value) ga binoan har bir form maydoni dasturiy jihatdan uning tavsifiga (`<label htmlFor="auth-email">` -> `<input id="auth-email">`) mahkamlangan bo‘lishi shart.
- **Kamchilik yoki xavf:** Ko‘rish imkoniyati cheklangan foydalanuvchilar login yoki ro‘yxatdan o‘tish shakllarini to‘ldira olmaydi.
- **Foydalanuvchiga ta’sir:** Mahsulotdan ko‘rish imkoniyati cheklangan shaxslar umuman foydalana olmaydi (Digital Exclusion).
- **Root cause:** Tezkor prototiplash davrida CSS klasslari orqali vizual ko‘rinishga e’tibor berilib, semantik `htmlFor`/`id` bog‘lanishi e’tibordan chetda qolgan.
- **Tashqi manba:** 
  - W3C WCAG 2.2 SC 1.3.1 Info and Relationships (Level A): https://www.w3.org/TR/WCAG22/#info-and-relationships
  - W3C WCAG 2.2 SC 4.1.2 Name, Role, Value (Level A): https://www.w3.org/TR/WCAG22/#name-role-value
- **Tavsiya:** Har bir input uchun unikal identifikator yaratish va `<label htmlFor={uniqueId}>` orqali bog‘lash yoki `aria-label="Elektron pochta"` atributini qo‘shish.
- **Qabul mezoni:** Windows Narrator yoki NVDA yoqilganda har bir inputga o‘tishda uning nomi va vazifasi ("Elektron pochta, matn kiritish maydoni") to‘liq ovozda o‘qilishi.
- **Cheklovlar:** Barcha 10 ta tab va modal formalar kod orqali tekshirildi; real NVDA audio chiqishi emulyatorda tekshirilmadi.

---

### Finding ID: A11Y-002
- **Sarlavha:** Command Palette Qidiruvida W3C ARIA Combobox / Listbox Semantikasi Yo‘qligi
- **Kategoriya:** Accessible Keyboard Interaction & Semantics
- **Jiddiylik:** High
- **Ishonchlilik:** Confirmed
- **Tekshiruv turi:** Code inspection & APG Pattern Mapping
- **Aniq joylashuv:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\components\CommandPalette.tsx` (Lines: 275-350)
- **Dalillar:**
  ```tsx
  // CommandPalette.tsx L275-L295:
  <input
    ref={inputRef}
    type="text"
    value={query}
    onChange={(e) => setQuery(e.target.value)}
    placeholder="Buyruqni kiriting yoki qidiring..."
    className="palette-input"
  />
  <div className="palette-results">
    {filteredCommands.map((cmd, idx) => (
      <div
        key={cmd.id}
        className={`palette-item ${idx === selectedIndex ? 'selected' : ''}`}
        onClick={() => execute(cmd)}
      >
        {cmd.title}
      </div>
    ))}
  </div>
  ```
- **Amaldagi holat:** `input` oddiy `type="text"`, ro‘yxat esa oddiy `<div>` konteynerlaridan iborat. Klaviaturada strelkalar (`ArrowUp`/`ArrowDown`) bosilganda `selectedIndex` React state orqali o‘zgaradi va elementga `.selected` klassi qo‘shiladi, ammo fokus inputda qoladi. Natijada screen reader foydalanuvchiga hech qanday ma’lumot bermaydi.
- **Kutiladigan holat:** W3C WAI-ARIA Authoring Practices Guide (APG) "Combobox Pattern" talabiga muvofiq:
  - Input: `role="combobox"`, `aria-autocomplete="list"`, `aria-expanded="true"`, `aria-controls="cmd-listbox"`, `aria-activedescendant={selectedItemId}`.
  - Ro‘yxat konteyneri: `id="cmd-listbox"`, `role="listbox"`.
  - Har bir element: `id={cmdId}`, `role="option"`, `aria-selected={idx === selectedIndex}`.
- **Kamchilik yoki xavf:** Screen reader foydalanuvchisi strelka tugmalarini bosganda qaysi buyruq tanlangani, ro‘yxatda nechta natija borligi va nima sodir bo‘layotganidan bexabar qoladi.
- **Foydalanuvchiga ta’sir:** Klaviatura va screen reader foydalanuvchilari tezkor navigatsiya (Command Palette) imkoniyatidan foydalana olmaydi.
- **Root cause:** WAI-ARIA combobox standartini bilmaslik yoki oddiy UI komponent sifatida yaratish.
- **Tashqi manba:** W3C WAI-ARIA Authoring Practices Guide: Combobox Pattern: https://www.w3.org/WAI/ARIA/apg/patterns/combobox/
- **Tavsiya:** Standart ARIA combobox atributlarini qo‘shish va `aria-activedescendant` orqali faol elementni screen readerga e’lon qilish.
- **Qabul mezoni:** Strelka tugmalari bosilganda screen reader avtomatik ravishda tanlangan komandani ("Mavzuni o‘zgartirish, 2 dan 8") o‘qib berishi.
- **Cheklovlar:** Faqat kod semantikasi tahlil qilindi.

---

### Finding ID: A11Y-003
- **Sarlavha:** Modallarda Fokus Qopqoni (Focus Trap) va `role="dialog"` Bo‘lmagani Sababli Klaviaturaning Fon Elementlariga O‘tib Ketishi
- **Kategoriya:** Focus Management & Modal Accessibility
- **Jiddiylik:** Critical
- **Ishonchlilik:** Confirmed
- **Tekshiruv turi:** Code inspection
- **Aniq joylashuv:** 
  - `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\components\UpdateModal.tsx` (Lines: 60-120)
  - `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\components\ServerDiagnosticModal.tsx` (Lines: 40-95)
- **Dalillar:**
  ```tsx
  // UpdateModal.tsx L60-L75:
  <div className="update-modal-backdrop">
    <div className="update-modal-card">
      <h3>Yangi versiya mavjud</h3>
      ...
      <button onClick={onUpdate}>Yangilash</button>
      <button onClick={onClose}>Bekor qilish</button>
    </div>
  </div>
  ```
- **Amaldagi holat:** Modal ochilganda:
  1. Fokus modal ichidagi birinchi interaktiv elementga avtomatik ko‘chirilmaydi.
  2. Foydalanuvchi `Tab` tugmasini bosganda, fokus modal orqasidagi fon sahifasidagi tugmalar va inputlarga o‘tib ketadi (Focus Leak).
  3. Konteynerda `role="dialog"` va `aria-modal="true"` atributlari yo‘q.
  4. `Escape` tugmasi bosilganda modal yopilishi uchun global key listener belgilanmagan.
- **Kutiladigan holat:** W3C WCAG 2.2 SC 2.1.2 (No Keyboard Trap) va SC 2.4.3 (Focus Order) hamda APG Dialog Modal tamoyiliga ko‘ra, modal ochilganda:
  - Fon elementlari `inert` yoki `aria-hidden="true"` qilinishi kerak.
  - Fokus modal ichida aylanma harakat qilishi (focus trap: oxirgi elementdan birinchisiga o‘tishi) lozim.
  - `Escape` bosilganda modal yopilib, fokus modalni ochgan elementga qaytishi kerak.
- **Kamchilik yoki xavf:** Ko‘rish imkoniyati cheklangan yoki faqat klaviaturadan foydalanuvchi modal ochilganini sezmay, fon bilan muloqotni davom ettiradi va kutilmagan amallarni bajarib qo‘yishi mumkin.
- **Foydalanuvchiga ta’sir:** Dastur boshqaruvida chalkashlik, muhim yangilanishlar yoki xatolik dialoglaridan chiqib ketolmaslik.
- **Root cause:** Dialog oynalari uchun maxsus `FocusTrap` utility komponenti yaratilmaganligi.
- **Tashqi manba:**
  - W3C WCAG 2.2 SC 2.1.2 No Keyboard Trap: https://www.w3.org/TR/WCAG22/#no-keyboard-trap
  - W3C WAI-ARIA APG Dialog (Modal) Pattern: https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/
- **Tavsiya:** React Focus Trap (masalan, `focus-trap-react` yoki native `keydown` sikli) implementatsiyasini qo‘shish, `role="dialog"`, `aria-modal="true"`, `aria-labelledby` atributlarini o‘rnatish.
- **Qabul mezoni:** Modal ochilganda `Tab` faqat modal tugmalari orasida aylanib yurishi, fondagi elementlarga fokus tushmasligi, `Escape` bosilganda yopilishi.
- **Cheklovlar:** Barcha 4 ta modal oynasi kod bo‘yicha tekshirildi.

---

### Finding ID: A11Y-004
- **Sarlavha:** Interaktiv Tugmalarning Bosish Maydoni Standartdan Kichikligi (Target Size < 44px)
- **Kategoriya:** Target Size & Motor Accessibility
- **Jiddiylik:** Medium
- **Ishonchlilik:** Confirmed
- **Tekshiruv turi:** Code inspection & CSS Geometry Calculation
- **Aniq joylashuv:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\components\ui\IconButton.tsx` (Lines: 15-35)
- **Dalillar:**
  ```tsx
  // IconButton.tsx L20-L28:
  width: '34px',
  height: '34px',
  borderRadius: '50%',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 0
  ```
- **Amaldagi holat:** Yuqori paneldagi barcha yordamchi tugmalar (sozlamalar, tozalash, yopish, minimallashtirish) qat’iy `34px x 34px` o‘lchamda belgilangan.
- **Kutiladigan holat:** WCAG 2.2 Success Criterion 2.5.8 Target Size (Minimum) (Level AA) talabiga binoan, sensorli ekranlar va harakat imkoniyati cheklangan foydalanuvchilar (tremor, falajlik, kattaroq kursorlar) uchun har bir interaktiv nishon kamida 24x24px (va tavsiya etiladigan optimal daraja bo‘yicha kamida 44x44px maydonga ega bo‘lishi yoki atrofida 10px margin/padding buferi bo‘lishi) kerak.
- **Kamchilik yoki xavf:** Kichik tugmalarni sichqoncha bilan aniq bosish harakatida adashish, nishondan chetga bosib yuborish.
- **Foydalanuvchiga ta’sir:** Motorik zaifligi bor foydalanuvchilar uchun qiyinchilik tug‘diradi.
- **Root cause:** Desktop interfeyslarda faqat optik ixchamlikka intilish.
- **Tashqi manba:** W3C WCAG 2.2 SC 2.5.8 Target Size (Minimum): https://www.w3.org/TR/WCAG22/#target-size-minimum
- **Tavsiya:** Tugma ko‘rinishini 34px saqlagan holda ham, uning `click target` maydonini pseudo-element (`::after` inset -5px) orqali kamida 44x44px ga kengaytirish.
- **Qabul mezoni:** Bosish maydoni (bounding box) kamida 44x44px bo‘lishi.
- **Cheklovlar:** Sensorli ekranda jismoniy barmoq bosishi o‘lchanmadi.

---

### Finding ID: A11Y-005
- **Sarlavha:** Maxsus Tugmalar va Linklarda Vizual Klaviatura Fokus Indikatori (`:focus-visible`) Mutlaqo Yo‘qligi
- **Kategoriya:** Visual Focus & Operability
- **Jiddiylik:** High
- **Ishonchlilik:** Confirmed
- **Tekshiruv turi:** Code inspection & CSS token review
- **Aniq joylashuv:** 
  - `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\components\ui\Button.tsx` (Lines: 25-60)
  - `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\components\ui\IconButton.tsx` (Lines: 20-40)
  - `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\styles\tokens.css`
- **Dalillar:**
  ```tsx
  // Button.tsx va IconButton.tsx inline stillarida:
  outline: 'none',
  // tokens.css ichida esa :focus yoki :focus-visible qoidalari ta'riflanmagan
  ```
- **Amaldagi holat:** Barcha maxsus tugmalarda brauzerning standart fokus doirasi `outline: none` orqali o‘chirib tashlangan, ammo uning o‘rniga hech qanday alternativ `:focus-visible` ko‘rsatkichi (masalan, 2px yorqin hoshiya) qo‘yilmagan.
- **Kutiladigan holat:** WCAG 2.2 SC 2.4.7 Focus Visible (Level A) va SC 2.4.13 Focus Appearance (Level AAA) talablariga binoan, klaviatura orqali `Tab` bosilganda qaysi element aktiv ekani ko‘z bilan 100% aniq ko‘rinib turishi shart.
- **Kamchilik yoki xavf:** Klaviaturadan foydalanuvchi `Tab` tugmasini bosganda ekrandagi qaysi tugmada turganini ko‘ra olmaydi ("ko‘r navigatsiya").
- **Foydalanuvchiga ta’sir:** Faqat klaviatura bilan ishlovchi shaxs dasturda adashib qoladi va qaysi buyruqni faollashtirayotganini bila olmaydi.
- **Root cause:** Ko‘pchilik frontend dasturchilarining brauzer "ko‘k hoshiyasi"ni estetik jihatdan yoqimsiz deb bilib, `outline: none` qilish odati.
- **Tashqi manba:**
  - W3C WCAG 2.2 SC 2.4.7 Focus Visible: https://www.w3.org/TR/WCAG22/#focus-visible
  - W3C WCAG 2.2 SC 2.4.13 Focus Appearance: https://www.w3.org/TR/WCAG22/#focus-appearance
- **Tavsiya:** Global CSS qoidasi sifatida `:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }` joriy qilish.
- **Qabul mezoni:** `Tab` bosilganda har bir faol element atrofida kamida 3:1 kontrastli yorqin ko‘k/binafsha hoshiya paydo bo‘lishi.
- **Cheklovlar:** Faqat desktop klaviatura tekshiruviga asoslangan.

---

## 4. XULOSA VA KEYINGI QADAMLAR
Misa vizual jihatdan zamonaviy ko‘rinsa-da, qulaylik (Accessibility) arxitekturasi deyarli noldan qurilishi kerak. Hozirgi holatida dastur WCAG 2.2 Level AA sertifikatsiyasidan o‘ta olmaydi. 
Eng ustuvor qadamlar:
1. `UpdateModal` va dialog oynalariga fokus qopqoni o‘rnatish.
2. Global `:focus-visible` uslubini kiritish.
3. Barcha form inputlarini semantik `<label htmlFor>` bilan bog‘lash.
