# Misa AI — Xavfsizlik va Maxfiylik Auditi Hujjati (Privacy & Security Audit)

**Versiya:** 9.0.0 (Filial: `dev-v9.0.0`)
**Holat:** Yakunlangan va Sinovdan O'tgan
**Sana:** 2026-10-10

---

## 1. Umumiy Maxfiylik Arxitekturasi (Zero-Leak Architecture)

Misa AI foydalanuvchining shaxsiy daxlsizligi va maxfiy ma'lumotlarini himoya qilishni eng yuqori ustuvorlik deb biladi. Ovozli muloqot tizimi lokal birinchi tamoyili (local-first approach) asosida qurilgan bo'lib, uning har bir moduli qat'iy tekshiruvdan o'tkazilgan.

```
[ Mikrofon ]
     │
     ▼
[ sounddevice (16kHz PCM) ]
     │
     ├─► [ Wake-Word Detektori ] ───► 100% Offline (ONNX / Spektral Heuristic) — ZERO Network
     │
     └─► [ VAD (Ovoz Faolligi) ] ───► Lokal Bufer (RAM, no disk)
              │
              ▼
       [ STT Menejeri ]
              ├─► Offline Local STT (Vosk/Whisper): 100% Mahalliy
              └─► Online Google STT: Faqat foydalanuvchi ruxsati bilan (MISA_ALLOW_CLOUD_STT=1)
```

---

## 2. Modullar Bo'yicha Tarmoq Xatti-Harakati Matritsasi

| Komponent | Ijro Muhiti | Tarmoqqa Ulanish | Ruxsat / Nazorat Sharti | Xavfsizlik Kafolati |
| :--- | :--- | :--- | :--- | :--- |
| **Wake-Word Detektori** (`wake_word.py`) | Mahalliy (RAM) | **0% (Mutlaqo yo'q)** | Doimiy lokal | Hech qanday audio yoki ma'lumot tarmoqqa chiqmaydi (`test_zero_network_connections_during_detection` testi bilan isbotlangan) |
| **Offline STT** (`stt_provider.py`) | Mahalliy (CPU) | **0% (Mutlaqo yo'q)** | Doimiy lokal | Mahalliy model yo'q bo'lsa, halol "not_installed" qaytaradi, soxtalashtirmaydi |
| **Online Google STT** (`stt_provider.py`) | Tashqi Bulut | **Bor** (`google.com`) | `MISA_ALLOW_CLOUD_STT=1` | Foydalanuvchi sozlamasi orqali bloklanadi; faqat foydalanuvchi ruxsat berganda ishlaydi |
| **TTS (Ovoz Sintezi)** | Giprid | **Tanlovga bog'liq** | Foydalanuvchi ovoz turi | Mahalliy Windows SAPI (offline) yoki Edge-TTS (faqat matn jo'natiladi, audio qaytadi) |
| **AI Aql (LLM)** | Tashqi HTTPS | **Bor** (Gemini / OpenRouter) | Foydalanuvchi API kaliti | Faqat matnli so'rov yuboriladi; barcha kalitlar maskalanadi |

---

## 3. Wake-Word Aniqlash Auditi

### 3.1. Tarmoq So'rovlarining Yo'qligi
- Wake-word jarayonida (`OpenWakeWordEngine` va `AcousticWakeWordDetector`) hech qanday tashqi HTTP, WebSocket, DNS yoki TCP socket so'rovlari amalga oshirilmaydi.
- Avtomatik model yuklab olish taqiqlangan (`download_model=False`). Dastur ishga tushganda internetdan fayl qidirmaydi.
- **Tekshiruv dalili:** `tests/test_v9_wake_word_acoustic_evaluation.py` faylidagi `test_zero_network_connections_during_detection` testi `socket.socket.connect` ni monkeypatch qilib, 20 ta freym tahlili davomida 0 ta ulanish bo'lganini tasdiqladi.

### 3.2. Audio Yozuvlarni Saqlash
- Audio freymlar faqat RAM dagi aylanma buferda (1.2 soniya davomiyligida) saqlanadi.
- Wake-word tahlili davomida qattiq diskka `.wav`, `.mp3` yoki boshqa audio fayllar yozilmaydi.
- Jimlik yoki chalg'ituvchi tovushlar tahlil qilingach, RAM buferi eskisining ustiga yozilib tozalanadi.

---

## 4. STT va Bulutli Ovoz Auditi

1. **Halol Mahalliy Provayder:**
   - `OfflineLocalSTTProvider` tizimda haqiqiy Vosk yoki Whisper modeli o'rnatilmagan bo'lsa, soxta transkripsiya qaytarmaydi. U aniq `status="not_installed"` va `is_available() -> False` qaytaradi.
2. **Bulutli STT Nazorati:**
   - Foydalanuvchi maxfiylikni talab qilganda `MISA_ALLOW_CLOUD_STT=0` qilib sozlay oladi.
   - `STTManager` ruxsatsiz Google Speech API ga ulanmaydi va foydalanuvchiga audio bulutga chiqmasligini kafolatlaydi.

---

## 5. Loglar va Maxfiy Ma'lumotlarni Filtrlash (Redaction)

Tizim loglarida shaxsiy ma'lumotlar oqib ketmasligi uchun quyidagi choralar ko'rilgan:
1. **API Kalitlari:** Gemini (`AIza...`), OpenRouter (`sk-or-...`) va boshqa bearer tokenlar loglarda to'liq maskalanadi (`redact_sensitive_tokens`).
2. **Audio Ma'lumotlar:** Loggerga xom audio massivlari, PCM baytlari yoki base64 signallari chiqarilmaydi. Faqat xavfsiz sonli ko'rsatkichlar (masalan: `rms=0.015`, `score=0.72`) loglanadi.
3. **Foydalanuvchi Parollari va Tokenlari:** Supabase va OAuth callbacklarida tokenlar URL va xatolik matnlaridan darhol tozalanadi (`scrubUrlOAuthTokens`).

---

## 6. Xulosa va Qolgan Tavsiyalar

- Misa AI wake-word va ovoz moduli to'liq auditdan o'tdi va xavfsizlik talablariga javob beradi.
- Keyingi bosqichda to'liq offline ishlashni istagan foydalanuvchilar uchun ixcham offline Vosk o'zbekcha modeli (`models/stt/vosk-model-uz/`) ni bir martalik qo'lda o'rnatish imkoniyatini taqdim etish tavsiya etiladi.
