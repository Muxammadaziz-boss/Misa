# 05 — FINAL PRIORITIZED RISK & REMEDIATION REGISTER
## MISA V9 — Yig'ma Qat'iy Xavf-Xatarlar Reyestri va Tuzatish Ketma-Ketligi

- **Audit Turi:** Calibrated Risk Prioritization & Engineering Action Register (Phase 4)
- **Sana:** 2026-10-24
- **Auditor Roli:** Chief Risk Officer, Principal Security Architect & Engineering Lead
- **Jami Unifikatsiyalangan Muammolar:** 32 ta Root Cause
- **Qat'iy Qoida:** 100% READ-ONLY. Hech qanday kod o'zgartirilmadi.

---

## 1. JIDDIY LIK DARAJALARI BO'YICHA TAQSIMOT

Audit yaxlitligi tekshiruvidan so'ng jiddiylik darajalari real ta'sirga qarab to'liq qayta kalibrlandi:

```
   Tier 1: CRITICAL [██████] 6 ta (19%) — Zudlik bilan to'xtatuvchi xavflar (RCE, Crash, Secret Leak)
   Tier 2: HIGH     [███████████] 11 ta (34%) — Jiddiy xavfsizlik, a11y va agent boshqaruv to'siqlari
   Tier 3: MEDIUM   [███████████] 11 ta (34%) — Foydalanish qulayligi, dizayn va xotira boshqaruvi
   Tier 4: LOW      [████] 4 ta (13%) — Estetika, intro va arxitektura tozaligi
   ---------------------------------------------------------------------------------------------------
   JAMI             : 32 ta To'liq Isbotlangan Master Muammo (100% Confirmed)
```

---

## 2. TIER 1: CRITICAL (O'TA JIDDIY VA ZUDLIK BILAN TUZATILISHI SHART — 6 TA)

Ushbu 6 ta muammo bartaraf etilmaguncha Misa v9 ni ommaga yoki foydalanuvchilarga tarqatish qat'iyan taqiqlanadi:

### 1. `MISA-ROOT-001`: Port 18420 dagi mahalliy API autentifikatsiyasi yo'qligi va CORS `*`
- **Fayl & Qator:** [`core/api_server.py:7328-7330`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/api_server.py#L7328), [7351](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/api_server.py#L7351)
- **CWE / Standart:** CWE-306, OWASP ASVS v4.0.3 V13.2.3
- **Haqiqiy Xavf:** Foydalanuvchi oddiy Chrome/Edge brauzerida ixtiyoriy zararli veb-saytga kirsa, saytdagi JavaScript `http://127.0.0.1:18420` ga so'rov yuborib, kompyuterda fayllarni o'qishi yoki buyruqlar bajarishi mumkin (`Access-Control-Allow-Private-Network: true` bunga yo'l ochib beradi).
- **Tuzatish Talabi:** Desktop rejimida ham dinamik sessiya tokeni (`X-Misa-Session-Token`) majburiy qilinsin va faqat `tauri://localhost` yoki `http://localhost:1420` ga CORS ruxsati berilsin.

### 2. `MISA-ROOT-002`: NSIS Installerda `_internal` katalogining yo'qligi sababli qulash
- **Fayl & Qator:** [`Misa/src-tauri/tauri.conf.json:37-40`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src-tauri/tauri.conf.json#L37)
- **Haqiqiy Xavf:** O'rnatilgan dastur yangi kompyuterda ochilishi bilan `python311.dll topilmadi` xatosi bilan birinchi soniyada qulaydi (Installer faqat `.exe` ni olib, C-kutubxonalarni tashlab ketgan).
- **Tuzatish Talabi:** `tauri.conf.json` dagi `bundle.resources` ga `"backend/**/*"` deb yozilsin.

### 3. `MISA-ROOT-003`: Native `ShellExecuteW` da URL protokoli tekshirilmasligi
- **Fayl & Qator:** [`Misa/src-tauri/src/lib.rs:681`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src-tauri/src/lib.rs#L681)
- **CWE / Standart:** CWE-20, MITRE ATT&CK T1204
- **Haqiqiy Xavf:** Frontenddan `app_open_external_url` chaqirilganda `url` prefiksi tekshirilmaydi. Agar URL sifatida `cmd.exe /c ...` yoki `.bat` yuborilsa, Windows uni bevosita ishga tushiradi (RCE).
- **Tuzatish Talabi:** Faqat `http://` va `https://` protokollariga qat'iy ruxsat berilsin, boshqa har qanday sxema bloklansin.

### 4. `MISA-ROOT-004`: `open_app` vositasida PowerShell argument inyeksiyasi
- **Fayl & Qator:** [`core/agent_tools.py:514`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/agent_tools.py#L514)
- **CWE / Standart:** CWE-78 (OS Command Injection)
- **Haqiqiy Xavf:** `f"Start-Process '{app_cmd}'"` satrida `app_cmd` ga `calc'; Start-Process 'cmd.exe` yozilsa, bittalik qo'shtirnoq yopilib, ixtiyoriy PowerShell komandasi bajariladi.
- **Tuzatish Talabi:** Argumentlarni f-string bilan ulamasdan, `subprocess.Popen(["powershell", "-NoProfile", "-Command", "Start-Process", "-FilePath", app_cmd])` ko'rinishida argumentli massiv orqali uzatilsin yoki whitelist tekshiruvi qo'yilsin.

### 5. `MISA-ROOT-005`: API kalitlarning ochiq JSON faylda saqlanishi
- **Fayl & Qator:** [`core/v8/ai_key_manager.py:115`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/core/v8/ai_key_manager.py#L115)
- **CWE / Standart:** CWE-312, OWASP ASVS V8.1
- **Haqiqiy Xavf:** OpenAI, Gemini va OpenRouter kalitlari `data/ai_keys_cache.json` faylida shifrlashsiz saqlanadi. Kompyuterdagi har qanday begona dastur ularni bir lahzada o'g'irlashi mumkin.
- **Tuzatish Talabi:** Windows DPAPI (`CryptProtectData`) yoki tizim keyring vositasi orqali shifrlash joriy etilsin.

### 6. `MISA-ROOT-006`: Destruktiv amallarda Human-In-The-Loop frontend tasdiqlovining yo'qligi
- **Fayl & Qator:** [`Misa/src/pages/ChatPage.tsx`](file:///d:/Ishchi%20stoli/Misa/yordamchi_9.0.0/Misa/src/pages/ChatPage.tsx)
- **CWE / Standart:** OWASP Top 10 for LLMs 2025 LLM06:2025 (Excessive Agency)
- **Haqiqiy Xavf:** Backendda `security_policy.py` tasdiqlash talab qilsa ham, frontend `ChatPage.tsx` da bu tasdiqni ko'rsatuvchi hech qanday dialog mavjud emas; xavfli harakatlar yo bloklanib qotib qoladi yoki foydalanuvchining bexabar bajariladi.
- **Tuzatish Talabi:** `CONFIRMATION_REQUIRED` signali kelganda frontendda foydalanuvchiga aniq ruxsat berish / rad etish modali chiqarilsin.

---

## 3. TIER 2: HIGH (MUHIM FOYDALANISH VA XAVFSIZLIK TO'SIQLARI — 11 TA)

1. **`MISA-ROOT-007`:** Rust `lib.rs:290, 314` da `release/v9.3` qidiruv yo'lining yo'qligi (eski v9.2 backend ishga tushadi).
2. **`MISA-ROOT-008`:** `App.css:91` dagi `outline: none` tufayli klaviatura fokusining yo'qolishi (WCAG 2.2 SC 2.4.7 buzilishi).
3. **`MISA-ROOT-009`:** `AuthPage.tsx:1824` dagi inputlarda `<label htmlFor>` va `id` yo'qligi (Screen readerlar ishlamaydi).
4. **`MISA-ROOT-010`:** `UpdateModal.tsx:150` da `role="dialog"` va focus trap yo'qligi (Klaviatura orqaga chiqib ketadi).
5. **`MISA-ROOT-011`:** High-DPI 150% ekranlarda 800px oyna balandligi sababli chat kiritish maydoni ekrandan pastga qirqilishi (`lib.rs:1310`).
6. **`MISA-ROOT-012`:** `ChatPage.tsx` da agent generatsiyasini to'xtatuvchi `[■ To'xtatish]` (AbortController) tugmasi yo'qligi.
7. **`MISA-ROOT-013`:** Agent qadamlari va rejasi foydalanuvchiga ko'rinmasligi ("Qora quti" sindromi — NN/g #1).
8. **`MISA-ROOT-014`:** Ovozli muloqotda AEC va Ducking yo'qligi tufayli Misa o'z karnayidagi ovozidan o'zini to'xtatishi (`core/audio_service.py`).
9. **`MISA-ROOT-015`:** `models/wake_word/` da "Salom Misa" `.onnx` modeli yo'qligi (faqat README.md bor).
10. **`MISA-ROOT-016`:** Oyna sarlavhalari va klipbord matnining filtrsiz promptga qo'shilishi (Indirect Prompt Injection).
11. **`MISA-ROOT-017`:** `AuthPage.tsx` da forma yuborishda takroriy bosish va so'rovlar poygasi (Double-Click Race).

---

## 4. TIER 3: MEDIUM (FOYDALANISH QULAYLIGI VA DIZAYN — 11 TA)

1. **`MISA-ROOT-018`:** `Button.tsx` da `--glass-bg`, `--glass-border` kabi mavjud bo'lmagan tokenlar ishlatilishi.
2. **`MISA-ROOT-019`:** Yorug' mavzuda (`theme-light`) oq fonda qattiq `#FFFFFF` yozuvlar qolib, kontrast yo'qolishi.
3. **`MISA-ROOT-020`:** Sozlamalarning 5 ta alohida sahifaga tarqalib ketganligi (Yagona `/settings` markazi zarur).
4. **`MISA-ROOT-021`:** Xotira va Rejalashtiruvchi sahifalarida boy bo'sh holatlar (Empty States) yo'qligi.
5. **`MISA-ROOT-022`:** Yangi suhbatda birinchi marta kirgan foydalanuvchi uchun tayyor Prompt chiplari yo'qligi.
6. **`MISA-ROOT-023`:** Lokal SQLite xotirasida ko'p foydalanuvchilar o'rtasida ma'lumotlar ajratilmaganligi.
7. **`MISA-ROOT-024`:** Ctrl+K Command Palette'da WAI-ARIA Combobox semantikasi yo'qligi.
8. **`MISA-ROOT-025`:** `IconButton.tsx` 34px bo'lib, sensorli ekranlar uchun 44px minimal nishon mezoniga mos emasligi.
9. **`MISA-ROOT-026`:** Web Speech API orqali ovoz uzatilishida sozlamalarda shaffof opt-in ruxsat bildirishnomasi yo'qligi.
10. **`MISA-ROOT-027`:** Foydalanuvchi xotiradagi faktlarni interfeys orqali to'g'ridan-to'g'ri o'chira yoki tahrirlay olmasligi.
11. **`MISA-ROOT-028`:** AI provayderi xato berganda zaxira modelga o'tish holati foydalanuvchiga ko'rinmasligi.

---

## 5. TIER 4: LOW (ESTETIKA VA KOSMETIK TOZALASH — 4 TA)

1. **`MISA-ROOT-029`:** Tarmoq uzilganda yoki xato berganda chatda [Qayta urinish] (Retry) tugmasi yo'qligi.
2. **`MISA-ROOT-030`:** Monolit fayllar (`api_server.py` 7920 qator, `backendService.ts` 4900 qator) arxitekturaviy og'irligi.
3. **`MISA-ROOT-031`:** Har ochilishda majburiy 800ms intro video va audio ijro etilishi.
4. **`MISA-ROOT-032`:** Manba kodlarida eski `Mikasa` brand qoldiqlari (`mikasa-logo`, `mikasa-button`).

---

## 6. TUZATISH KETMA-KETLIGI VA BOG'LIQLIK DARAHTI (DEPENDENCY TREE)

Muhandislik guruhi tuzatishlarni quyidagi qat'iy texnologik zanjir bo'yicha bajarishi shart:

```
+-------------------------------------------------------------------------+
| BOSQICH 1: YADRO VA XAVFSIZLIK (BLOKLOVCHILAR)                          |
| - MISA-ROOT-001 (API Auth & CORS)                                       |
| - MISA-ROOT-002 (Tauri installer _internal resursi)                     |
| - MISA-ROOT-003 (Rust ShellExecuteW protokoli)                          |
| - MISA-ROOT-004 (PowerShell command injection)                          |
| - MISA-ROOT-005 (DPAPI bilan API kalitlarni shifrlash)                  |
| - MISA-ROOT-007 (lib.rs dagi v9.3 nomzod yo'li)                         |
+------------------------------------+------------------------------------+
                                     |
+------------------------------------v------------------------------------+
| BOSQICH 2: FOYDALANUVCHI NAZORATI VA ACCESSIBILITY BAZASI               |
| - MISA-ROOT-006 (ChatPage HITL tasdiqlash modali)                       |
| - MISA-ROOT-008 (App.css dagi :focus-visible tiklanishi)                |
| - MISA-ROOT-009 (AuthPage inputlariga label/id ulash)                   |
| - MISA-ROOT-010 (Modal focus trap va dialog semantikasi)                |
| - MISA-ROOT-012 (ChatPage [■ To'xtatish] AbortController)               |
| - MISA-ROOT-017 (AuthPage isSubmitting double-click himoyasi)           |
+------------------------------------+------------------------------------+
                                     |
+------------------------------------v------------------------------------+
| BOSQICH 3: MULTIMODAL VA AGENT SHAFFOFLIGI                              |
| - MISA-ROOT-011 (Tauri 150% scaling va dinamik oyna balandligi)         |
| - MISA-ROOT-013 (ChatPage agent rejasi va qadamlar akordeoni)           |
| - MISA-ROOT-014 (Audio Ducking va echo suppression)                     |
| - MISA-ROOT-015 (models/wake_word neyron modeli)                        |
| - MISA-ROOT-016 (Active window context sanitizatsiyasi)                 |
+------------------------------------+------------------------------------+
                                     |
+------------------------------------v------------------------------------+
| BOSQICH 4: DIZAYN TIZIMI VA AXBOROT ARXITEKTURASI                       |
| - MISA-ROOT-018 (tokens.css ga --glass-bg va --radius-pill qo'shish)    |
| - MISA-ROOT-019 (Yorug' mavzuda matn kontrastini tuzatish)              |
| - MISA-ROOT-020 (Yagona /settings sozlamalar paneli)                    |
| - MISA-ROOT-021 (Memory va Scheduler Empty State kartalari)             |
| - MISA-ROOT-022 (Yangi chatda boshlang'ich Prompt chiplari)             |
| - MISA-ROOT-024 (Command Palette WAI-ARIA Combobox)                     |
| - MISA-ROOT-027 (Xotirani tahrirlash interfeysi)                        |
| - MISA-ROOT-031 (Intro videoni sozlamalarda ixtiyoriy qilish)           |
+-------------------------------------------------------------------------+
```

Ushbu 4 bosqichli registr loyiha egasiga va muhandislar jamoasiga Misa AI v9 ni eng qisqa yo'l bilan mutlaqo barqaror, xavfsiz va xalqaro talablarga mos mahsulot darajasiga olib chiqish uchun to'liq yo'llanma beradi.
