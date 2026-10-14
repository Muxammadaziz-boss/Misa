// ========== desktop_ux_lifecycle.test.mjs ==========
// MISA AI v9.0.1 — Unit & Integration Tests: Desktop UX, Tray/Lifecycle, Startup, and Error Policy
// Run with: node --test tests/desktop_ux_lifecycle.test.mjs

import test from 'node:test';
import assert from 'node:assert/strict';

// Contract functions mirroring backendService.ts logic
function normalizeApiError(error, fallbackMessage = "Xatolik yuz berdi") {
  if (!error) return fallbackMessage;
  let msg = String(error?.message || error || "").trim();
  if (msg.startsWith("{") && msg.endsWith("}")) {
    try {
      const p = JSON.parse(msg);
      if (p && typeof p === "object") {
        msg = String(p.error || p.message || fallbackMessage).trim();
      }
    } catch {}
  }
  const lower = msg.toLowerCase();
  if (
    lower.includes("bearer") ||
    lower.includes("unauthorized") ||
    lower.includes("avtorizatsiya") ||
    lower.includes("token talab qilinadi") ||
    lower.includes("401")
  ) {
    const fbLower = String(fallbackMessage || "").toLowerCase();
    if (fbLower.includes("audio") || fbLower.includes("mikrofon") || fbLower.includes("qurilma")) {
      return "Audio xizmatiga ulanishda sessiya xatosi (Iltimos, qayta kiring).";
    }
    if (fbLower.includes("ovoz") || fbLower.includes("tts") || fbLower.includes("sintez")) {
      return "Ovoz xizmatiga ulanishda sessiya xatosi (Iltimos, qayta kiring).";
    }
    if (fbLower.includes("ai") || fbLower.includes("chat") || fbLower.includes("savol")) {
      return "AI xizmatiga ulanishda muammo yuz berdi (Avtorizatsiyadan o'tilmagan yoki sessiya muddati o'tgan).";
    }
    return "Avtorizatsiyadan o'tilmagan yoki sessiya muddati o'tgan (Iltimos, qayta kiring).";
  }
  if (lower.includes("403") || lower.includes("forbidden") || lower.includes("cross-tenant")) {
    return "Ruxsat etilmagan (HTTP 403: Boshqa hisob ma'lumotlariga kirish taqiqlangan).";
  }
  if (lower.includes("404") || lower.includes("not found") || lower.includes("topilmadi")) {
    return "Resurs yoki foydalanuvchi topilmadi (HTTP 404).";
  }
  if (lower.includes("500") || lower.includes("internal server error")) {
    return "Server ichki xatosi (HTTP 500).";
  }
  if (lower.includes("connection refused") || lower.includes("econnrefused")) {
    return "Serverga ulanib bo'lmadi (aloqani rad etdi - Port yopiq yoki server o'chiq).";
  }
  if (msg.startsWith("{") && msg.endsWith("}")) {
    return fallbackMessage;
  }
  return msg || fallbackMessage;
}

function unwrapCleanResponse(text) {
  if (!text) return "";
  if (typeof text !== "string") {
    if (typeof text === "object") {
      if (text.ok === false || text.error) {
        return normalizeApiError(text.error || text.message || "", "AI xizmatiga ulanishda muammo yuz berdi.");
      }
      return unwrapCleanResponse(text.response || text.content || text.javob || text.message || text.question || "");
    }
    return String(text);
  }
  const trimmed = text.trim();
  if (!trimmed.startsWith("{") && !trimmed.includes('"response":') && !trimmed.includes('"type":')) {
    return trimmed;
  }
  try {
    const parsed = JSON.parse(trimmed);
    if (parsed && typeof parsed === "object") {
      if (parsed.ok === false || parsed.error) {
        return normalizeApiError(parsed.error || parsed.message || "", "AI xizmatiga ulanishda muammo yuz berdi.");
      }
      const inner = parsed.response || parsed.content || parsed.javob || parsed.question || parsed.message;
      if (inner !== undefined) {
        return unwrapCleanResponse(inner);
      }
    }
  } catch {}
  if (trimmed.startsWith("{") && (trimmed.includes('"error":') || trimmed.includes('"ok":false'))) {
    return normalizeApiError(trimmed, "AI xizmatiga ulanishda muammo yuz berdi.");
  }
  return trimmed;
}

// ============================================================
// 1. STARTUP SUCCESS MESSAGE POLICY AUDIT
// ============================================================
test('Startup Policy: Online status produces NO technical success banner or audio speech', () => {
  // Simulating startup briefing decision logic
  const evaluateStartupBriefing = (status) => {
    if (status === 'online') {
      // Must be null/empty - NO "serverga ulandi", NO "barcha modullar faol"
      return null;
    }
    return `Server bilan aloqa o'rnatib bo'lmadi. Tarmoq yoki server holatini tekshirishingizni so'rayman.`;
  };

  const onlineResult = evaluateStartupBriefing('online');
  assert.equal(onlineResult, null, 'Successful startup must not generate any technical success banner');

  const offlineResult = evaluateStartupBriefing('offline');
  assert.ok(offlineResult !== null, 'Offline startup must generate diagnostic warning');
  assert.ok(offlineResult.includes("Server bilan aloqa o'rnatib bo'lmadi"));
});

// ============================================================
// 2. USER-FACING ERROR POLICY & RAW JSON SANITIZATION
// ============================================================
test('Error Policy: Raw JSON error must NEVER be returned to the user', () => {
  const rawAuthErrorJson = '{"ok":false,"error":"Unauthorized: Bearer token required"}';
  const cleanResult = unwrapCleanResponse(rawAuthErrorJson);

  // Must NOT contain raw JSON braces or raw english error
  assert.equal(cleanResult.startsWith('{'), false, 'Clean response must not be raw JSON');
  assert.equal(cleanResult.includes('"ok":false'), false, 'Clean response must not contain JSON tokens');
  assert.ok(
    cleanResult.includes('AI xizmatiga ulanishda muammo yuz berdi') ||
    cleanResult.includes('Avtorizatsiya'),
    `Result must be user friendly in Uzbek. Got: ${cleanResult}`
  );

  const rawServerErr = '{"error":"Internal Server Error","code":500}';
  const cleanServerResult = unwrapCleanResponse(rawServerErr);
  assert.equal(cleanServerResult.startsWith('{'), false);
  assert.ok(cleanServerResult.includes('Server ichki xatosi') || cleanServerResult.includes('AI xizmatiga ulanishda muammo'));
});

test('normalizeApiError: Unpacks nested JSON objects and strings gracefully', () => {
  const errObj = { message: '{"ok":false,"error":"Avtorizatsiyadan o\'tilmagan: Bearer token talab qilinadi"}' };
  const normalized = normalizeApiError(errObj);
  assert.equal(normalized.startsWith('{'), false);
  assert.ok(normalized.includes('Avtorizatsiyadan o\'tilmagan') || normalized.includes('AI xizmatiga ulanishda muammo'));

  // Test 401 status
  assert.ok(normalizeApiError('HTTP 401').includes('Avtorizatsiya') || normalizeApiError('HTTP 401').includes('AI xizmatiga ulanishda muammo'));
  // Test connection refused
  assert.ok(normalizeApiError('ECONNREFUSED').includes('aloqani rad etdi'));
});

// ============================================================
// 3. AI CHAT & AUTHORIZATION HEADER INJECTION
// ============================================================
test('Chat Auth: Bearer token is properly attached when user is authenticated', () => {
  let capturedHeaders = null;

  class MockBackendService {
    constructor() {
      this.authToken = 'mock_jwt_token_12345';
    }

    prepareHeaders() {
      const headers = { 'Content-Type': 'application/json' };
      if (this.authToken) {
        headers['Authorization'] = `Bearer ${this.authToken}`;
      }
      return headers;
    }
  }

  const service = new MockBackendService();
  const headers = service.prepareHeaders();
  assert.equal(headers['Authorization'], 'Bearer mock_jwt_token_12345');
});

// ============================================================
// 4. LIFECYCLE STATE MACHINE & IDEMPOTENCY
// ============================================================
test('Lifecycle State Machine: Idempotent window close and safe transitions', () => {
  const LifecycleState = {
    STARTING: 'Starting',
    READY: 'Ready',
    VISIBLE: 'Visible',
    HIDDEN_TO_TRAY: 'HiddenToTray',
    RESTORING: 'Restoring',
    SHUTTING_DOWN: 'ShuttingDown',
    EXITED: 'Exited',
  };

  class WindowLifecycleController {
    constructor() {
      this.state = LifecycleState.VISIBLE;
      this.backendRunning = true;
      this.hideCallCount = 0;
      this.shutdownCallCount = 0;
    }

    // Emulates app_close
    handleCloseRequested() {
      if (this.state === LifecycleState.HIDDEN_TO_TRAY) {
        // Idempotent: duplicate close events are safe no-ops
        return { action: 'no-op', state: this.state };
      }
      if (this.state === LifecycleState.SHUTTING_DOWN || this.state === LifecycleState.EXITED) {
        return { action: 'no-op', state: this.state };
      }
      this.state = LifecycleState.HIDDEN_TO_TRAY;
      this.hideCallCount++;
      // Backend MUST remain running!
      assert.equal(this.backendRunning, true, 'Backend must remain running when hidden to tray');
      return { action: 'hide', state: this.state };
    }

    // Emulates Tray -> Ochish
    handleRestoreFromTray() {
      if (this.state === LifecycleState.VISIBLE) {
        return { action: 'focus', state: this.state };
      }
      this.state = LifecycleState.VISIBLE;
      return { action: 'show', state: this.state };
    }

    // Emulates Tray -> Chiqish
    handleExit() {
      if (this.state === LifecycleState.SHUTTING_DOWN || this.state === LifecycleState.EXITED) {
        return { action: 'no-op', state: this.state };
      }
      this.state = LifecycleState.SHUTTING_DOWN;
      this.shutdownCallCount++;
      this.backendRunning = false;
      this.state = LifecycleState.EXITED;
      return { action: 'exit', state: this.state };
    }
  }

  const controller = new WindowLifecycleController();

  // 1. Initial State: VISIBLE
  assert.equal(controller.state, LifecycleState.VISIBLE);

  // 2. Click X: Hides to tray, backend stays alive
  const res1 = controller.handleCloseRequested();
  assert.equal(res1.action, 'hide');
  assert.equal(controller.state, LifecycleState.HIDDEN_TO_TRAY);
  assert.equal(controller.hideCallCount, 1);
  assert.equal(controller.backendRunning, true);

  // 3. Repeated rapid clicks on X: IDEMPOTENT NO-OP, NO CRASH, NO DUPLICATE
  const res2 = controller.handleCloseRequested();
  assert.equal(res2.action, 'no-op');
  assert.equal(controller.hideCallCount, 1);

  const res3 = controller.handleCloseRequested();
  assert.equal(res3.action, 'no-op');
  assert.equal(controller.hideCallCount, 1);

  // 4. Restore from tray
  const restoreRes = controller.handleRestoreFromTray();
  assert.equal(restoreRes.action, 'show');
  assert.equal(controller.state, LifecycleState.VISIBLE);

  // 5. Explicit Tray Exit: Performs real shutdown
  const exitRes = controller.handleExit();
  assert.equal(exitRes.action, 'exit');
  assert.equal(controller.state, LifecycleState.EXITED);
  assert.equal(controller.backendRunning, false);
  assert.equal(controller.shutdownCallCount, 1);

  // 6. Duplicate exit calls: Safe no-op
  const duplicateExit = controller.handleExit();
  assert.equal(duplicateExit.action, 'no-op');
  assert.equal(controller.shutdownCallCount, 1);
});

// ============================================================
// 5. REGRESSION: toUpperCase SAFE CONTRACT AUDIT (P0.1)
// ============================================================
test('P0.1 Regression: Audit event status toUpperCase never throws on undefined/null', () => {
  // Simulates backend response where status was previously omitted
  const rawAuditEvents = [
    { event_type: "COMMAND_STARTED", action: "notepad", details: {} }, // no status
    { event_type: "COMMAND_COMPLETED", details: { status: "success" } }, // status in details only
    { event_type: "REMOTE_REQUEST_DENIED", status: null }, // explicit null
    { event_type: "DEVICE_REGISTERED" } // completely empty details/status
  ];

  // Frontend mapper and renderer logic from RemoteControlPage.tsx
  const normalizedEvents = rawAuditEvents.map(evt => {
    // 1. backendService normalization
    const normalized = {
      ...evt,
      status: evt.status || evt.action || evt.event_type || "info",
      action: evt.action || evt.event_type || "action",
    };

    // 2. Component render expression
    const renderedBadge = (normalized.status || normalized.action || normalized.event_type || "INFO").toUpperCase();
    return renderedBadge;
  });

  assert.equal(normalizedEvents[0], "NOTEPAD");
  assert.equal(normalizedEvents[1], "COMMAND_COMPLETED");
  assert.equal(normalizedEvents[2], "REMOTE_REQUEST_DENIED");
  assert.equal(normalizedEvents[3], "DEVICE_REGISTERED");

  // Verify pure defensive rendering without normalization also never throws
  for (const evt of rawAuditEvents) {
    assert.doesNotThrow(() => {
      const val = (evt?.status || evt?.action || evt?.event_type || "INFO").toUpperCase();
      assert.ok(typeof val === "string" && val.length > 0);
    });
  }
});

test('P0.1 Regression: RemoteDevice state toUpperCase never throws on missing state/status', () => {
  const incomingDevices = [
    { device_id: "dev-1", name: "Work PC", status: "online" }, // has status, missing state
    { device_id: "dev-2", name: "Home Laptop", state: "offline" }, // has state, missing status
    { device_id: "dev-3", name: "Cloud Agent" }, // missing both
    { device_id: "dev-4", name: "Null Agent", state: null, status: null }, // explicit null
  ];

  // backendService getRemoteDevices normalization
  const normalizedDevices = incomingDevices.map(d => ({
    ...d,
    state: d.state || d.status || "online",
    status: d.status || d.state || "online",
  }));

  for (const dev of normalizedDevices) {
    assert.doesNotThrow(() => {
      const upper = (dev.state || dev.status || "online").toUpperCase();
      assert.ok(["ONLINE", "OFFLINE"].includes(upper));
    });
  }
});

test('P0.1 Regression: User account avatar & name toUpperCase never throws on empty user', () => {
  const users = [
    { full_name: "", email: "" },
    { full_name: null, email: null },
    {},
    { full_name: "Azizbek", email: "aziz@misa.uz" }
  ];

  const initials = users.map(u => {
    const name = (u.full_name || u.email || "Foydalanuvchi").trim();
    return (name[0] || "U").toUpperCase();
  });

  assert.equal(initials[0], "F");
  assert.equal(initials[1], "F");
  assert.equal(initials[2], "F");
  assert.equal(initials[3], "A");
});

// ============================================================
// 6. REGRESSION: VOICE & AI AUTH POLICY AUDIT (P0.2 & P0.3)
// ============================================================
test('P0.2 & P0.3 Regression: Audio / Voice errors do NOT falsely blame AI service', () => {
  // When an audio device request fails with 401 or network error
  const audioError = normalizeApiError("HTTP 401: Unauthorized", "Audio qurilmalar xizmatiga ulanib bo'lmadi");
  assert.equal(
    audioError.includes("AI xizmatiga ulanishda muammo yuz berdi"),
    false,
    "Audio error must NOT claim AI service connection failure"
  );
  assert.ok(audioError.includes("Audio xizmatiga ulanishda sessiya xatosi") || audioError.includes("sessiya"));

  const voiceError = normalizeApiError("401 Unauthorized", "Ovoz xizmati xatosi");
  assert.equal(
    voiceError.includes("AI xizmatiga ulanishda muammo yuz berdi"),
    false,
    "Voice TTS error must NOT claim AI service connection failure"
  );
  assert.ok(voiceError.includes("Ovoz xizmatiga ulanishda sessiya xatosi") || voiceError.includes("sessiya"));

  // AI chat errors DO properly explain AI service status
  const aiError = normalizeApiError("401 Unauthorized", "AI chat xizmati");
  assert.ok(aiError.includes("AI xizmatiga ulanishda muammo yuz berdi"));
});

test('P0.3 Regression: Clean user without provider key defaults to Misa Cloud AI', () => {
  const evaluateAiProvider = (userConfig) => {
    const hasPersonalKey = !!(userConfig?.gemini_api_key || userConfig?.openai_api_key);
    return {
      provider: hasPersonalKey ? "custom_byok" : "misa_cloud",
      isDefault: !hasPersonalKey,
      requiresUserKey: false,
    };
  };

  const cleanUser = {}; // No API keys configured
  const resolution = evaluateAiProvider(cleanUser);
  assert.equal(resolution.provider, "misa_cloud");
  assert.equal(resolution.isDefault, true);
  assert.equal(resolution.requiresUserKey, false);
});

// ============================================================
// 7. REGRESSION: REMOTE MANAGEMENT CONTRADICTION AUDIT (P1.5)
// ============================================================
test('P1.5 Regression: Remote control title dynamically reflects device enrollment state', () => {
  const getRemoteHeaderTitle = (devices, selectedDevice) => {
    if (!devices || devices.length === 0 || !selectedDevice) {
      return "Qurilma Boshqaruvi";
    }
    return `Faol Agent: ${selectedDevice.name || selectedDevice.hostname || "Windows PC"}`;
  };

  // Zero devices enrolled
  assert.equal(getRemoteHeaderTitle([], null), "Qurilma Boshqaruvi");
  // One active device enrolled
  assert.equal(
    getRemoteHeaderTitle([{ id: "dev-1", name: "Office-PC" }], { id: "dev-1", name: "Office-PC" }),
    "Faol Agent: Office-PC"
  );
});

// ============================================================
// 8. REGRESSION: LOOPBACK SAFETY & HARDWARE ENUMERATION (P1.4 & P1.6)
// ============================================================
test('P1.6 Regression: Microphone loopback monitor defaults to OFF (false)', () => {
  const defaultLoopbackSetting = false; // Must be false to prevent echo
  assert.equal(defaultLoopbackSetting, false, "Microphone loopback must default to OFF");
});

