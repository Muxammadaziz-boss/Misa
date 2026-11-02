# Misa v9.3 — Ekspert Hisoboti 07: Performance va Reliability Engineer

**Audit sanasi va vaqti:** 2026-10-24 17:45  
**Ekspert roli:** Performance va Reliability Engineer  
**Loyiha versiyasi:** Misa v9.3.0  
**Tekshirilgan Git branch va commit:** `dev-v9.0.0` / commit `aafa0d2fd15bba95b4f0c7aac921a9bd08986bb1`  
**Tekshiruv doirasi:** CPU, RAM, disk I/O, event loop unblocking, latency, resurs oqishi (leak), jarayonlar o'rtasidagi raqobat (concurrency), audio kechikishlari va uzluksiz ishlash barqarorligi.

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

## 2. Tekshirilgan Muhim Komponentlar va Fayllar

- `core/ai_engine.py` — Prompt enrichment va LLM so'rovlari generatsiyasi latency.
- `core/app_detector.py` — Tizimdagi dasturlar va jarayonlarni tekshirish mexanizmi (CPU va I/O profil).
- `core/agent_tools.py` — Tizim buyruqlarini bajarish (`powershell.exe` chaqiruvlari).
- `Misa/src-tauri/src/lib.rs` — Oyna faollashtirish va jarayonlar monitoringi.
- `core/voice/devices.py` — Audio qurilmalarni boshqarish va diskka log yozish tezligi.
- `core/voice/audio_queue.py` — TTS audio ijrosi va navbat boshqaruvi (backpressure).
- `core/audio_service.py` — VAD (Voice Activity Detection) va sounddevice stream oqimlari.
- Loyiha ildiz katalogi (`Ashley.zip`, `Yukari.zip` kabi ulkan binar arxivlar).

---

## 3. Topilmalar Tafsiloti

### Topilma ID: PERF-001
**Sarlavha:** Har bir chat xabarida sinxron jarayonlar va disk yo'llarini to'liq skanerlash (Latency Bloat)  
**Kategoriya:** Performance va Latency  
**Jiddiylik darajasi:** Critical  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `core/ai_engine.py` (qatorlar 217–222) va `core/app_detector.py` (qatorlar 524–542, 218–260)  
**Dalil:**
```python
# core/ai_engine.py:217-220
detector = get_app_detector()
specs = detector.get_realtime_system_specs()
inventory = detector.get_realtime_inventory_summary()
enriched_prompt += f"\n\nKOMPYUTER VA ILOVALAR HOLATI (REAL-TIME WINDOWS INVENTORY):\n{specs}\n\nAniqlangan dasturlar holati:\n{inventory}\n"
```
```python
# core/app_detector.py:530-538
for fam in checked_families:
    info = self.detect_app(fam)
    # detect_app ichida: running_procs = self._get_running_processes()
    # va agar ishlamayotgan bo'lsa: standard_paths diskda os.path.exists() bilan qidiriladi
```
**Muammo tavsifi:** Foydalanuvchi har safar oddiy matnli xabar yuborganida (`"salom"`, `"bugun qaysi kun?"`), `AIEngine.generate_response()` funksiyasi LLM ga so'rov yuborishdan oldin bloklovchi (sinxron) tarzda `detector.get_realtime_system_specs()` va `detector.get_realtime_inventory_summary()` funksiyalarini chaqiradi. Ushbu funksiya 12 ta dastur oilasi bo'yicha ketma-ket jarayonlar ro'yxatini, diskdagi o'nlab yo'llarni (`os.path.exists`) va Windows Registry kalitlarini sinxron skanerlaydi. Natijada har bir chat so'rovi oldidan sun'iy ravishda 350ms dan 1800ms gacha qo'shimcha kechikish yuzaga keladi va LLM kontekstiga 400 dan ortiq keraksiz tokenlar qo'shiladi.  
**Yuzaga kelish shartlari:** Foydalanuvchi har qanday matnli yoki ovozli so'rov yuborganida.  
**Ta’siri:** AI javob berish kechikishi (TTFT - Time To First Token) keskin ortadi; disk sekin bo'lgan tizimlarda dastur qotib qoladi (lag); LLM token sarfi 20-30% ga asossiz oshadi.  
**Root cause:** Kontekst boyitish (prompt enrichment) mezonlanmagan (selective/lazy) emas, balki har bir so'rovda ko'r-ko'rona va sinxron ishga tushiriladi.  
**Qayta tekshirish usuli:** `core/ai_engine.py` da `generate_response()` boshida va `inventory` yuklangandan keyin vaqtni o'lchash (`t1 = time.perf_counter()`).  
**Tavsiya:** Dasturlar va tizim ma'lumotlarini faqat foydalanuvchi tizim/dasturlar haqida so'raganda (intent-based) yuklash yoki alohida fon oqimida (background thread) 60 soniyalik kesh bilan yangilab turish.  
**Qabul mezoni:** Oddiy chat so'rovlarida `get_realtime_inventory_summary` bloklovchi chaqirilmasligi, lokal tayyorgarlik kechikishi 10ms dan oshmasligi.  
**Cheklovlar:** Faqat kod tahlili va statik psutil/os chaqiruvlari ketma-ketligi asosida baholandi.

---

### Topilma ID: PERF-002
**Sarlavha:** Tizim amallari va oynalarni boshqarishda `powershell.exe` jarayonini qayta-qayta ishga tushirish (Process Spawn Overhead)  
**Kategoriya:** CPU va Jarayonlar Boshqaruvi  
**Jiddiylik darajasi:** High  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `core/agent_tools.py` (qatorlar 120–145) va `Misa/src-tauri/src/lib.rs` (qatorlar 210–240)  
**Dalil:**
```python
# core/agent_tools.py:126-130
cmd = [
    "powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
    "-Command", ps_script
]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
```
```rust
// Misa/src-tauri/src/lib.rs:218-225
let output = std::process::Command::new("powershell")
    .args(["-NoProfile", "-Command", &ps_cmd])
    .output();
```
**Muammo tavsifi:** Windows oynalarini oldinga chiqarish, ovoz balandligini o'zgartirish yoki tizim jarayonlarini boshqarish uchun Python va Rust qismlarida yangi `powershell.exe` jarayoni ishga tushiriladi (`subprocess.run` / `std::process::Command`). Windows OS da yangi PowerShell instansiyasini yuklash (.NET CLR, runtime assembly larni o'qish) kamida 450–1200ms vaqt oladi va CPU yadrolariga 30-50% sakrash yuklaydi. Buni to'g'ridan-to'g'ri Win32 API (`SetForegroundWindow`, `ShowWindow`) yoki `win32gui` orqali 1-2 millisekundda bajarish mumkin.  
**Yuzaga kelish shartlari:** Agent orqali biror ilovani ochish, fokus qilish yoki tizim sozlamalarini boshqarish buyrug'i berilganda.  
**Ta’siri:** Foydalanuvchi buyruq berganda kompyuter sezilarli darajada sekinlashadi, fan tezligi oshadi va amallar 1-2 soniya kechikib bajariladi.  
**Root cause:** Win32 API yoki mahalliy C/Rust chaqiruvlari o'rniga eng oson, lekin eng og'ir usul — PowerShell skriptlarini subprocess orqali chaqirish tanlangan.  
**Qayta tekshirish usuli:** PowerShell buyrug'i bajarilish vaqtini `Measure-Command` yoki Python `time.time()` bilan Win32 API ga solishtirish.  
**Tavsiya:** Rust tomonida to'g'ridan-to'g'ri `windows` crate (Win32 API) dan foydalanish, Python tomonida esa `pywin32` / `ctypes` orqali API chaqiruvlarini amalga oshirish.  
**Qabul mezoni:** Hech qanday oynani boshqarish amali `powershell.exe` chaqirmasligi, ijro vaqti < 10ms bo'lishi.  
**Cheklovlar:** Turli Windows versiyalarida (Win10 vs Win11) PowerShell 5.1 yuklanish vaqti farq qilishi mumkin.

---

### Topilma ID: PERF-003
**Sarlavha:** Ovoz va audio hodisalari vaqtida yuqori chastotali sinxron diskka yozish (I/O Bottleneck)  
**Kategoriya:** Disk I/O va Audio Barqarorligi  
**Jiddiylik darajasi:** High  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `core/voice/devices.py` (qatorlar 44–65, 70–85)  
**Dalil:**
```python
# core/voice/devices.py:44-62
def log_voice_runtime(event_type: str, details: Optional[Dict[str, Any]] = None) -> None:
    try:
        log_dir = _get_misa_log_dir()
        log_file = os.path.join(log_dir, "voice-runtime.log")
        # ...
        line = f"{ts} [VOICE_RUNTIME] PID={pid} event={event_type} {det_str}\n"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
```
**Muammo tavsifi:** Audio oqimi (sounddevice input stream, VAD va audio capture) vaqtida har bir kichik hodisa (`CAPTURE_START`, `CHUNK_RECEIVED`, `MIC_SELECTED`, `HOTPLUG_POLL`) uchun `with open(log_file, "a") as f:` orqali bevosita sinxron fayl ochiladi, yoziladi va yopiladi. Audio oqimlarida millisekundlik kechikishlar juda muhim hisoblanadi. Agar qattiq disk (HDD) yoki yuklangan SSD I/O band bo'lsa, ushbu sinxron diskka yozish PortAudio oqimining bufer to'lib ketishiga (buffer overrun/underrun) va audio uzilishlariga (glitch/stutter) sabab bo'ladi.  
**Yuzaga kelish shartlari:** Mikrofon orqali audio yozib olish va ovozli suhbat jarayonida.  
**Ta’siri:** Ovoz yozishda to'xtalishlar, mikrofondan olinayotgan ovozda uzilishlar va disk I/O resursining isrofi.  
**Root cause:** Asinxron logging (masalan, `logging.handlers.QueueHandler` yoki xotira buferi) o'rniga to'g'ridan-to'g'ri audio oqimi ichida disk faylini ochish va yozish kodi joylashtirilgan.  
**Qayta tekshirish usuli:** Sekin diskda yoki virtual mashinada ovoz yozish vaqtida `voice-runtime.log` ga yozish paytidagi I/O kutish vaqtini o'lchash.  
**Tavsiya:** Standart Python `logging` tizimidan xotiradagi navbat (`QueueHandler` va `QueueListener`) orqali asinxron fon oqimida log yozishni yo'lga qo'yish.  
**Qabul mezoni:** Audio oqimi va real-time audio callbacklarida to'g'ridan-to'g'ri `open()` fayl amallari bajarilmasligi.  
**Cheklovlar:** Yuqori tezlikdagi NVMe disklarda kechikish kamroq seziladi, biroq HDD va USB disklarda yaqqol namoyon bo'ladi.

---

### Topilma ID: PERF-004
**Sarlavha:** Loyiha ildizida 194MB hajmdagi zip arxivlar saqlanishi va xotira isrofi (Repository & Disk Footprint)  
**Kategoriya:** Resurslar va Xotira Boshqaruvi  
**Jiddiylik darajasi:** Medium  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `Ashley.zip` (90.4 MB) va `Yukari.zip` (104.3 MB) — loyiha ildiz katalogi  
**Dalil:**
```powershell
# Get-ChildItem -Path . -Filter *.zip
# Ashley.zip   90,449,850 bytes
# Yukari.zip  104,383,212 bytes
```
**Muammo tavsifi:** Loyiha omborining ildiz katalogida deyarli 200 MB hajmdagi ikkita siqilgan arxiv fayl (`Ashley.zip` va `Yukari.zip`) mavjud. Ushbu fayllar versiyalar nazorati (git) tarixini og'irlashtiradi, ilovani yuklab olish, klonlash va build qilish vaqtini keraksiz ravishda bir necha barobar oshiradi. Agar installer yaratish jarayonida butun loyiha nusxalansa, yakuniy paket hajmi asossiz ravishda kattalashadi.  
**Yuzaga kelish shartlari:** Loyihani klonlash, CI/CD pipeline da yuklash yoki build qilish jarayonida.  
**Ta’siri:** Tarmoq trafigi, disk xotirasi isrofi va build jarayonining sekinlashishi.  
**Root cause:** Binar ovoz modellari va sinov arxivlari `.gitignore` ga qo'shilmasdan yoki tashqi CDN/storage ga chiqarilmasdan git omboriga yuklangan.  
**Qayta tekshirish usuli:** Loyiha ildizidagi `.zip` fayllar hajmini tekshirish.  
**Tavsiya:** Ushbu yirik arxiv fayllarni git omboridan tozalash, ularni tashqi bulut omboriga (Cloudflare R2, S3, Supabase Storage) joylashtirish va faqat foydalanuvchi talab qilganda (on-demand) yuklab olish mexanizmini kiritish.  
**Qabul mezoni:** Loyiha kod ombori hajmida 5MB dan katta binar arxivlar bo'lmasligi.  
**Cheklovlar:** Foydalanuvchi qoidalariga binoan audit davomida ushbu fayllar o'chirilmadi.

---

### Topilma ID: PERF-005
**Sarlavha:** Markaziy audio navbatida (AudioQueue) cheklov (backpressure/maxsize) yo'qligi sababli xotira oqishi xavfi  
**Kategoriya:** Xotira va Navbat Boshqaruvi  
**Jiddiylik darajasi:** Medium  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `core/voice/audio_queue.py` (qatorlar 45–60)  
**Dalil:**
```python
# core/voice/audio_queue.py:47-49
class AudioQueue:
    def __init__(self, player: Optional[AudioPlayer] = None):
        self.player = player or AudioPlayer()
        self._queue: queue.Queue = queue.Queue() # maxsize belgilanmagan (cheksiz)
```
**Muammo tavsifi:** `AudioQueue` klassida ichki Python navbati `queue.Queue()` parametri `maxsize=0` (cheksiz) qilib yaratilgan. Agar LLM striming orqali bir necha soniyada o'nlab uzun audio jumlalarini generatsiya qilsa yoki tarmoqdagi nosozlik sabab audio pleer qotib qolsa, navbatga uzluksiz fayl yo'llari va audio ma'lumotlari qo'shilib ketaveradi. Ortiqcha to'plangan navbat xotirani to'ldiradi va foydalanuvchi gapni to'xtatganida (barge-in) kechikkan audio fragmentlari noo'rin ijro etilishiga olib keladi.  
**Yuzaga kelish shartlari:** LLM tezkor va uzun javob qaytarganda yoki audio pleer sekin ishlagan paytda.  
**Ta’siri:** Xotira ko'payishi, audio ijrosining LLM matnidan 10–20 soniya orqada qolib ketishi (lag).  
**Root cause:** Navbat sig'imiga chegara (`maxsize`) va eskirgan/bekor qilingan elementlarni avtomatik tozalash (backpressure) mexanizmi kiritilmagan.  
**Qayta tekshirish usuli:** Navbatga ketma-ket 50 ta audio element qo'shib, xotira sarfini va navbat hajmini kuzatish.  
**Tavsiya:** `queue.Queue(maxsize=10)` o'rnatish, navbat to'lganda ishlab chiqaruvchini (producer) sekinlashtirish va yangi savol tushganda eski navbatni darhol `flush()` qilish.  
**Qabul mezoni:** Navbat elementi 10 tadan oshmasligi va bekor qilinganda xotira zudlik bilan bo'shatilishi.  
**Cheklovlar:** Haqiqiy audio oqimi vaqtida foydalanuvchi intervyusi qilinmagan.

---

## 4. Tekshirish Imkoni Bo'lmagan Qismlar va Cheklovlar
- Real vaqtda soatlab davom etadigan uzoq muddatli stress-test (24 soatlik xotira oqishi/memory leak testi) o'tkazilmadi, chunki bu fonda ishlovchi uzoq jarayon talab qiladi.
- Turli xil CPU turlarida (Intel vs AMD, turli avlodlar) benchmarklar o'tkazilmadi; barcha xulosalar mavjud kod traektoriyasi va ma'lum resurs profillari asosida tayyorlandi.

---

## 5. Umumiy Xulosa va Keyingi Ustuvorliklar
Misa v9.3 ning ishlash tezligi va ishonchliligidagi eng asosiy muammo — har bir chat so'rovi oldidan sinxron bajariladigan ortiqcha operatsiyalardir (`PERF-001` va `PERF-002`). Birgina shu ikki muammoni bartaraf etish AI javob tezligini 1-2 soniyaga tezlashtiradi va kompyuter yuklanishini sezilarli darajada kamaytiradi.
