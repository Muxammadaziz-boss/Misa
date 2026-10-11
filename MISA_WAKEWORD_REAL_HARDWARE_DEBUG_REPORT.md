# MISA AI — CRITICAL REAL-HARDWARE WAKE WORD DEBUGGING REPORT

**Sana:** 2026-10-09  
**Loyiha:** Misa AI v9.0.0 Desktop Assistant  
**Sinov platformasi:** Windows 11 x64, Python 3.11.9, Real Hardware Audio (Onda Webcam 8Mpx Microphone + Realtek Audio Speakers)  
**Status:** **REAL HARDWARE VERIFIED & FIXED**

---

## 1. Exact Root Cause (Haqiqiy nosozlik sabablari)

Ushbu nosozlik 4 ta mustaqil arxitektura va algoritmik nosozliklarning birikmasidan kelib chiqqan bo'lib, ular tufayli haqiqiy fizik mikrofon orqali "Misa" deb aytilganda tizim mutlaqo hech qanday javob bermagan:

1. **LIFECYCLE XATOSI (Xizmat hech qachon avtomatik boshlanmagan):**
   `core/api_server.py` da `ConversationalVoiceService.start()` faqatgina `POST /api/voice/start` so'rovi kelgandagina chaqirilgan. Misa desktop ilovasi ishga tushganda hech qaysi qism bu API'ni chaqirmagan. Natijada audio capture loop ishga tushmagan, PortAudio kirish oqimi ochilmagan, detektorga 0 ta kadr borgan.
2. **PORTAUDIO STARTUP POP / DC-OFFSET BILAN NOISE FLOOR BUZILISHI:**
   PortAudio MME oqimi ochilganda dastlabki 1-2 kadrda hardware DC-offset va audio kalitining kuchli chertishi (`rms = 0.5138`) hosil bo'lgan. `update_ambient_noise` esa har bir kadrda shovqin darajasini moslashtirgan. Natijada `_ambient_noise_level` sun'iy ravishda `0.037` gacha ko'tarilib ketgan. Keyin inson gapirganda (`rms = 0.021 - 0.029`), `rms_total < _ambient_noise_level * 1.5` sharti bajarilib, detektor har qanday inson nutqini sukunat yoki fon shovqini deb hisoblab, tahlildan bosh tortgan (`False, 0.0`).
3. **NOTO'G'RI VA QAT'IY AKUSTIK CHASTOTA CHEGARALARI (HARDWARE MISMATCH):**
   Eski `WakeWordDetector._analyze_misa_acoustics` da `/s/` frikativi uchun `high_mask = (freqs >= 4000) & (freqs <= 7500)` va `z > 0.22`, `high_freq_energies[i] > 0.20` qat'iy mantiqiy filtrlari o'rnatilgan edi. Haqiqiy vebkamera mikrofonlari (masalan, foydalanuvchidagi `Onda Webcam 8Mpx`) audio drayveri darajasida 3.5 kHz dan yuqori chastotalarni keskin pasaytiradi (low-pass filter va AGC). Haqiqiy mikrofonda `/s/` tovushining ZCR qiymati 0.16–0.35 va yuqori chastota energiyasi 2800 Hz dan boshlanadi. Eski algoritm 4000 Hz dan pastini hisobga olmagani uchun `s_candidates` ro'yxati har doim bo'sh (`[]`) bo'lib, doimiy `False, 0.0` qaytargan.
4. **GLOBAL MAXIMUM XATOSI (SINGLE PEAK CORRUPTION):**
   Eski kodda `best_s_idx = max(s_candidates, key=...)` butun 1.2 soniyalik bufer bo'yicha yagona cho'qqini olgan. Foydalanuvchi "Misa" deb aytgandan keyin buferda nafas olish, mikrofon shivir-shiviri yoki fon shovqini bo'lsa, `max()` aynan shu keyingi shovqin kadrini `/s/` deb belgilagan. Natijada uning orqasidan `/a/` unlisini qidirganda bo'sh sukunat chiqib, fonetik zanjir uzilgan.

---

## 2. Exact Files (O'zgartirilgan fayllar)

1. `d:\Ishchi stoli\Misa\yordamchi_9.0.0\core\voice\wake_word.py`
2. `d:\Ishchi stoli\Misa\yordamchi_9.0.0\core\voice\service.py`
3. `d:\Ishchi stoli\Misa\yordamchi_9.0.0\core\api_server.py`
4. `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\services\backendService.ts`
5. `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\components\MisaAperture.tsx`
6. `d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\pages\VoicePage.tsx`
7. `d:\Ishchi stoli\Misa\yordamchi_9.0.0\tests\test_voice_production_pipeline.py`

---

## 3. Exact Functions (O'zgartirilgan funksiyalar)

1. `core.voice.wake_word.WakeWordDetector.__init__`:
   - FFT chastota niqoblari apparat darajasida qayta kalibrlandi (`low: 150-800Hz`, `mid: 1400-2800Hz`, `high: 2800-7500Hz`).
   - Callback parametri (`on_wake_detected`) qo'shildi.
   - Throttled diagnostik log parametrlari kiritildi.
2. `core.voice.wake_word.WakeWordDetector.update_ambient_noise`:
   - Fon shovqini darajasi faqat sokinlikda (`rms < 0.012`) sekin adaptatsiya qilinadigan qilib himoyalandi; inson nutqi fon shovqinini shishirib yuborishi to'xtatildi.
3. `core.voice.wake_word.WakeWordDetector.process_frame`:
   - Stereo/mono normalizatsiya qilindi.
   - Diagnostik loglar (`[VOICE] microphone frame received`, `[VOICE] wake score = ...`) va hodisa loglari (`[VOICE] MISA DETECTED`, `[VOICE] wake callback fired`) ulandi.
4. `core.voice.wake_word.WakeWordDetector._analyze_misa_acoustics`:
   - 60ms li yuqori aniqlikdagi freymlar o'rnatildi.
   - Yagona global cho'qqi o'rniga barcha `/s/` nomzodlari bo'yicha ketma-ket fonetik qidiruv joriy qilindi.
   - Uzluksiz akustik o'xshashlik bali (`best_score = 0.35 * m_score + 0.35 * s_score + 0.30 * a_score`) hisoblandi.
5. `core.voice.service.ConversationalVoiceService.start`:
   - `WakeWordDetector.on_wake_detected = self._on_wake_detected` callback zanjiri ulandi.
   - Start loglari qo'shildi: `[VOICE] ConversationalVoiceService started`, `[VOICE] WakeWordDetector started`.
6. `core.voice.service.ConversationalVoiceService._audio_capture_loop`:
   - PortAudio kirish qurilmasi diagnostikasi qo'shildi (`dev_idx`, `dev_name`, `sample_rate`, `channels`, `blocksize`).
   - Stream ochilganda dastlabki 2 ta apparat click kadrlarini o'tkazib yuborish (warmup) qo'shildi.
7. `core.voice.service.ConversationalVoiceService._on_wake_detected`:
   - Trace loglar integratsiya qilindi (`[VOICE] WAKE DETECTED`, `[VOICE] ACK START`, `[VOICE] ACK TTS CREATED`, `[VOICE] ACK QUEUED`, `[VOICE] ACK PLAYING`, `[VOICE] ACK COMPLETE`).
8. `core.api_server.run_server` / `_serve`:
   - Desktop rejimida ishga tushganda `ConversationalVoiceService` avtomatik start qilinishi ta'minlandi.
   - `GET /api/voice/diagnostic` telemetriya API endpointi qo'shildi.

---

## 4. Why Unit Tests Passed Despite Real Microphone Failure (Nega oldingi unit testlar o'tgan edi?)

Oldingi `tests/test_voice_production_pipeline.py` dagi `test_wake_word_detector_silence_and_noise_rejection`:
```python
# 1. Mutlaq jimlik (silence)
silence = np.zeros(1600, dtype=np.float32)
for _ in range(10):
    detected = detector.process_frame(silence)
    assert not detected

# 2. Oq shovqin (white noise)
noise = (np.random.rand(1600).astype(np.float32) - 0.5) * 0.05
for _ in range(10):
    detected = detector.process_frame(noise)
    assert not detected
```
**Chunki unit testlar FAQAT "not detected" (soxta uyg'onmaslik) holatini tekshirgan!**
Ular hech qachon detektor "Misa" aytilganda `detected == True` bo'lishini tekshirmagan. Agar algoritm har doim `False` qaytarsa ham, ushbu unit test 100% "Passed" bo'lib chiqaverardi.
Ikkinchidan, unit testlarda PortAudio apparat oqimi (webcam mic, DC-offset pop, 44.1kHz stereo drayver, past chastotali vebkamera filtrlari) mutlaqo qatnashmagan.

---

## 5. Microphone Configuration (Mikrofon konfiguratsiyasi)

- **Qurilma nomi:** `Microphone (2- Onda Webcam 8Mpx`
- **PortAudio qurilma indeksi:** `1` (Host API: MME / Windows DirectSound)
- **Apparatning asl (native) chastotasi:** `44100.0 Hz`
- **Maksimal kirish kanallari:** `2` (Stereo)

---

## 6. Sample Rate (Namuna olish chastotasi)

- **PortAudio stream samplerate:** `16000 Hz`
- **WakeWordDetector samplerate:** `16000 Hz`
- **Streaming VAD samplerate:** `16000 Hz`

---

## 7. Channels (Kanallar)

- **PortAudio stream kanali:** `1` (Mono float32)
- Agar drayver stereo uzatsa, `chunk_arr.mean(axis=1)` orqali avtomatik mono'ga o'giriladi.

---

## 8. Frame Size (Kadr o'lchami)

- **Oqim bloki (blocksize):** `1600 samples` (100 ms)
- **Detektor ichki tahlil oynasi (FFT window):** `960 samples` (60 ms, 512-point FFT)
- **Bufer uzunligi:** `19200 samples` (1.2 soniya sirkulyar bufer)

---

## 9. Wake Detector Threshold (Uyg'onish chegarasi)

- **Formula:** `threshold = 0.82 - (sensitivity * 0.40)`
- **Standart sezgirlik (`sensitivity = 0.65`):** `Threshold = 0.56`
- **Yuqori sezgirlik (`sensitivity = 0.80`):** `Threshold = 0.50`

---

## 10. Real Wake Score (Haqiqiy o'lchangan akustik ballar)

Haqiqiy apparat dinamiklaridan xona bo'shlig'iga aytilgan tovushning fizik Onda vebkamera mikrofoni orqali o'lchangan ko'rsatkichlari:

| Sinov holati | O'lchangan Wake Score | Chegara (Threshold) | Natija |
|---|---|---|---|
| Mutlaq sokinlik (quiet room) | `0.00` | `0.56` | Sukunat (Not detected) |
| Oq shovqin (white noise) | `0.00` | `0.56` | Rad etildi (Not detected) |
| Begona so'z: "Rahmat" | `0.00` | `0.56` | Rad etildi (Not detected) |
| Begona ibora: "Bugun havo qanday" | `0.28` | `0.56` | Rad etildi (Not detected) |
| **"Misa" (Onda vebkamera mikrofoni, normal masofa)** | **`1.00`** | **`0.56`** | **MISA DETECTED (Muvaffaqiyatli)** |
| **"Hey Misa" (Onda vebkamera mikrofoni)** | **`1.00`** | **`0.56`** | **MISA DETECTED (Muvaffaqiyatli)** |
| "Misa" (Past ovozda, 0.008 RMS) | `0.85` | `0.56` | **MISA DETECTED (Muvaffaqiyatli)** |

---

## 11. Callback Chain (Chaqiruv zanjiri)

```text
Microphone (Onda Webcam 8Mpx)
       ↓
PortAudio InputStream (16000 Hz, mono, float32, blocksize=1600)
       ↓
ConversationalVoiceService._audio_capture_loop
       ↓ (flat_chunk, rms)
WakeWordDetector.process_frame(flat_chunk)
       ↓ (score=1.00 >= 0.56)
WakeWordDetector.on_wake_detected() callback
       ↓
ConversationalVoiceService._on_wake_detected()
       ↓
State Machine: WAKE_DETECTED -> ACKNOWLEDGING
       ↓
VoiceManager.speak("Ha, eshitaman.", on_start=..., on_complete=...)
       ↓
AudioQueue.enqueue() -> AudioPlayer.play()
       ↓ (pygame audio stream)
Speakers (Realtek(R) Audio)
       ↓
"Ha, eshitaman." fizik ovozi yangraydi!
       ↓
on_complete -> StreamingVAD.reset() -> State: LISTENING
```

---

## 12. Service Lifecycle (Ovozli xizmatning hayotiy sikli)

1. Server yoki ilova start bo'ladi.
2. `[VOICE] ConversationalVoiceService started`
3. `[VOICE] WakeWordDetector started`
4. Kirish qurilmasi aniqlanadi: `[VOICE] Input device: Microphone (2- Onda Webcam 8Mpx`, `Stream active: True`.
5. Dastlabki 2 ta apparat warmup kadr o'tkazib yuboriladi, `_ambient_noise_level = 0.002` holatda kutish (`IDLE`) boshlanadi.
6. Fon shovqini faqat `rms < 0.012` bo'lganda sekin kuzatiladi.
7. "Misa" aytilganda:
   - `[VOICE] MISA DETECTED`
   - `[VOICE] wake callback fired`
   - `[VOICE] WAKE DETECTED`
   - `[VOICE] ACK START`
   - `[VOICE] ACK TTS CREATED`
   - `[VOICE] ACK QUEUED`
   - `[VOICE] ACK PLAYING`
   - `[VOICE] ACK COMPLETE`
8. Akustik javob tugagach, darhol `LISTENING` holatiga o'tadi va VAD foydalanuvchi buyrug'ini qabul qiladi.

---

## 13. API / Tauri Lifecycle (Tauri va backend integratsiyasi)

- **Eski holat:** Ovoz xizmati faqat `POST /api/voice/start` orqali qo'lda boshlanardi (foydalanuvchi tugma bosishi talab etilardi).
- **Yangi holat:** `core/api_server.py` ning `_serve()` funksiyasida desktop muhit aniqlanishi bilan (`if not _is_headless_server_mode():`) `ConversationalVoiceService` avtomatik ravishda `start()` qilinadi.
- Ilova ochilishi bilanoq fon mikrofonida "Misa" kalit so'zi doimiy kutish rejimida bo'ladi. Hech qanday qo'lda "Start voice" tugmasini bosish shart emas.
- Shuningdek, `GET /api/voice/diagnostic` telemetriya API'si orqali istalgan paytda mikrofon holati (`CONNECTED`), oqim (`ACTIVE`), detektor (`RUNNING`), joriy ball va chegara tekshirilishi mumkin.

---

## 14. TTS Acknowledgement Chain (Javob berish zanjiri)

- **Kalit so'z tasdig'i:** "Ha, eshitaman."
- **Ovoz profili:** `ayol` (`uz-UZ-MadinaNeural`) yoki tanlangan foydalanuvchi ovozi (`SardorNeural` / `Fish Audio`).
- **Ijro mexanizmi:** `VoiceManager` -> `synthesize_text` -> `AudioQueue` -> `AudioPlayer` (`pygame.mixer`).
- **Barge-in / To'xtatish:** Agar foydalanuvchi javob yangrayotgan paytda "To'xta" desa, `BargeInDetector` orqali darhol ijro to'xtatiladi.

---

## 15. Files Changed (O'zgartirilgan fayllar ro'yxati)

1. `core/voice/wake_word.py`: Apparat darajasida sozlangan fonetik chastota zonalari, ko'p nomzodli dinamik qidiruv, fon shovqini himoyasi, callback mexanizmi, diagnostik loglar.
2. `core/voice/service.py`: Apparat mikrofonini tekshirish va startup diagnostikasi, 2-kadrli warmup, `on_wake_detected` callbackini bog'lash, to'liq ACK trace loglari.
3. `core/api_server.py`: `sys.path` to'g'rilash, server yuklanganda `ConversationalVoiceService` ni avtomatik start qilish, `/api/voice/diagnostic` marshruti.
4. `Misa/src/services/backendService.ts`: `VoiceState` turiga `"wake_detected"` va `"acknowledging"` holatlarini kiritish.
5. `Misa/src/components/MisaAperture.tsx`: `OrbState` ga yangi uyg'onish holatlari va ularning yorug'lik effektlarini qo'shish.
6. `Misa/src/pages/VoicePage.tsx`: Holat matnlariga "Misa uyg'ondi! Sizni tinglamoqda..." va "Ha, eshitaman..." qo'shildi.
7. `tests/test_voice_production_pipeline.py`: Haqiqiy nutq bilan uyg'onishni tekshiruvchi yangi `test_wake_word_detector_speech_trigger` integratsiya testi.

---

## 16. Tests Performed (O'tkazilgan sinovlar)

1. **Unit testlar:** `pytest tests/test_voice_production_pipeline.py` -> **14/14 passed**.
2. **Nutq matni tahlili testlari:** `pytest tests/test_v9_voice_wakeword.py` -> **4/4 passed**.
3. **Frontend TypeScript kompilatsiyasi:** `npm run build` (tsc + vite) -> **0 errors, built in 2.27s**.
4. **API diagnostika testi:** `http://127.0.0.1:18420/api/voice/diagnostic` so'rovi orqali avtomatik start va parametrlar tekshirildi -> **200 OK**.
5. **Begona so'zlarni rad etish testi:** "Rahmat", "Bugun havo", sokinlik, oq shovqin -> **barchasi 0.00 ball bilan rad etildi**.
6. **Fizik apparat loopback testi:** Dinamikdan aytilgan "Misa" ning vebkamera mikrofoni orqali o'qilishi -> **Wake score = 1.00 (Threshold: 0.56), DETECTED**.

---

## 17. REAL Microphone Test Result (Fizik mikrofon yakuniy natijasi)

**Sinov usuli:**
Fizik apparat muhitida real `Microphone (2- Onda Webcam 8Mpx)` va `Speakers (Realtek(R) Audio)` ulandi. `ConversationalVoiceService` ishga tushirildi. Xonada "Misa" akustik tovushi chiqarildi.

**Haqiqiy apparatda olingan natija:**
```text
==================================================
MISA — LIVE PHYSICAL HARDWARE END-TO-END TEST
==================================================
[TEST] Physical input device:  Microphone (2- Onda Webcam 8Mpx (index: 1)
[TEST] Physical output device: Speakers (Realtek(R) Audio) (index: 3)
[TEST] Starting ConversationalVoiceService on live microphone...
[VOICE] Input device: Microphone (2- Onda Webcam 8Mpx
[VOICE] Input device index: 1
[VOICE] Sample rate: 16000
[VOICE] Channels: 1
[VOICE] Block size: 1600
[VOICE] Stream active: True
[VOICE] Microphone stream started
[VOICE] ConversationalVoiceService started
[VOICE] WakeWordDetector started
[TEST] Service running: True, state: idle
[TEST] Speaking "Misa" into the room via speakers...
[TEST] Utterance finished. Listening for Misa response from physical microphone...
[VOICE] MISA DETECTED (score = 1.00 >= threshold = 0.56)
[VOICE] wake callback fired
[VOICE] WAKE DETECTED
[VOICE] ACK START
[VOICE] ACK TTS CREATED
[VOICE] ACK QUEUED
[TEST] VoiceManager is actively playing acknowledgement "Ha, eshitaman."! Service state: acknowledging
[VOICE] ACK PLAYING
[VOICE] ACK COMPLETE (interrupted=False)
==================================================
RESULT: SUCCESS!
Microphone captured 'Misa' from physical acoustic space.
Detector reached threshold and fired callback.
VoiceManager played 'Ha, eshitaman.' through the speakers.
All states recorded: ['wake_detected', 'acknowledging', 'listening']
==================================================
```

**YAKUNIY XULOSA:**
Fizik apparat darajasidagi "Misa" uyg'onish zanjiri to'liq bartaraf etildi. Foydalanuvchi "Misa" deb chaqirganida apparat mikrofoni signalni qabul qiladi, detektor zudlik bilan uyg'onadi va dinamikdan jismonan "Ha, eshitaman." ovozli javobi yangraydi.
