# MISA V9 — UI/UX AUDIT: EXTERNAL RESEARCH, HEURISTICS & BENCHMARKS
**Loyiha:** Misa Desktop AI Assistant (v9.0.0 / v9.3)  
**Audit Davri:** 2026-10-24  
**Auditor:** Senior UX Researcher & Principal Interaction Designer  
**Katalog:** `hal qilinishi kerak bo'lgan xatoliklar\ui_ux_deep_audit_2026-10-24_18-29\`  
**Standartlar:** Nielsen Norman Group (NN/g) 10 Usability Heuristics, Google People + AI Guidebook (PAIR), Microsoft Guidelines for Human-AI Interaction, W3C WAI-ARIA APG  
**Holat:** Rasmiy UX Standartlari va Ilmiy Tadqiqotlar Bazasi

---

## 1. TADQIQOT METODOLOGIYASI

Desktop AI Agent mahsulotlarining foydalanuvchi tajribasi (UX) an’anaviy dasturlardan farq qiladi. Chunki sun’iy intellekt agenti foydalanuvchi nomidan murakkab, noaniq va ko‘p qadamli harakatlarni bajaradi. Bu yerda asosiy mezon — **Foydalanuvchi nazorati (User Agency)**, **Tizim holatining shaffofligi (Transparency)** va **Xatolardan tiklanish qulayligi (Forgiveness)** dir.

Ushbu tadqiqotda inson-mashina o‘zaro ta’siri (HCI) sohasidagi dunyoning eng nufuzli standartlari va yetakchi AI desktop mahsulotlari (Raycast, Cursor, Claude Desktop, ChatGPT) amaliy tajribasi o‘rganildi.

---

## 2. RASMIY USABILITY VA INTERACTION STANDARTLARI

### 1. Nielsen Norman Group (NN/g): 10 Usability Heuristics
- **Tashkilot:** Nielsen Norman Group (Jakob Nielsen)
- **Rasmiy Manba:** https://www.nngroup.com/articles/ten-usability-heuristics/
- **Asosiy Qoidalar:**
  - **Heuristic #1: Visibility of System Status:** Tizim doimo nima bo‘layotgani haqida foydalanuvchiga o‘z vaqtida va tushunarli fikr-mulohaza (feedback) berishi kerak.
  - **Heuristic #3: User Control and Freedom:** Foydalanuvchi adashib boshlagan amalni darhol to‘xtatish yoki bekor qilish (Emergency Exit / Undo) imkoniga ega bo‘lishi shart.
  - **Heuristic #5: Error Prevention:** Xato yuz berishini kutmasdan, uning oldini oluvchi sharoitlar yaratilishi lozim.
  - **Heuristic #9: Help Users Recognize, Diagnose, and Recover from Errors:** Xato xabarlari texnik kodlar emas, balki oddiy tilda yozilishi va yechim yo‘lini ko‘rsatishi kerak.
- **Misa Uchun Tatbiq:** Misa'da agent uzoq vaqt ishlaganda foydalanuvchiga qaysi qadamda ekani ko‘rinmaydi, jarayonni darhol to‘xtatuvchi `Abort` tugmasi yo‘q va xatolar ko‘pincha texnik inglizcha yozuvlar bilan chiqadi.

### 2. Google People + AI Guidebook (PAIR)
- **Tashkilot:** Google PAIR (People + AI Research)
- **Rasmiy Manba:** https://pair.withgoogle.com/guidebook/
- **Asosiy Qoidalar:**
  - **Mental Models & Expectations:** Foydalanuvchi AI nimalarni qila olishi va nimalarni qila olmasligini birinchi daqiqalardanoq to‘g‘ri tushunishi kerak. Sun’iy umidlar berish ishonchni o‘ldiradi.
  - **Explainability & Trust:** AI bergan javob yoki bajargan amali nima uchun shunday bo‘lganini qisqa va aniq dalil bilan asoslashi shart.
  - **Feedback & Control:** Foydalanuvchi AI natijasini osongina tahrirlashi, rad etishi yoki o‘zgartirishi kerak.
- **Misa Uchun Tatbiq:** Misa'ning birinchi ishga tushishida qat’iy ro‘yxatdan o‘tish oynasi (Auth Wall) foydalanuvchining ilova imkoniyatlarini sinab ko‘rishiga to‘siq bo‘lmoqda.

### 3. Microsoft Guidelines for Human-AI Interaction
- **Tashkilot:** Microsoft Research (Amershi et al.)
- **Rasmiy Manba:** https://www.microsoft.com/en-us/research/project/guidelines-for-human-ai-interaction/
- **Asosiy Qoidalar:**
  - **G1 (Make clear what the system can do):** Tizim o‘z imkoniyatlarini ochiq ko‘rsatsin.
  - **G5 (Match relevant social norms):** Madaniy va lingvistik me’yorlarga mos so‘zlashuv.
  - **G9 (Support efficient invocation):** Kerakli paytda chaqirish qulayligi (Global hotkey / Command Palette).
  - **G10 (Support efficient dismissal):** Chaqirilgan yordamchini bir tugma bilan bekor qilish.
- **Misa Uchun Tatbiq:** Misa'da ovozli assistent o‘zi gapirayotgan paytda foydalanuvchining gapini tinglay olmaydi va o‘z-o‘zini to‘xtatib qo‘yish (self-interruption) xatolariga uchraydi.

---

## 3. BENCHMARK TAQQOSLAVI: DESKTOP AI INTERACTION PATTERNS

| Usability Mezoni | Misa AI (Amaldagi Holat) | Raycast Desktop | Cursor AI Agent | Claude Desktop |
|---|---|---|---|---|
| **Birinchi Taassurot (Onboarding)** | Majburiy Auth Wall (Sinab ko‘rib bo‘lmaydi) | Mehmon rejimi (Guest / Instant Utility) | Mahalliy kodda darhol ishlash | Boshlang‘ich tezkor suhbat |
| **Agent Vazifasi Shaffofligi** | Qora quti (Apertura porlaydi, lekin qadamlar yo‘q) | Qadamlar ro‘yxati (Step checklist) | Fayllar diffi va tool loglari | Fikr yuritish bloki (Collapsible Thought) |
| **Amalni To‘xtatish (Cancel/Abort)** | Mavjud emas (server tugatishini kutish kerak) | `Escape` tugmasi bilan bir zumda to‘xtatish | `Stop Generating` qizil tugmasi | `Stop` tugmasi |
| **Sozlamalar Arxitekturasi** | 4 xil sahifada tarqoq (Account, Voice, Remote, Commands) | Bitta markazlashgan qidiruvli Preferences | Standart VSCode Settings UI | Bitta sodda Settings paneli |
| **Ovozli Muloqot Feedbacki** | Ovoz balandligi indikatori chala, uzilishlar ko‘p | Faqat matnli diktovka (Whisper) | Audio kiritilmagan | Audio kiritilmagan |
| **Klaviatura Navigatsiyasi** | Chala (`Tab` tartibi buzilgan, fokus halqasi ko‘rinmaydi) | 100% klaviaturadan boshqariladigan interfeys | 100% klaviatura bilan mos | Standart klaviatura |

---

## 4. XULOSA
Usability tadqiqoti shuni ko‘rsatadiki, Misa'ning eng katta muammosi funksiyalar yetishmasligi emas, balki **mavjud funksiyalarning foydalanuvchiga ko‘rinmasligi, boshqaruvni yo‘qotish hissi va xatolardan keyin tiklanish yo‘lining yopiqligi**dir.
