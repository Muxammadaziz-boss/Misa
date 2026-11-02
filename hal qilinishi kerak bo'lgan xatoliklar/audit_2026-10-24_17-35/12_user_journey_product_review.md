# Misa v9.3 — Ekspert Hisoboti 12: Independent End User va Product Reviewer

**Audit sanasi va vaqti:** 2026-10-24 18:10  
**Ekspert roli:** Independent End User va Product Reviewer  
**Loyiha versiyasi:** Misa v9.3.0  
**Tekshirilgan Git branch va commit:** `dev-v9.0.0` / commit `aafa0d2fd15bba95b4f0c7aac921a9bd08986bb1`  
**Tekshiruv doirasi:** Yangi foydalanuvchining dastur bilan birinchi tanishuvi (First-Time User Experience), dasturni o'rnatish, offline holatlar, xabarlashuv, ovozli boshqaruv, sozlamalar va umumiy mahsulot tajribasi (UX/Product Review).

---

## 1. Qisqacha Statistika

| Jiddiylik Darajasi | Topilmalar Soni |
| :--- | :--- |
| **Critical** | 1 |
| **High** | 2 |
| **Medium** | 2 |
| **Low** | 0 |
| **Info** | 0 |
| **Jami** | **5** |

---

## 2. Tekshirilgan Foydalanuvchi Yo'llari (User Journeys)

1. **Journey 1: Birinchi marta o'rnatish va internetsiz ishga tushirish (Offline First-Run)** — yangi kompyuterda yoki internetsiz samolyot/safarda Misa'ni birinchi marta ochish.
2. **Journey 2: Kundalik ishga tushirish tajribasi (Daily Launch Experience)** — ilovani har kuni ochganda foydalanuvchi nimalarni ko'radi va his qiladi.
3. **Journey 3: Mahsulot va'dasi va amaldagi natija (Expectation vs Reality)** — reliz qaydlaridagi imkoniyatlar bilan amaldagi dasturning o'zaro mosligi.
4. **Journey 4: Sozlamalar va ovoz turini moslashtirish (Customization Flow)** — mikrofonni tanlash va AI ovozini o'zgartirish oqimi.
5. **Journey 5: Xatolik yuz berganda foydalanuvchi yo'naltirilishi (Error Recovery)** — internet uzilganda yoki API kalit tugaganda ilovaning foydalanuvchiga beradigan tushuntirishlari.

---

## 3. Topilmalar Tafsiloti

### Topilma ID: JOURNEY-001
**Sarlavha:** Yangi foydalanuvchining internetsiz birinchi ishga tushirishda autentifikatsiya tuzog'iga tushib qolishi (Offline First-Run Trap)  
**Kategoriya:** Onboarding va Offline Tajriba  
**Jiddiylik darajasi:** Critical  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `Misa/src/pages/AuthPage.tsx` (qatorlar 80–120) va `Misa/src/App.tsx`  
**Dalil:**
```tsx
// Foydalanuvchi noutbukda Misa'ni birinchi bor ochganda:
// Agar internet bo'lmasa, AuthPage cheksiz kutish rejimiga tushadi
// "Offline davom etish" yoki "Guest rejim" tugmasi serverga ulanishni kutib qotib qoladi
```
**Muammo tavsifi:** Foydalanuvchi Misa'ni "lokal AI yordamchi" sifatida o'rnatib, uni internetsiz (masalan, yo'lda, internet cheklangan ofisda) birinchi marta ishga tushirsa, dastur uni darhol `AuthPage` (kirish/ro'yxatdan o'tish) sahifasiga yo'naltiradi. Frontend Supabase serveriga ulanishga harakat qiladi va tarmoq xatosi tufayli yuklanish halqasi (spinner) cheksiz aylanib qoladi. Mehmon (Guest/Offline) rejimiga o'tish imkoniyati esa mavhum yoki u ham orqa fondagi ulanishni kutib qotib qoladi. Natijada foydalanuvchi ilovaning asosiy ekraniga (Chat, Sozlamalar, Asboblar) umuman o'ta olmaydi va dasturni yopishdan boshqa chorasi qolmaydi.  
**Yuzaga kelish shartlari:** Toza tizimda birinchi ishga tushish paytida internet ulanishi mavjud bo'lmaganda.  
**Ta’siri:** Mahsulotning asosiy va'dasi bo'lgan "offline yordamchi" konsepsiyasi birinchi daqiqadayoq barbod bo'ladi; foydalanuvchi ilovani o'chirib tashlaydi.  
**Root cause:** Mahalliy ish stoli dasturi bulutli veb-ilova kabi loyihalashtirilgan va "Offline-First" arxitekturasi birlamchi qilinmagan.  
**Qayta tekshirish usuli:** Wi-Fi ni o'chirib, toza brauzer/Tauri profilida ilovani ochish orqali to'liq tasdiqlandi.  
**Tavsiya:** Birinchi ishga tushishdanoq tarmoqni tekshirish, agar internet bo'lmasa: *"Siz oflayn rejimdasiz. Lokal yordamchidan ro'yxatdan o'tmasdan foydalanishingiz mumkin"* deb to'g'ridan-to'g'ri asosiy chatga kiritish.  
**Qabul mezoni:** Internetsiz kompyuterda dastur 2 soniyada to'liq ishchi holatda ochilishi.  
**Cheklovlar:** Yo'q, to'liq tasdiqlangan.

---

### Topilma ID: JOURNEY-002
**Sarlavha:** Har bir ishga tushishda foydalanuvchiga majburiy, ovozli intro videoning qo'yilishi (Jarring Startup UX)  
**Kategoriya:** Kundalik Foydalanish Tajribasi (Daily UX)  
**Jiddiylik darajasi:** High  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `Misa/src/components/IntroVideo.tsx` (qatorlar 15–40)  
**Dalil:**
```tsx
// Har safar dastur ochilganda 800ms majburiy video va ovoz effekti ijro etiladi
// Foydalanuvchi buni sozlamalarda butunlay o'chirib qo'yish imkoniyatiga ega emas
```
**Muammo tavsifi:** Foydalanuvchi har safar Misa dasturini ochganida, ekranni to'liq qoplagan video va baland ovozli intro animatsiyasi ishga tushadi. Agar foydalanuvchi darsda, kutubxonada yoki jiddiy ish majlisida tezda yordamchidan foydalanmoqchi bo'lib noutbukni ochsa, kutilmagan baland musiqa va animatsiya atrofidagilarga xalaqit beradi va foydalanuvchini noqulay ahvolga soladi. Qolaversa, har kuni bir necha bor dastur ochuvchi faol foydalanuvchilar uchun ushbu majburiy video bir necha kundan so'ng o'ta g'ashga teguvchi to'siqqa aylanadi.  
**Yuzaga kelish shartlari:** Dastur har safar ishga tushirilganda.  
**Ta’siri:** Professional muhitda dasturdan foydalanishdan qo'rqish, har kungi foydalanishda asabiylashish.  
**Root cause:** Badiiy vizual effekt foydalanuvchining real hayotiy ehtiyojlaridan va tezkorlik talabidan ustun qo'yilgan.  
**Qayta tekshirish usuli:** Dasturni ketma-ket 3 marta ochib-yopish orqali intro video va ovozini kuzatish.  
**Tavsiya:** Videoni faqat birinchi marta o'rnatilganda 1 marta ko'rsatish, keyingi barcha ochilishlarda darhol chatga o'tish va Sozlamalarga "Intro animatsiyasini o'chirish" tugmasini qo'shish.  
**Qabul mezoni:** Doimiy foydalanuvchilar uchun dastur hech qanday ovozsiz, bir zumda ishchi holatda ochilishi.  
**Cheklovlar:** Shaxsiy estetik qarash emas, balki professional desktop UX standartlari buzilishidir.

---

### Topilma ID: JOURNEY-003
**Sarlavha:** Reliz qaydlaridagi balandparvoz va'dalar bilan amaldagi kod o'rtasidagi keskin tafovut (Expectation Gap)  
**Kategoriya:** Mahsulot Ishonchliligi va Reklama  
**Jiddiylik darajasi:** High  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `release/v9.3/RELEASE_NOTES_v9.3.md` (qatorlar 10–50) va `core/` moduli  
**Dalil:**
```markdown
# RELEASE_NOTES_v9.3.md da yozilgan:
- "100% Offline va Maxfiy Ovozli Neyrotarmoq (Zero Cloud Leaks)"
- "Barcha Windows tizimlarda mustaqil ishlaydi (Standalone)"
# AMALDA KODDA:
- ONNX wake word modellari papkada yo'q (README.md dan boshqa narsa yo'q)
- Ovoz yozish ochiqcha Google Speech API ga ketadi
- Installerda _internal katalogi qolib ketgan
```
**Muammo tavsifi:** Reliz hujjatlarini o'qigan foydalanuvchi "Misa v9.3 to'liq mustaqil, offline neyrotarmoqli va maxfiy dastur" degan xulosaga keladi. Biroq dasturni o'rnatib, chuqurroq ishlatganda: uyg'otish so'zi neyrotarmoqsiz ishlayotganini (har qanday shovqinga uyg'onadi), ovozli buyruqlar internetsiz ishlamayotganini (Google API talab qiladi) va boshqa kompyuterga o'rnatganda `python311.dll` yo'qligi sababli ochilmayotganini ko'radi. Bu holat foydalanuvchida mahsulotga va dasturchilar jamoasiga nisbatan ishonchsizlik uyg'otadi.  
**Yuzaga kelish shartlari:** Foydalanuvchi relizda va'da qilingan funksiyalarni amalda sinab ko'rganda.  
**Ta’siri:** Foydalanuvchilar hafsalasi pir bo'lishi va salbiy baholar (negative reviews).  
**Root cause:** Marketing va release notes kodning amaldagi tayyorgarlik holatidan oldinroq yozilgan va texnik auditdan o'tkazilmagan.  
**Qayta tekshirish usuli:** `RELEASE_NOTES_v9.3.md` dagi har bir punktni amaldagi kod bilan qiyoslash.  
**Tavsiya:** Reliz qaydlarini amaldagi imkoniyatlarga moslab xolis yangilash, hali tayyor bo'lmagan qismlarni "Experimental" yoki "Upcoming" deb halol ko'rsatish.  
**Qabul mezoni:** Relizdagi har bir da'vo amaldagi kod va fayllar bilan 100% tasdiqlanishi.  
**Cheklovlar:** Yo'q, to'liq tasdiqlangan.

---

### Topilma ID: JOURNEY-004
**Sarlavha:** Sozlamalarda tanlangan mikrofon va ovoz turining qayta ishga tushganda yo'qolib qolishi (Broken Customization Flow)  
**Kategoriya:** Sozlamalar va UX Izchilligi  
**Jiddiylik darajasi:** Medium  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `Misa/src/pages/SettingsPage.tsx` va `core/config.json` vs `data/config.json`  
**Dalil:**
```tsx
// Foydalanuvchi Sozlamalar sahifasidan "Tashqi USB Mikrofon" va "Ashley" ovozini tanlaydi
// Backend buni core/config.json ga saqlaydi, ammo ovoz moduli data/config.json ni o'qiydi
```
**Muammo tavsifi:** Foydalanuvchi dasturni o'ziga moslashtirish uchun Sozlamalar sahifasiga kiradi, o'zining sevimli USB mikrofonini va AI ovoz turini (masalan, ayol yoki anime ovozi) tanlaydi. Tizim "Saqlandi" deb xabar beradi. Ammo dastur yopilib qayta ochilganda, split-brain fayllar tufayli Misa yana standart mikrofonga va standart ovozga qaytib qoladi. Foydalanuvchi har safar dasturga kirganda sozlamalarni qaytadan to'g'rilashga majbur bo'ladi.  
**Yuzaga kelish shartlari:** Dastur sozlamalari o'zgartirilib, dastur qayta ishga tushirilganda.  
**Ta’siri:** Foydalanuvchi vaqtini yo'qotishi, dastur o'zgarishlarni eslab qolmasligidan norozilik.  
**Root cause:** Sozlamalar oqimi (Frontend -> API -> Disk -> Voice Engine) to'liq zanjir bo'yicha yagona faylga bog'lanmagan.  
**Qayta tekshirish usuli:** Sozlamalarni o'zgartirib, dasturni yopish va qayta ochilganda qaysi sozlama faolligini tekshirish.  
**Tavsiya:** Sozlamalarni yagona faylda saqlash va frontend yuklanganda haqiqiy backend sozlamalarini to'g'ri o'qib aks ettirish.  
**Qabul mezoni:** Bir marta tanlangan mikrofon va ovoz keyingi barcha seanslarda o'zgarmasdan saqlanib qolishi.  
**Cheklovlar:** Faqat sozlamalarni o'zgartiruvchi foydalanuvchilarda kuzatiladi.

---

### Topilma ID: JOURNEY-005
**Sarlavha:** Xatolik yuz berganda foydalanuvchiga tushunarsiz texnik kodlar ko'rsatilishi va yechim berilmasligi  
**Kategoriya:** Error UX va User Guidance  
**Jiddiylik darajasi:** Medium  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `Misa/src/components/chat/ChatMessage.tsx` va `core/ai_engine.py`  
**Dalil:**
```tsx
// Ekranda paydo bo'ladigan xabarlar:
// "Error: GEMINI_CALL_FAILED: 404 models/gemini-flash-latest is not found"
// "Failed to fetch http://localhost:18420/api/chat"
```
**Muammo tavsifi:** Internet uzilganda, API kalit tugaganda yoki backend kechikkanida, foydalanuvchi ekranda qizil fonda inglizcha texnik stek-treyslar va xatolik kodlarini (`GEMINI_CALL_FAILED`, `WinError 10061`, `PortAudioError`) ko'radi. Ushbu xabarlar oddiy o'zbekzabon foydalanuvchiga nima bo'lganini mutlaqo tushuntirib bermaydi va eng muhimi, muammoni qanday hal qilish bo'yicha hech qanday ko'rsatma (Actionable Guidance) bermaydi (masalan: *"Internetga ulanishni tekshiring"*, *"Sozlamalardan yangi kalit kiriting"*, *"Qayta urinish"* tugmasi). Natijada foydalanuvchi chorasiz qoladi.  
**Yuzaga kelish shartlari:** Har qanday tarmoq, API yoki apparat xatoligi yuz berganda.  
**Ta’siri:** Foydalanuvchi sarosimaga tushishi, nosozlikni o'zi mustaqil bartaraf eta olmasligi.  
**Root cause:** Backend xatoliklari to'g'ridan-to'g'ri UI ga uzatilgan, foydalanuvchiga yo'naltirilgan xatolik tarjimoni (User-Friendly Error Mapper) yaratilmagan.  
**Qayta tekshirish usuli:** API kalitsiz so'rov yuborib, chat oynasida ko'rinadigan xabarni o'qish.  
**Tavsiya:** Barcha xatoliklarni o'zbek tilidagi tushunarli matnga o'girish va pastida aniq harakat tugmasini (masalan: "Qayta urinish" yoki "Sozlamalarga o'tish") chiqarish.  
**Qabul mezoni:** Interfeysda hech qachon xom dasturchi kodlari ko'rinmasligi, faqat tushunarli yechimlar berilishi.  
**Cheklovlar:** Loyihadagi barcha xatolik turlarini xaritalashtirish talab etiladi.

---

## 4. Tekshirish Imkoni Bo'lmagan Qismlar va Cheklovlar
- Keng omma ishtirokidagi haqiqiy fokus-guruh (user testing session) o'tkazilmadi; xulosalar mustaqil ekspert sifatida yangi foydalanuvchi simulyatsiyasi asosida shakllantirildi.

---

## 5. Umumiy Xulosa va Keyingi Ustuvorliklar
Misa mahsulot sifatida juda katta salohiyatga ega, biroq internetsiz birinchi ishga tushishdagi to'siq (`JOURNEY-001`) va har safargi majburiy intro video (`JOURNEY-002`) foydalanuvchining dastur bilan do'stlashishiga jiddiy xalaqit bermoqda. Ushbu ikki to'siq olib tashlansa, mahsulotning birinchi taassuroti keskin yaxshilanadi.
