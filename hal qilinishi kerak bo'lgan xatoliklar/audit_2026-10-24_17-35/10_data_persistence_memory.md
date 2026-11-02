# Misa v9.3 — Ekspert Hisoboti 10: Data, Persistence va Memory Engineer

**Audit sanasi va vaqti:** 2026-10-24 18:00  
**Ekspert roli:** Data, Persistence va Memory Engineer  
**Loyiha versiyasi:** Misa v9.3.0  
**Tekshirilgan Git branch va commit:** `dev-v9.0.0` / commit `aafa0d2fd15bba95b4f0c7aac921a9bd08986bb1`  
**Tekshiruv doirasi:** Ma'lumotlarning saqlanishi (persistence), xotira arxitekturasi (`AgentMemory`), atomik tranzaksiyalar, foydalanuvchilar orasidagi ma'lumotlar izolyatsiyasi, sxemalar versiyalanishi va zaxiralash barqarorligi.

---

## 1. Qisqacha Statistika

| Jiddiylik Darajasi | Topilmalar Soni |
| :--- | :--- |
| **Critical** | 2 |
| **High** | 2 |
| **Medium** | 1 |
| **Low** | 0 |
| **Info** | 0 |
| **Jami** | **5** |

---

## 2. Tekshirilgan Muhim Komponentlar va Fayllar

- `core/agent_memory.py` — Markaziy xotira menejeri, JSON saqlash, profil va bilimlar bazasi.
- `core/voice/devices.py` va `core/voice_engine.py` — Sozlamalar fayllari (`config.json`, `ovoz_turi.txt`).
- `supabase/migrations/20260918_phase41_supabase_auth.sql` — PostgreSQL relatsion sxemalari va RLS qoidalari.
- `data/` katalogi — Lokal ma'lumotlar ombori (`agent_conversations.json`, `agent_knowledge.json`, `agent_profile.json`).

---

## 3. Topilmalar Tafsiloti

### Topilma ID: DATA-001
**Sarlavha:** `_save_json` fallback rejimida faylning 0 baytga qisqarishi (Truncation) va xotiraning butunlay yo'qolish xavfi  
**Kategoriya:** Data Integrity va File Persistence  
**Jiddiylik darajasi:** Critical  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `core/agent_memory.py` (qatorlar 523–537)  
**Dalil:**
```python
# core/agent_memory.py:523-535
temp_path = f"{path}.tmp"
try:
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    try:
        os.replace(temp_path, path)
    except OSError:
        # Windows fallback: agar os.replace vaqtincha bloklangan bo'lsa
        with open(path, "w", encoding="utf-8") as f: # XAVF: Faylni darhol 0 baytga qisqartiradi!
            json.dump(data, f, ensure_ascii=False, indent=2)
```
**Muammo tavsifi:** Windows OS da biror fayl boshqa oqim yoki dastur (antivirus, backup agent, boshqa Python thread) tomonidan o'qish uchun ochiq bo'lsa, `os.replace(temp_path, path)` `PermissionError / WinError 32` xatoligini beradi. `_save_json` funksiyasi buni ushlab olib, fallback sifatida bevosita asosiy faylni `with open(path, "w")` bilan ochadi. Python da faylni `"w"` rejimi bilan ochish operatsion tizim darajasida fayl hajmini **bir zumda 0 baytga tushiradi (truncate)**. Agar aynan shu millisekundda Rust supervisor `taskkill /F /T` buyrug'ini yuborsa (dastur yopilganda) yoki elektr uzilsa yoki xotira yetmay qolsa, fayl 0 bayt holatida qolib ketadi. Natijada foydalanuvchining oylik barcha suhbatlar tarixi va bilimlari abadiy yo'qoladi.  
**Yuzaga kelish shartlari:** Dastur yopilayotgan paytda yoki parallel disk operatsiyalarida Windows faylni qulflaganda.  
**Ta’siri:** Ma'lumotlarning butunlay o'chib ketishi va `json.decoder.JSONDecodeError` tufayli keyingi ishga tushishlarda dasturning ochilmay qolishi.  
**Root cause:** Windows platformasida xavfsiz atomik almashtirish uchun maxsus qayta urinish (exponential backoff retry) o'rniga faylni o'chirib qayta yozuvchi xavfli fallback tanlangan.  
**Qayta tekshirish usuli:** Faylga o'qish qulfi (`open(..., 'r')`) qo'yib, `_save_json()` chaqirilganda fallback ishga tushishini va jarayon to'xtatilganda fayl bo'shab qolishini kuzatish.  
**Tavsiya:** Windows da `os.replace` xatoga uchrasa, to'g'ridan-to'g'ri `"w"` bilan ochmaslik; 3 marta qisqa tanaffus (`time.sleep(0.05)`) bilan qayta urinish va agar iloji bo'lmasa, `.tmp` faylni saqlab qolgan holda xatolik berish.  
**Qabul mezoni:** Xatolik yuz berganda ham asosiy JSON faylining avvalgi mazmuni 100% buzilmasdan saqlanib qolishi.  
**Cheklovlar:** Faqat Windows fayl tizimi (`NTFS`) xususiyatlarida yuzaga keladi.

---

### Topilma ID: DATA-002
**Sarlavha:** Lokal xotira fayllarida foydalanuvchilar o'rtasida izolyatsiyaning yo'qligi (Multi-Tenant Bleed)  
**Kategoriya:** Data Privacy va Storage Isolation  
**Jiddiylik darajasi:** Critical  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `core/agent_memory.py` (qatorlar 40–55)  
**Dalil:**
```python
# core/agent_memory.py:44-48
DATA_DIR = os.path.join(BASE_DIR, "data")
self._conversations_file = os.path.join(DATA_DIR, "agent_conversations.json")
self._profile_file = os.path.join(DATA_DIR, "agent_profile.json")
self._knowledge_file = os.path.join(DATA_DIR, "agent_knowledge.json")
```
**Muammo tavsifi:** Misa v9.3 ko'p foydalanuvchili Supabase autentifikatsiyasini qo'llab-quvvatlaydi (turli xil email va hisoblar bilan kirish mumkin). Ammo mahalliy diskda barcha suhbatlar, shaxsiy ma'lumotlar va AI bilimlari bitta umumiy fayllarda (`agent_conversations.json`, `agent_profile.json`) saqlanadi. Agar "A" foydalanuvchi tizimdan chiqib (logout), uning o'rniga "B" foydalanuvchi kirsa, "B" foydalanuvchi "A" foydalanuvchining barcha shaxsiy suhbatlarini, qiziqishlarini, ismi va sirlarini ko'radi va AI o'sha xotiralar asosida javob beradi. Foydalanuvchi identifikatori (`user_id`) bo'yicha hech qanday katalog yoki fayl ajratilmagan.  
**Yuzaga kelish shartlari:** Bitta kompyuterda bittadan ortiq foydalanuvchi hisobiga kirilganda.  
**Ta’siri:** Shaxsiy ma'lumotlarning boshqa foydalanuvchiga oshkor bo'lishi (Privacy Leak).  
**Root cause:** Xotira tizimi dastlab bir foydalanuvchili desktop ilova sifatida loyihalashtirilgan va Supabase multi-user auth ga moslashtirilmagan.  
**Qayta tekshirish usuli:** 1-hisobdan suhbat olib borib, tizimdan chiqish va 2-hisob bilan kirganda o'sha suhbatlar ko'rinishini tekshirish.  
**Tavsiya:** Ma'lumotlarni foydalanuvchi IDsi bo'yicha alohida kataloglarga saqlash: `data/users/{user_id}/conversations.json`.  
**Qabul mezoni:** Yangi hisob bilan kirilganda xotira toza bo'lishi va faqat shu foydalanuvchiga tegishli ma'lumotlar yuklanishi.  
**Cheklovlar:** Faqat bir nechta foydalanuvchi bitta kompyuterdan foydalanganda namoyon bo'ladi.

---

### Topilma ID: DATA-003
**Sarlavha:** Konfiguratsiyaning split-brain holati: `core/config.json` va `data/config.json` o'rtasidagi nomuvofiqlik  
**Kategoriya:** Configuration Integrity  
**Jiddiylik darajasi:** High  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `core/voice/devices.py` (qator 25) va `core/voice_engine.py` (qator 24)  
**Dalil:**
```python
# core/voice/devices.py:25
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
# __file__ = core/voice/devices.py -> dirname = core/voice -> dirname = core -> path = core/config.json!

# core/voice_engine.py:24
CONFIG_FILE = os.path.join(BASE_DIR, "data", "config.json")
# BASE_DIR = loyiha ildizi -> path = data/config.json!
```
**Muammo tavsifi:** Tizimda ikkita mutlaqo alohida `config.json` fayli mavjud va turli modullar turli fayllarga yozadi va o'qiydi. Masalan, mikrofonni tanlash va saqlash moduli (`devices.py`) foydalanuvchi tanlagan audio qurilmani `core/config.json` ga yozadi. Ovoz dvigateli va boshqa umumiy modullar esa sozlamalarni `data/config.json` dan qidiradi. Natijada foydalanuvchi mikrofoni yoki ovoz turini o'zgartirsa, bitta fayl yangilanadi, lekin boshqa modullar eski faylni o'qishda davom etadi.  
**Yuzaga kelish shartlari:** Foydalanuvchi sozlamalar (Settings) sahifasidan audio qurilma yoki ovoz turini o'zgartirganda.  
**Ta’siri:** Sozlamalar saqlanmagandek tuyuladi, dastur qayta ishga tushganda o'zgarishlar yo'qoladi.  
**Root cause:** Nisbiy yo'l hisoblashda adashish tufayli `core/config.json` tasodifan alohida fayl sifatida paydo bo'lgan.  
**Qayta tekshirish usuli:** Ikkala fayl mavjudligini `Test-Path` orqali tekshirish va ulardagi parametrlarning bir-biriga mos kelmasligini ko'rish.  
**Tavsiya:** `core/config.json` faylini olib tashlash, barcha konfiguratsiyalar uchun yagona haqiqat manbai (Single Source of Truth) sifatida `data/config.json` ni belgilash.  
**Qabul mezoni:** Loyiha bo'yicha faqat bitta `config.json` bo'lishi va barcha modullar yagona yo'ldan foydalanishi.  
**Cheklovlar:** Yo'q, yo'llar to'liq tasdiqlangan.

---

### Topilma ID: DATA-004
**Sarlavha:** Lokal xotirada relyatsion yaxlitlik (ACID), tranzaksiya va migratsiyalarning yo'qligi  
**Kategoriya:** Database Architecture va Reliability  
**Jiddiylik darajasi:** High  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `core/agent_memory.py` (qatorlar 35–120)  
**Dalil:**
```python
# core/agent_memory.py:
# Barcha ma'lumotlar oddiy Python xotirasidagi List va Dict lar orqali boshqariladi
# Har bir yangi xabarda butun boshli JSON fayl noldan qayta yoziladi
```
**Muammo tavsifi:** Misa AI lokal xotirasi uchun hech qanday o'rnatilgan relatsion ma'lumotlar bazasidan (masalan, SQLite yoki DuckDB) foydalanmaydi. Har bir yangi xabar, eslatma yoki bilim qo'shilganda, butun boshli massiv xotiraga yuklanadi va diskka ulkan JSON matni sifatida qayta-qayta to'liq yoziladi (O(N) I/O complexity). Suhbatlar soni bir necha mingtaga yetganda, har bir xabarda megabaytlab ma'lumot diskka yoziladi. Bundan tashqari, WAL (Write-Ahead Logging) va tranzaksiyalar bo'lmagani sababli ma'lumotlar yaxlitligini kafolatlab bo'lmaydi.  
**Yuzaga kelish shartlari:** Dastur bir necha hafta yoki oy davomida faol ishlatilib, suhbatlar soni ko'payganda.  
**Ta’siri:** Disk I/O sekinlashadi, xotira sarfi ortadi va fayl buzilish ehtimoli keskin oshadi.  
**Root cause:** Dastlabki prototip bosqichidagi sodda faylli yondashuv professional agent darajasidagi ma'lumotlar bazasiga almashtirilmagan.  
**Qayta tekshirish usuli:** `agent_conversations.json` ga 5000 ta xabar yozib, har bir saqlash davomiyligini o'lchash.  
**Tavsiya:** Lokal xotira uchun tranzaksiyali SQLite (WAL rejimida) omboriga o'tish yoki JSON saqlashni append-only (JSONL) formatiga o'tkazish.  
**Qabul mezoni:** Yangi xabar saqlash vaqti suhbatlar soniga bog'liq bo'lmasligi (O(1) murakkablik).  
**Cheklovlar:** Mavjud foydalanuvchilarning JSON fayllarini SQLite ga migratsiya qilish skripti talab etiladi.

---

### Topilma ID: DATA-005
**Sarlavha:** Xotiradagi suhbatlar ro'yxatining cheksiz o'sishi va xotira chegarasining yo'qligi  
**Kategoriya:** RAM va Memory Retention  
**Jiddiylik darajasi:** Medium  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `core/agent_memory.py` (qatorlar 215–240)  
**Dalil:**
```python
# core/agent_memory.py:220-225
self._conversations.append(conv)
# Hech qanday rolling buffer (masalan deque(maxlen=...)) yoki eskirgan suhbatlarni arxivlash yo'q
```
**Muammo tavsifi:** `AgentMemory` ishga tushganda `agent_conversations.json` dagi barcha xabarlarni RAM ga yuklaydi va foydalanuvchi yozgan har bir xabar doimiy ravishda `self._conversations` ro'yxatiga qo'shib boriladi. Dastur bir necha oy yopilmasdan ishlasa, Python xotirasidagi ushbu obyektlar doimiy RAM sarfini yuzlab megabaytga yetkazadi.  
**Yuzaga kelish shartlari:** Foydalanuvchi uzoq vaqt davomida faol suhbatlashganda.  
**Ta’siri:** RAM oqishi (memory bloat) va dasturning sekinlashishi.  
**Root cause:** Xotirani sahifalash (pagination) va eskirgan suhbatlarni arxivlash mexanizmi ishlab chiqilmagan.  
**Qayta tekshirish usuli:** `self._conversations` obyektining xotiradagi hajmini `sys.getsizeof` bilan tekshirish.  
**Tavsiya:** Faol xotirada faqat so'nggi 100 ta xabarni saqlash, qolganlarini esa so'rov bo'yicha diskdan o'qish (lazy loading/archival).  
**Qabul mezoni:** Xotiradagi faol suhbatlar keshining hajmi 5MB dan oshmasligi.  
**Cheklovlar:** Faqat juda uzoq davom etgan suhbatlarda seziladi.

---

## 4. Tekshirish Imkoni Bo'lmagan Qismlar va Cheklovlar
- PostgreSQL Supabase bulut bazasida tranzaksiyalarning haqiqiy yuklama ostidagi konkurent blokirovkasi (lock contention) jonli production serverga ulanmasdan tekshirilmadi.
- 100,000 dan ortiq yozuvlar bo'lgandagi SQLite vs JSON benchmarklari o'tkazilmadi.

---

## 5. Umumiy Xulosa va Keyingi Ustuvorliklar
Misa ma'lumotlarining xavfsizligi va yaxlitligidagi eng katta zaiflik — `_save_json` dagi xavfli fayl qisqarishi (`DATA-001`) hamda ko'p foydalanuvchilar o'rtasida ma'lumotlar izolyatsiyasining mavjud emasligidir (`DATA-002`). Ushbu ikki xato zudlik bilan bartaraf etilishi shart.
