# 🚀 Misa AI v9.4 — Rasmiy Reliz Qaydlari (Release Notes)

🎉 **Misa AI v9.4 (Universal MCP Ecosystem, Clean UX/UI, Autonomous Memory & In-App Update Center) muvaffaqiyatli yakunlandi!**

Ushbu relizda foydalanuvchi talablariga asosan interfeys to'liq tozalandi, ortiqcha va sun'iy bo'limlar chiqarib tashlandi, yangi MCP arxitekturasi joriy etildi hamda ilova ichidan yangilanishlarni tekshirish mexanizmi qo'shildi.

---

### 🛠️ Kiritilgan Asosiy Yangilanishlar:

1. **UX/UI Sodalashtirish va Tozalash (User-Centric Refinement):**
   - **Ortiqcha Audio Bo'limi Olib Tashlandi:** Bosh sahifaning (`LandingPage`) o'zi markaziy neyron audio va interaktiv Misa Aperture tizimi bo'lganligi sababli, alohida dublikat audio bo'limlari butunlay to'xtatildi.
   - **Xotiradagi 5 ta Shablon Olib Tashlandi:** Xotira bo'limidagi barcha 5 ta tizimli bo'sh shablon (`ovoz_turi`, `til`, `qiziqishlar`, `yoqtirgan_platformalar`, `yaratilgan`) tozalandi. AI faqat foydalanuvchi bilan suhbatda haqiqiy muhim ma'lumotlarni aniqlaganida xotiraga qo'shadi.
   - **Rejalashtirish Markazidagi Test Qiymatlari Tozalandi:** Dummy/test reja qiymatlari olib tashlandi; foydalanuvchi rejalarni o'zi kiritadi yoki AI orqali shakllantiradi.
   - **Buyruqlar Bo'limi Olib Tashlandi:** Alohida qiyin buyruqlar ro'yxati menyulardan olib tashlandi — endi barcha amallar tabiiy chat va ovozli buyruqlar orqali bajariladi.

2. **Universal MCP (Model Context Protocol) Tizimi:**
   - Stdio va HTTP/SSE JSON-RPC 2.0 protokollarini to'liq qo'llab-quvvatlovchi MCP mijozi backendga integratsiya qilindi.
   - Plaginlar Markazida real vaqtda MCP serverlarni qo'shish, tekshirish va vositalarini boshqarish imkoniyati yaratildi.

3. **Ilova Ichidan Yangilanishlarni Tekshirish (In-App Update Center):**
   - Sozlamalar / Hisob (`AccountPage`) bo'limida tizim yangilanishlarini bir bosish orqali tekshirish kartasi joylashtirildi.
   - Yangi reliz mavjud bo'lganda modal oyna orqali o'rnatish taklif etiladi.

4. **Avtonom Fakt Ajratuvchi va Semantik Xotira:**
   - Muloqot davomida AI foydalanuvchi ma'lumotlarini qoidalarga tayangan holda aniqlaydi va bazada xavfsiz saqlaydi.

5. **Desktop Screen Capture & Telemetriya:**
   - Real ishchi stoli skrinshotini tezkor suratga olish va tahlil qilish imkoniyati ta'minlandi.

---

### 📦 Reliz Binar Fayllari va SHA-256 Nazorat Yig'indisi:

| Fayl nomi | Hajmi | Turi | SHA-256 Nazorat Yig'indisi |
| :--- | :--- | :--- | :--- |
| **`Misa-AI-v9.4-Portable.zip`** | **307.12 MB** | To'liq Portativ Paket (Backend Runtime bilan) | `2f3ef80f5f77dcc8480760bef71d01d8f4959366298ab349e4d2bb671b126023` |
| **`Misa.exe`** | **10.17 MB** | Rasmiy Standalone Desktop Ilova | `73ab941bd386f79cd6f421d9c05c4b1d09878beb1cb2952a836f386628051b2e` |
| **`WebView2Loader.dll`** | **0.15 MB** | Native Windows WebView2 yuklagich | `8427b1fc58ec707813e5c0a51eb5d69397bb333250a7b891be4d3b123f1e0f1c` |
| **`webview2/MicrosoftEdgeWebview2Setup.exe`** | **1.77 MB** | Offline WebView2 Bootstrapper | `87ad3fe4e3faa1b48bad79de1b9269e5eb30574545bb6f5f7c37d51035748caf` |
| **`run_portable.bat`** | **422 B** | Bir bosishda ishga tushiruvchi skript | — |
| **`SHA256SUMS.txt`** | **167 B** | Kriptografik Nazorat Summalari | — |
| **`version_manifest.json`** | **999 B** | Versiya Manifesti | — |

Barcha fayllar mahalliy ravishda quyidagi papkada tayyor:
📂 `yordamchi_9.0.0/release/v9.4/`
