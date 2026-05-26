/**
 * Nexus módulos desktop (pywebview) — chamadas ao mesmo motor que a IA.
 */

// Polyfill pywebview para iframes (Painel Unificado)
if (window !== window.parent) {
  Object.defineProperty(window, 'pywebview', {
    get: function() { return window.parent.pywebview; }
  });
}

function readBoot() {
  try {
    if (typeof window.__NEXUS_BOOT__ !== "undefined" && window.__NEXUS_BOOT__ !== null) {
      return window.__NEXUS_BOOT__;
    }
    const q = new URLSearchParams(window.location.search).get("boot");
    if (!q) return {};
    return JSON.parse(decodeURIComponent(q));
  } catch (_) {
    return {};
  }
}

const NX_THEME_KEY = "nexus.theme";
const NX_THEME_MODULE_PREFIX = "nexus.theme.";
const NX_THEME_TOKEN_KEYS = [
  "--bg", "--bg-panel", "--surface", "--surface-hover", "--border",
  "--border-accent", "--text", "--text-dim", "--text-muted", "--muted",
  "--accent", "--accent-hover", "--accent-glow", "--accent-subtle",
  "--danger", "--success", "--warning", "--sidebar", "--shadow"
];

function nxThemeStorageKey() {
  const boot = readBoot();
  const mod = (boot.module || "global").toString().replace(/[^a-z0-9_-]/gi, "").toLowerCase() || "global";
  return NX_THEME_MODULE_PREFIX + mod;
}

function nxApplyThemeTokens() {
  const boot = readBoot();
  const tokens = boot.theme_tokens || {};
  if (!tokens || typeof tokens !== "object") return;
  const wrapper = document.getElementById("nx-app-wrapper");
  NX_THEME_TOKEN_KEYS.forEach((key) => {
    const value = tokens[key];
    if (typeof value !== "string" || !value.trim()) return;
    document.documentElement.style.setProperty(key, value);
    if (wrapper) wrapper.style.setProperty(key, value);
  });
}

function nxStoredTheme() {
  const boot = readBoot();
  if (boot.theme_preset || boot.theme_tokens) {
    return boot.theme === "light" ? "light" : "dark";
  }
  try {
    const stored = window.localStorage && (
      window.localStorage.getItem(nxThemeStorageKey()) ||
      window.localStorage.getItem(NX_THEME_KEY)
    );
    if (stored === "light" || stored === "dark") return stored;
  } catch (_) {}
  return boot.theme === "light" ? "light" : "dark";
}

function nxApplyTheme(theme) {
  const next = theme === "light" ? "light" : "dark";
  const wrapper = document.getElementById("nx-app-wrapper");
  if (wrapper) wrapper.setAttribute("data-theme", next);
  document.documentElement.setAttribute("data-nx-theme", next);
  const btn = document.querySelector("[data-nx-theme-toggle]");
  if (btn) {
    btn.textContent = next === "light" ? "☀" : "☾";
    btn.title = next === "light" ? "Usar tema escuro" : "Usar tema claro";
    btn.setAttribute("aria-label", btn.title);
  }
  return next;
}

function nxToggleTheme() {
  const wrapper = document.getElementById("nx-app-wrapper");
  const current = wrapper ? wrapper.getAttribute("data-theme") : nxStoredTheme();
  const next = current === "light" ? "dark" : "light";
  try {
    if (window.localStorage) window.localStorage.setItem(nxThemeStorageKey(), next);
  } catch (_) {}
  return nxApplyTheme(next);
}

function nxInitTheme() {
  nxApplyThemeTokens();
  nxApplyTheme(nxStoredTheme());
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", nxInitTheme);
} else {
  nxInitTheme();
}

window.nxApplyTheme = nxApplyTheme;
window.nxToggleTheme = nxToggleTheme;
window.nxApplyThemeTokens = nxApplyThemeTokens;

async function nxBridge(method, args) {
  if (!window.pywebview || !pywebview.api || !pywebview.api.bridge) {
    return { ok: false, error: 'pywebview não disponível' };
  }
  const raw = await pywebview.api.bridge(method, JSON.stringify(args || {}));
  return JSON.parse(raw);
}

function moneyBRL(n) {
  try {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(n) || 0);
  } catch (_) {
    return 'R$ ' + n;
  }
}

function showToastBanner(text) {
  if (!text) return;
  const el = document.createElement('div');
  el.className = 'toast-banner';
  el.textContent = text;
  const main = document.querySelector('main');
  if (main && main.firstChild) main.insertBefore(el, main.firstChild);
  else document.body.insertBefore(el, document.body.firstChild);
  setTimeout(() => el.remove(), 4200);
}

const nxFullscreenObserver = new ResizeObserver(() => {
  const isMaximized = window.innerWidth >= window.screen.availWidth - 10 && window.innerHeight >= window.screen.availHeight - 10;
  if (isMaximized) {
    document.documentElement.style.setProperty('background-color', 'var(--bg)', 'important');
    document.body.style.setProperty('padding', '0', 'important');
    document.body.style.setProperty('margin', '0', 'important');
    const wrapper = document.getElementById("nx-app-wrapper") || document.getElementById("app-wrapper");
    if (wrapper) {
      wrapper.style.setProperty('border-radius', '0', 'important');
      wrapper.style.setProperty('border', 'none', 'important');
      wrapper.style.setProperty('box-shadow', 'none', 'important');
      wrapper.style.setProperty('margin', '0', 'important');
    }
  } else {
    document.documentElement.style.setProperty('background-color', 'transparent', 'important');
    document.body.style.removeProperty('padding');
    document.body.style.removeProperty('margin');
    const wrapper = document.getElementById("nx-app-wrapper") || document.getElementById("app-wrapper");
    if (wrapper) {
      wrapper.style.removeProperty('border-radius');
      wrapper.style.removeProperty('border');
      wrapper.style.removeProperty('box-shadow');
      wrapper.style.removeProperty('margin');
    }
  }
});
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    if (document.body) nxFullscreenObserver.observe(document.body);
  });
} else {
  if (document.body) nxFullscreenObserver.observe(document.body);
}
