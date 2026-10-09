# Misa AI — Lokal Wake-Word Modellari Katalogi

Ushbu katalog Misa AI tizimining offline va maxfiy uyg'otuvchi so'z modellarini saqlash uchun mo'ljallangan.

## Xavfsizlik va Maxfiylik Kafolati (Zero-Leak Policy)
1. **Offline ishlash:** Ushbu model lokal qurilmada ishlaydi. Audio signallari hech qanday tashqi server, bulut yoki uchinchi tomon tahlil xizmatlariga uzatilmaydi.
2. **Avtomatik yuklab olmaslik:** Misa tizimi runtime vaqtida internetdan yashirincha model fayllarini yuklab olmaydi. Model fayllari bevosita ushbu papkadan yuklanadi.
3. **Litsenziya muvofiqligi:**
   - `openWakeWord` kodi **Apache-2.0** litsenziyasi ostida.
   - Rasmiy openWakeWord tayyor modellari **CC BY-NC-SA 4.0** litsenziyasiga ega.
   - Foydalanuvchi tomonidan o'qitilgan maxsus modellar foydalanuvchi ma'lumotlar to'plami shartlariga bo'ysunadi.

## Kerakli Fayllar
- `salom_misa.onnx` — "Salom Misa" iborasi uchun o'qitilgan asosiy ONNX modeli.
- `melspectrogram.onnx` — Audio signalini Mel-spektrogrammaga aylantiruvchi yordamchi model (openWakeWord bazaviy modeli).
- `embedding_model.onnx` — Google Speech Embedding arxitekturasidagi xususiyatlar ekstraktori.

### Muqobil Modellari (Ixtiyoriy)
- `hey_misa.onnx` — "Hey Misa" muqobil chaqiruv modeli.
- `mikasa.onnx` — "Mikasa" muqobil chaqiruv modeli.

## Agar Model Fayli Topilmasa Nima Bo'ladi?
Misa AI avtomatik ravishda **Acoustic Fallback** (apparat-kalibrlangan lokal fonetik tahlilchi) rejimiga o'tadi. Tizim to'xtab qolmaydi va internetga so'rov yubormasdan, apparat mikrofonidan `/m-i-s-a/` fonemalarini lokal tahlil qilishda davom etadi.

Maxsus modelni qanday o'qitish va eksport qilish haqida to'liq qo'llanma: `docs/WAKE_WORD_TRAINING.md`.
