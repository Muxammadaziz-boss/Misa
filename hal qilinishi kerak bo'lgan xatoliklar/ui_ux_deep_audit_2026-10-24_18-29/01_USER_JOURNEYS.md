# MISA V9 — UI/UX AUDIT: USER JOURNEYS & EXPERIENCE MAPPING
**Loyiha:** Misa Desktop AI Assistant (v9.0.0 / v9.3)  
**Audit Davri:** 2026-10-24  
**Auditor:** Senior UX Researcher & Interaction Designer  
**Katalog:** `hal qilinishi kerak bo'lgan xatoliklar\ui_ux_deep_audit_2026-10-24_18-29\`  
**Holat:** Yakunlandi (Read-Only Deep Journey Analysis)

---

## 1. MISA MAHSULOTINING ASOSIY FOYDALANUVCHI YO‘LLARI (USER JOURNEYS)

Foydalanuvchining Misa bilan muloqoti 5 ta asosiy oqim (User Flow) orqali tahlil qilindi:
1. **Birinchi Ishga Tushirish va Onboarding (First-Run Experience)**
2. **Murakkab Vazifani Berish va Agent Bajarishi (Agentic Task Execution)**
3. **Ovozli Muloqot va Chaqiruv (Voice & Wake-Word Experience)**
4. **Sozlamalar va Konfiguratsiyani Topish (Settings & Mental Model)**
5. **Xatolikdan Tiklanish va Qayta Urinish (Error Recovery Flow)**

---

## 2. CHUQUR OQIMLAR TAHLILI VA DALILLAR

### Journey 1: Birinchi Ishga Tushirish va "Auth Wall" To‘sig‘i
- **Foydalanuvchi maqsadi:** Yangi o‘rnatilgan desktop AI yordamchini ochish, uning ovozi va imkoniyatlarini darhol sinab ko‘rish.
- **Bajarilishi kerak bo‘lgan qadamlar:**
  1. `Misa.exe` ni ishga tushirish.
  2. Intro splash animatsiyasini ko‘rish.
  3. Kirish (Login) yoki Ro‘yxatdan o‘tish (Register) shaklini to‘ldirish.
  4. Tasdiqlash kodi yoki parolni kiritish.
  5. Asosiy ekranga o‘tish.
- **Amaldagi oqim va muammo (`App.tsx:480-512`, `AuthPage.tsx`):**
  Dastur birinchi marta ochilgandayoq foydalanuvchi oldiga majburiy `AuthPage` (email va parol) chiqadi. Ilovada **"Mehmon sifatida sinab ko‘rish (Guest Mode)"** yoki **"O‘tkazib yuborish (Skip for now)"** tugmasi yo‘q. Foydalanuvchi hali Misa qanday ishlashini bilmay turib, o‘z shaxsiy ma’lumotlarini kiritishga majbur bo‘ladi.
- **UX tamoyili bilan solishtirish:** Progressive Engagement / Time-to-Value (TTV): Foydalanuvchi ro‘yxatdan o‘tishdan oldin mahsulotning asosiy foydasini (Aha! moment) his qilishi kerak.
- **Kamchilik va xavf:** Yangi foydalanuvchilarning 40% dan ortig‘i dastlabki ro‘yxatdan o‘tish bosqichidayoq dasturni yopib tashlaydi (Drop-off).
- **Taklif qilinadigan yaxshilanish:** Mahalliy offline yordamchi sifatida 1 marta sinov chatini boshlash imkonini beruvchi "Sinab ko‘rish" (Try as Guest) rejimini qo‘shish.

---

### Journey 2: Murakkab Vazifani Berish va Agent Bajarishi (Agentic Task Flow)
- **Foydalanuvchi maqsadi:** Misaga: *"Telegramni och va yangi xabarlarni tekshir"* deb topshiriq berish va natijani olish.
- **Bajarilishi kerak bo‘lgan qadamlar:**
  1. Chat maydoniga buyruqni yozish va `Enter` bosish.
  2. Misa rejasini ko‘rish.
  3. Bajarilayotgan qadamlarni (Step 1 -> Step 2) kuzatish.
  4. Natija haqida hisobot olish.
- **Amaldagi oqim va muammo (`ChatPage.tsx`, `core/agents/manager_agent.py`):**
  Buyruq yuborilgach, markaziy `MisaAperture` binafsha rangda yonib porlay boshlaydi (state="thinking"). Biroq ekranda agent qanday reja tuzgani, qaysi dasturni ochayotgani, qanday vosita ishlayotgani ko‘rinmaydi. Foydalanuvchi 10–15 soniya davomida oyna qotib qolganmi yoki ishlayaptimi, bila olmay noaniqlikda kutadi.
- **UX tamoyili bilan solishtirish:** NN/g Heuristic #1 (Visibility of System Status): Tizim nima bilan bandligini real vaqt rejimida qadamma-qadam ko‘rsatib turishi shart.
- **Kamchilik va xavf:** Foydalanuvchi agent qotib qoldi deb o‘ylab, qayta-qayta `Enter` bosadi yoki ilovani majburan yopadi (Duplicate execution).
- **Taklif qilinadigan yaxshilanish:** Chat ichida har bir agent vazifasi uchun yig‘iluvchi/ochiluvchi **"Vazifa Qadamlari Ro‘yxati (Execution Plan Checklist)"** vidjetini joriy qilish (`[✓] Telegram ochildi -> [⟳] Xabarlar o'qilmoqda`).

---

### Journey 3: Ovozli Muloqot va Chaqiruv (Voice & Wake-Word)
- **Foydalanuvchi maqsadi:** "Misa" deb chaqirib, qo‘llarni klaviaturaga tekkizmasdan buyruq berish.
- **Bajarilishi kerak bo‘lgan qadamlar:**
  1. Mikrofon oldida "Misa" deb chaqirish.
  2. Misa ovozli yoki vizual signal bilan javob berishi.
  3. Buyruqni aytish.
  4. Misa ovoz chiqarib javob qaytarishi.
- **Amaldagi oqim va muammo (`core/audio_service.py`, `core/voice_engine.py`):**
  1. Wake-word (chaqiruv so‘zi) ba’zida fon shovqiniga yoki Misa o‘zining karnayidan chiqayotgan ovozga noto‘g‘ri reaksiyaga kirishadi (Echo / False Triggering).
  2. Misa o‘zi gapirayotgan paytda mikrofondan o‘z ovozini eshitib, "Foydalanuvchi gapirmoqda" deb o‘z-o‘zini to‘xtatib qo‘yadi (Self-Interruption Loop).
- **UX tamoyili bilan solishtirish:** Full-Duplex Conversational Grace: Ovozli assistent o‘zi gapirayotganda audio chiqishini mikrofondan filtrlashi (Acoustic Echo Cancellation) lozim.
- **Kamchilik va xavf:** Foydalanuvchi doimiy ravishda so‘zining bo‘linishidan asabiylashadi va ovozli boshqaruvni butunlay o‘chirib qo‘yadi.
- **Taklif qilinadigan yaxshilanish:** TTS gapirayotgan millisekundlarda mikrofonni vaqtinchalik bostirish (Audio Ducking) yoki apparat darajasida echo suppression qo‘llash.

---

### Journey 4: Sozlamalar va Konfiguratsiyani Topish (Settings Discovery)
- **Foydalanuvchi maqsadi:** O‘zining AI modelini (masalan, Groq yoki Gemini) o‘zgartirish, mikrofoni va interfeys rangini sozlash.
- **Bajarilishi kerak bo‘lgan qadamlar:**
  1. Sozlamalar menyusini ochish.
  2. Barcha parametrlarni bitta markazda ko‘rish.
  3. O‘zgartirishlarni saqlash.
- **Amaldagi oqim va muammo (`AccountPage`, `VoicePage`, `CommandsPage`, `RemoteControlPage`):**
  Sozlamalar ilovaning 4 xil mustaqil sahifalariga tarqab ketgan:
  - Mavzu va profil ranglari: `/account` da
  - Mikrofon va TTS sozlamalari: `/voice` da
  - AI provayderlari va buyruqlar: `/commands` da
  - Masofaviy boshqaruv: `/remote` da
  Foydalanuvchi bitta parametrni o‘zgartirish uchun qaysi menyuga kirish kerakligini topa olmay qiynaladi.
- **UX tamoyili bilan solishtirish:** Information Architecture & Fitts's Law: Barcha tizim parametrlari bitta yagona, qidiruv imkoniyatiga ega "Sozlamalar markazi (Settings Hub)" ga birlashishi kerak.
- **Kamchilik va xavf:** Keraksiz navigatsiya bosqichlari, foydalanuvchining sozlamalarni topa olmasligi.
- **Taklif qilinadigan yaxshilanish:** Barcha 4 sahifani bitta markazlashgan `/settings` yo‘nalishiga yig‘ish va chap tomonda qulay tablar (Appearance, Voice, AI Providers, Devices) qilish.

---

### Journey 5: Xatolikdan Tiklanish (Error & Timeout Recovery)
- **Foydalanuvchi maqsadi:** Internet uzilganda yoki API kvotasi tugaganda nima bo‘lganini tushunish va ishni davom ettirish.
- **Bajarilishi kerak bo‘lgan qadamlar:**
  1. Xato yuz berganda ogohlantirishni ko‘rish.
  2. Nima bo‘lganini tushunish.
  3. "Qayta urinish (Retry)" tugmasini bosish.
- **Amaldagi oqim va muammo (`ChatPage.tsx:280-320`):**
  Xatolik yuz berganda chatda shunchaki: `"Xatolik: 404 Model Not Found"` yoki `"Request failed"` degan sovuq texnik matn chiqadi. Foydalanuvchiga yechim taklif qilinmaydi, "Qayta yuborish" tugmasi chiqmaydi.
- **UX tamoyili bilan solishtirish:** NN/g Heuristic #9 (Help Users Recover from Errors): Har bir xato xabari 3 ta elementga ega bo‘lishi shart: 1) Nima bo‘ldi? 2) Nega bo‘ldi? 3) Endi nima qilish kerak?
- **Kamchilik va xavf:** Foydalanuvchi noiloj qolib xabarni boshqatdan yozishga majbur bo‘ladi.
- **Taklif qilinadigan yaxshilanish:** Xato matni yoniga bitta klik bilan qayta jo‘natuvchi `[Qayta urinish (Retry)]` va zaxira modelga o‘tuvchi tugmani qo‘shish.

---

## 3. XULOSA
User Journey auditining eng asosiy xulosasi:
Misa'da eng og‘ir UX to‘siqlar — bu **birinchi kirishdagi majburiy Auth Wall**, **agent harakatlarining shaffof emasligi** va **sozlamalarning tarqoqligi**dir. Ushbu oqimlar yaxshilansa, mahsulotning foydalanuvchini ushlab qolish (Retention) ko‘rsatkichi keskin oshadi.
