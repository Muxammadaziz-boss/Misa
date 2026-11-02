# 🚀 Misa AI v9.3 — Rasmiy Reliz Qaydlari (Release Notes)

🎉 **Misa AI v9.3 (Local Release & AI Subsystem / Voice Engine Upgrades) muvaffaqiyatli yangilandi!**

Ushbu relizda dastur to'liq qayta yig'ildi va quyidagi muhim yangilanishlar kiritildi:

---

### 🛠️ Kiritilgan Asosiy Yangilanishlar:

1. **Barcha Ishlaydigan AI API'lari Standart (Default) Qilindi:**
   - **Gemini**, **Groq**, **Cerebras** va **OpenRouter** kalitlari tizimga default ulandi va dastur o'rnatilishi bilanoq darhol AI bilan ishlashga tayyor.
   - Foydalanuvchi Sozlamalar sahifasida o'zining shaxsiy API kalitini kiritish imkoniyati saqlandi va shaxsiy kalit doimo standart kalitdan ustun turadi (priority override).

2. **Ovozlar Tizimi (TTS) va RVC Modellar To'liq Tiklandi:**
   - Microsoft Edge-TTS yangi `Sec-MS-GEC v2` token talabiga moslashtirilib, `edge-tts 7.3.1` ga yangilandi. Madina va Sardor ovozlari to'liq tiklandi.
   - Lokal RVC vositalari (`torch`, `torchaudio`, `faiss-cpu`) va `hubert_base.pt` modeli (189.5 MB) o'rnatildi.
   - Barcha 6 ta ovoz modeli (`ayol`, `erkak`, `fish_yigit`, `fish_anime`, `ashley`, `yukari`) muvaffaqiyatli sintez qiladi va ovoz hech qachon to'xtab qolmasligi uchun Madinaga xavfsiz fallback ta'minlandi.

3. **Versiyalar Sinxronizatsiyasi:**
   - Ilovaning barcha UI oynalari (Chat, Profil/Sozlamalar, Buyruqlar paneli, Rejalashtiruvchi, Brend nishonlari) va backend konfiguratsiyalari to'liq **v9.3** (`9.3.0`) ga o'tkazildi.

4. **Portativ Binar Paketlar:**
   - Rust Tauri frontend-desktop executable rasmiy **`Misa.exe`** sifatida eng so'nggi `dist/` bilan to'liq qayta kompilyatsiya qilindi.
   - Yangi Python muhiti, eng so'nggi `core/` kodlari va HuBERT modeli bilan boyitilgan to'liq `Misa-AI-v9.3-Portable.zip` qayta shakllantirildi.

---

### 📦 Reliz Binar Fayllari va SHA-256 Nazorat Yig'indisi:

| Fayl nomi | Hajmi | Turi | SHA-256 Nazorat Yig'indisi |
| :--- | :--- | :--- | :--- |
| **`Misa-AI-v9.3-Portable.zip`** | **506.76 MB** | To'liq Portativ Paket (Backend + Python Runtime + RVC HuBERT bilan) | `ad465d010e43ef1df51b9127d095238eec1a364bdedceb3f65fc07eb3974e050` |
| **`Misa.exe`** | **10.16 MB** | Rasmiy Standalone Desktop Ilova | `a07b4723b946d77e05b508ff847a21da82a21c3a206484657015e8719b1b44af` |
| **`WebView2Loader.dll`** | **0.15 MB** | Native Windows WebView2 yuklagich | `8427b1fc58ec707813e5c0a51eb5d69397bb333250a7b891be4d3b123f1e0f1c` |
| **`webview2/MicrosoftEdgeWebview2Setup.exe`** | **1.77 MB** | Offline WebView2 Bootstrapper | `87ad3fe4e3faa1b48bad79de1b9269e5eb30574545bb6f5f7c37d51035748caf` |
| **`run_portable.bat`** | **422 B** | Bir bosishda ishga tushiruvchi skript | — |
| **`SHA256SUMS.txt`** | **167 B** | Kriptografik Nazorat Summalari | — |
| **`version_manifest.json`** | **999 B** | Versiya Manifesti | — |

Barcha fayllar mahalliy ravishda quyidagi papkada tayyor:
📂 `yordamchi_9.0.0/release/v9.3/`
