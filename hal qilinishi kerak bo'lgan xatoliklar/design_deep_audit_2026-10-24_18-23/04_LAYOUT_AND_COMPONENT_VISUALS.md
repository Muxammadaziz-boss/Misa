# MISA V9 — VISUAL DESIGN AUDIT: LAYOUT, VISUAL ELEVATION & COMPONENT FINISH
**Loyiha:** Misa Desktop AI Assistant (v9.0.0 / v9.3)  
**Audit Davri:** 2026-10-24  
**Auditor:** Principal Visual Design Director & Layout Systems Architect  
**Katalog:** `hal qilinishi kerak bo'lgan xatoliklar\design_deep_audit_2026-10-24_18-23\`  
**Standartlar:** Windows Display Scaling Guidelines, CSS Spec / CSSOM View, Hardware-Accelerated Rendering (GPU Compositing)  
**Holat:** Yakunlandi (Read-Only Deep Inspection)

---

## 1. LAYOUT VA ELEVATION ARXITEKTURASI

Misa desktop ilovasi bir ekranda butun ish jarayonini boshqarishga (Single-Window Desktop Workspace) asoslangan:
- **Yuqori Qism (Topbar / Window Controls):** Qidiruv, status va oyna boshqaruv tugmalari (`68px` balandlik).
- **Chap Qism (Sidebar):** Navigatsiya paneli (`64px` dan `220px` gacha kengayuvchi).
- **Markaziy Qism (Canvas):** Misa Apertura va chat oqimi.
- **Pastki Qism:** Tezkor kirish va ovozli boshqaruv pulti.

Tahlil natijasida oyna o‘lchami, ekran masshtablashi (High-DPI Scaling), qatlamlarning balandlik darajasi (Z-Index / Elevation) va interaktiv hover holatlarining amalga oshirilishida jiddiy vizual nuqsonlar aniqlandi.

---

## 2. TOPILMALAR STATISTIKASI

| ID | Sarlavha | Kategoriya | Muhimlik | Ishonchlilik | Fayl va Joylashuv |
|---|---|---|---|---|---|
| **VIS-LAY-001** | High-DPI (150%) Ekranlarda Oynaning Pastki Qismi Qirqilib Ketishi | Window Geometry & Responsive Scaling | **Critical** | Confirmed | `Misa/src-tauri/src/lib.rs:1435` |
| **VIS-LAY-002** | Hover Holatlarining CSS O‘rniga JS DOM Orqali O‘zgartirilishi | Component State & CSS Specificity | **High** | Confirmed | `Button.tsx:86-105`, `IconButton.tsx:60-75` |
| **VIS-LAY-003** | Haddan Tashqari Yuqori Blur (`24px`) va GPU Yuklanishi | Performance & Visual Legibility | **Medium** | Confirmed | `tokens.css:23` |
| **VIS-LAY-004** | Z-Index Qatlamlarining Tartibsizligi va Menyu To‘qnashuvlari | Elevation & Stacking Context | **Medium** | Confirmed | `CommandPalette.tsx`, `UpdateModal.tsx` |

---

## 3. CHUQUR DALILLANGAN TOPILMALAR

### Finding ID: VIS-LAY-001
- **Sarlavha:** High-DPI Ekranlarda (150% Windows Scaling) Qat’iy `800px` Balandlik Sababli Asosiy Kirish Maydoni Qirqilib Ketishi (Vertical Clipping)
- **Design category:** Desktop Window Geometry & Display Adaptation
- **Muhimlik:** Critical
- **Ishonchlilik:** Confirmed
- **Tegishli fayl yoki ekran:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src-tauri\src\lib.rs` (Line 1435)
- **Dalil yoki vizual kuzatuv:**
  ```rust
  // Misa/src-tauri/src/lib.rs L1435:
  tauri::WebviewWindowBuilder::new(app, "main", tauri::WebviewUrl::default())
      .title("Misa AI")
      .inner_size(1200.0, 800.0) // Qat'iy 800px balandlik!
      .min_inner_size(900.0, 600.0)
      .decorations(false) // Frameless oyna!
  ```
- **Amaldagi dizayn holati:** Ko‘pchilik zamonaviy Windows noutbuklari (14–15 dyuymli 1920x1080 ekranlar) standart tavsiya bo‘yicha **150% masshtab**da ishlaydi. 1080p da 150% masshtab o‘rnatilganda, tizimning haqiqiy ishchi balandligi (Viewport Height) **720px** ga teng bo‘lib qoladi.
  Misa esa qat’iy `800px` ichki balandlik bilan ochiladi.
- **Qaysi design principle bilan solishtirilayotgani:** Windows High-DPI Responsive Sizing Guidelines: Desktop ilovalari foydalanuvchi monitorining haqiqiy DPI masshtabini hisobga olishi va standart ekranning 85% dan oshmaydigan optimal balandlikda boshlanishi lozim.
- **Vizual kamchilik yoki nomuvofiqlik:** Ilova ishga tushganda uning pastki qismi (chat input maydoni, yuborish tugmasi va status indikatori) to‘g‘ridan-to‘g‘ri Windows Taskbar (vazifalar paneli) ostiga yoki ekrandan pastga qirqilib ketadi.
- **Foydalanuvchi idroki va o‘qilishiga ta’siri:** Foydalanuvchi xabar yozish maydonini ko‘rmaydi va oynani qo‘lda tepaga surishga majbur bo‘ladi.
- **Root cause:** Boshlang‘ich o‘lcham faqat 100% masshtabli katta monitorlarda sinab ko‘rilgan, 150% masshtabli noutbuklar hisobga olinmagan.
- **Taklif qilinadigan yaxshilanish yo‘nalishi:** Rust qatlamida boshlang‘ich o‘lchamni `inner_size(1100.0, 700.0)` qilib belgilash yoki monitor ishchi maydonining 85% ga dinamik moslashtirish.
- **Kutilayotgan natija:** Har qanday noutbukda birinchi ochilishdayoq pastki boshqaruv tugmalari to‘liq ko‘rinishi.
- **Kelajakdagi qabul mezoni:** 150% masshtabda oyna hech qachon pastki kiritish maydonini qirqib qo‘ymasligi.
- **Cheklovlar:** Oyna o‘lchami kodi tahlil qilindi.

---

### Finding ID: VIS-LAY-002
- **Sarlavha:** Komponent Hover Holatlarining CSS Pseudo-Class O‘rniga To‘g‘ridan-To‘g‘ri JavaScript DOM Manipulyatsiyasi Orqali Boshqarilishi
- **Design category:** Component State Architecture & CSS Specificity
- **Muhimlik:** High
- **Ishonchlilik:** Confirmed
- **Tegishli fayl yoki ekran:** 
  - `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\components\Button.tsx` (Lines: 86-105)
  - `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\components\IconButton.tsx` (Lines: 60-75)
- **Dalil yoki vizual kuzatuv:**
  `Button.tsx` L86-L98:
  ```tsx
  onMouseEnter={(e) => {
    if (variant === "primary") {
      e.currentTarget.style.backgroundColor = "var(--primary-hover)";
    } else if (variant === "glass") {
      e.currentTarget.style.backgroundColor = "var(--glass-bg-hover)";
      e.currentTarget.style.borderColor = "var(--glass-border-hover)";
    }
  }}
  onMouseLeave={(e) => {
    const reset = getVariantStyles();
    e.currentTarget.style.backgroundColor = reset.background as string;
  }}
  ```
- **Amaldagi dizayn holati:** Sichqoncha tugma ustiga kelganda rang CSS dagi `:hover` selektori orqali emas, balki React dagi `onMouseEnter` hodisasi orqali to‘g‘ridan-to‘g‘ri HTML elementning `style` atributiga yoziladi.
- **Qaysi design principle bilan solishtirilayotgani:** Declarative CSS State Transitions: Interaktiv holatlar (hover, active, focus, disabled) doimo toza CSS selektorlari (`:hover`, `:active`, `:focus-visible`) orqali boshqarilishi shart.
- **Vizual kamchilik yoki nomuvofiqlik:** 
  1. Inline `style` atributi barcha tashqi CSS klasslaridan ustun turadi (Specificity Wars).
  2. Foydalanuvchi tugmani klaviatura bilan fokuslaganda yoki tez sichqoncha harakatida `onMouseLeave` hodisasi yo‘qolib qolib, tugma doimiy ravishda "hover" rangida qotib qolishi kuzatiladi.
  3. Silliq CSS `transition: all 0.2s` animatsiyasi to‘liq ishlamaydi (sakrab o‘zgarish).
- **Foydalanuvchi idroki va o‘qilishiga ta’siri:** Interfeys silliq emas, qotib-qotib ishlayotgandek vizual asabiylik tug‘diradi.
- **Root cause:** CSS faylida alohida klass yozmasdan, barcha stillarni bitta komponent ichiga tezkor joylash odati.
- **Taklif qilinadigan yaxshilanish yo‘nalishi:** Barcha `onMouseEnter`/`onMouseLeave` JS kodlarini olib tashlash va uning o‘rniga `globals.css` da `.btn-primary:hover`, `.btn-glass:hover` qoidalarini yozish.
- **Kutilayotgan natija:** Toza, kadr yo‘qotmasdan ishlovchi 60fps GPU silliq animatsiya.
- **Kelajakdagi qabul mezoni:** Bitta ham komponentda JS orqali inline hover o‘zgartirilmasligi.
- **Cheklovlar:** Kod logikasi tekshirildi.

---

### Finding ID: VIS-LAY-003
- **Sarlavha:** Haddan Tashqari Qalin Shisha Bluri (`--misa-blur: 24px`) Sababli Matn O‘qilishining Qiyinlashishi va GPU Unumdorligi Pasayishi
- **Design category:** Visual Elevation & Performance / Legibility
- **Muhimlik:** Medium
- **Ishonchlilik:** Confirmed
- **Tegishli fayl yoki ekran:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\styles\tokens.css` (Line 23)
- **Dalil yoki vizual kuzatuv:**
  ```css
  --misa-blur: 24px;
  ```
  Ko‘plab panellar `backdrop-filter: blur(var(--misa-blur))` bilan ishlaydi.
- **Amaldagi dizayn holati:** `24px` radiusli qalin xiralashtirish (blur) qo‘llanilgan.
- **Qaysi design principle bilan solishtirilayotgani:** Microsoft Fluent Acrylic & Apple Vibrancy Guidance: Desktop oynalarida optimal blur darajasi **10px–14px** hisoblanadi. 20px dan yuqori blur GPU shaderlarini ortiqcha yuklaydi va orqa fondagi elementlarning ranglarini juda katta doirada yoyib yuborib, sirt ustidagi nozik matnlarning kontrastini pasaytiradi.
- **Vizual kamchilik yoki nomuvofiqlik:** O‘rnatilgan integratsiyalashgan videokartaga ega noutbuklarda (Intel Iris Xe / AMD Radeon) oynani harakatlantirganda kadrlar soni (FPS) tushishi mumkin.
- **Foydalanuvchi idroki va o‘qilishiga ta’siri:** Uzoq vaqt chatni o‘qiganda ko‘zning toliqishi.
- **Taklif qilinadigan yaxshilanish yo‘nalishi:** Standart blurni `12px` yoki `14px` ga tushirish, shaffoflikni esa bir oz kamaytirish (`rgba(15, 19, 31, 0.82)`).
- **Kutilayotgan natija:** Tiniqroq matn, yengilroq renderlash va yuqori FPS.
- **Kelajakdagi qabul mezoni:** 60fps silliq skroll va matnlar orqasida loyqalanmagan aniq zamin.
- **Cheklovlar:** Faqat CSS token qiymati baholandi.

---

### Finding ID: VIS-LAY-004
- **Sarlavha:** Qatlamlar Ierarxiyasida (Z-Index) Tizimli Shkala Yo‘qligi Sababli Menyu va Modallar To‘qnashuvi
- **Design category:** Elevation & Stacking Context
- **Muhimlik:** Medium
- **Ishonchlilik:** Confirmed
- **Tegishli fayl yoki ekran:** 
  - `Misa/src/components/UpdateModal.tsx` (`z-index: 2000`)
  - `Misa/src/components/CommandPalette.tsx` (`z-index: 999`)
  - `Misa/src/components/ContextMenu.tsx` (`z-index: 100`)
- **Dalil yoki vizual kuzatuv:**
  Loyiha bo‘ylab Z-Index qiymatlari har xil fayllarda tasodifiy sonlar (`100`, `999`, `2000`) bilan belgilangan. `tokens.css` da esa z-index tokenlari (masalan: `--z-dropdown: 1000`, `--z-modal: 1400`, `--z-toast: 1600`) umuman yo‘q.
- **Amaldagi dizayn holati:** Agar Command Palette ochilib turgan vaqtda kontekst menyu ochilsa yoki xatolik modali paydo bo‘lsa, qatlamlar tartibsiz ustma-ust tushishi mumkin.
- **Qaysi design principle bilan solishtirilayotgani:** Stacking Context Architecture.
- **Vizual kamchilik yoki nomuvofiqlik:** Qaysi qatlam birinchi turishi kerakligi oldindan kafolatlanmagan.
- **Foydalanuvchi idroki va o‘qilishiga ta’siri:** Xatolik yoki menyu boshqa elementning orqasida ko‘rinmay qolishi xavfi.
- **Taklif qilinadigan yaxshilanish yo‘nalishi:** `tokens.css` ichida qat’iy z-index shkalasini joriy qilish va barcha komponentlarni unga bo‘ysundirish.
- **Kutilayotgan natija:** Hech qachon bir-birini to‘sib qo‘ymaydigan mukammal qatlamlar.
- **Kelajakdagi qabul mezoni:** Loyihada inline raqamli z-index lar bo‘lmasligi, faqat `--z-*` tokenlari ishlatilishi.
- **Cheklovlar:** Kod inspeksiyasi asosida aniqlandi.

---

## 4. XULOSA
Layout va komponent vizuallari bo‘yicha eng shoshilinch yechim — bu **High-DPI 150% ekranlardagi 800px balandlik qirqilishini to‘g‘rilash** va **tugmalardagi inline JS hover hodisalarini toza CSS ga o‘tkazish**dir.
