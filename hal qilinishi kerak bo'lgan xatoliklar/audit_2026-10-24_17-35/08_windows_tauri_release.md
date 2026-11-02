# Misa v9.3 — Ekspert Hisoboti 08: Windows Desktop, Tauri va Release Engineer

**Audit sanasi va vaqti:** 2026-10-24 17:50  
**Ekspert roli:** Windows Desktop, Tauri va Release Engineer  
**Loyiha versiyasi:** Misa v9.3.0  
**Tekshirilgan Git branch va commit:** `dev-v9.0.0` / commit `aafa0d2fd15bba95b4f0c7aac921a9bd08986bb1`  
**Tekshiruv doirasi:** Tauri 2 desktop lifecycle, child process (Python backend) nazorati, Windows single-instance mexanizmi, installer va portable resurslar to'liqligi, toza Windows muhitida ishga tushish tayyorgarligi, tray va oyna integratsiyasi.

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

- `Misa/src-tauri/src/lib.rs` — Tauri 2 desktop dasturining markaziy Rust kodi (SingleInstance, backend lifecycle, supervisor, tray, WebviewWindow).
- `Misa/src-tauri/tauri.conf.json` — Tauri konfiguratsiyasi, resurslar ro'yxati (`resources`), NSIS installer sozlamalari, CSP va oyna parametrlari.
- `release/v9.3/` va `release/v9.2/` — Ishlab chiqarish binar fayllari, `misa_backend.exe` va `_internal` papkalari.
- `Misa/src-tauri/Cargo.toml` — Rust bog'liqliklari va desktop plaginlari.

---

## 3. Topilmalar Tafsiloti

### Topilma ID: WIN-001
**Sarlavha:** `tauri.conf.json` da PyInstaller `_internal` katalogi resurslarga kiritilmagani sababli toza Windows tizimida qulash xavfi  
**Kategoriya:** Tauri Packaging va Installer  
**Jiddiylik darajasi:** Critical  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `Misa/src-tauri/tauri.conf.json` (qatorlar 37–42)  
**Dalil:**
```json
// Misa/src-tauri/tauri.conf.json:37-41
"resources": [
  "WebView2Loader.dll",
  "backend/misa_backend.exe"
]
```
```powershell
# release/v9.3/backend/ tarkibi:
# misa_backend.exe
# _internal/ (python311.dll, pywin32, pyd kutubxonalari)
```
**Muammo tavsifi:** `misa_backend.exe` PyInstaller ning `onedir` rejimida kompilyatsiya qilingan bo'lib, uning ishlashi uchun bevosita yonida joylashgan `_internal` katalogi (Python 3.11 runtime, `python311.dll`, binar C-kengaytmalar) talab etiladi. Biroq, `tauri.conf.json` faylidagi `"resources"` bo'limida faqatgina `"backend/misa_backend.exe"` ko'rsatilgan. Natijada, Tauri installer (`.msi` yoki NSIS `.exe`) paketini yaratganda faqat `misa_backend.exe` faylini oladi va butun `_internal` katalogini qoldirib ketadi. Ushbu o'rnatgich toza kompyuterga o'rnatilganda, backend ishga tusha olmaydi (`python311.dll not found` xatosi) va butun Misa dasturi oq ekran (deadlock) holatida qoladi.  
**Yuzaga kelish shartlari:** Loyiha `cargo tauri build` orqali yakuniy installer qilinganda va toza Windows OS ga o'rnatilganda.  
**Ta’siri:** Foydalanuvchi ilovani o'rnatgandan so'ng backend ishlamaydi, ilovadan foydalanish mutlaqo imkonsiz bo'ladi.  
**Root cause:** PyInstaller `onedir` tuzilmasi e'tiborga olinmay, resurslarga faqat bitta `.exe` fayl ko'rsatilgan (`backend/**/*` o'rniga).  
**Qayta tekshirish usuli:** `target/release/bundle/nsis/` ichidagi o'rnatilgan papkani tekshirib, `resources/backend/` ichida `_internal` papkasi yo'qligini ko'rish.  
**Tavsiya:** `tauri.conf.json` dagi `resources` ga `"backend/**/*"` yoki `"release/v9.3/backend/**/*"` glob naqshini kiritish.  
**Qabul mezoni:** Tauri tomonidan yaratilgan yakuniy o'rnatish paketida `python311.dll` va `_internal` katalogi to'liq mavjud bo'lishi.  
**Cheklovlar:** Lokal ishlab chiquvchi kompyuterida manba kataloglar mavjudligi sababli ushbu xato sezilmasligi mumkin; faqat toza muhitda namoyon bo'ladi.

---

### Topilma ID: WIN-002
**Sarlavha:** Rust `lib.rs` dagi backend qidiruv ketma-ketligida joriy reliz versiyasi `v9.3` ning qoldirib ketilgani  
**Kategoriya:** Backend Lifecycle va Relizlar Mosligi  
**Jiddiylik darajasi:** Critical  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `Misa/src-tauri/src/lib.rs` (qatorlar 285–335)  
**Dalil:**
```rust
// Misa/src-tauri/src/lib.rs:293-298
if let Ok(cwd) = std::env::current_dir() {
    candidates.push((cwd.join("backend").join("misa_backend.exe"), cwd.join("backend")));
    candidates.push((cwd.join("release").join("v9.2").join("backend").join("misa_backend.exe"), cwd.join("release").join("v9.2").join("backend")));
    candidates.push((cwd.join("release").join("v9.0.2").join("backend").join("misa_backend.exe"), cwd.join("release").join("v9.0.2").join("backend")));
    candidates.push((cwd.join("release").join("v9.0.1").join("backend").join("misa_backend.exe"), cwd.join("release").join("v9.0.1").join("backend")));
    candidates.push((cwd.join("release").join("v9.0.0").join("backend").join("misa_backend.exe"), cwd.join("release").join("v9.0.0").join("backend")));
    // DIQQAT: "release/v9.3" mutlaqo yo'q!
```
```rust
// Misa/src-tauri/src/lib.rs:315-330
while let Some(parent) = curr.parent() {
    let rel92 = parent.join("release").join("v9.2").join("backend");
    if rel92.exists() { candidates.push((rel92.join("misa_backend.exe"), rel92)); }
    // ... v9.0.2, v9.0.1, v9.0.0 bor, ammo v9.3 yo'q!
}
```
**Muammo tavsifi:** Misa loyihasi ayni paytda `v9.3` versiyasiga yangilangan va `release/v9.3/backend/misa_backend.exe` mavjud. Biroq, Rust `lib.rs` dagi `find_bundled_backend_binary()` funksiyasi qattiq kodlangan (hardcoded) yo'llar bo'yicha qidiradi va unda faqat `v9.2`, `v9.0.2`, `v9.0.1`, `v9.0.0`, `v8.0.0` ko'rsatilgan. Natijada, foydalanuvchi v9.3 ni ishga tushirganda, Rust kodi yangi v9.3 backend o'rniga tizimda topilgan eski `v9.2` binar faylini yuklaydi! Agar v9.2 mavjud bo'lmasa, backend topilmay qoladi.  
**Yuzaga kelish shartlari:** Dastur portable yoki reliz rejimida `release/v9.3` papkasidan ishga tushirilganda.  
**Ta’siri:** Foydalanuvchi v9.3 relizidagi yangi xususiyatlar, tuzatilgan xatolar va API endpointlarini ololmaydi, eski v9.2 kodi ishlashda davom etadi.  
**Root cause:** Versiyalash yo'llari dinamik emas, balki qattiq kodlangan qatorlar (hardcoded strings) bilan yozilgan va v9.3 relizida yangilanmagan.  
**Qayta tekshirish usuli:** `Misa/src-tauri/src/lib.rs` ning 290–335-qatorlarini ko'zdan kechirish orqali tasdiqlangan.  
**Tavsiya:** Versiyalarni qattiq kodlash o'rniga eng yuqori semver versiyali papkani dinamik aniqlash yoki birinchi navbatda `release/v9.3` ni ro'yxatning eng boshiga qo'shish.  
**Qabul mezoni:** Rust supervisor joriy v9.3 backend faylini birinchi navbatda topishi va yuklashi.  
**Cheklovlar:** Yo'q, kod to'liq tasdiqlangan.

---

### Topilma ID: WIN-003
**Sarlavha:** Dastur yopilganda backend jarayonini majburiy `taskkill /F /T` bilan o'ldirish (Brutal Kill & State Corruption)  
**Kategoriya:** Process Lifecycle va Graceful Shutdown  
**Jiddiylik darajasi:** High  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `Misa/src-tauri/src/lib.rs` (qatorlar 241–250)  
**Dalil:**
```rust
// Misa/src-tauri/src/lib.rs:242-250
{
    const CREATE_NO_WINDOW: u32 = 0x08000000;
    let _ = Command::new("taskkill")
        .args(["/F", "/T", "/PID", &pid.to_string()])
        .creation_flags(CREATE_NO_WINDOW)
        .status();
}
let _ = child.kill();
let _ = child.wait();
```
**Muammo tavsifi:** Foydalanuvchi Misa oynasini yopganda, Rust `SupervisorState` backend jarayoniga yumshoq to'xtash (graceful shutdown) xabarini (masalan, HTTP `POST /api/shutdown`, IPC signali yoki `SIGINT`) yubormaydi. Buning o'rniga to'g'ridan-to'g'ri `taskkill /F /T /PID` buyrug'i orqali jarayon va uning barcha bola jarayonlari majburiy tarzda o'ldiriladi. Bu holatda Python backend xotiradagi o'zgarishlarni (`agent_conversations.json`, `agent_memory.py` keshlarini) diskka saqlashga ulgurmaydi, ochiq fayl deskriptorlari va SQLite/PostgreSQL ulanishlari kutilmaganda uziladi, bu esa JSON fayllarining sinishi (truncation/corruption) ga olib keladi.  
**Yuzaga kelish shartlari:** Dastur har safar oddiy tarzda yopilganda.  
**Ta’siri:** Xotira va suhbatlar tarixining yo'qolishi, oxirgi kiritilgan ma'lumotlarning saqlanmay qolishi.  
**Root cause:** Graceful shutdown mexanizmi kiritilmagani sababli orqa fonda zombi jarayon qolmasligi uchun haddan tashqari agressiv `taskkill /F` usuli tanlangan.  
**Qayta tekshirish usuli:** Misa da suhbat olib borib, oynani yopish va `data/agent_conversations.json` ning oxirgi qatorlarini tekshirish.  
**Tavsiya:** Dastur yopilishida avval HTTP orqali `/api/shutdown` yuborib, 1.5 soniya kutish va faqat jarayon to'xtamasa majburiy o'ldirish (graceful shutdown with timeout).  
**Qabul mezoni:** Backend jarayoni o'z xotiralarini to'liq saqlab, `code 0` bilan xotirjam yopilishi.  
**Cheklovlar:** Windows platformasida Python jarayoniga konsolsiz `SIGINT` yuborish murakkab bo'lgani uchun HTTP shutdown afzal hisoblanadi.

---

### Topilma ID: WIN-004
**Sarlavha:** Tizim trayga yashirilgan oyna uchun Single-Instance faollashtirishning ishlamay qolishi  
**Kategoriya:** Windows Single-Instance va Window Management  
**Jiddiylik darajasi:** High  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `Misa/src-tauri/src/lib.rs` (qatorlar 90–109)  
**Dalil:**
```rust
// Misa/src-tauri/src/lib.rs:91-108
let titles = ["MISA AI v9.3", "MISA AI v9.2", "Misa AI", "MISA AI", "MISA AI v9.0.2"];
let mut hwnd = 0;
for t in &titles {
    let win_title: Vec<u16> = OsStr::new(t).encode_wide().chain(std::iter::once(0)).collect();
    let found = unsafe { FindWindowW(std::ptr::null(), win_title.as_ptr()) };
    if found != 0 {
        hwnd = found;
        break;
    }
}
if hwnd != 0 {
    unsafe {
        ShowWindow(hwnd, SW_SHOW);
        ShowWindow(hwnd, SW_RESTORE);
        SetForegroundWindow(hwnd);
    }
}
```
**Muammo tavsifi:** Foydalanuvchi Misa oynasini "Minimize to Tray" qilganda, Tauri oynani to'liq yashiradi (`window.hide()`). Agar foydalanuvchi ish stolidan Misa belgisini qayta bossa, yangi jarayon `SingleInstanceGuard` orqali ikkinchi nusxa ochilishini to'xtatadi va `FindWindowW` orqali eski oynani topib `ShowWindow(hwnd, SW_RESTORE)` qilmoqchi bo'ladi. Biroq, Tauri 2 da yashirilgan WebView oynalari Win32 `ShowWindow` chaqiruvi bilan to'g'ri qayta tiklanmaydi, chunki Tauri ichki veb-kontent renderlash tsiklini to'xtatgan bo'ladi. Natijada foydalanuvchi ikonkani bosganda ekranda hech narsa sodir bo'lmaydi va ilova ochilmagandek tuyuladi.  
**Yuzaga kelish shartlari:** Misa dasturi trayda turgan paytda uning `.exe` fayli qayta ishga tushirilganda.  
**Ta’siri:** Foydalanuvchi dastur buzilgan deb o'ylab Task Manager orqali jarayonni o'ldirishga majbur bo'ladi.  
**Root cause:** Jarayonlararo IPC (masalan, nomlangan kanal yoki mahalliy soket) orqali mavjud Tauri instansiyasiga `app.emit("restore-window")` signali yuborish o'rniga oddiy Win32 `FindWindowW` ga tayanilgan.  
**Qayta tekshirish usuli:** Dasturni trayga tushirib, Misa yorlig'ini qayta ishga tushirish orqali vizual holatni tekshirish.  
**Tavsiya:** Tauri ning rasmiy `tauri-plugin-single-instance` plaginidan foydalanish yoki birinchi instansiyaga lokal soket orqali xabar yuborish.  
**Qabul mezoni:** Trayda yotgan dastur qayta bosilganda zudlik bilan ekranda to'liq jonlanishi.  
**Cheklovlar:** Faqat Windows desktop UI kontekstida sinovdan o'tkaziladi.

---

### Topilma ID: WIN-005
**Sarlavha:** Rivojlantirish muhitida (Dev Mode) qattiq kodlangan katalog nomlariga bog'liqlik  
**Kategoriya:** Developer Experience va Build Portableligi  
**Jiddiylik darajasi:** Medium  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** `Misa/src-tauri/src/lib.rs` (qatorlar 350–385)  
**Dalil:**
```rust
// Misa/src-tauri/src/lib.rs:350-357
if parent.join("core").join("api_server.py").exists() { return Some(parent.to_path_buf()); }
if parent.join("yordamchi_9.0.0").join("core").join("api_server.py").exists() { return Some(parent.join("yordamchi_9.0.0")); }
if parent.join("yordamchi_8.0.0").join("core").join("api_server.py").exists() { return Some(parent.join("yordamchi_8.0.0")); }
```
**Muammo tavsifi:** `resolve_dev_base_dir()` funksiyasida `yordamchi_9.0.0` va `yordamchi_8.0.0` kabi qattiq kodlangan (hardcoded) papka nomlari mavjud. Agar boshqa dasturchi yoki CI tizimi loyihani `MisaAI`, `Misa_v9` yoki boshqa nomdagi papkaga yuklasa, ushbu shartlar ishlamaydi va dastur lokal muhitdagi backendni topa olmaydi.  
**Yuzaga kelish shartlari:** Loyiha papkasi nomi standart `yordamchi_9.0.0` dan farq qilganda.  
**Ta’siri:** Yangi dasturchilar loyihani klonlab ishga tushirganida backend topilmaydi.  
**Root cause:** Nisbiy yo'l va marker fayllarga (`Cargo.toml`, `.git`) tayanish o'rniga shaxsiy ishchi papka nomlari kodga kiritilgan.  
**Qayta tekshirish usuli:** Loyiha nusxasini boshqa nomli papkaga ko'chirib, dev rejimda `cargo tauri dev` buyrug'ini berish.  
**Tavsiya:** Faqat `api_server.py` mavjudligiga qarab yuqoriga qarab yuruvchi dinamik tekshiruvdan foydalanish va qattiq kodlangan papka nomlarini olib tashlash.  
**Qabul mezoni:** Papka nomi qanday bo'lishidan qat'i nazar dev muhit o'z-o'zini aniqlashi.  
**Cheklovlar:** Ishlab chiquvchi mashinasidagi o'ziga xos konfiguratsiya.

---

## 4. Tekshirish Imkoni Bo'lmagan Qismlar va Cheklovlar
- Windows Defender SmartScreen sertifikati va EV Code Signing jarayoni haqiqiy sertifikat mavjud bo'lmagani sababli tekshirilmadi.
- Windows 10 ning eski buildlaridagi (masalan, 1809 gacha bo'lgan) WebView2 bootstrapper o'rnatilishi tekshirilmadi.

---

## 5. Umumiy Xulosa va Keyingi Ustuvorliklar
Windows va Tauri integratsiyasidagi eng jiddiy nuqson — installerda `_internal` katalogining tushib qolganligi (`WIN-001`) va `lib.rs` ning v9.3 reliz binarini tanimasligidir (`WIN-002`). Ushbu ikki xato Misa v9.3 ning boshqa kompyuterlarda mustaqil ishlay olishiga to'sqinlik qiluvchi asosiy omillardir.
