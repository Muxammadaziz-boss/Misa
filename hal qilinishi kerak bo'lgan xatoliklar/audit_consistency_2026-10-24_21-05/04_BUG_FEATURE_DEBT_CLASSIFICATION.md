# 04 — DEFECT, SECURITY, FEATURE GAP & TECHNICAL DEBT CLASSIFICATION
## MISA V9 — Master Topilmalarning Aniq Muhandislik Tasnifi

- **Audit Turi:** Engineering Taxonomy & Defect Categorization (Phase 4.1)
- **Sana:** 2026-10-24
- **Auditor Roli:** Principal Systems Architect & Engineering Auditor
- **Qamrov:** Barcha 32 ta Master Root Cause.
- **Qat'iy Qoida:** 100% READ-ONLY. Hech qanday kod o'zgartirilmadi.

---

## 1. MUHANDISLIK TASNIFI PRINSIPLARI

Oldingi hisobotlarda loyihaning har qanday kamchiligi — xoh arxitektura og'irligi bo'lsin, xoh kichik vizual tavsiya — bir xilda "Bug" yoki "Xatolik" deb atalgan. Bu esa loyiha rahbariyati va muhandislar jamoasida noto'g'ri taassurot uyg'otadi.

Ushbu hisobot har bir muammoni uning haqiqiy muhandislik mohiyatiga ko'ra quyidagi 6 ta qat'iy toifaga ajratadi:

1. **`SECURITY_RISK` (Xavfsizlik Zaifligi):** Tizimga ruxsatsiz kirish, buyruq inyeksiyasi yoki maxfiy ma'lumotlar sizishiga sabab bo'luvchi zaiflik.
2. **`CONFIRMED_DEFECT` (Haqiqiy Dasturiy Xatolik / Bug):** Mavjud kodning funksional talabni buzishi, qulashi yoki standartlarga zid ishlashi.
3. **`FEATURE_GAP` (Funksional Yetishmovchilik):** Dasturda bo'lishi kerak bo'lgan, ammo hali ishlab chiqilmagan yangi imkoniyat.
4. **`TECHNICAL_DEBT` (Texnik Qarz):** Dastur ishiga to'sqinlik qilmaydigan, biroq kodni saqlash va rivojlantirishni qiyinlashtiruvchi arxitektura og'irligi.
5. **`UX_RECOMMENDATION` (Foydalanish Qulayligi Tavsiyasi):** Dastur xatosi bo'lmagan, lekin foydalanuvchi qoniqishini oshiruvchi ergonomik taklif.
6. **`UNVERIFIED_CLAIM` (Isbotlanmagan Faraz):** Empirik test yoki telemetriya loglari mavjud bo'lmagan da'vo.

---

## 2. 32 TA MASTER MUAMMONING TASNIF JADVALI

| Master ID | Canonical Sarlavha | Toifasi (Classification) | Jiddiylik | Nega Bu Toifaga Kiritildi? |
|---|---|---|---|---|
| **`MISA-ROOT-001`** | Port 18420 dagi auth bypass va CORS `*` | **`SECURITY_RISK`** | **Critical** | RCE va brauzer orqali ruxsatsiz buyruq berish xavfi (ASVS V14.5.3). |
| **`MISA-ROOT-002`** | NSIS Installerda `_internal` yo'qligi | **`CONFIRMED_DEFECT`** | **Critical** | Yangi kompyuterda ilova birinchi soniyadayoq qulaydi (Packaging bug). |
| **`MISA-ROOT-003`** | `ShellExecuteW` da URL protokol tekshiruvi yo'qligi | **`SECURITY_RISK`** | **Critical** | URL orqali ixtiyoriy `.exe` yoki `.bat` ishga tushirish (RCE / CWE-20). |
| **`MISA-ROOT-004`** | `open_app` da PowerShell argument inyeksiyasi | **`SECURITY_RISK`** | **Critical** | f-string qo'shtirnoq orqali OS buyrug'i bajarish (CWE-78). |
| **`MISA-ROOT-005`** | API kalitlarning ochiq JSON da saqlanishi | **`SECURITY_RISK`** | **Critical** | Shaxsiy API kalitlarning o'g'irlanishi (CWE-312). |
| **`MISA-ROOT-006`** | Destruktiv amallarda frontend HITL dialogi yo'qligi | **`SECURITY_RISK`** | **Critical** | AI agent tomonidan fayllarni ruxsatsiz yo'q qilish xavfi (OWASP LLM06). |
| **`MISA-ROOT-007`** | Rust `lib.rs` nomzodlarida `v9.3` yo'qligi | **`CONFIRMED_DEFECT`** | **High** | Yangi backend o'rniga eski v9.2 ishga tushadi (Binar yuklash xatosi). |
| **`MISA-ROOT-008`** | Global `outline: none` (fokus yo'qolishi) | **`CONFIRMED_DEFECT`** | **High** | WCAG 2.2 SC 2.4.7 (Level A) me'yoriy standartini to'g'ridan-to'g'ri buzadi. |
| **`MISA-ROOT-009`** | AuthPage inputlarida `<label>` va `id` yo'qligi | **`CONFIRMED_DEFECT`** | **High** | WCAG 2.2 SC 1.3.1 (Level A) me'yoriy standartini buzadi. |
| **`MISA-ROOT-010`** | Modallarda `role="dialog"` va focus trap yo'qligi | **`CONFIRMED_DEFECT`** | **High** | WCAG 2.2 SC 2.1.2 (Level A) me'yoriy standartini buzadi. |
| **`MISA-ROOT-011`** | High-DPI 150% da 800px oyna qirqilishi | **`CONFIRMED_DEFECT`** | **High** | Chat maydoni vazifalar paneli ostida qoladi (Layout bug). |
| **`MISA-ROOT-012`** | Generatsiyani to'xtatuvchi `[Stop]` tugmasi yo'qligi | **`FEATURE_GAP`** | **High** | Dasturda to'xtatish imkoniyati hali yaratilmagan (Kerakli funksiya). |
| **`MISA-ROOT-013`** | Agent topshiriq rejasining yashirinligi | **`FEATURE_GAP`** | **High** | Step-by-step akordeon vidjeti hali frontendda ishlab chiqilmagan. |
| **`MISA-ROOT-014`** | Ovozli muloqotda AEC va Ducking yo'qligi | **`CONFIRMED_DEFECT`** | **High** | Misa o'z karnayidan o'zini to'xtatadi (Mantiqiy audio xatosi). |
| **`MISA-ROOT-015`** | "Salom Misa" neyron wake-word modelining yo'qligi | **`FEATURE_GAP`** | **High** | Papkada faqat README bor, model hali o'rgatilmagan/qo'yilmagan. |
| **`MISA-ROOT-016`** | Indirect Prompt Injection (Oyna sarlavhalari) | **`SECURITY_RISK`** | **High** | Filtrsiz oyna sarlavhalari AI ni manipulyatsiya qilishi mumkin (LLM01). |
| **`MISA-ROOT-017`** | Kirish formasida so'rovlar poygasi (Double-Click) | **`CONFIRMED_DEFECT`** | **High** | `isSubmitting` flagi yo'qligi sababli takroriy so'rovlar chiqadi. |
| **`MISA-ROOT-018`** | `Button.tsx` dagi arvoh tokenlar (`--glass-bg`) | **`CONFIRMED_DEFECT`** | **Medium** | Mavjud bo'lmagan CSS o'zgaruvchilari tugma fonini shaffof qilib qo'ygan. |
| **`MISA-ROOT-019`** | Yorug' mavzuda oq fonda oq yozuv qolishi | **`CONFIRMED_DEFECT`** | **Medium** | Qattiq `#FFFFFF` yozuvlar kontrastni 1.05:1 ga tushiradi (Visual bug). |
| **`MISA-ROOT-020`** | Sozlamalarning 5 ta alohida sahifaga tarqalishi | **`TECHNICAL_DEBT`** | **Medium** | Axborot arxitekturasi tarqoq, yagona markaz talab etiladi. |
| **`MISA-ROOT-021`** | Xotira va Rejalashtiruvchida bo'sh holatlar yo'qligi | **`UX_RECOMMENDATION`** | **Medium** | Bo'sh sahifada yo'l-yo'riq kartasi bo'lishi foydalanuvchiga yordam beradi. |
| **`MISA-ROOT-022`** | Boshlang'ich namunaviy Prompt chiplari yo'qligi | **`UX_RECOMMENDATION`** | **Medium** | Yangi foydalanuvchiga 4 ta namuna chip ko'rsatish tavsiya etiladi. |
| **`MISA-ROOT-023`** | SQLite xotirasida ko'p foydalanuvchili izolyatsiya | **`SECURITY_RISK`** | **Medium** | Foydalanuvchilar suhbatlari umumiy bazada saqlanadi (Privacy risk). |
| **`MISA-ROOT-024`** | Command Palette da WAI-ARIA Combobox yo'qligi | **`UX_RECOMMENDATION`** | **Medium** | Ekran o'quvchilar uchun qulaylikni oshirish (Informative APG). |
| **`MISA-ROOT-025`** | `IconButton.tsx` 34px bo'lib, 44px HIG ga mos emasligi | **`UX_RECOMMENDATION`** | **Medium** | WCAG 24px AA mezonidan o'tadi, ammo sensorli ekranlar uchun 44px tavsiya. |
| **`MISA-ROOT-026`** | Web Speech API audio trafigi ruxsatnomasi | **`SECURITY_RISK`** | **Medium** | Sozlamalarda maxfiylik haqida shaffof bildirishnoma berish zarur. |
| **`MISA-ROOT-027`** | Xotirani interfeys orqali tahrirlash imkoni yo'qligi | **`FEATURE_GAP`** | **Medium** | Xotiradagi faktlarni o'chirish / o'zgartirish vidjeti hali yo'q. |
| **`MISA-ROOT-028`** | AI Provayder nosozligida zaxira model holati | **`FEATURE_GAP`** | **Medium** | Model o'zgarganda foydalanuvchiga bildirishnoma chiqarish funksiyasi. |
| **`MISA-ROOT-029`** | Xatolik yuz berganda qayta urinish (Retry) tugmasi | **`UX_RECOMMENDATION`** | **Low** | Foydalanuvchi tajribasini oshiruvchi tugma taklifi. |
| **`MISA-ROOT-030`** | Monolit "Xudo-fayllar" (`api_server.py`, `backendService`) | **`TECHNICAL_DEBT`** | **Low** | Tizim ishlaydi, ammo kod bazasini saqlash qiyinlashgan (Refactoring). |
| **`MISA-ROOT-031`** | Ochilishda majburiy 800ms intro video | **`UX_RECOMMENDATION`** | **Low** | Foydalanuvchi xohishiga ko'ra o'chirib qo'yish imkoni berilishi lozim. |
| **`MISA-ROOT-032`** | Brend nomlarida eski `Mikasa` qoldiqlari | **`TECHNICAL_DEBT`** | **Low** | Matn va klass nomlarini tozalash (Codebase hygiene). |

---

## 3. TOIFALAR BO'YICHA STATISTIK TAQSIMOT

```
   1. CONFIRMED_DEFECT (Haqiqiy Dasturiy Xatoliklar) : 10 ta (31%)
   2. SECURITY_RISK (Xavfsizlik Zaifliklari)          : 8 ta (25%)
   3. FEATURE_GAP (Funksional Yetishmovchiliklar)     : 6 ta (19%)
   4. UX_RECOMMENDATION (Foydalanish Qulayligi)       : 5 ta (16%)
   5. TECHNICAL_DEBT (Texnik Qarz va Tozalash)        : 3 ta (9%)
   ------------------------------------------------------------------
   JAMI MASTER ROOT CAUSE                             : 32 ta (100%)
```

---

## 4. XULOSA VA MUHANDISLIK KAFOLATI

Ushbu tasnif orqali:
1. **Xavfsizlik xatarlari (`SECURITY_RISK` — 8 ta)** dasturchilar uchun birinchi guruh vazifa qilib belgilandi.
2. **Tizim qulashi va standart buzilishlari (`CONFIRMED_DEFECT` — 10 ta)** darhol tuzatilishi kerak bo'lgan ikkinchi guruhga ajratildi.
3. **Funksional yetishmovchiliklar (`FEATURE_GAP` — 6 ta)** loyiha mahsulot rejasiga (Product Backlog) kiritildi.
4. **Texnik qarz va UX tavsiyalari (`TECHNICAL_DEBT` & `UX_RECOMMENDATION` — 8 ta)** Critical bug emasligi ochiq e'lon qilinib, arxitektura va dizaynni yaxshilash bosqichiga qoldirildi.
