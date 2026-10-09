# Misa AI — "Salom Misa" openWakeWord Modelini Mahalliy O'qitish va Eksport Qilish Qo'llanmasi

Ushbu hujjat Misa AI uchun `"Salom Misa"` uyg'otuvchi so'zini rasmiy [openWakeWord](https://github.com/dscripka/openWakeWord) arxitekturasida lokal ravishda o'qitish, ONNX formatiga eksport qilish va tizimga integratsiya qilish bo'yicha to'liq qo'llanmani taqdim etadi.

---

## 1. Nazariy Asos va O'qitish Arxitekturasi

openWakeWord modellari ikki bosqichli neyrotarmoq tizimiga tayanadi:
1. **Audio xususiyat ekstraktori (Feature Extractor):**
   - 16kHz mono audio signali olinadi.
   - `melspectrogram.onnx` orqali Mel-spektrogramma hisoblanadi (80ms li qadamlar bilan).
   - `embedding_model.onnx` (Google Speech Embedding arxitekturasi) orqali 96-o'lchamli vektorlar ketma-ketligi generatsiya qilinadi.
2. **Klassifikator (Wake Word Classifier):**
   - 16 ta freym (taxminan 1.28 soniya) audio embeddinglari ketma-ketligini qabul qiladi.
   - Kichik va tezkor 2 qatlamli Dense / Conv1D arxitekturasi orqali `0.0` dan `1.0` gacha uyg'onish ehtimolligini hisoblaydi.

---

## 2. Tayyorgarlik va Muhit

Maxsus modelni o'qitish uchun alohida o'quv muhitida quyidagi paketlar zarur:

```bash
pip install openwakeword onnxruntime torch torchaudio soundfile numpy
```

Ixtiyoriy ravishda, sintetik ovoz namunalari (synthetic dataset) yaratish uchun Piper TTS yoki Coqui TTS o'rnatiladi:
```bash
pip install piper-tts
```

---

## 3. Bosqichma-bosqich O'qitish Jarayoni

### 1-qadam: Ijobiy (Positive) Audio Namunalarini Yaratish
"Salom Misa" iborasini turli ohang, tezlik va urg'ular bilan ifodalovchi kamida 1,000–5,000 ta audio namuna hosil qilinadi.

Sintetik avtomatlashtirilgan skript namunasi:
```python
import os
import subprocess

voices = ["uz_UZ-dilfuza-medium", "uz_UZ-otabek-medium"]  # Piper modellari
phrases = [
    "Salom Misa",
    "Salom Misa, qalaysan?",
    "Salom, Misa",
    "Hey Salom Misa",
]

output_dir = "dataset/positive/salom_misa"
os.makedirs(output_dir, exist_ok=True)

# Audio generatsiya qilish...
```

### 2-qadam: Salbiy (Negative) va Fon Shovqini Namunalarini Tayyorlash
Yolg'on faollashuvlarni (False Positives) kamaytirish uchun:
- Oddiy o'zbekcha suhbatlar (Common Voice uzbek qismi).
- Shovqinlar (musiqa, televizor, qadam tovushlari, xona akustikasi).
- Chalg'ituvchi o'xshash so'zlar: *"Salom Mirza"*, *"Salom do'stlar"*, *"Salom barchaga"*, *"Maysa"*, *"Kassa"*.

### 3-qadam: openWakeWord Synthetic Training Skriptini Ishga Tushirish
openWakeWord rasmiy o'qitish quvuridan foydalanib:

```python
import openwakeword
from openwakeword.train import train_custom_model

# Modelni o'qitish
model = train_custom_model(
    model_name="salom_misa",
    positive_data_dir="dataset/positive/salom_misa",
    negative_data_dir="dataset/negative",
    n_epochs=50,
    learning_rate=0.001,
    target_false_positive_rate=0.05
)

# ONNX formatida saqlash
model.export_to_onnx("salom_misa.onnx")
print("Model muvaffaqiyatli 'salom_misa.onnx' fayliga eksport qilindi!")
```

---

## 4. Modelni Misa AI ga Joylashtirish

1. Hosil bo'lgan `salom_misa.onnx` faylini va xususiyat modellarini (`melspectrogram.onnx`, `embedding_model.onnx`) loyihaning quyidagi papkasiga joylashtiring:
   ```
   yordamchi_9.0.0/
   └── models/
       └── wake_word/
           ├── salom_misa.onnx
           ├── melspectrogram.onnx
           └── embedding_model.onnx
   ```

2. Misa backend serverini ishga tushiring yoki `/api/voice/wakeword/configure` orqali qayta tekshiring:
   ```bash
   curl -X GET http://127.0.0.1:18420/api/voice/wakeword/status
   ```
   Qaytariladigan natija:
   ```json
   {
     "ok": true,
     "data": {
       "phrase": "Salom Misa",
       "active_engine": "openwakeword",
       "openwakeword": {
         "available": true,
         "status": "ready",
         "model_exists": true,
         "is_ready": true
       }
     }
   }
   ```

---

## 5. Litsenziya va Huquqiy Holat
- **openWakeWord Framework:** Apache-2.0 litsenziyasi ostida. Tijoriy va shaxsiy loyihalarda erkin foydalanish mumkin.
- **Rasmiy Pre-trained modellar:** CC BY-NC-SA 4.0 litsenziyasi ostida.
- **Maxsus yaratilgan "Salom Misa" modeli:** O'zingiz yig'gan yoki generatsiya qilgan ma'lumotlar to'plami litsenziyasiga bo'ysunadi.
