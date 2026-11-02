# 05 — ACCESSIBILITY & KEYBOARD USABILITY AUDIT
## MISA V9 — WCAG 2.2 Level AA & Interaction Standards Assessment

- **Audit sanasi:** 2026-10-24
- **Auditor roli:** Senior Accessibility Specialist & Principal Interaction Engineer
- **Loyiha versiyasi:** Misa v9.0.0 / v9.3
- **Baholash standartlari:** W3C Web Content Accessibility Guidelines (WCAG) 2.2 Level AA, WAI-ARIA 1.2 Authoring Practices Guide (APG), Section 508.
- **Cheklov:** Kod o'zgartirish mutlaqo taqiqlangan. Tahlil manba kodlari, komponentlar tuzilishi va desktop interfeys semantikasi asosida amalga oshirildi.

---

## 1. KIRISH VA AUDIT METODOLOGIYASI

Ushbu audit Misa desktop ilovasida (Tauri + React + TypeScript) jismoniy, sensor va motor cheklovlariga ega bo'lgan foydalanuvchilar, klaviatura orqali boshqaruvchi mutaxassislar hamda screen reader (ekran o'quvchi dasturlar — NVDA, JAWS, Windows Narrator) foydalanuvchilari uchun yaratilgan qulaylik va to'siqlarni baholaydi.

Baholash to'rtta asosiy WCAG tamoyili bo'yicha olib borildi:
1. **Perceivable (Idrok etiladigan):** Axborot va foydalanuvchi interfeysi komponentlari foydalanuvchi idrok qila oladigan tarzda taqdim etilishi kerak.
2. **Operable (Boshqariladigan):** Foydalanuvchi interfeysi komponentlari va navigatsiyasi to'liq boshqarilishi mumkin bo'lishi kerak (ayniqsa klaviatura orqali).
3. **Understandable (Tushunarli):** Axborot va foydalanuvchi interfeysi bilan ishlash mantiqiy va tushunarli bo'lishi kerak.
4. **Robust (Mustahkam):** Kontent yordamchi texnologiyalar (screen readerlar) tomonidan ishonchli talqin qilinishi kerak.

---

## 2. TOPILMALAR RO'YXATI (A11Y FINDINGS MATRIX)

| Finding ID | Sarlavha | WCAG Mezon | Severity | Confidence | Tegishli Komponent |
|---|---|---|---|---|---|
| `A11Y-UX-001` | AuthPage inputlarida dasturiy bog'langan label va ID yo'qligi | SC 1.3.1, SC 4.1.2 | High | Confirmed | [AuthPage.tsx](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/AuthPage.tsx) |
| `A11Y-UX-002` | Global `outline: none` tufayli klaviatura fokus halqasining yo'qligi | SC 2.4.7, SC 2.4.13 | Critical | Confirmed | [App.css](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/App.css#L89-L92) |
| `A11Y-UX-003` | Modal oynalarda `role="dialog"` va Focus Trap mexanizmining yo'qligi | SC 2.1.2, SC 2.4.3 | High | Confirmed | [UpdateModal.tsx](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/UpdateModal.tsx) |
| `A11Y-UX-004` | IconButton komponentida minimal nishon hajmi (Target Size) mezonining buzilishi | SC 2.5.8 | Medium | Confirmed | [IconButton.tsx](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/IconButton.tsx#L12) |
| `A11Y-UX-005` | Global Command Palette'da WAI-ARIA Combobox semantikasi va Live Region yetishmasligi | SC 4.1.2, SC 4.1.3 | High | Confirmed | [CommandPalette.tsx](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/CommandPalette.tsx) |
| `A11Y-UX-006` | Vestibulyar sezuvchanlik uchun `prefers-reduced-motion` qo'llab-quvvatlanmaganligi | SC 2.3.3 | Medium | Confirmed | [App.css](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/App.css), Inline CSS |
| `A11Y-UX-007` | Ovozli kiritish (Voice Input) paytida eshitish imkoniyati cheklanganlar uchun matnli fallback yo'qligi | SC 1.2.1, SC 1.3.3 | High | Likely | [ChatPage.tsx](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx) |

---

## 3. CHUQUR DALILLAR VA TAHLILLAR

### Finding A11Y-UX-001: AuthPage inputlarida dasturiy bog'langan label va ID yo'qligi

- **Finding ID:** `A11Y-UX-001`
- **Sarlavha:** AuthPage forma maydonlarida `<label htmlFor>` va `id` atributlari yo'qligi, screen readerlarda "Edit, blank" deb o'qilishi
- **Asosiy kategoriya:** Accessibility / Form Labeling (Semantika)
- **Severity:** High
- **Confidence:** Confirmed
- **Tegishli ekran/fayl:** [AuthPage.tsx](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/AuthPage.tsx#L1824-L1840) (qatorlar 1824–1840, 1920–1935, 2131–2145)
- **Foydalanuvchining maqsadi:** Screen reader yoki ovozli boshqaruv yordamida tizimga kirish uchun elektron pochta va parolni kiritish.
- **Amaldagi oqim:** Screen reader foydalanuvchisi Tab tugmasi bilan forma inputiga o'tadi. Inputda faqat `placeholder="elektron@pochta.uz"` mavjud, biroq `id` yoki bog'langan `<label>` mavjud emas. Label faqat vizual `div` yoki `span` sifatida input tepasida turadi.
- **Muammo va dalil:**
  ```tsx
  // AuthPage.tsx L1824-L1835:
  <div style={{ marginBottom: "16px" }}>
    <div style={{ fontSize: "12px", color: "rgba(255, 255, 255, 0.7)", marginBottom: "6px" }}>
      Elektron pochta
    </div>
    <input
      type="email"
      value={email}
      onChange={(e) => setEmail(e.target.value)}
      placeholder="elektron@pochta.uz"
      style={{ ... }}
    />
  </div>
  ```
  `input` tegida `id="auth-email"` yo'q, sarlavhada esa `<label htmlFor="auth-email">` ishlatilmagan. Shuningdek, `aria-label` yoki `aria-labelledby` ham ko'rsatilmagan.
- **Kutiladigan UX natijasi:** Screen reader maydonga fokuslanganda "Elektron pochta, matn kiritish maydoni" deb aniq e'lon qilishi kerak.
- **Foydalanuvchiga ta'siri:** Ko'zi ojiz yoki ekranni to'liq ko'ra olmaydigan foydalanuvchi qaysi maydonda turganini (pochta, parol yoki tasdiqlash kodi) bilolmaydi va ro'yxatdan o'tolmaydi.
- **Yuzaga kelish shartlari:** Har qanday screen reader (NVDA, Narrator) yoqilganda.
- **Tavsiya etilgan yaxshilanish:** Har bir `input` uchun unikal `id` berish va tegishli `<label htmlFor="...">` semantik tegidan foydalanish yoki `aria-label` bilan to'ldirish.
- **Kutiladigan foyda:** WCAG 2.2 SC 1.3.1 (Info and Relationships) va SC 4.1.2 (Name, Role, Value) talablariga to'liq mos kelish.
- **Kelajakda tekshiriladigan acceptance criteria:** NVDA yoki Windows Narrator orqali Tab bosilganda har bir inputning nomi va turi ovoz chiqarib o'qilishi.
- **Tashqi manba:** W3C WAI Web Accessibility Tutorials: Labeling Controls (https://www.w3.org/WAI/tutorials/forms/labels/).
- **Cheklovlar:** Faqat frontend React teglari atributlarini to'g'irlash kifoya, vizual dizaynga ta'sir qilmaydi.

---

### Finding A11Y-UX-002: Global `outline: none` tufayli klaviatura fokus halqasining yo'qligi

- **Finding ID:** `A11Y-UX-002`
- **Sarlavha:** `App.css` faylida global `outline: none` qo'llanilishi oqibatida klaviatura fokusining butunlay yo'qolishi
- **Asosiy kategoriya:** Keyboard Usability / Focus Visibility
- **Severity:** Critical
- **Confidence:** Confirmed
- **Tegishli ekran/fayl:** [App.css](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/App.css#L89-L92)
- **Foydalanuvchining maqsadi:** Sichqonchasiz, faqat klaviatura (Tab, Shift+Tab) orqali interfeys bo'ylab harakatlanish.
- **Amaldagi oqim:** Foydalanuvchi Tab tugmasini bosib tugmalar va inputlar bo'ylab o'tadi.
- **Muammo va dalil:**
  ```css
  /* Misa/src/App.css lines 89-92 */
  input,
  button {
    outline: none;
  }
  ```
  Global darajada `outline: none` o'rnatilgan va hech qanday `:focus-visible` o'rnini bosuvchi vizual uslub (masalan, `box-shadow` yoki kontrastli chegara) belgilanmagan. Natijada fokus qaysi tugmada yoki qaysi linkda turgani mutlaqo ko'rinmaydi.
- **Kutiladigan UX natijasi:** Foydalanuvchi Tab bosganda faol element atrofida kamida 2px qalinlikdagi, 3:1 kontrast nisbatiga ega bo'lgan aniq fokus halqasi (focus indicator) paydo bo'lishi kerak.
- **Foydalanuvchiga ta'siri:** Motorik cheklovlari bor yoki klaviaturada ishlovchi foydalanuvchilar ilovani umuman boshqara olmaydi. Hozirda qaysi amal bajarilishini bilmasdan "ko'r-ko'rona" Enter bosishga majbur bo'ladi.
- **Yuzaga kelish shartlari:** Har qanday klaviatura navigatsiyasida.
- **Tavsiya etilgan yaxshilanish:**
  ```css
  :focus-visible {
    outline: 2px solid var(--primary-glow, #C04CFD) !important;
    outline-offset: 2px !important;
  }
  ```
- **Kutiladigan foyda:** WCAG 2.2 SC 2.4.7 (Focus Visible - Level A) va SC 2.4.13 (Focus Appearance - Level AA) bajariladi.
- **Kelajakda tekshiriladigan acceptance criteria:** Ilovada faqat Tab orqali barcha tugmalar, inputlar va havolalar bosqichma-bosqich yoritilishi va ko'z bilan ko'rinishi.
- **Tashqi manba:** W3C Understanding SC 2.4.7: Focus Visible (https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html).

---

### Finding A11Y-UX-003: Modal oynalarda `role="dialog"` va Focus Trap mexanizmining yo'qligi

- **Finding ID:** `A11Y-UX-003`
- **Sarlavha:** Modal oynalarda (UpdateModal, ServerDiagnosticModal) dialog semantikasi va klaviatura fokusining ichkarida ushlanmasligi (Focus Trap yo'qligi)
- **Asosiy kategoriya:** Modal Interaction & Dialog Semantics
- **Severity:** High
- **Confidence:** Confirmed
- **Tegishli ekran/fayl:** [UpdateModal.tsx](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/UpdateModal.tsx#L140-L165), [ServerDiagnosticModal.tsx](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/ServerDiagnosticModal.tsx)
- **Foydalanuvchining maqsadi:** Yangilanish yoki diagnostika modali ochilganda faqat modal ichidagi tugmalar bilan ishlash, Escape bilan yopish yoki Tab orqali modal elementlari bo'ylab aylanib yurish.
- **Amaldagi oqim:** Modal ochiladi. Foydalanuvchi Tab tugmasini bosganda, fokus modal ichidagi tugmalardan o'tib, orqa fondagi (asosiy sahifadagi) tugmalarga o'tib ketadi.
- **Muammo va dalil:**
  1. Ikkala modalda ham `role="dialog"`, `aria-modal="true"` va `aria-labelledby` atributlari mavjud emas.
  2. Fokus trap yo'q (`focus-trap-react` yoki custom ref loop ishlatilmagan).
  3. Yopish tugmasida (L202–L218) `aria-label="Yopish"` yo'q, screen reader foydalanuvchisiga "tugma" deb noaniq xabar beriladi.
- **Kutiladigan UX natijasi:** Modal ochilganda fokus avtomatik ravishda uning ichidagi birinchi interaktiv elementga o'tishi va Tab bosilganda modal ichida aylanib turishi kerak (focus containment).
- **Foydalanuvchiga ta'siri:** Foydalanuvchi modal ochilganini sezmasdan orqa fondagi chat yoki sozlamalar tugmalarini bosib yuborishi mumkin.
- **Yuzaga kelish shartlari:** Yangilanish xabarnomasi yoki xatolik modal dialogi chiqqanda.
- **Tavsiya etilgan yaxshilanish:** Modal konteyneriga `role="dialog"`, `aria-modal="true"`, `aria-labelledby="modal-title"` qo'shish va `focus-trap` logikasini joriy etish.
- **Kutiladigan foyda:** WCAG SC 2.1.2 (No Keyboard Trap) va SC 2.4.3 (Focus Order) ta'minlanadi.
- **Tashqi manba:** W3C WAI-ARIA APG: Dialog (Modal) Pattern (https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/).

---

### Finding A11Y-UX-004: IconButton komponentida minimal nishon hajmi (Target Size) mezonining buzilishi

- **Finding ID:** `A11Y-UX-004`
- **Sarlavha:** `IconButton` komponentida default hajm 34x34px bo'lib, mobil va sensorli ekranlar uchun 44x44px/48x48px tavsiyasiga mos kelmasligi
- **Asosiy kategoriya:** Touch & Pointer Usability / Target Size
- **Severity:** Medium
- **Confidence:** Confirmed
- **Tegishli ekran/fayl:** [IconButton.tsx](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/IconButton.tsx#L12)
- **Foydalanuvchining maqsadi:** Sensorli ekranda (Surface Pro, Windows 2-in-1 noutbuklar) yoki noaniq sichqoncha bilan tugmani adashmasdan bosish.
- **Amaldagi oqim:** Foydalanuvchi chat panelidagi nusxa olish, ovozli yozish yoki tozalash tugmasini bosmoqchi bo'ladi.
- **Muammo va dalil:**
  ```tsx
  export const IconButton: React.FC<IconButtonProps> = ({
    size = 34,
    ...
  }) => {
    ...
    style={{
      width: `${size}px`,
      height: `${size}px`,
  ```
  Default hajm 34px qilib belgilangan. Bir-biriga yaqin joylashgan ikkita 34px tugma oralig'i ham 4-6px bo'lib, qo'l tekkanda qo'shni tugma bosilib ketish ehtimoli yuqori.
- **Kutiladigan UX natijasi:** Har qanday interaktiv boshqaruv elementi kamida 44x44 CSS piksel maydonga ega bo'lishi yoki atrofida yetarli bo'shliq (margin/padding) bo'lishi kerak.
- **Foydalanuvchiga ta'siri:** Titroq qo'l, tremor yoki planshet rejimida ishlayotgan foydalanuvchilar noto'g'ri tugmani bosib, amalni bekor qilib yuborishi mumkin.
- **Yuzaga kelish shartlari:** Sensorli ekran yoki past aniqlikdagi trekpad ishlatilganda.
- **Tavsiya etilgan yaxshilanish:** `IconButton` vizual hajmi 34px bo'lsa ham, uning `hit-target` maydonini `padding` yoki psevdo-element (`::after`) orqali kamida 44x44px ga kengaytirish.
- **Kutiladigan foyda:** WCAG 2.2 SC 2.5.8 (Target Size - Minimum) talablariga moslashish.
- **Tashqi manba:** W3C WCAG 2.2 Success Criterion 2.5.8 Target Size (Minimum) (https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).

---

### Finding A11Y-UX-005: Global Command Palette'da WAI-ARIA Combobox semantikasi va Live Region yetishmasligi

- **Finding ID:** `A11Y-UX-005`
- **Sarlavha:** `CommandPalette.tsx` komponentida WAI-ARIA Combobox / Listbox semantikasi yo'qligi sababli natijalar screen readerda e'lon qilinmasligi
- **Asosiy kategoriya:** Accessible Rich Internet Applications (ARIA)
- **Severity:** High
- **Confidence:** Confirmed
- **Tegishli ekran/fayl:** [CommandPalette.tsx](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/CommandPalette.tsx#L332-L440)
- **Foydalanuvchining maqsadi:** Ctrl+K orqali tezkor buyruqlar menyusini ochish, qidiruv natijalarini ko'rish va klaviatura bilan buyruqni tanlash.
- **Amaldagi oqim:** Foydalanuvchi qidiruv maydoniga yozadi va Up/Down strelkalari bilan harakatlanadi.
- **Muammo va dalil:**
  1. Qidiruv inputida `role="combobox"`, `aria-autocomplete="list"`, `aria-expanded="true"`, `aria-controls="palette-results"` va `aria-activedescendant` atributlari yo'q.
  2. Natijalar konteynerida `role="listbox"` yo'q.
  3. Har bir natija qatorida `role="option"` va `aria-selected={isSelected}` yo'q.
  4. Natijalar soni (masalan, "7 ta buyruq topildi") haqida `aria-live="polite"` xabari mavjud emas.
- **Kutiladigan UX natijasi:** Strelka pastga bosilganda, ekran o'quvchi dastur tanlangan buyruq nomini, kategoriyasini va "1/7" tartib raqamini ovoz chiqarib aytishi kerak.
- **Foydalanuvchiga ta'siri:** Screen reader foydalanuvchilari uchun Ctrl+K palitrasi butunlay "ko'r" qora qutiga aylanadi; ular qaysi buyruq tanlanganini eshita olmaydi.
- **Yuzaga kelish shartlari:** Ctrl+K ochilganda.
- **Tavsiya etilgan yaxshilanish:** W3C APG Combobox patternini to'liq joriy etish.
- **Kutiladigan foyda:** WCAG 2.2 SC 4.1.2 (Name, Role, Value) va SC 4.1.3 (Status Messages) mezonlariga moslik.
- **Tashqi manba:** WAI-ARIA Authoring Practices: Combobox Pattern (https://www.w3.org/WAI/ARIA/apg/patterns/combobox/).

---

### Finding A11Y-UX-006: Vestibulyar sezuvchanlik uchun `prefers-reduced-motion` qo'llab-quvvatlanmaganligi

- **Finding ID:** `A11Y-UX-006`
- **Sarlavha:** Tizimning "Harakatni kamaytirish" (Reduce Motion) sozlamasi inobatga olinmaganligi, animatsiyalar to'xtatilmasligi
- **Asosiy kategoriya:** Visual Accessibility / Vestibular Motion Disorders
- **Severity:** Medium
- **Confidence:** Confirmed
- **Tegishli ekran/fayl:** [App.css](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/App.css), [Button.tsx](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/components/Button.tsx#L81)
- **Foydalanuvchining maqsadi:** Bosh aylanishi, kinetoz yoki vestibulyar buzilishlarga ega foydalanuvchining Windows sozlamalarida "Turn off animations" ni yoqqanida Misa'dagi barcha o'tishlar va suzuvchi animatsiyalarning statik bo'lishi.
- **Amaldagi oqim:** Windows parametrlarida animatsiyalar o'chirilgan bo'lsa ham, Misa interfeysi `transition: all 0.18s ease`, `keyframes` va spinning spinnerlarni to'xtovsiz aylantiradi.
- **Muammo va dalil:** CSS fayllarida `@media (prefers-reduced-motion: reduce)` qoidasi umuman yozilmagan.
- **Kutiladigan UX natijasi:** Foydalanuvchi tizimida "Reduce Motion" yoqilgan bo'lsa, barcha animatsiyalar `transition: none` va `animation: none` holatiga o'tishi kerak.
- **Foydalanuvchiga ta'siri:** Kinetoz yoki kognitiv toliqishdan aziyat chekuvchi insonlarda diskomfort va charchoq yuzaga keladi.
- **Yuzaga kelish shartlari:** Windows Accessibility sozlamalarida animatsiyalar o'chirilgan muhitda.
- **Tavsiya etilgan yaxshilanish:**
  ```css
  @media (prefers-reduced-motion: reduce) {
    *, ::before, ::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }
  ```
- **Kutiladigan foyda:** WCAG 2.2 SC 2.3.3 (Animation from Interactions) bajariladi.
- **Tashqi manba:** MDN Web Docs: prefers-reduced-motion (https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion).

---

### Finding A11Y-UX-007: Ovozli kiritish (Voice Input) paytida eshitish imkoniyati cheklanganlar uchun matnli fallback yo'qligi

- **Finding ID:** `A11Y-UX-007`
- **Sarlavha:** Ovozli muloqot rejimida jonli transkripsiya va audio holati uchun ko'rgazmali (visual) indikatsiya yetarli emasligi
- **Asosiy kategoriya:** Multimodal Accessibility & Sensory Substitution
- **Severity:** High
- **Confidence:** Likely
- **Tegishli ekran/fayl:** [ChatPage.tsx](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx), [audio_service.py](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/backend/services/audio_service.py)
- **Foydalanuvchining maqsadi:** Eshitishida nuqsoni bor foydalanuvchi mikrofon orqali gapirganda yoki Misa ovoz chiqarib javob berganda nima aytilayotganini ekranda so'zma-so'z o'qishi.
- **Amaldagi oqim:** Mikrofon yoqilganda faqat bitta statik/pulsatsiyalanuvchi doira ko'rinadi. Mikrofon qanday ovoz olayotgani, foydalanuvchining aytgan gapi qanday tushunilayotgani jonli matn sifatida ko'rsatilmaydi; faqat butun STT yakunlangachgina bitta blok matn paydo bo'ladi.
- **Muammo va dalil:** Audio yozish va TTS javobi paytida eshitish imkoniyati past insonlar uchun vizual tovush to'lqini (decibel meter) va jonli so'zma-so'z matn (live captioning) oqimi yo'q.
- **Kutiladigan UX natijasi:** Ovoz yozilayotganda STT real vaqt rejimida qisman olingan matnni ("eshitilmoqda: ...") va TTS o'qiyotganda qaysi jumla talaffuz qilinayotganini vizual tarzda ko'rsatishi lozim.
- **Foydalanuvchiga ta'siri:** Eshitish qobiliyati past foydalanuvchilar ovozli rejimda ilova ularni eshitayotganini yoki ovoz tugaganini bilolmaydi.
- **Yuzaga kelish shartlari:** Ovozli rejim (Voice Mode) yoqilganda.
- **Tavsiya etilgan yaxshilanish:** Ovozli rejimda doimiy vizual to'lqin shakli (waveform) va real-vaqtli matnli subtitr (live captions) panelini joriy qilish.
- **Kutiladigan foyda:** WCAG 2.2 SC 1.2.1 (Audio-only) va SC 1.3.3 (Sensory Characteristics) ga muvofiqlik.
- **Tashqi manba:** W3C Captions and Subtitles Accessibility Principles (https://www.w3.org/WAI/media/av/captions/).

---

## 4. ACCESSIBILITY BO'YICHA XULOSA VA TAVSIYALAR

Misa v9.0.0 interfeysi vizual jihatdan zamonaviy ultra-glass estetikasiga ega bo'lsa-da, yordamchi texnologiyalar (assistive technology) va qat'iy accessibility mezonlari bo'yicha jiddiy to'siqlarga ega.

**Asosiy qizil chiziqlar:**
1. `App.css` dagi `outline: none` klaviatura foydalanuvchilarini to'liq ko'r holatga keltiradi — bu birinchi navbatda tuzatilishi shart bo'lgan eng xavfli to'siqdir.
2. Form inputlarida semantik `<label>` va `id` larning yo'qligi screen readerlar orqali avtorizatsiyadan o'tish imkonini yo'qqa chiqaradi.
3. Dialog va modal oynalarda Focus Trap yo'qligi foydalanuvchini adashtiradi.

Ushbu muammolarni bartaraf etish Misa'ni nafaqat maxsus ehtiyojli insonlar, balki klaviatura orqali tez ishlaydigan barcha professional foydalanuvchilar uchun ancha qulay va samarali vositaga aylantiradi.
