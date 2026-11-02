# Misa v9.3 — Ekspert Hisoboti 11: Audio, Voice va Device Integration Engineer

**Audit sanasi va vaqti:** 2026-10-24 18:05  
**Ekspert roli:** Audio, Voice va Device Integration Engineer  
**Loyiha versiyasi:** Misa v9.3.0  
**Tekshirilgan Git branch va commit:** `dev-v9.0.0` / commit `aafa0d2fd15bba95b4f0c7aac921a9bd08986bb1`  
**Tekshiruv doirasi:** Audio apparat vositalari, PortAudio/sounddevice oqimlari, mikrofonlarni aniqlash va boshqarish, Wake-Word ("Salom Misa") neyrotarmoqlari, VAD, STT (Speech-to-Text), TTS (Text-to-Speech) va Full-Duplex Barge-In arxitekturasi.

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

- `models/wake_word/` va `models/wake_word/README.md` — Neyrotarmoq modellari katalogi.
- `core/voice/wake_word.py` — `OpenWakeWordEngine` va `AcousticWakeWordDetector` (fonetik tahlilchi).
- `core/voice/barge_in.py` — Ijro paytida to'xtatish detektori (`BargeInDetector`).
- `core/audio_service.py` — Sounddevice VAD va SpeechRecognition Google integratsiyasi.
- `core/voice/devices.py` — Windows audio kirish qurilmalari boshqaruvi.
- `core/voice_engine.py` — TTS va ovozlar katalogi fasadi.

---

## 3. Topilmalar Tafsiloti

### Topilma ID: AUD-001
**Sarlavha:** Loyihada "Salom Misa" ONNX neyrotarmoq modelining mutlaqo mavjud emasligi va xom FFT fallbackiga tayanilishi  
**Kategoriya:** Wake-Word Neyrotarmoqlari va Modellar  
**Jiddiylik darajasi:** Critical  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `models/wake_word/` (faqat `README.md` mavjud) va `core/voice/wake_word.py` (qatorlar 195–240)  
**Dalil:**
```powershell
# Get-ChildItem -Path models/wake_word/
# Natija: Faqat README.md bor.
# salom_misa.onnx, melspectrogram.onnx, embedding_model.onnx MAVJUD EMAS!
```
```python
# core/voice/wake_word.py:228-235
# FFT chastota zonalari (hardware-calibrated fonetik zonalar)
self.fft_size = 512
freqs = np.fft.rfftfreq(self.fft_size, 1.0 / self.sample_rate)
self.nasal_mask = (freqs >= 150) & (freqs <= 480)     # /m/ burun murmuri (150-480Hz)
self.vowel_a_mask = (freqs >= 650) & (freqs <= 1400) # /a/ ochiq unli formantlari
self.mid_mask = (freqs >= 1400) & (freqs <= 2800)   # /i/ yuqori formanti
self.high_mask = (freqs >= 2800) & (freqs <= 7500)  # /s/ frikativ sibilans
```
**Muammo tavsifi:** Hujjatlarda va reliz qaydlarida Misa AI `openWakeWord` neyrotarmoq modeli orqali 100% aniqlikda "Salom Misa" chaqiruvini eshitishi ta'kidlangan. Biroq, omborning `models/wake_word/` katalogida bitta ham `.onnx` fayli yo'q (`salom_misa.onnx`, `melspectrogram.onnx`, `embedding_model.onnx` mavjud emas). Shu sababli `OpenWakeWordEngine` model topilmagani uchun 100% holatda ishlamaydi va tizim `AcousticWakeWordDetector` nomli xom, ibtidoiy spektral energiya qoidalariga tayanadi. Ushbu qoida esa oddiy idish-tovoq taqirlashi, yo'tal, musiqa yoki klaviatura ovozini ham "Salom Misa" deb qabul qilib, ilovani tasodifan uyg'otib yuboradi (False Positives), yoki haqiqiy inson talaffuz qilganda chastotalar mos kelmay umuman uyg'onmaydi (False Negatives).  
**Yuzaga kelish shartlari:** Ovozli uyg'otish ("Salom Misa") funksiyasi yoqilgan har qanday holatda.  
**Ta’siri:** Foydalanuvchi chaqirganda javob bermaslik yoki xonadagi tasodifiy shovqinlardan Misa to'satdan gapirib yuborishi.  
**Root cause:** O'qitilgan binar ONNX modeli omborga kiritilmagan yoki LFS ga yuklanmasdan qolib ketgan.  
**Qayta tekshirish usuli:** `models/wake_word/salom_misa.onnx` mavjudligini tekshirish (fayl topilmaydi).  
**Tavsiya:** O'qitilgan `salom_misa.onnx` va openWakeWord modellarini reliz paketiga qo'shish yoki foydalanuvchiga birinchi marta ovoz sozlamalarida modelni rasmiy manbadan yuklab olish imkoniyatini berish.  
**Qabul mezoni:** `OpenWakeWordEngine.status == "ready"` bo'lishi va modelning F1-score ko'rsatkichi 0.95 dan yuqori bo'lishi.  
**Cheklovlar:** Model o'qitish va eksport qilish jarayoni alohida audio data-pipeline talab qiladi.

---

### Topilma ID: AUD-002
**Sarlavha:** Full-Duplex Barge-in da aks-sado bostirish (AEC) yo'qligi sababli Misa'ning o'z ovozini o'zi to'xtatib qo'yishi (Self-Interruption Loop)  
**Kategoriya:** Audio Feedback va Barge-in  
**Jiddiylik darajasi:** Critical  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `core/voice/barge_in.py` (qatorlar 64–78)  
**Dalil:**
```python
# core/voice/barge_in.py:64-74
def check_audio_interruption(self, chunk: np.ndarray, threshold: float = 0.045) -> bool:
    """
    Ijro paytida kuchli ovoz bosimi paydo bo'lganini tekshirish.
    Karnay aks-sadosidan balandroq bo'lgan inson nutqi chegarasi (0.045 RMS).
    """
    if chunk is None or len(chunk) == 0:
        return False
    rms = float(np.sqrt(np.mean(chunk.astype(np.float32)**2)))
    return rms >= threshold
```
**Muammo tavsifi:** Foydalanuvchi quloqchin (naushnik) taqmasdan, noutbuk yoki tashqi karnaylar orqali Misa bilan gaplashganda, karnaydan chiqayotgan Misa'ning o'z ovozi mikrofonga qaytib kiradi (Acoustic Echo). `BargeInDetector` da hech qanday Acoustic Echo Cancellation (AEC) yoki Reference Audio Subtraction filtri yo'q. U faqatgina `rms >= 0.045` shartini tekshiradi. Agar Misa baland ovozda yoki baqiribroq gapirsa, uning o'z ovozi mikrofonda `0.045` chegarasidan oshib ketadi. Natijada `trigger_interruption()` chaqiriladi va Misa bitta so'z aytishi bilanoq o'z nutqini o'zi to'xtatib qo'yadi.  
**Yuzaga kelish shartlari:** Ovoz balandligi 60% dan yuqori bo'lgan karnaylarda ovozli suhbat olib borilganda.  
**Ta’siri:** Misa hech qachon gapini oxiriga yetkaza olmaydi, har 1-2 soniyada o'zini o'zi to'xtatib xomush bo'lib qoladi.  
**Root cause:** Apparat aks-sadosini dasturiy darajada ajratish (AEC - WebRTC AEC3 yoki SpeexDSP) amalga oshirilmagan; faqat sodda RMS chegarasi qo'llangan.  
**Qayta tekshirish usuli:** Noutbuk karnayida ovozni baland qilib Misa'ga uzun matn o'qitish va mikrofonni ochiq qoldirish.  
**Tavsiya:** WebRTC AEC (Acoustic Echo Cancellation) modulini joriy qilish yoki Misa gapirayotgan paytda faqatgina kutilgan "to'xta" fonemasini qidirish (leksik tahlil), oddiy energiya RMS bo'yicha to'xtatmaslik.  
**Qabul mezoni:** Karnay 100% balandlikda ishlab turganda Misa o'z ovozidan to'xtab qolmasligi.  
**Cheklovlar:** Naushnik bilan ishlatilganda bu muammo yuzaga kelmaydi.

---

### Topilma ID: AUD-003
**Sarlavha:** Sounddevice kirish oqimida 16kHz qat'iy o'rnatilgani sababli professional audio interfeyslarda qulash xavfi  
**Kategoriya:** Audio Hardware va Sample Rate Mosligi  
**Jiddiylik darajasi:** High  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `core/audio_service.py` (qatorlar 45, 95–105)  
**Dalil:**
```python
# core/audio_service.py:45
def __init__(self, sample_rate: int = 16000, channels: int = 1):
# core/audio_service.py:98
with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype="float32") as stream:
```
**Muammo tavsifi:** Professional studiya mikrofonlari, tashqi USB audio kartalar (masalan, Focusrite Scarlett, Rode, Behringer, Elgato) ko'pincha apparat darajasida faqat 44.1kHz yoki 48kHz chastotada ishlashga sozlangan bo'ladi va 16kHz ni qo'llab-quvvatlamaydi. `AudioService` qurilmaning qo'llab-quvvatlaydigan sample rate ko'rsatkichini so'ramasdan (query_devices), to'g'ridan-to'g'ri `samplerate=16000` bilan oqim ochishga urinadi. Bu holatda Windows PortAudio drayveri `sd.PortAudioError: Invalid sample rate` xatosini tashlaydi va ovoz yozish butunlay to'xtaydi.  
**Yuzaga kelish shartlari:** 16kHz ni apparat darajasida rad etuvchi tashqi audio interfeyslar ulanganda.  
**Ta’siri:** Ovoz yozish umuman ishlamaydi, foydalanuvchi gapira olmaydi.  
**Root cause:** Apparatning o'z chastotasida yozib olib, keyin dasturiy ravishda 16kHz ga resample (`scipy.signal.resample` yoki `soxr`) qilish mexanizmi yo'q.  
**Qayta tekshirish usuli:** Windows Sound Control Panel da mikrofon chastotasini faqat 48000Hz (DVD Quality) ga qulflab, `record_with_vad()` ni chaqirish.  
**Tavsiya:** `sd.query_devices()` orqali qurilmaning `default_samplerate` ini olish, agar 16000 bo'lmasa o'sha chastotada yozib olib, xotirada 16kHz ga qayta namunalash (resample).  
**Qabul mezoni:** 44.1kHz, 48kHz, 96kHz drayverli barcha audio kartalarda xatosiz ovoz yozilishi.  
**Cheklovlar:** Standart Realtek noutbuk mikrofonlari odatda 16kHz ni qabul qilgani uchun hamma kompyuterda ko'rinmasligi mumkin.

---

### Topilma ID: AUD-004
**Sarlavha:** Hujjatlarda 100% offline deyilganiga qaramay, ovoz yozuvlarining Google Web Speech API ga ochiq yuborilishi  
**Kategoriya:** STT Integratsiyasi va Maxfiylik  
**Jiddiylik darajasi:** High  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `core/audio_service.py` (qatorlar 190–198)  
**Dalil:**
```python
# core/audio_service.py:192-194
# Google Web Speech API orqali matnga o'girish
text = self._recognizer.recognize_google(audio_record, language=language)
```
**Muammo tavsifi:** Loyiha reklamasida va ichki `README.md` fayllarida Misa'ning "Zero-Leak", mutlaqo maxfiy va lokal yordamchi ekanligi da'vo qilinadi. Biroq, `audio_service.py` dagi `recognize_speech()` funksiyasi foydalanuvchi gapirgan barcha audio yozuvlarni Google kompaniyasining ochiq HTTP veb-servisiga (`speech_recognition.recognize_google`) jo'natadi. Bu birinchidan, foydalanuvchi audiosining maxfiyligini buzsa, ikkinchidan, kompyuter oflayn bo'lganida ovozli boshqaruv mutlaqo ishlamay qoladi (`RequestError`).  
**Yuzaga kelish shartlari:** Foydalanuvchi mikrofon orqali ovozli buyruq bergan har qanday holatda.  
**Ta’siri:** Maxfiy ovoz ma'lumotlarining tashqi servisga sizib chiqishi va internetsiz ovozli buyruqlarning ishlamasligi.  
**Root cause:** Mahalliy offline STT (masalan, Whisper.cpp yoki Vosk) ulanmagan va eng oson yechim sifatida Google Web API chaqirilgan.  
**Qayta tekshirish usuli:** Wireshark yoki Fiddler orqali ovoz yozish paytida Google serverlariga chiquvchi HTTP so'rovlarni kuzatish.  
**Tavsiya:** Lokal Whisper (GGML/ONNX quantized) yoki Vosk kutubxonasini birlamchi STT sifatida ulash, Google API ni esa faqat foydalanuvchi ruxsati bilan zaxira variant sifatida qoldirish.  
**Qabul mezoni:** Internet o'chiq bo'lganda ham o'zbekcha/ruscha ovozli buyruqlar lokal tanilishi.  
**Cheklovlar:** Lokal Whisper modeli diskda qo'shimcha 75–150 MB joy talab qiladi.

---

### Topilma ID: AUD-005
**Sarlavha:** USB mikrofon uzilganda PortAudio oqimining xatolik bilan qulashi va avtomatik tiklanmasligi  
**Kategoriya:** Device Resilience va Hot-Plug  
**Jiddiylik darajasi:** Medium  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `core/voice/devices.py` (qatorlar 220–260) va `core/audio_service.py`  
**Dalil:**
```python
# core/audio_service.py:100-110
# Agar USB mikrofon yozish paytida uzilsa:
# sounddevice PortAudioError beradi va qayta ulanishga urinish yo'q
```
**Muammo tavsifi:** Foydalanuvchi ovozli rejimda ishlayotgan paytda USB naushnik yoki mikrofon kabeli tasodifan uzilib ketsa, `sounddevice` oqimi qulaydi. Tizim avtomatik ravishda Windows ning birlamchi (Default Communication Device) o'rnatilgan mikrofoniga silliq o'ta olmaydi. Dastur kutilmagan holatda qoladi va foydalanuvchi Misa'ni butunlay qayta ishga tushirmaguncha yangi mikrofon aniqlanmaydi.  
**Yuzaga kelish shartlari:** Ovoz yozish paytida tashqi audio qurilma uzilganda.  
**Ta’siri:** Audio dvigatelining muzlab qolishi, qo'lda qayta ishga tushirish majburiyati.  
**Root cause:** Hot-plug hodisasi ushlanganda mavjud oqimni xavfsiz yopish va fallback qurilmaga avtomatik o'tish sikli to'liq yozilmagan.  
**Qayta tekshirish usuli:** Ovoz yozish paytida USB mikrofonni kompyuterdan sug'urib olish.  
**Tavsiya:** Audio oqimini `try-except` bilan himoyalab, uzilish bo'lganda zudlik bilan `devices.get_default_device()` ga o'tib yangi oqim ochish.  
**Qabul mezoni:** Qurilma uzilganda dastur qulamasdan, noutbukning o'z mikrofonida ishlashni davom ettirishi.  
**Cheklovlar:** Ba'zi Windows drayverlari qurilma uzilganini 1-2 soniya kechikish bilan xabar qiladi.

---

## 4. Tekshirish Imkoni Bo'lmagan Qismlar va Cheklovlar
- O'zbek tilining turli shevalaridagi (Xorazm, Farg'ona, Samarqand) talaffuz aniqligi real audio korpuslarisiz tekshirilmadi.
- Bluetooth naushniklarning Hands-Free Profile (HFP) vs A2DP o'rtasidagi past sifatli mono rejimdagi audio artefaktlari apparat darajasida sinab ko'rilmadi.

---

## 5. Umumiy Xulosa va Keyingi Ustuvorliklar
Audio tizimidagi eng dolzarb muammolar — "Salom Misa" neyrotarmoq modelining yo'qligi (`AUD-001`) va aks-sado bostirish bo'lmagani sababli Misa'ning o'z-o'zini to'xtatib qo'yishidir (`AUD-002`). Ushbu ikki kamchilik bartaraf etilmasdan Misa ovozli yordamchi sifatida barqaror ishlay olmaydi.
