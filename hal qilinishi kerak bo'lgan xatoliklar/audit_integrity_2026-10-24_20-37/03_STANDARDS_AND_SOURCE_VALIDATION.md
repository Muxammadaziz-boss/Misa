# 03 — STANDARDS COMPLIANCE & SOURCE VALIDATION
## MISA V9 — Xalqaro Standartlar, Manbalar va Jiddiylik Darajalarini Qayta Tekshirish

- **Audit Turi:** Regulatory Standards & Severity Re-calibration (Phase 4)
- **Sana:** 2026-10-24
- **Auditor Roli:** Lead Compliance, Security Standards & Accessibility Auditor
- **Qamrov:** OWASP ASVS v4.0.3, OWASP LLM 2025 v2.0, W3C WCAG 2.2 AA, WAI-ARIA 1.2 APG, Microsoft Win32 Security.
- **Qat'iy Qoida:** 100% READ-ONLY. Hech qanday kod o'zgartirilmadi.

---

## 1. ME’YORIY STANDART BUZILISHI VS TAVSIYAVIY YAXSHILANISH

Avvalgi hisobotlarda ko'pincha sub'yektiv UX tavsiyalari qat'iy standart buzilishi yoki "Critical" darajadagi xato sifatida ko'rsatilgan. Ushbu hisobot qat'iy me'yoriy mezonlar (Normative Standards) bilan dizayn tavsiyalarini (Advisory Recommendations) aniq ajratadi:

```
+-------------------------------------------------------------------------+
|                  STANDARTLAR VA TAVSIYALAR TAQSIMOTI                    |
+-------------------------------------------------------------------------+
| [QAT'IY ME'YORIY BUZILISHLAR]             [TAVSIYAVIY YAXSHILANISHLAR]  |
| - OWASP ASVS 13.2.3: CORS Bypass          - NN/g: Starter Prompt Chips  |
| - CWE-78: PowerShell Command Injection    - Fluent: Shisha qalinligi    |
| - CWE-20: ShellExecuteW Protokol xatosi   - IA: Yagona /settings paneli |
| - WCAG 2.2 SC 2.4.7: Focus Visible yo'qligi - UI: Tugma soyasining tusi   |
| - WCAG 2.2 SC 1.3.1: Formada Label yo'qligi - Brand: Mikasa vs Misa matni |
| - OWASP LLM06: Excessive Agency           - Motion: Tugma transitioni   |
+-------------------------------------------------------------------------+
```

---

## 2. RASMIY STANDARTLAR REYESTRI VA TEKSHIRUV

Quyidagi jadvalda Misa auditida qo'llanilgan xalqaro standartlar, ularning aniq bandlari, rasmiy URL manzillari va loyihaga tegishlilik darajasi tekshirildi:

| Standart Kodi | Standart Nomi & Versiyasi | Aniq Band / Mezon | Rasmiy Manba (URL) | Misa'dagi Amaliy Qo'llanilishi |
|---|---|---|---|---|
| **OWASP ASVS** | Application Security Verification Standard v4.0.3 | V13.2.3 (REST CORS), V13.1.4 (Localhost Auth) | [OWASP ASVS v4.0.3](https://owasp.org/www-project-application-security-verification-standard/) | **Qat'iy mezon.** Port 18420 dagi `Access-Control-Allow-Origin: *` va `_is_production_mode == False` holati ASVS V13.2.3 ni to'g'ridan-to'g'ri buzadi. |
| **CWE-78** | Improper Neutralization of Special Elements in OS Command | CWE-78 (OS Command Injection) | [CWE-78 MITRE](https://cwe.mitre.org/data/definitions/78.html) | **Qat'iy mezon.** `core/agent_tools.py:514` dagi `Start-Process '{app_cmd}'` f-stringi single-quote orqali escape qilinishi mumkin. |
| **CWE-20** | Improper Input Validation | CWE-20 (Missing Protocol Scheme Validation) | [CWE-20 MITRE](https://cwe.mitre.org/data/definitions/20.html) | **Qat'iy mezon.** `lib.rs:681` dagi `ShellExecuteW` chaqiruvida `http/https` prefikslari tekshirilmaydi. |
| **OWASP LLM 2025** | Top 10 for Large Language Models v2.0 (2025) | LLM01:2025 (Prompt Injection), LLM06:2025 (Excessive Agency) | [OWASP LLM Top 10 2025](https://genai.owasp.org/llm-top-10/) | **Qat'iy mezon.** Oyna sarlavhalari kiritilishi (LLM01) va Human-In-The-Loop frontend modali yo'qligi (LLM06) to'g'ridan-to'g'ri mos keladi. |
| **W3C WCAG 2.2** | Web Content Accessibility Guidelines 2.2 | SC 2.4.7 Focus Visible (Level A), SC 1.3.1 Info & Relationships (Level A) | [W3C WCAG 2.2 Full](https://www.w3.org/TR/WCAG22/) | **Qat'iy mezon.** `App.css:91` dagi `outline: none` SC 2.4.7 ni, `AuthPage.tsx` dagi labellarsiz inputlar SC 1.3.1 ni buzadi. |
| **WAI-ARIA APG** | WAI-ARIA Authoring Practices Guide 1.2 | Dialog (Modal) Pattern, Combobox Pattern | [WAI-ARIA APG](https://www.w3.org/WAI/ARIA/apg/) | **Qat'iy mezon.** `UpdateModal.tsx` da `role="dialog"` va focus-trap yo'qligi APG standartiga zid. |
| **NN/g Heuristics** | Nielsen Norman Group 10 Usability Heuristics | Heuristic #1, Heuristic #3, Heuristic #9 | [NN/g 10 Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/) | **Tavsiyaviy mezon.** Agent faoliyatini tushuntirish va bekor qilish tugmasi (`[Stop]`) foydalanish sifatini oshirish uchun zarur. |
| **Microsoft Fluent** | Fluent Design System (Windows 11) | Acrylic Material & High-DPI Scaling | [Microsoft Fluent Design](https://learn.microsoft.com/en-us/windows/apps/design/) | **Tavsiyaviy mezon.** 150% scalingda 800px oyna qirqilishi Windows UX ko'rsatmasiga ziddir. |

---

## 3. JIDDIY LIK DARAJALARINI QAYTA KALIBRLASH (SEVERITY RE-CALIBRATION)

Audit sifatini buzuvchi eng katta muammo — **"Severity Inflation" (Jiddiylikni sun'iy oshirib yuborish)** holatidir. Masalan, ba'zi hisobotlarda "Oq mavzuda matn oq bo'lib qolishi" yoki "Oyna pastki qismi 150% scalingda biroz qirqilishi" xavfsizlikdagi RCE (Remote Code Execution) bilan bir xil "Critical" deb belgilangan.

Haqiqiy xavf-xatarlar bo'yicha jiddiylik darajalari quyidagicha qayta kalibrlandi:

| Topilma ID | Asl Hisobotdagi Nomi | Asl Daraja | Qayta Kalibrlangan Daraja | Kalibrlash Sababi va Asosi |
|---|---|---|---|---|
| `SEC-001` / `API-001` | Desktop 18420 portida auth yo'qligi va CORS `*` | **Critical** | **Critical** | O'zgarishsiz qoldi. Haqiqiy tarmoq hujumiga (RCE/CSRF) olib keladi. |
| `WIN-001` | Tauri resurslarida `_internal` yo'qligi | **Critical** | **Critical** | O'zgarishsiz qoldi. Dastur o'rnatilgach darhol qulaydi. |
| `SEC-002` | `ShellExecuteW` da protokol tekshiruvi yo'qligi | **Critical** | **Critical** | O'zgarishsiz qoldi. Zararli URL orqali `.exe` ishga tushirish mumkin. |
| `VIS-005` / `VIS-CLR-001` | Oq mavzuda oq fonda oq matn qolishi | **Critical** | **Medium** | **Pasaytirildi.** Bu xavfsizlikka daxli yo'q, tizimni qulatmaydi, foydalanuvchi qorong'i rejimda (default) qulay ishlayveradi. Estetik nuqson. |
| `UI-003` / `VIS-LAY-001` | 150% scalingda 800px oyna qirqilishi | **Critical** | **High** | **Pasaytirildi.** Critical darajaga kirmaydi, chunki oyna o'lchamini sichqoncha bilan o'zgartirish yoki Fullscreen qilish mumkin. Lekin birinchi taassurotni buzgani uchun High qilib belgilandi. |
| `UX-001` | Ochilishda 800ms intro video va ovoz | **Critical** | **Low** | **Pasaytirildi.** Foydalanuvchining shunchaki asabiga tegishi mumkin bo'lgan multimedia xususiyati. Hech qanday ma'lumot yo'qolishiga sabab bo'lmaydi. |
| `A11Y-003` / `A11Y-UX-003` | Modallarda focus trap yo'qligi | **Critical** | **High** | **Pasaytirildi.** Klaviatura foydalanuvchisi uchun noqulay, ammo tizim ishdan chiqmaydi. |
| `AISEC-002` / `AI-UX-002` | Destruktiv amallarda HITL modalining yo'qligi | **High** | **Critical** | **Oshirildi!** AI agent fayllarni o'chirish yoki tizimni o'chirish buyruqlarini foydalanuvchi roziligisiz to'g'ridan-to'g'ri bajarib yuborishi mumkin (OWASP LLM06). |

---

## 4. XULOSA

Ushbu qayta kalibrlash orqali:
- Asosli va xavfli **Critical** muammolar soni sun'iy 16 tadan **haqiqiy va tasdiqlangan 6 taga** tushirildi.
- Dizayn va kosmetik nuqsonlar o'zining to'g'ri o'rniga (**Medium va Low**) joylashtirildi.
- Xalqaro me'yoriy standartlar (OWASP ASVS, WCAG, CWE) faqat ularning rasmiy talablariga mos kelgan taqdirdagina havola qilindi.
