# 05 — TASDIQLANMAGAN DA'VOLAR VA SOXTA MUSHOHADALAR TAHLILI (PHASE 4.2)
**Hujjat turi:** Mustaqil Skeptik Tekshiruv va False Positive / Unverified Ekspertizasi  
**Sana:** 2026-10-24  
**Auditor:** Independent Technical Auditor & Verification Specialist  
**Holat:** Final Verified  

---

## 1. KIRISH VA METODOLOGIYA

Professional texnik auditda har bir da'vo ishonchli, takrorlanuvchi (reproducible) va kontekstga mos dalillar bilan tasdiqlanishi shart. Ko'pincha auditorlar ilova tabiatini (masalan, shaxsiy desktop ilovasi va ko'p foydalanuvchili korporativ bulutli SaaS tizimini) adashtirib, o'rinsiz xavfsizlik yoki arxitektura talablarini qo'yishadi.

Ushbu hisobot oldingi audit hisobotlaridagi:
1. `MISA-ROOT-007` ning haqiqiy tabiatini (u haqiqatan ham ishlab chiqarish nuqsonimi yoki shunchaki dev-muhit kamchiligimi);
2. 6 ta soxta mushohada (False Positive);
3. 8 ta dalili yetarli bo'lmagan (Unverified) da'volarni chuqur tahlil qiladi.

---

## 2. MISA-ROOT-007: `release/v9.3` QIDIRUV YO'LI TALQINI

### 2.1. Da'vo nima edi?
Oldingi auditlarda `Misa/src-tauri/src/lib.rs` (290 va 314-qatorlar) backend `.exe` faylini qidirishda faqat `release/v9.2/backend/misa_backend.exe`, `v9.0.2`, `v9.0.1`, `v9.0.0` yo'llarini tekshirishi, ammo yangi `release/v9.3` yo'lini kiritmaganligi sababli "Misa v9.3 ishga tushmaydi" degan da'vo ilgari surilgan edi.

### 2.2. Kodning Haqiqiy Mantiqiy Zanjiri
`lib.rs` dagi backendni topish funksiyasi (`find_backend_candidates`) quyidagi ketma-ketlikda yo'llarni tekshiradi:
1. **O'rnatilgan dastur katalogi (Production Installed Path):**
   - `exe_dir.join("resources").join("backend").join("misa_backend.exe")`
   - `exe_dir.join("backend").join("misa_backend.exe")`
   - `exe_dir.join("misa_backend.exe")`
2. **Ishchi katalog / ishlab chiquvchi muhiti (Development Fallback Path):**
   - Faqat yuqoridagi 1-bosqichda fayl topilmasa, `cwd.join("release").join("v9.2")...` tekshiriladi.

### 2.3. Haqiqiy Baho va Xulosa
- **Ishlab chiqarish (Production/Installer) muhitida:** Inno Setup o'rnatuvchisi barcha backend fayllarni `{app}\resources\backend\` ga joylashtiradi. Dastur birinchi navbatda aynan shu yerdan qidiradi. Demak, o'rnatilgan yakuniy dasturda `v9.3` nomli papka qidirilishi umuman talab qilinmaydi va dastur aynan shu sababli ishlamay qolmaydi!
- **Ishlab chiqish (Development/Debug) muhitida:** Dasturchi dasturni repo ichidan to'g'ridan-to'g'ri `cargo tauri dev` orqali yurgizganda, u `release/v9.3` o'rniga tasodifan eski `release/v9.2` binarysini yuklab yuborishi mumkin.
- **Xulosa:** `MISA-ROOT-007` — **BLOCKER PRODUCTION DEFECT EMAS**. Bu **Dev/Staging Runtime Environment Discrepancy** (Ishlab chiquvchi muhitidagi sinxronizatsiya nuqsoni) hisoblanadi. Uning xavflilik darajasi **CRITICAL emas, balki MEDIUM** deb qayta baholandi.

---

## 3. TASDIQLANGAN 6 TA SOXTA MUSHOHADA (FALSE POSITIVES)

Quyidagi 6 ta topilma kontekstni noto'g'ri tushunish yoki amalda mavjud bo'lmagan xavfni taxmin qilish natijasida kiritilgan bo'lib, ular rasman **FALSE POSITIVE** deb tasniflandi:

### 1. `DATA-002` / `UX-FIND-016`: Ko'p Foydalanuvchili Ma'lumotlar Izolyatsiyasi (Multi-Tenant Isolation)
- **Da'vo:** Dastur bir nechta foydalanuvchilar (multi-user workspace) o'rtasida ma'lumotlar, chatlar va modellarni to'liq izolyatsiya qilmaydi.
- **Raddiya:** Misa — shaxsiy desktop AI yordamchisidir (Personal Desktop AI Assistant). U SaaS yoki ko'p foydalanuvchili bulutli platforma emas. Windows operatsion tizimida har bir foydalanuvchi o'zining shaxsiy Windows profili (`%APPDATA%`, `C:\Users\Username`) doirasida ishlaydi. Desktop ilovadan ichki multi-tenancy talab qilish noto'g'ri.

### 2. `SEC-004`: Kodda Qattiq Kodlangan Maxfiy API Kalitlar (Hardcoded Production Secrets)
- **Da'vo:** Source code'da haqiqiy production API kalitlari qoldirib ketilgan.
- **Raddiya:** Kod bazasi tekshirilganda faqat `"your-api-key-here"`, `"sk-proj-test123456789"` kabi misol va test placeholder satrlari topildi. Hech qanday faol, haqiqiy yoki xavfli maxfiy kalit ochiq kodda yo'q.

### 3. `DR-SEC-005`: Mahalliy Loopback API da Rate Limiting Yo'qligi
- **Da'vo:** `127.0.0.1:8000` portiga so'rovlar chastotasini cheklovchi (Rate Limiting / Brute Force Protection) qo'yilmagan.
- **Raddiya:** Bir foydalanuvchili mahalliy desktop ilovasida frontend va backend o'rtasidagi IPC oqimida rate limit o'rnatish foydalanuvchi interfeysining qotishiga (lag, request drop) sabab bo'ladi. Bu yerda xavf so'rovlar sonida emas, balki so'rov yuboruvchining kimligida (origin/autentifikatsiyada).

### 4. `SEC-FIND-010`: Taxmin Qilinadigan Tokenlar Orqali Sessiyani O'g'irlash (Session Hijacking via Predictable Token)
- **Da'vo:** Mahalliy API sessiya tokenlari zaif generatsiya qilinadi va ularni o'g'irlash mumkin.
- **Raddiya:** Hozirgi Misa backendida umuman hech qanday token yoki sessiya boshqaruvi mavjud emas (`allow_origins=["*"]`, no auth). Mavjud bo'lmagan tokenni "zaif yoki o'g'irlanishi mumkin" deb da'vo qilish mantiqiy ziddiyatdir.

### 5. `VOX-FIND-FALSE-01`: VOSK STT Oflayn Modelining Tarmoqqa Ma'lumot Sizdirishi
- **Da'vo:** Ovozli kirish paytida Vosk STT moduli ovoz yozuvlarini tashqi serverlarga yuboradi.
- **Raddiya:** Vosk kutubxonasi 100% oflayn ishlaydigan C-asosidagi mahalliy modeldir. Kodda va kutubxona arxitekturasida audio fayllarni tashqariga uzatuvchi hech qanday tarmoq ulanishi mavjud emas.

### 6. `FE-FIND-FALSE-02`: Tauri WebView da CORS Bloklanishi Tufayli Backendga Ulanolmaslik
- **Da'vo:** Brauzer xavfsizlik siyosati Tauri frontendining backend API ga so'rov yuborishini butunlay bloklaydi.
- **Raddiya:** Tauri mahalliy `tauri://localhost` yoki xavfsiz WebView kontekstida ishlaydi va uning IPC imkoniyatlari mahalliy loopback chaqiruvlarini cheklamaydi. Aksincha, muammo CORS ning haddan tashqari ochiqligida (`allow_origins=["*"]`), bloklanishida emas.

---

## 4. DALILI YETARLI BO'LMAGAN 8 TA TOPILMA (UNVERIFIED)

Quyidagi topilmalar faqat umumiy mulohaza yoki taxminga asoslangan bo'lib, amaldagi repo, o'lchov asboblari yoki testlar bilan tasdiqlanmagan:

| Topilma ID | Da'vo Mazmuni | Nega Tasdiqlanmadi? (Sabab) | Hozirgi Holat |
| :--- | :--- | :--- | :--- |
| **`DR-VOX-001`** | Ovozli javob paytida dinamikdan chiqqan tovush mikrofonga qayta kirib, kuchli akustik aks-sado (echo) hosil qiladi. | Sinov laboratoriyasida real mikrofoniya va dinamik yozuvlari o'lchanmagan. Kodda `PyAudio` oqimi ko'ringan, lekin fizik akustik tekshiruv o'tkazilmagan. | **UNVERIFIED** |
| **`UX-FIND-015`** | Uzluksiz audio oqimida aks-sadoni bekor qilish (AEC) filtri yetishmaydi. | `DR-VOX-001` ning takrori. Haqiqiy audio test fayllari mavjud emas. | **UNVERIFIED** |
| **`SEC-FIND-011`** | Mahalliy API ga bir necha megabaytlik yuklama yuborish orqali backendni DoS holatiga keltirish mumkin. | Dasturga stress yuklama (fuzzing / load test) berib ko'rilmagan. Xotira hajmi va cheklovlar live o'lchanmagan. | **UNVERIFIED** |
| **`PERF-UNV-01`** | Ko'p soatlik uzluksiz ishlashda xotira hajmi 4 GB dan oshib ketishi haqidagi da'vo. | Dastur uzoq muddatli profiler ostida sinovdan o'tkazilmagan (statik audit doirasida). | **UNVERIFIED** |
| **`AGENT-UNV-02`** | LLM agenti o'z-o'zidan cheksiz rekursiyaga kirib, kompyuter protsessorini 100% band qilib qo'yadi. | Agent tsiklining to'xtash shartlari mavjud, faqat ba'zi istisnolarda xato qaytishi mumkin. To'liq freeze isbotlanmagan. | **UNVERIFIED** |
| **`VOX-UNV-03`** | Silero TTS ba'zi o'zbekcha harflarda fonetik buzilishlar hosil qilishi. | Ovoz sifati bo'yicha subyektiv baholash o'tkazilmagan, fonetik test matnlari auditi yo'q. | **UNVERIFIED** |
| **`NET-UNV-04`** | WebSocket ulanishi WiFi o'zgarganda operatsion tizim tarmog'ini qotirib qo'yishi. | Tarmoq o'zgarishi ssenariysi simulyatsiya qilinmagan. | **UNVERIFIED** |
| **`SYS-UNV-05`** | Windows 11 yangilanishlarida PyAudio drayveri qulashi. | Har xil Windows OS buildlarida matritsali test o'tkazilmagan. | **UNVERIFIED** |

---

## 5. XULOSA

Ushbu re-validatsiya audit natijalarining shaffofligini ta'minlaydi. Haqiqiy dasturiy nuqsonlar va xavflar ajratib olindi, sun'iy ravishda bo'rttirilgan yoki ilova tabiatiga mos kelmaydigan da'volar esa risk reestridan chiqarildi yoki `UNVERIFIED` / `FALSE_POSITIVE` maqomida belgilandi.
