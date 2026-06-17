window.onerror = function(msg, url, line) {
    console.error("JS Error:", msg, "at", url, "line", line);
    if (typeof showToast === 'function') showToast("Erro: " + msg);
    return true;
};

// Supabase Configuration
const supabaseUrl = 'https://oxwpwfhjyiiwdhcggtlt.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im94d3B3ZmhqeWlpd2RoY2dndGx0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExMzA3NjAsImV4cCI6MjA5NjcwNjc2MH0.mIOis8ugOlubw2P6Z8_TuNeLukvltsXAlPb-ttaaOpY';
window.nexusSupabase = null;
if (window.supabase && typeof window.supabase.createClient === 'function') {
    window.nexusSupabase = window.supabase.createClient(supabaseUrl, supabaseKey);
} else {
    console.warn("Supabase client not loaded. Running in full offline mode.");
}

// ----------------------------------------------------
// Network Guard (Wi-Fi required for Jarvis / cloud AI)
// ----------------------------------------------------
function isNetworkOnline() {
    if (window.AndroidNative && typeof window.AndroidNative.isNetworkOnline === 'function') {
        try { return !!window.AndroidNative.isNetworkOnline(); } catch (_) {}
    }
    return !!navigator.onLine;
}

function isWifiConnected() {
    if (window.AndroidNative && typeof window.AndroidNative.isWifiConnected === 'function') {
        try { return !!window.AndroidNative.isWifiConnected(); } catch (_) {}
    }
    if (!navigator.onLine) return false;
    const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (conn && conn.type) {
        return conn.type === 'wifi' || conn.type === 'ethernet';
    }
    // APK antigo sem bridge Wi-Fi: usa rede geral até rebuild do app
    if (window.AndroidNative && typeof window.AndroidNative.isNetworkOnline === 'function') {
        try { return !!window.AndroidNative.isNetworkOnline(); } catch (_) {}
    }
    if (window.AndroidNative) return true;
    return false;
}

function isJarvisCloudReady() {
    return isWifiConnected() && !!window.nexusSupabase;
}

function requireWifiForJarvis(label) {
    if (isWifiConnected()) return true;
    showToast('Conecte-se ao Wi-Fi para usar o Jarvis' + (label ? ' (' + label + ')' : '') + '.');
    updateJarvisFabState();
    return false;
}

function updateJarvisFabState() {
    const fab = document.getElementById('nexus-ai-fab');
    if (!fab) return;
    const ok = isWifiConnected();
    fab.classList.toggle('jarvis-disabled', !ok);
    fab.setAttribute('aria-disabled', ok ? 'false' : 'true');
    fab.title = ok ? 'Ligar para o Jarvis' : 'Wi-Fi necessário';
}

function updateNetworkSettingsUI() {
    const el = document.getElementById('settings-wifi-status');
    if (!el) return;
    if (isWifiConnected()) {
        el.innerHTML = '<i class="fa-solid fa-wifi" style="color:var(--accent-green)"></i> Wi-Fi conectado';
        el.className = 'settings-net-ok';
    } else if (isNetworkOnline()) {
        el.innerHTML = '<i class="fa-solid fa-signal" style="color:#fbbf24"></i> Dados móveis (Jarvis indisponível)';
        el.className = 'settings-net-warn';
    } else {
        el.innerHTML = '<i class="fa-solid fa-plane" style="color:var(--accent-pink)"></i> Sem conexão';
        el.className = 'settings-net-off';
    }
}

let _syncIntervalMs = parseInt(localStorage.getItem('nexus_sync_interval_ms') || '60000', 10) || 60000;
let _syncIntervalId = null;

function startSyncInterval() {
    if (_syncIntervalId) clearInterval(_syncIntervalId);
    _syncIntervalId = setInterval(backgroundSync, _syncIntervalMs);
}

window.setSyncInterval = function(seconds) {
    const ms = Math.max(15000, parseInt(seconds, 10) * 1000);
    _syncIntervalMs = ms;
    localStorage.setItem('nexus_sync_interval_ms', String(ms));
    startSyncInterval();
    const hint = document.getElementById('sync-interval-hint');
    if (hint) hint.textContent = 'Sincronização automática a cada ' + (ms / 1000) + ' segundos quando online.';
};

window.applyMotionLevel = function(level) {
    const v = level || 'balanced';
    document.body.setAttribute('data-motion', v);
    localStorage.setItem('nexus_motion_level', v);
};

window.applyEnemMode = function(enabled) {
    document.body.classList.toggle('enem-mode', !!enabled);
    localStorage.setItem('nexus_enem_mode', enabled ? '1' : '0');
    if (enabled) showToast('Modo ENEM ativo — foco em estudos!');
};

window.applyNotificationsPref = function(enabled) {
    localStorage.setItem('nexus_notifications', enabled ? '1' : '0');
};

function initAppPreferences() {
    applyMotionLevel(localStorage.getItem('nexus_motion_level') || 'balanced');
    if (localStorage.getItem('nexus_enem_mode') === '1') document.body.classList.add('enem-mode');
    const syncSel = document.getElementById('cfg-sync-interval');
    if (syncSel) syncSel.value = String(_syncIntervalMs / 1000);
    const motionSel = document.getElementById('cfg-motion-level');
    if (motionSel) motionSel.value = localStorage.getItem('nexus_motion_level') || 'balanced';
    const enemCb = document.getElementById('toggle-enem-mode');
    if (enemCb) enemCb.checked = localStorage.getItem('nexus_enem_mode') === '1';
    const notifCb = document.getElementById('toggle-notifications');
    if (notifCb) notifCb.checked = localStorage.getItem('nexus_notifications') !== '0';
    const amoledCb = document.getElementById('toggle-amoled');
    if (amoledCb) amoledCb.checked = !!localStorage.getItem('nexus_amoled') || document.body.classList.contains('theme-amoled');
}

window.addEventListener('online', () => {
    updateSyncIndicator('synced');
    updateJarvisFabState();
    updateNetworkSettingsUI();
    backgroundSync();
});
window.addEventListener('offline', () => {
    updateSyncIndicator('offline');
    updateJarvisFabState();
    updateNetworkSettingsUI();
    if (typeof jarvisCallActive !== 'undefined' && jarvisCallActive && typeof window.endJarvisCall === 'function') {
        window.endJarvisCall();
        showToast('Ligação encerrada — sem conexão.');
    }
});
setInterval(() => { updateJarvisFabState(); updateNetworkSettingsUI(); }, 8000);

