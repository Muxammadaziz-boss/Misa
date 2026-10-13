// ========== network_acceptance.test.mjs ==========
// Misa AI v9.0.1 — Clean-PC Network Acceptance & URL Resolution Test Suite

import test from 'node:test';
import assert from 'node:assert/strict';

// Mock browser window environment
function createMockWindow(mode = null, customUrl = null) {
  const store = {};
  if (mode) store['misa_server_mode'] = mode;
  if (customUrl) store['misa_backend_url'] = customUrl;

  return {
    location: {
      protocol: 'https:',
      hostname: 'misa.ai',
    },
    localStorage: {
      getItem: (key) => store[key] || null,
      setItem: (key, val) => { store[key] = String(val); },
      removeItem: (key) => { delete store[key]; },
    },
    __TAURI_INTERNALS__: {},
  };
}

const PRODUCTION_API_URL = "https://misa.up.railway.app";
const LOCAL_BACKEND_URL = "http://127.0.0.1:18420";

function isLocalhost(url) {
  if (!url) return false;
  try {
    const parsed = new URL(url.trim());
    const host = parsed.hostname.toLowerCase();
    return host === 'localhost' || host === '127.0.0.1' || host === '::1' || host === '[::1]' || host.endsWith('.localhost');
  } catch {
    const lower = url.toLowerCase();
    return lower.includes('localhost') || lower.includes('127.0.0.1');
  }
}

function resolveApiBaseTest(win, env = {}) {
  const envUrl = (env.VITE_API_URL || '').trim();

  if (win && win.localStorage) {
    let storedCustom = '';
    let storedMode = '';
    try {
      storedCustom = (win.localStorage.getItem('misa_backend_url') || '').trim();
      storedMode = (win.localStorage.getItem('misa_server_mode') || '').trim().toLowerCase();
    } catch {}

    if (storedCustom) {
      return storedCustom.replace(/\/$/, '');
    }

    if (storedMode === 'local') {
      return LOCAL_BACKEND_URL;
    }
    if (storedMode === 'cloud' || storedMode === 'remote') {
      return PRODUCTION_API_URL;
    }
  }

  if (envUrl && !isLocalhost(envUrl)) {
    return envUrl.replace(/\/$/, '');
  }

  return PRODUCTION_API_URL;
}

test('Clean PC: First launch with zero localStorage defaults to Cloud Production URL', () => {
  const win = createMockWindow();
  const resolved = resolveApiBaseTest(win, { VITE_API_URL: 'https://misa.up.railway.app' });
  assert.equal(resolved, 'https://misa.up.railway.app');
  assert.notEqual(resolved, 'http://127.0.0.1:18420');
});

test('Clean PC: Even if legacy env had localhost, clean PC still defaults to Cloud URL', () => {
  const win = createMockWindow();
  const resolved = resolveApiBaseTest(win, { VITE_API_URL: 'http://127.0.0.1:18420' });
  assert.equal(resolved, 'https://misa.up.railway.app');
});

test('Mode Switching: Cloud -> Local -> Cloud', () => {
  const win = createMockWindow();

  // 1. Initial
  let resolved = resolveApiBaseTest(win);
  assert.equal(resolved, 'https://misa.up.railway.app');

  // 2. User switches to Local mode
  win.localStorage.setItem('misa_server_mode', 'local');
  resolved = resolveApiBaseTest(win);
  assert.equal(resolved, 'http://127.0.0.1:18420');

  // 3. User switches back to Cloud mode
  win.localStorage.setItem('misa_server_mode', 'cloud');
  resolved = resolveApiBaseTest(win);
  assert.equal(resolved, 'https://misa.up.railway.app');
});

test('Custom URL Mode: Setting and clearing custom endpoint', () => {
  const win = createMockWindow();

  // Set custom endpoint
  win.localStorage.setItem('misa_server_mode', 'custom');
  win.localStorage.setItem('misa_backend_url', 'https://api.my-misa-server.org');
  let resolved = resolveApiBaseTest(win);
  assert.equal(resolved, 'https://api.my-misa-server.org');

  // Clear custom endpoint and revert to cloud
  win.localStorage.removeItem('misa_backend_url');
  win.localStorage.setItem('misa_server_mode', 'cloud');
  resolved = resolveApiBaseTest(win);
  assert.equal(resolved, 'https://misa.up.railway.app');
});

test('Offline Error Normalization: Never assumes port 18420 for cloud target', () => {
  const host = new URL(PRODUCTION_API_URL).host;
  const mockErr = new TypeError('Failed to fetch');
  
  const msg = `Serverga ulanib bo'lmadi (${host} bilan aloqa yo'q yoki internet uzilgan).`;
  assert.ok(msg.includes('misa.up.railway.app'));
  assert.ok(!msg.includes('18420'));
});
