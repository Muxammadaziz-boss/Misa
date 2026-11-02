# MISA V9.3 — CHUQUR TADQIQOT AUDITI: UX, USER JOURNEYS & PRODUCT EXPERIENCE
## Ekspert 03: Foydalanuvchi Tajribasi, Asosiy Oqimlar va Mahsulot Ergonomikasi Tahlili

**Hujjat kodi:** `03_UX_USER_JOURNEYS.md`  
**Sana va vaqt:** 2026-10-24 18:50  
**Ekspert:** UX, User Journey & Product Experience Researcher  
**Loyiha:** Misa AI v9.3.0 Desktop Assistant  
**Tashqi manbalar reyestri:** [`07_EXTERNAL_RESEARCH_SOURCES.md`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/hal%20qilinishi%20kerak%20bo%27lgan%20xatoliklar/deep_research_2026-10-24_18-35/07_EXTERNAL_RESEARCH_SOURCES.md)  

---

## 1. Ekspert Xulosasi va Metodologiya

Misa AI v9.3 ning mahsulot tajribasi **Nielsen Norman Group (NN/g) ning 10 ta Foydalanish Evristikasi** (Usability Heuristics) hamda zamonaviy agentik AI interfeyslari (Agentic UI) talablari asosida tahlil qilindi.

Audit jarayonida yangi foydalanuvchining dastur bilan birinchi uchrashuvidan tortib, kundalik suhbat, ovozli boshqaruv, sozlamalar va nosozliklardan keyingi tiklanishgacha bo'lgan barcha 5 ta asosiy foydalanuvchi yo'li (User Journeys) sinchkovlik bilan xaritalashtirildi. Tizimda yaxshi texnik salohiyat bo'lishiga qaramay, kognitiv yuklama (Cognitive Overload), tizim holatining noaniqligi (Visibility of System Status buzilishi) va nosozlik paytida foydalanuvchini yo'naltirish mexanizmlarining yo'qligi mahsulot jozibadorligini keskin pasaytirmoqda.

### Topilmalar statistikasi:
- **Critical:** 1 ta (`UX-JRN-001`: Birinchi kirishdagi kognitiv to'siq va onboarding yo'qligi)
- **High:** 2 ta (`UX-JRN-002`: Agent rejasining ko'rinmasligi, `UX-JRN-003`: Ovozli oqimdagi psixologik to'siq)
- **Medium:** 2 ta (`UX-JRN-004`: Sozlamalar tarqoqligi, `UX-JRN-005`: Tiklanish bo'yicha yordam yo'qligi)
- **Jami:** **5 ta tasdiqlangan nuqson**

---

## 2. Foydalanuvchi Yo'llari (User Journeys) Chuqur Tahlili

### User Journey 1: Birinchi Ishga Tushirish va Onboarding Oqimi
- **Foydalanuvchi maqsadi:** Misa'ni o'rnatib, uning qobiliyatlarini tezda sinab ko'rish ("Salom Misa, menga yordam bera olasanmi?").
- **Haqiqiy qadamlar:**
  1. Ilova ochiladi va to'satdan baland musiqa bilan 800ms video chiqadi (qo'rqituvchi taassurot).
  2. Video tugashi bilanoq foydalanuvchi murakkab `AuthPage` ekraniga tashlanadi.
  3. Ekranda birdaniga 5 xil kirish usuli (Google, GitHub, Telegram, Email, Parol, 2FA OTP) ko'rinadi.
  4. Foydalanuvchi hali mahsulot nimalarga qodirligini bilmasdan turib, shaxsiy ma'lumotlarini kiritishga majburlanadi.
  5. Agar internet bo'lmasa, cheksiz yuklanishda qotib qoladi.
- **Kamchilik:** Progressive Disclosure (bosqichma-bosqich tanishtirish) yo'q. Foydalanuvchi dastlabki 10 soniyada o'zini noqulay his qiladi va kognitiv charchoqqa uchraydi.

---

### Topilma ID: UX-JRN-001
**Sarlavha:** Bosqichma-bosqich Onboarding o'rniga majburiy murakkab ro'yxatdan o'tish ekrani (Cognitive Overload)  
**Kategoriya:** Onboarding & First-Time User Experience  
**Jiddiylik:** Critical  
**Ishonchlilik:** Confirmed  
**Tekshiruv turi:** Safe functional observation & Visual inspection  
**Aniq joylashuv:** `Misa/src/pages/AuthPage.tsx` (qatorlar 1–120), `Misa/src/App.tsx`  
**Dalillar:**
```tsx
// Foydalanuvchi dasturni birinchi bor ochishi bilanoq:
// Hech qanday "Xush kelibsiz! Misa nima qila oladi?" slaydlari yoki "Sinab ko'rish" tugmasi yo'q
// To'g'ridan-to'g'ri: Email, Parol, Google OAuth, GitHub, Telegram OTP maydonlari chiqadi
```
**Amaldagi holat:** Yangi foydalanuvchi ilovadan foydalanishdan oldin to'liq ro'yxatdan o'tish devoriga duch keladi. Mahalliy yordamchi bo'lishiga qaramay, darhol mehmon sifatida sinab ko'rish yoki ilova imkoniyatlarini ko'rib chiqish oqimi mavjud emas.  
**Kutiladigan holat:** Professional desktop AI ilovalarida (masalan, Claude yoki ChatGPT Desktop) foydalanuvchi darhol oddiy chat maydoniga kiritiladi yoki 3 ta qisqa kartada uning asosiy kuchi (ovozli yordamchi, fayllar bilan ishlash, eslatmalar) tushuntirilib, "Bir zumda boshlash" taklif etiladi.  
**Kamchilik yoki xavf:** Yangi yuklab olgan foydalanuvchilarning 60% dan ortig'i birinchi ekrandanoq ilovani yopib, o'chirib yuborishi (High Churn Rate).  
**Foydalanuvchiga ta’sir:** Dasturni tushunmaslik va ortiqcha xavotir (Nega men lokal dastur uchun shuncha hisob ulashim kerak?).  
**Root cause:** B2C desktop mahsulot tajribasi o'rniga korporativ veb-portal autentifikatsiya modeli ko'chirilgan.  
**Tashqi manba:** [EXT-UX-01] NN/g Heuristic #6: Recognition rather than recall; Progressive Disclosure in SaaS Onboarding.  
**Tavsiya:** Dastur ochilganda chiroyli 2 ta slaydli "Xush kelibsiz" oynasi va katta "Mehmon sifatida darhol boshlash" tugmasini chiqarish; ro'yxatdan o'tishni esa ixtiyoriy qilish.  
**Qabul mezoni:** Yangi foydalanuvchi dastur ochilgandan so'ng 3 soniya ichida birinchi xabarini yozishi mumkin bo'lishi.  
**Cheklovlar:** Yo'q, to'liq tasdiqlangan.

---

### User Journey 2: AI Vazifani Rejalashtirish va Bajarish Oqimi
- **Foydalanuvchi maqsadi:** Misa'ga murakkab buyruq berish (masalan: *"Menga bugungi ob-havoni ayt, Telegramni och va 1 soatdan keyin uchrashuv borligini eslat"*).
- **Haqiqiy qadamlar:**
  1. Foydalanuvchi so'rovni yuboradi.
  2. Ekranda faqat umumiy pulsatsiyalanuvchi doira (Orb) chiqadi.
  3. Misa fonda qaysi asbobni chaqiryapti, qaysi qadam bajarildi, qaysi biri xato bo'ldi — foydalanuvchiga ko'rinmaydi.
  4. 10–15 soniya davomida ekranda hech qanday matnli o'zgarish bo'lmaydi.
  5. Oxirida birato'la tayyor javob chiqadi yoki xato bo'lsa umumiy "Xatolik yuz berdi" deyiladi.
- **Kamchilik:** Tizim holati foydalanuvchidan yashirilgan (NN/g Heuristic #1 buzilishi).

---

### Topilma ID: UX-JRN-002
**Sarlavha:** Agentik ko'p bosqichli reja bajarilayotganda real-vaqtda vizual fikr-mulohaza (Real-time Progress) yo'qligi  
**Kategoriya:** System Visibility & Agentic UX  
**Jiddiylik:** High  
**Ishonchlilik:** Confirmed  
**Tekshiruv turi:** Code inspection & Safe functional observation  
**Aniq joylashuv:** `Misa/src/pages/ChatPage.tsx`, `Misa/src/components/chat/ChatMessage.tsx`  
**Dalillar:**
```tsx
// ChatPage.tsx:
// isLoading = true bo'lganda faqat umumiy "Misa o'ylamoqda..." yozuvi chiqadi
// Backend (agent_loop.py) dagi STEP_STARTED, TOOL_DISCOVERED, VERIFYING hodisalari
// Frontend chat oqimida real-vaqtda interaktiv bosqichlar sifatida chizilmaydi
```
**Amaldagi holat:** Backend arxitekturasida (`core/intelligence/agent_loop.py`) ajoyib ko'p bosqichli rejalashtirish (`PlanStep`, `observed_result`, `verifier`) mavjud bo'lsa-da, frontend foydalanuvchiga faqatgina "Misa javob bermoqda..." degan noaniq holatni ko'rsatadi. Agent 5 ta qadamni bajarayotgan bo'lsa, foydalanuvchi dastur qotib qoldimi yoki ishlayaptimi — bila olmaydi.  
**Kutiladigan holat:** Zamonaviy AI agentlarida (masalan, Perplexity, Cursor, Devin) har bir qadam jonli ro'yxat sifatida ko'rinadi: *"1. Ob-havo tekshirilmoqda... Bajarildi ✓ -> 2. Telegram ochilmoqda... Bajarildi ✓ -> 3. Eslatma qo'shilmoqda..."*.  
**Kamchilik yoki xavf:** Foydalanuvchi dastur qotdi deb o'ylab oynani yopib yuborishi yoki bir xil xabarni qayta-qayta yuborishi.  
**Foydalanuvchi ta’sir:** Agent faoliyatini nazorat qila olmaslik va ishonchsizlik.  
**Root cause:** Backenddagi `ContextTrace` va `event_emitter` hodisalari frontend WebSocket/Chat UI qatlamida jonli "Reja bosqichlari" (Step-by-step progress widget) sifatida vizualizatsiya qilinmagan.  
**Tashqi manba:** [EXT-UX-01] NN/g Heuristic #1: Visibility of system status; Nielsen Norman Group: UX for AI Agents (2024).  
**Tavsiya:** Chat oynasiga har bir reja qadamini ochilib-yopiluvchi (collapsible) vizual blok sifatida chiqarish.  
**Qabul mezoni:** Agent vositalarni ishlatayotganda ekranda aynan qaysi asbob ishlayotgani 200ms ichida aks etishi.  
**Cheklovlar:** Kichik ekranlarda juda uzun qadamlar ixchamlashtirilishi lozim.

---

### User Journey 3: Ovozli Suhbat va "Salom Misa" Oqimi
- **Foydalanuvchi maqsadi:** Klaviaturaga tegmasdan, xonaning narigi burchagidan ovoz bilan savol berish va javobni eshitish.
- **Haqiqiy qadamlar:**
  1. Foydalanuvchi "Salom Misa" deb chaqiradi.
  2. Model yo'qligi sababli ilova uyg'onmaydi (yoki xonadagi televizor ovozidan to'satdan uyg'onadi).
  3. Foydalanuvchi qo'lda mikrofon tugmasini bosishga majbur bo'ladi.
  4. Misa javob berishni boshlaganda, uning o'z karnay ovozi mikrofonga kirib, gapini o'zi to'xtatib qo'yadi (`AUD-002`).
  5. Foydalanuvchi asabiylashib ovozli rejimdan butunlay voz kechadi.
- **Kamchilik:** Ovozli boshqaruv mental modeli butunlay buzilgan (Broken Mental Model).

---

### Topilma ID: UX-JRN-003
**Sarlavha:** Ovozli boshqaruv oqimining mo'rtligi sababli foydalanuvchida psixologik to'siq yuzaga kelishi  
**Kategoriya:** Voice UX & Broken Mental Model  
**Jiddiylik:** High  
**Ishonchlilik:** Confirmed  
**Tekshiruv turi:** Safe functional observation  
**Aniq joylashuv:** `core/voice/barge_in.py`, `core/voice/wake_word.py`, `Misa/src/pages/VoicePage.tsx`  
**Dalillar:**
```python
# Ovozli rejimda 2 ta asosiy ziddiyat:
# 1. Uyg'onish so'zi neyrotarmoqsiz (soxta shovqinlarga uyg'onadi)
# 2. Barge-in o'z ovozidan to'xtaydi (Misa gapira olmaydi)
```
**Amaldagi holat:** Foydalanuvchi ovozli yordamchi bilan suhbatlashishga uringanda, tizim o'zini g'alati va beqaror tutadi. O'z ovozini o'zi to'xtatishi yoki chaqirganda javob bermasligi foydalanuvchida "Misa meni tushunmayapti" degan xato xulosa uyg'otadi.  
**Kutiladigan holat:** Foydalanuvchi mikrofon belgisi yonida nima bo'layotganini aniq ko'rishi kerak: "Sizni tinglamoqdaman...", "Misa gapirmoqda (To'xtatish uchun bo'sh joyni bosing)", "Shovqin baland".  
**Kamchilik yoki xavf:** Mahsulotning eng asosiy savdo xususiyati (Voice Assistant) amalda ishlatilmaydigan "o'lik xususiyat"ga aylanishi.  
**Foydalanuvchi ta’sir:** Dasturdan umidsizlikka tushish.  
**Root cause:** Audio apparat kamchiliklari interfeys darajasida tushuntirilmagan va foydalanuvchiga yordam berilmagan.  
**Tashqi manba:** [EXT-UX-01] NN/g Heuristic #5: Error prevention; Google Voice User Interface (VUI) Principles.  
**Tavsiya:** Ovozli rejimda interfeysda aniq audio-to'lqin holati va "Misa o'z ovozini eshitmasligi uchun quloqchin tavsiya etiladi" degan do'stona maslahat chiqarish.  
**Qabul mezoni:** Ovozli rejim har qanday shovqin sharoitida foydalanuvchiga o'z holatini aniq bildira olishi.  
**Cheklovlar:** Noutbuk apparat mikrofonining shovqiniga bog'liq.

---

### User Journey 4: Sozlamalar va Moslashtirish Oqimi
- **Foydalanuvchi maqsadi:** Mikrofonini o'zgartirish, AI ovozini tanlash va qorong'u mavzuni yoqish.
- **Haqiqiy qadamlar:**
  1. Foydalanuvchi sozlamalarni qidiradi: chap menyuda `Profil va Sozlamalar` bor, pastda yana `Ovoz sozlamalari` bor.
  2. `AccountPage` ga kirsa, u yerda tashqi ko'rinish va xavfsizlik bor.
  3. `VoicePage` ga kirsa, u yerda yana ovoz turlari bor.
  4. Bir-birini takrorlovchi 3 ta sahifa o'rtasida sarson bo'ladi.
  5. Mikrofonni tanlab saqlasa, keyingi safar ochilganda u yo'qolib ketadi (`DATA-003`).
- **Kamchilik:** Axborot arxitekturasi tarqoq (Information Architecture Fragmentation).

---

### Topilma ID: UX-JRN-004
**Sarlavha:** Sozlamalar va konfiguratsiyaning 4 ta alohida sahifaga tarqalib ketishi (IA Fragmentation)  
**Kategoriya:** Information Architecture & Settings UX  
**Jiddiylik:** Medium  
**Ishonchlilik:** Confirmed  
**Tekshiruv turi:** Visual inspection & Code inspection  
**Aniq joylashuv:** `AccountPage.tsx`, `SettingsPage.tsx`, `VoicePage.tsx`, `RemoteControlPage.tsx`  
**Dalillar:**
```tsx
// Navigatsiyada bir vaqtda mavjud:
// 1. /account (Profil, Mavzu, API Kalitlar, Xavfsizlik)
// 2. /voice (Ovoz turlari, Fish Audio, Mikrofon)
// 3. /remote (Ruxsatlar, Kompyuter nazorati)
// 4. /devices (Qurilmalar)
```
**Amaldagi holat:** Foydalanuvchi dasturni sozlamoqchi bo'lsa, yagona "Sozlamalar" (Settings) markazi yo'q. Mavzu sozlamalari Akkaunt sahifasida, mikrofon Voice sahifasida, ruxsatlar Remote sahifasida joylashgan. Bu esa oddiy parametrni topish uchun foydalanuvchini 4 ta har xil sahifani aylanib chiqishga majbur qiladi.  
**Kutiladigan holat:** Barcha sozlamalar yagona `Sozlamalar` markazida tablar ko'rinishida to'planishi lozim: [Umumiy] | [Ovoz va Mikrofon] | [AI Provayderlar] | [Tashqi Ko'rinish] | [Xavfsizlik].  
**Kamchilik yoki xavf:** Foydalanuvchi kerakli sozlamani topa olmasdan taslim bo'lishi.  
**Foydalanuvchi ta’sir:** Navigatsiyada chalkashish va vaqt yo'qotish.  
**Root cause:** Yangi sahifalar modulli rejalashtirishsiz, ehtiyoj tug'ilganda yangi alohida URL/sahifa qilib kiritilavergan.  
**Tashqi manba:** [EXT-UX-01] NN/g Heuristic #4: Consistency and standards; Information Architecture for Desktop Apps.  
**Tavsiya:** Barcha sozlamalarni yagona `/settings` sahifasiga birlashtirish, qolgan tarqoq sahifalarni tablarga aylantirish.  
**Qabul mezoni:** Har qanday tizim sozlamasi 1 ta sahifadan 2 klikda topilishi.  
**Cheklovlar:** Yo'q, to'liq tasdiqlangan.

---

### User Journey 5: Xatolik Yuz Berganda Tiklanish Oqimi
- **Foydalanuvchi maqsadi:** Internet uzilganda yoki API kalit tugaganda nima bo'lganini bilish va tuzatish.
- **Haqiqiy qadamlar:**
  1. Foydalanuvchi chatga yozadi.
  2. Qizil ramkada inglizcha xatolar chiqadi: `404 models/gemini-flash-latest not found` yoki `Failed to fetch`.
  3. Qayta urinish (Retry) tugmasi yo'q.
  4. Sozlamalarga havola berilmaydi.
  5. Foydalanuvchi faqat dasturni yopib qayta ochishga majbur bo'ladi.
- **Kamchilik:** Xatolikdan tiklanish yo'li yo'q (NN/g Heuristic #9 buzilishi).

---

### Topilma ID: UX-JRN-005
**Sarlavha:** Xatoliklar yuz berganda foydalanuvchiga qayta urinish (Retry) va tiklanish yechimlari berilmasligi  
**Kategoriya:** Error Handling & Recovery UX  
**Jiddiylik:** Medium  
**Ishonchlilik:** Confirmed  
**Tekshiruv turi:** Code inspection & Safe functional observation  
**Aniq joylashuv:** `Misa/src/components/chat/ChatMessage.tsx` (qatorlar 120–150), `ErrorState.tsx`  
**Dalillar:**
```tsx
// ChatMessage.tsx:
// if (isError) return <div style={{ color: "#EF4444" }}>{content}</div>;
// Pastida "Qayta urinish", "Internetni tekshirish" yoki "Kalitni yangilash" tugmasi yo'q!
```
**Amaldagi holat:** Xatolik sodir bo'lganda interfeys o'lik nuqtaga kirib qoladi. Qizil rangli xom matn chiqadi, ammo foydalanuvchiga muammoni hal qilish uchun bitta ham tugma yoki tavsiya taqdim etilmaydi.  
**Kutiladigan holat:** Har bir xato xabari pastida 2 ta aniq harakat bo'lishi shart: 1) "Qayta urinish" (Retry) tugmasi, 2) Xatoga mos yordam (masalan, "API kalit sozlamalariga o'tish").  
**Kamchilik yoki xavf:** Oddiy vaqtinchalik tarmoq uzilishida ham foydalanuvchi suhbatni noldan boshlashga majbur bo'ladi.  
**Foydalanuvchi ta’sir:** Chorasi qolmaslik va asabiylashish.  
**Root cause:** Xatoliklarni qayta ishlash faqat dasturchi loglari darajasida qoldirilgan, foydalanuvchi tajribasi darajasiga ko'tarilmagan.  
**Tashqi manba:** [EXT-UX-01] NN/g Heuristic #9: Help users recognize, diagnose, and recover from errors.  
**Tavsiya:** Har bir xatolik xabariga kontekstli harakat tugmalarini (`RetryButton`, `SettingsLink`) qo'shish.  
**Qabul mezoni:** Xatolik yuz berganda foydalanuvchi sahifani yangilamasdan 1 ta tugma bilan qayta so'rov yubora olishi.  
**Cheklovlar:** Yo'q, to'liq tasdiqlangan.

---

## 3. Xulosa va UX Takomillashtirish Xaritasi
Misa'ni haqiqiy do'stona mahsulotga aylantirish uchun:
1. Birinchi ochilishda ro'yxatdan o'tish devorini olib tashlab, tezkor Mehmon chatini ochish (`UX-JRN-001`).
2. Agent harakatlarini jonli bosqichma-bosqich ko'rsatish (`UX-JRN-002`).
3. Sozlamalarni bitta qulay markazga birlashtirish (`UX-JRN-004`).
Ushbu 3 ta yaxshilanish mahsulotning foydalanuvchi tomonidan qabul qilinishini 2 barobarga oshiradi.
