# AUDIT HISOBOTI: 01. PRINCIPAL SOFTWARE ARCHITECT
**Ekspert roli:** Principal Software Architect  
**Audit sanasi va vaqti:** 2026-10-24 17:35 (Toshkent vaqti)  
**Tekshirilgan branch va commit:** `dev-v9.0.0` (commit `aafa0d2fd15bba95b4f0c7aac921a9bd08986bb1`)  
**Loyiha ildiz katalogi:** `d:\Ishchi stoli\Misa\yordamchi_9.0.0`  

---

## 1. TEKSHIRUV QAMROVI VA METODOLOGIYASI

Ushbu audit Misa AI v9 (va 9.3) tizimining umumiy dasturiy ta'minot arxitekturasini, qatlamlar orasidagi chegaralarni, komponentlar bog'liqligini, hayot sikli (lifecycle) boshqaruvini, resurs egaligini va tizim kengayuvchanligini (scalability) chuqur tahlil qilishga qaratilgan.

### Tekshirilgan asosiy komponentlar va fayllar:
- `core/api_server.py` — Backend monolit API serveri (7,920 qator)
- `main.py` — Klassik ishga tushirish kirish nuqtasi (2,500 qator)
- `Misa/src-tauri/src/lib.rs` — Desktop Tauri v2 Rust supervayzeri (1,559 qator)
- `Misa/src/services/backendService.ts` — Frontend API va integratsiya xizmati (4,560 qator)
- `Misa/src/pages/AccountPage.tsx` — Foydalanuvchi va sozlamalar sahifasi (4,500 qator)
- `Misa/src/pages/AuthPage.tsx` — Autentifikatsiya portali (2,609 qator)
- `core/v8/` — Multi-device, Telegram, autentifikatsiya va masofaviy boshqaruv modullari

### Qo'llangan tekshiruv usullari:
- Statik arxitekturaviy kod tahlili (Static Architectural Code Analysis)
- Bog'liqliklar grafigi va siklik importlar ekspertizasi (Dependency & Coupling Analysis)
- Davlat (State) va xotira boshqaruvi modeli tahlili
- Qatlamlararo kontraktlar (Frontend <-> Backend <-> Desktop Shell) mosligi tekshiruvi

---

## 2. JIDDIYLI DARADALARI BO'YICHA TOPILMALAR STATISTIKASI

| Jiddiylik darajasi | Topilmalar soni |
| :--- | :---: |
| **Critical** | 2 |
| **High** | 2 |
| **Medium** | 1 |
| **Low** | 0 |
| **Info** | 0 |
| **JAMI** | **5** |

---

## 3. BATAFSIL TOPILMALAR

### Topilma ID: ARC-001
**Sarlavha:** Monolit Gigant Fayllar ("God Objects") va Domen Ajratilishining Yo'qligi  
**Kategoriya:** Architecture / Modularization  
**Jiddiylik darajasi:** Critical  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** 
- [core/api_server.py](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/api_server.py#L1-L7920)
- [Misa/src/services/backendService.ts](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/services/backendService.ts#L1-L4565)
- [Misa/src/pages/AccountPage.tsx](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/AccountPage.tsx#L1-L4500)
- [Misa/src/pages/AuthPage.tsx](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/AuthPage.tsx#L1-L2609)

**Dalil:**
`core/api_server.py` bitta faylda 7,920 qator kodni o'z ichiga oladi (hajmi ~333 KB). Unda WebSocket boshqaruvi, audio oqimlari, LLM so'rovlari, rasmlar generatsiyasi, fayl boshqaruvi, MCP serverlari, tizim metrikalari, Telegram webhooklari, qurilmalar juftlashuvi va autentifikatsiya bitta faylga aralashtirib yozilgan. Frontendda `backendService.ts` 4,560 qator bo'lib, yuzlab bir-biriga aloqasiz funksiyalarni o'z ichiga oladi.

**Muammo tavsifi:**
Single Responsibility Principle (SRP) to'liq buzilgan. Barcha biznes domenlari (Ovoz, AI, Tizim boshqaruvi, Tarmoq, Xavfsizlik, Auth) yagona gigant fayllarda mujassamlangan. Natijada kodni testlash, refaktoring qilish, parallel ishlab chiqish va regressiyasiz saqlash deyarli imkonsiz darajaga yetgan.

**Yuzaga kelish shartlari:**
Loyihaga yangi endpoint qo'shilganda yoki mavjud mantiq tahrirlanganda butun fayl qayta yuklanadi, bitta sintaktik yoki import xatosi butun serverni to'xtatadi.

**Ta’siri:**
Tizim barqarorligi pasayadi, circular import xatolari ehtimoli keskin oshadi, dasturchilar uchun loyihani kengaytirish murakkablashadi.

**Root cause:**
Versiyalar ketma-ketligida (v6 -> v7 -> v8 -> v9) yangi funksiyalar mavjud fayllarning oxiriga shunchaki qo'shib borilgan, arxitekturaviy modul ajratish (domain decomposition) amalga oshirilmagan.

**Qayta tekshirish usuli:**
`core/api_server.py` va `backendService.ts` qatorlar soni va import strukturasini tekshirish orqali tasdiqlanadi.

**Tavsiya:**
API serverni aiohttp Blueprints / Modular Routers (`core/api/routers/`) shaklida alohida fayllarga bo'lish (`auth.py`, `voice.py`, `agent.py`, `devices.py`, `system.py`). Frontendda `backendService.ts` ni har bir domen bo'yicha alohida xizmatlarga (`authService.ts`, `voiceService.ts`, `deviceService.ts`) parchalash.

**Qabul mezoni:**
Bitta ham manba kodi fayli 1000 qatordan oshmasligi, har bir modul faqat o'z domeniga tegishli marshrutlarni boshqarishi.

**Cheklovlar:**
Ushbu audit davomida refaktoring kodi yozilmagan (ruxsat yo'qligi sababli).

---

### Topilma ID: ARC-002
**Sarlavha:** Dual Arxitektura va "Split-Brain" Holat Boshqaruvi (Supabase Direct vs Backend Proxy)  
**Kategoriya:** Architecture / State & Data Flow  
**Jiddiylik darajasi:** Critical  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** 
- [Misa/src/services/supabaseClient.ts](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/services/supabaseClient.ts#L10-L37)
- [Misa/src/services/backendService.ts](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/services/backendService.ts#L4536-L4554)
- [Misa/src/pages/AuthPage.tsx](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/AuthPage.tsx#L562-L580)
- [core/api_server.py](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/api_server.py#L7603-L7620)

**Dalil:**
```typescript
// Misa/src/pages/AuthPage.tsx L562-L575
const res = await backendService.loginWithTelegram(...);
if (res.ok && res.user) {
  // Frontend to'g'ridan-to'g'ri Supabase ga yozmoqda:
  await supabase.from("telegram_links").upsert({ user_id: res.user.id, ... });
}
```
Ayni vaqtda Python backendda ham `/api/auth/*` va `/api/telegram/*` endpointlari mavjud bo'lib, ular o'zlarining lokal keshlariga yozishadi.

**Muammo tavsifi:**
Tizimda bitta yagona haqiqat manbai (Single Source of Truth) mavjud emas. Frontend ba'zi ma'lumotlarni to'g'ridan-to'g'ri Supabase SDK orqali o'qib-yozadi, boshqa ma'lumotlarni esa Python backend orqali o'tkazadi. Natijada foydalanuvchi sessiyasi, tokenlar va ma'lumotlar ikkala qatlam orasida desinxronizatsiyaga uchraydi.

**Yuzaga kelish shartlari:**
Foydalanuvchi tizimga kirganda yoki ma'lumotlarni yangilaganda bir tomon (Supabase) yangilanadi, lekin lokal Python backend xotirasi bundan bexabar qoladi (yoki aksincha).

**Ta’siri:**
Foydalanuvchi akkaunti holati chalg'ituvchi bo'lib qoladi, sessiyalar tasodifiy uziladi, lokal ma'lumotlar bulut bilan to'qnashuvga keladi (data conflict).

**Root cause:**
Loyihaning dastlabki versiyalari to'liq lokal bo'lgan (v6/v7), keyinchalik bulutli Supabase integratsiyasi (v8/v9) qo'shilganda lokal arxitektura bekor qilinmasdan, uning ustiga parallel ikkinchi arxitektura qurilgan.

**Qayta tekshirish usuli:**
Frontend kodida `supabase.from()` chaqiruvlari bilan `backendService` chaqiruvlari ketma-ketligini solishtirish.

**Tavsiya:**
Frontend faqat va faqat yagona qatlam bilan muloqot qilishi kerak: barcha so'rovlar Backend API orqali o'tishi va backend Supabase bilan muloqotni boshqarishi lozim (Backend-for-Frontend / BFF pattern).

**Qabul mezoni:**
Frontend kodida `supabaseClient` orqali to'g'ridan-to'g'ri jadval manipulyatsiyasi qolmasligi, barcha CRUD operatsiyalari API orqali amalga oshirilishi.

**Cheklovlar:**
Mavjud Supabase RLS qoidalarining to'liq ro'yxati faqat SQL fayllar orqali o'rganildi.

---

### Topilma ID: ARC-003
**Sarlavha:** Global O'zgaruvchan Singletonlar va Multi-Tenant Izolyatsiyasining Yo'qligi  
**Kategoriya:** Architecture / State Management  
**Jiddiylik darajasi:** High  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** 
- [core/ai_engine.py](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/ai_engine.py#L74-L76)
- [core/agent_memory.py](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/agent_memory.py#L41-L65)
- [core/v8/auth_session.py](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/v8/auth_session.py#L64)

**Dalil:**
```python
# core/ai_engine.py L74-L76
suhbat_tarixi_gemini = []  # Global ro'yxat
suhbat_tarixi_openrouter = []  # Global ro'yxat
```
```python
# core/agent_memory.py L42-L44
self._conversations_file = get_data_path("agent_conversations.json")
self._profile_file = get_data_path("agent_profile.json")
```

**Muammo tavsifi:**
AI suhbat tarixi va foydalanuvchi bilimlari global modul darajasidagi ro'yxatlar va yagona JSON fayllarda saqlanadi. Agar Telegram bot orqali boshqa foydalanuvchi murojaat qilsa yoki masofaviy qurilma ulansa, barcha so'rovlar ayni bitta global xotiraga yoziladi va o'qiladi.

**Yuzaga kelish shartlari:**
Bir vaqtning o'zida desktop foydalanuvchisi va Telegram foydalanuvchisi Misa bilan muloqot qilganda.

**Ta’siri:**
Foydalanuvchilar suhbati va shaxsiy ma'lumotlari bir-biriga aralashib ketadi (Data Bleed / Cross-Talk).

**Root cause:**
Dastlab faqat bir kishilik shaxsiy kompyuter skripti sifatida yozilgan mantiq ko'p foydalanuvchili (Telegram / Remote) rejimga kengaytirilganda sessiya konteksti kiritilmagan.

**Qayta tekshirish usuli:**
Ikkita turli foydalanuvchi nomidan parallel chat so'rovi yuborilib, `suhbat_tarixi_gemini` ro'yxati tekshiriladi.

**Tavsiya:**
Har bir sessiya va foydalanuvchi uchun alohida `SessionContext` yaratish, suhbat tarixini `user_id` / `session_id` ga bog'langan holda boshqarish.

**Qabul mezoni:**
Har bir foydalanuvchi faqat o'z suhbat kontekstini ko'rishi va global mutable ro'yxatlar butunlay olib tashlanishi.

**Cheklovlar:**
Haqiqiy parallel ko'p foydalanuvchili yuklama testi o'tkazilmadi.

---

### Topilma ID: ARC-004
**Sarlavha:** Rivojlantirish Portlari (1420) va Imtiyozli Portlar (140) Bilan To'qnashuv Arxitekturasi  
**Kategoriya:** Architecture / Network Lifecycle  
**Jiddiylik darajasi:** High  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** 
- [core/api_server.py](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/api_server.py#L7847-L7862)
- [Misa/src-tauri/tauri.conf.json](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src-tauri/tauri.conf.json#L8)

**Dalil:**
```python
# core/api_server.py L7848-L7852
for aux_port in (1420, 140):
    if resolved_port != aux_port:
        aux_site = web.TCPSite(runner, resolved_host, aux_port)
        await aux_site.start()
```
`tauri.conf.json` faylida esa:
```json
"devUrl": "http://localhost:1420"
```

**Muammo tavsifi:**
Python backend server asosiy 18420 portidan tashqari, 1420 va 140 portlarini ham egallashga (bind) urinadi. Port 1420 Vite frontend dev-serverining standart porti bo'lib, uning backend tomonidan egallanishi Vite ishga tushishini bloklaydi. Port 140 esa tizim imtiyozli porti bo'lib, unga ulanish OS darajasida xatolik keltirib chiqaradi.

**Yuzaga kelish shartlari:**
Desktop ilova ishlab chiquvchi muhitida (`npm run desktop`) ishga tushirilganda.

**Ta’siri:**
Frontend serveri boshqa tasodifiy portga ko'chadi yoki ishga tushmay qoladi, desktop oyna bo'sh (oq ekran) bo'lib qoladi.

**Root cause:**
Eski OAuth callbacklarini ushlash uchun kiritilgan vaqtinchalik yechim tozalab tashlanmagan.

**Qayta tekshirish usuli:**
`core/api_server.py` ishga tushirilganda `netstat -ano | findstr 1420` buyrug'i bilan tekshiriladi.

**Tavsiya:**
Auxiliary portlar (1420, 140) listening qismini butunlay o'chirish. OAuth callbacklari faqat asosiy 18420 porti yoki Tauri maxsus URI scheme (`misa://`) orqali qabul qilinishi shart.

**Qabul mezoni:**
Backend faqat va faqat belgilangan yagona portda (standart: 18420) tinglashi.

**Cheklovlar:**
Port 140 ga bog'lanish faqat admin huquqlari bo'lmaganda rad etiladi.

---

### Topilma ID: ARC-005
**Sarlavha:** Rust Desktop Supervayzerida Sinxron PowerShell Jarayonlarini Qayta-Qayta Ishga Tushirish  
**Kategoriya:** Architecture / Process Lifecycle  
**Jiddiylik darajasi:** Medium  
**Ishonchlilik darajasi:** Confirmed  
**Aniq joylashuv:** 
- [Misa/src-tauri/src/lib.rs](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src-tauri/src/lib.rs#L420-L431)

**Dalil:**
```rust
// Misa/src-tauri/src/lib.rs L427-L430
let _ = Command::new("powershell")
    .args(["-NoProfile", "-NonInteractive", "-Command", &cmd_str])
    .creation_flags(CREATE_NO_WINDOW)
    .status();
```

**Muammo tavsifi:**
Desktop supervayzeri portni egallab turgan jarayonni aniqlash va o'ldirish uchun har safar yangi `powershell.exe` jarayonini ishga tushiradi. PowerShell yuklanishi Windows tizimida 500-1500ms vaqt va sezilarli disk/CPU resursini talab qiladi. Bu asinxron Rust arxitekturasini bloklaydi.

**Yuzaga kelish shartlari:**
Backend qayta ishga tushirilganda yoki sog'lomlik tekshiruvi muvaffaqiyatsiz bo'lganda.

**Ta’siri:**
Ilova interfeysi muzlab qolishi (UI hang/freeze), keraksiz og'ir jarayonlar oqimi.

**Root cause:**
Windows API (`GetExtendedTcpTable`, `TerminateProcess`) o'rniga tezkor skript orqali muammoni hal qilishga urinish.

**Qayta tekshirish usuli:**
Windows Task Manager yoki Process Explorer orqali Misa ishga tushishida `powershell.exe` chaqiruvlarini kuzatish.

**Tavsiya:**
PowerShell o'rniga to'g'ridan-to'g'ri Windows API (`windows-sys` yoki `winapi` krate) yordamida port va PID ni boshqarish.

**Qabul mezoni:**
Misa desktop ishga tushishida va yopilishida bitta ham `powershell.exe` jarayoni ochilmasligi.

**Cheklovlar:**
Windows OS versiyalariga qarab PowerShell yuklanish tezligi farq qilishi mumkin.

---

## 4. TEKSHIRISH IMKONI BO'LMAGAN QISMLAR VA CHEKLOVLAR
- Haqiqiy ko'p foydalanuvchili tarmoq yuklamasi ostidagi CPU va xotira profillash o'tkazilmadi (faqat statik arxitektura tahlili).
- Loyiha kodini o'zgartirish taqiqlangani sababli, taklif qilingan router dekompozitsiyasi amalda sinab ko'rilmadi.

---

## 5. UMUMIY XULOSA VA USTUVOR YO'NALISHLAR
Misa arxitekturasi jiddiy qayta tashkil etishga (Refactoring / Domain Separation) muhtoj. 7,900 qatorli monolit backend va 4,500 qatorli frontend sahifalari tizimning keyingi rivojlanishini deyarli to'xtatib qo'ygan.

### Boshlang'ich ustuvor vazifalar:
1. `core/api_server.py` ni kichik, mustaqil routerlarga ajratish.
2. Global mutable holatlarni (`suhbat_tarixi_gemini` va `AgentMemory`) ko'p foydalanuvchili sessiya modeliga o'tkazish.
3. Supabase bilan to'g'ridan-to'g'ri frontend muloqotini to'xtatib, barcha tranzaksiyalarni backend orqali markazlashtirish.
