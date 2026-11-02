# MISA V9 — SECURITY AUDIT: PRIVACY & DATA GOVERNANCE REPORT
**Loyiha:** Misa Desktop AI Assistant (v9.0.0 / v9.3)  
**Audit Davri:** 2026-10-24  
**Auditor:** Principal Privacy Engineer & Data Governance Auditor  
**Katalog:** `hal qilinishi kerak bo'lgan xatoliklar\security_deep_audit_2026-10-24_18-14\`  
**Standartlar:** NIST Privacy Framework (CSWP 029), GDPR Principles (Art. 5, 12, 17), ISO/IEC 27701 Privacy Information Management  
**Holat:** Yakunlandi (Read-Only Deep Inspection)

---

## 1. IJROCHI XULOSA

Maxfiylik auditi Misa tizimida foydalanuvchi ma’lumotlarining (ovoz, suhbatlar, oyna nomlari, klipbord, jarayonlar) qanday yig‘ilishi, qayta ishlanishi, saqlanishi va uchinchi tomonlarga uzatilishini o‘rgandi.

Asosiy muammo — **Hujjatlardagi va'dalar bilan haqiqiy kod implementatsiyasi o‘rtasidagi nomuvofiqlik**:
- Marketing va chiqarilish eslatmalarida Misa "To‘liq mahalliy va shaxsiy (Zero-Leak Local Privacy)" deb ta’riflangan.
- Biroq kod tahlili ko‘rsatishicha, audio oqimi Google Cloud Web Speech API ga yuboriladi, chat so‘rovlari esa uchinchi tomon bulut provayderlariga (Gemini, OpenRouter, Groq) tranzit qilinadi, bu haqda esa interfeysda shaffof ogohlantirish yo‘q.

---

## 2. PRIVACY TOPILMALAR STATISTIKASI

| ID | Sarlavha | Maxfiylik Standarti | Jiddiylik | Ishonchlilik | Fayl va Joylashuv |
|---|---|---|---|---|---|
| **PRIV-001** | Google Web Speech API ga Yashirin Audio Tranziti | NIST Privacy CT.PO-P | **High** | Confirmed | `core/audio_service.py:185-205` |
| **PRIV-002** | Ochiq Hujjatlar va Oyna Nomlarining Doimiy Telemetriya Logiga Yozilishi | NIST Privacy CT.DP-P | **High** | Confirmed | `core/logger.py:45-80` |
| **PRIV-003** | Bulutdagi Sinxronlangan Ma’lumotlarni To‘liq O‘chirish (Right to be Forgotten) Yo‘qligi | GDPR Art. 17, NIST PR.PO-P | **Medium** | Confirmed | `core/v8/user_linking.py:65-95` |
| **PRIV-004** | AI Provayderlariga Ma’lumot Uzatilishi Haqida Foydalanuvchi Beparvoligi | NIST Privacy CM.AW-P | **Medium** | Confirmed | `Misa/src/pages/ChatPage.tsx:110-140` |

---

## 3. CHUQUR DALILLANGAN TOPILMALAR

### Finding ID: PRIV-001
- **Sarlavha:** Foydalanuvchi Ovozli Yozuvlarining Ogohlantirishsiz Google Cloud Web Speech API ga Yuborilishi ("Zero-Leak" Ziddiyati)
- **Xavfsizlik kategoriyasi:** Privacy / Data Flow Discrepancy & Third-Party Telemetry
- **Severity:** High
- **Confidence:** Confirmed
- **Fayl va qator raqami:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\core\audio_service.py` (Lines: 185-205)
- **Dalil va tegishli kod yo‘li:**
  ```python
  # core/audio_service.py L192-L198:
  try:
      # Offline vosita ishlamasa yoki tanlanmagan bo'lsa:
      text = recognizer.recognize_google(audio_data, language="uz-UZ")
  except sr.RequestError as e:
      logger.warning(f"Google STT so'rovida xatolik: {e}")
  ```
- **Muammoning yuzaga kelish shartlari:** Ovozli buyruq kiritilganda mahalliy model yuklanmagan bo‘lsa yoki standart fallback ishga tushganda, foydalanuvchining mikrofondan yozilgan ovozli baytlari to‘g‘ridan-to‘g‘ri Google serverlariga uzatiladi.
- **Ta’sir va ehtimoliy zarar:** Foydalanuvchi barcha ovozli suhbatlar faqat kompyuter ichida tahlil qilinmoqda deb ishonadi. Biroq uning xonadondagi shaxsiy suhbatlari, nozik parollar yoki suhbat parchalari Google tarmog‘iga yuboriladi. Bu korporativ xavfsizlik va shaxsiy daxlsizlik talablarini buzadi.
- **Root cause:** O‘zbek tili uchun mahalliy offline STT (Whisper) modelini yuklash qiyinligi tufayli eng oson yechim sifatida Google Web Speech API fallback qilib qo‘yilgan, ammo bu interfeysda shaffof ko‘rsatilmagan.
- **Tegishli rasmiy standart yoki hujjat:**
  - NIST Privacy Framework (CSWP 029): CT.PO-P (Data Processing Transparency)
  - GDPR 5-modda (Qonuniylik, haqqoniylik va shaffoflik)
- **Tavsiya qilinadigan himoya yo‘nalishi:** Sozlamalar menyusida "Ovozni aniqlash rejimi: [To'liq Offline / Mahalliy] yoki [Google Cloud STT]" tanlovini majburiy qilish va Google yoqilganda alohida opt-in rozilik so‘rash.
- **Kelajakdagi tekshiruv uchun qabul mezoni:** Foydalanuvchi aniq ruxsat bermagan taqdirda hech qanday audio baytlari tashqi IP-manzillarga chiqmasligi.
- **Cheklovlar va tekshirilmagan jihatlar:** Kod tahlili orqali tasdiqlandi.

---

### Finding ID: PRIV-002
- **Sarlavha:** Foydalanuvchining Shaxsiy Hujjatlari Sarlavhalari va Oyna Nomlarining Sanitsiyasiz Lokal Loglarga Yozilishi
- **Xavfsizlik kategoriyasi:** Privacy / Unredacted Telemetry & Data Minimization
- **Severity:** High
- **Confidence:** Confirmed
- **Fayl va qator raqami:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\core\logger.py` (Lines: 45-80) va `core/proactive_watcher.py`
- **Dalil va tegishli kod yo‘li:**
  ```python
  # core/logger.py:
  logger.info(f"Foydalanuvchi faol oynasi: {active_window_title}")
  # Masalan: "Shaxsiy_Hisobot_2026_Parollar.docx - Word" ochiq matnda log fayliga tushadi!
  ```
- **Muammoning yuzaga kelish shartlari:** Misa fonda ishlab turganda uning `proactive_watcher` yoki tizim logeri ochiq turgan dastur va hujjatlarning to‘liq sarlavhasini `%LOCALAPPDATA%\MisaAI\` dagi log fayllariga yozadi.
- **Ta’sir va ehtimoliy zarar:** Agar foydalanuvchi shaxsiy bank hujjati, tibbiy fayl yoki maxfiy loyiha ustida ishlayotgan bo‘lsa, ushbu fayllarning nomlari va shaxsiy ma’lumotlar doimiy log fayllarida qoladi. Keyinchalik foydalanuvchi "Diagnostika hisobotini yuborish" tugmasini bossa, ushbu nozik ma’lumotlar tashqariga chiqishi mumkin.
- **Root cause:** Telemetriyada Ma’lumotlarni Minimallashtirish (Data Minimization) va shaxsiy ma’lumotlarni niqoblash (Redaction) tamoyillariga e’tibor berilmagan.
- **Tegishli rasmiy standart yoki hujjat:**
  - NIST Privacy Framework: CT.DP-P (Data Protection & Privacy Disclosures)
  - GDPR 5(1)(c) moddasi (Ma’lumotlarni minimallashtirish)
- **Tavsiya qilinadigan himoya yo‘nalishi:** Loglarga yozishdan oldin oyna nomlaridagi fayl yo‘llari va kengaytmalarini faqat ilova nomi bilan cheklash (masalan: `"Microsoft Word"`, aniq fayl nomisiz).
- **Kelajakdagi tekshiruv uchun qabul mezoni:** Log fayllarida shaxsiy fayl nomlari yoki yo‘llari uchramasligi.
- **Cheklovlar va tekshirilmagan jihatlar:** Log mexanizmi kod orqali tekshirildi.

---

### Finding ID: PRIV-003
- **Sarlavha:** Supabase Bulut Bazasi va Mahalliy Xotirada Foydalanuvchi Ma’lumotlarini To‘liq O‘chirish (Right to be Forgotten) Mexanizmining Chala Ekanligi
- **Xavfsizlik kategoriyasi:** Privacy / Data Subject Rights & Data Retention
- **Severity:** Medium
- **Confidence:** Confirmed
- **Fayl va qator raqami:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\core\v8\user_linking.py` (Lines: 65-95)
- **Dalil va tegishli kod yo‘li:**
  `user_linking.py` da foydalanuvchi akkauntini bog‘lash va qurilmalarni ro‘yxatdan o‘tkazish funksiyalari mavjud, biroq `delete_user_data` yoki akkauntni to‘liq yo‘q qilish (Right to be Forgotten) endpointi Supabase jadvallaridagi (`user_devices`, `ai_keys`, `conversations`) bog‘liq yozuvlarni to‘liq kaskadli o‘chirmaydi.
- **Muammoning yuzaga kelish shartlari:** Foydalanuvchi dasturdan o‘z akkauntini o‘chirmoqchi bo‘lganda, ma’lumotlar bulutda qoldiq (orphan records) holida qoladi.
- **Ta’sir va ehtimoliy zarar:** Foydalanuvchi o‘z ma’lumotlari butunlay yo‘q qilindi deb hisoblaydi, biroq uning tarixiy yozuvlari ma’lumotlar bazasida saqlanib qolaveradi.
- **Root cause:** Dasturni yaratishda faqat ma’lumotlarni yozish va saqlashga e’tibor berilgan, ma’lumotlarning hayot sikli (Data Lifecycle Management) oxiriga yetkazilmagan.
- **Tegishli rasmiy standart yoki hujjat:**
  - GDPR 17-modda (Right to Erasure / Unutish huquqi)
  - NIST Privacy Framework: PR.PO-P (Privacy Governance & Data Lifecycle)
- **Tavsiya qilinadigan himoya yo‘nalishi:** Barcha tegishli jadvallar va mahalliy ChromaDB xotirasini bitta atomik tranzaksiya bilan to‘liq tozalovchi `Purge Account & Data` funksiyasini joriy qilish.
- **Kelajakdagi tekshiruv uchun qabul mezoni:** O‘chirish amali bajarilgandan so‘ng Supabase va diskda foydalanuvchiga tegishli 0 ta bayt ma’lumot qolishi.
- **Cheklovlar va tekshirilmagan jihatlar:** Baza sxemasi tahlili orqali tekshirildi.

---

### Finding ID: PRIV-004
- **Sarlavha:** AI Provayderlariga Ma’lumot Yuborilishi Bo‘yicha UI Darajasida Shaffoflikning Yetishmasligi
- **Xavfsizlik kategoriyasi:** Privacy / User Awareness & Consent
- **Severity:** Medium
- **Confidence:** Confirmed
- **Fayl va qator raqami:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\pages\ChatPage.tsx` (Lines: 110-140)
- **Dalil va tegishli kod yo‘li:**
  Foydalanuvchi xabar yozayotgan paytda chat oynasida joriy so‘rov qaysi modelga va qaysi davlatdagi serverga (Google US, Groq US, OpenRouter) ketayotgani haqida hech qanday vizual indikator yo‘q.
- **Muammoning yuzaga kelish shartlari:** Foydalanuvchi Misa'ga juda nozik shaxsiy yoki moliyaviy savollarni yozganda, uning xabari uchinchi tomon AI provayderi API siga chiqishini bilmay qoladi.
- **Ta’sir va ehtimoliy zarar:** Nozik ma’lumotlarning bexosdan uchinchi tomon sun’iy intellekt provayderlariga yuborilishi.
- **Root cause:** UI interfeysida model holati va ma’lumotlar tranziti indikatorining qo‘yilmagani.
- **Tegishli rasmiy standart yoki hujjat:**
  - NIST Privacy Framework: CM.AW-P (User Awareness and Controls)
- **Tavsiya qilinadigan himoya yo‘nalishi:** Input maydoni yonida har doim faol provayder nomini ko‘rsatib turuvchi belgi (masalan: `[🔒 Lokal Whisper / ☁️ Gemini Cloud]`) joylashtirish.
- **Kelajakdagi tekshiruv uchun qabul mezoni:** Foydalanuvchi o‘z so‘rovi qayerda qayta ishlanishini har doim ko‘rib turishi.
- **Cheklovlar va tekshirilmagan jihatlar:** UI komponentlari tahlil qilindi.

---

## 4. XULOSA
Misa'da maxfiylikni to‘g‘rilash uchun birinchi navbatda Google Web Speech API chaqiruvini sozlamalarda to‘liq oshkor qilish va oyna nomlari telemetriyasini tozalash lozim.
