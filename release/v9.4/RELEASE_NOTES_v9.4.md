# 🚀 Misa AI v9.4 — Rasmiy Reliz Qaydlari (Release Notes)

🎉 **Misa AI v9.4 (Universal MCP Ecosystem, Clean UX/UI, Autonomous Memory, NSIS Installer & In-App Update Center) muvaffaqiyatli yakunlandi!**

Ushbu relizda foydalanuvchi talablariga asosan interfeys to'liq tozalandi, ortiqcha va sun'iy bo'limlar chiqarib tashlandi, rasmiy **Windows NSIS Installer (.exe)** va **Portativ (.zip)** relizlari ishlab chiqildi hamda portable versiyada `WebView2Loader.dll` muammosi yuzaga kelmasligi uchun avtomatik tiklash mexanizmi joriy qilindi.

---

### 🛠️ Kiritilgan Asosiy Yangilanishlar:

1. **UX/UI Sodalashtirish va Tozalash (User-Centric Refinement):**
   - **Ortiqcha Audio Bo'limi Olib Tashlandi:** Bosh sahifaning (`LandingPage`) o'zi markaziy neyron audio va interaktiv Misa Aperture tizimi bo'lganligi sababli, alohida dublikat audio bo'limlari butunlay to'xtatildi.
   - **Xotiradagi 5 ta Shablon Olib Tashlandi:** Xotira bo'limidagi barcha 5 ta tizimli bo'sh shablon (`ovoz_turi`, `til`, `qiziqishlar`, `yoqtirgan_platformalar`, `yaratilgan`) tozalandi. AI faqat foydalanuvchi bilan suhbatda haqiqiy muhim ma'lumotlarni aniqlaganida xotiraga qo'shadi.
   - **Rejalashtirish Markazidagi Test Qiymatlari Tozalandi:** Dummy/test reja qiymatlari olib tashlandi; foydalanuvchi rejalarni o'zi kiritadi yoki AI orqali shakllantiradi.
   - **Buyruqlar Bo'limi Olib Tashlandi:** Alohida qiyin buyruqlar ro'yxati menyulardan olib tashlandi — endi barcha amallar tabiiy chat va ovozli buyruqlar orqali bajariladi.

2. **O'rnatuvchi (.exe) va Portativ (.zip) Paketlar:**
   - **Windows NSIS Installer:** `Misa-AI-Setup-v9.4.exe` (382.56 MB) — Windows ish stoli va Boshlash (Start) menyusiga avtomatik yorliq yaratuvchi to'liq o'rnatuvchi.
   - **Portativ Reliz:** `Misa-AI-v9.4-Portable.zip` (307.12 MB) — o'rnatishni talab qilmaydigan, to'g'ridan-to'g'ri ishga tushadigan paket.

3. **WebView2Loader.dll va WebView2 Muammosiga Qarshi Himoya:**
   - `run_portable.bat` skriptiga o'rnatilgan himoya qatlami:
     * Papkada `WebView2Loader.dll` mavjudligi avtomatik tekshiriladi; agar biron sabab bilan o'chib ketgan bo'lsa, zaxiradan darhol tiklanadi.
     * Tizimda Microsoft Edge WebView2 runtime mavjudligi registrdan tekshiriladi; topilmasa, ichki `webview2/MicrosoftEdgeWebview2Setup.exe` orqali fonda jimgina o'rnatiladi.
     * Har qanday Windows tizimida (hatto toza o'rnatilgan Windows 10/11 da) xatoliksiz ishga tushishi kafolatlanadi.

4. **Universal MCP (Model Context Protocol) Tizimi:**
   - Stdio va HTTP/SSE JSON-RPC 2.0 protokollarini to'liq qo'llab-quvvatlovchi MCP mijozi backendga integratsiya qilindi.
   - Plaginlar Markazida real vaqtda MCP serverlarni qo'shish, tekshirish va vositalarini boshqarish imkoniyati yaratildi.

5. **Ilova Ichidan Yangilanishlarni Tekshirish (In-App Update Center):**
   - Sozlamalar / Hisob (`AccountPage`) bo'limida tizim yangilanishlarini bir bosish orqali tekshirish kartasi joylashtirildi.
   - Kelajakda yangi relizlar chiqqanda foydalanuvchi xabardor qilinadi va 1-klik bilan avtomatik yangilanadi.

---

### 📦 Reliz Binar Fayllari va SHA-256 Nazorat Yig'indisi:

| Fayl nomi | Hajmi | Turi | SHA-256 Nazorat Yig'indisi |
| :--- | :--- | :--- | :--- |
| **`Misa-AI-Setup-v9.4.exe`** | **382.56 MB** | Windows NSIS O'rnatuvchi Setup Executable | `f0a980ec5f587b00d6cd5d52b9343ee25099ac4c51afc89e78229e1def654705` |
| **`Misa-AI-v9.4-Portable.zip`** | **307.12 MB** | To'liq Portativ Paket (Backend Runtime bilan) | `8164c78b77aba032383048c02f9336a3f99ff7464204681529000b9bdedc844c` |
| **`Misa.exe`** | **10.17 MB** | Rasmiy Standalone Desktop Ilova | `73ab941bd386f79cd6f421d9c05c4b1d09878beb1cb2952a836f386628051b2e` |
| **`WebView2Loader.dll`** | **0.15 MB** | Native Windows WebView2 yuklagich | `8427b1fc58ec707813e5c0a51eb5d69397bb333250a7b891be4d3b123f1e0f1c` |
| **`Misa-AI-v9.4.msi`** | **422.18 MB** | Windows MSI O'rnatuvchi Paketi | `3a347e3aa2113921e61169ae03af078da3ec09556a00199293bec0d6cea88fba` |
| **`webview2/MicrosoftEdgeWebview2Setup.exe`** | **1.77 MB** | Offline WebView2 Bootstrapper | `87ad3fe4e3faa1b48bad79de1b9269e5eb30574545bb6f5f7c37d51035748caf` |
| **`run_portable.bat`** | **1.62 KB** | Aqliy WebView2 tekshiruvchi portativ skript | — |
| **`SHA256SUMS.txt`** | **298 B** | Kriptografik Nazorat Summalari | — |
| **`version_manifest.json`** | **1.32 KB** | Versiya Manifesti | — |

Barcha fayllar mahalliy ravishda quyidagi papkada tayyor:
📂 `yordamchi_9.0.0/release/v9.4/`
