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
    return isNetworkOnline() && !!window.nexusSupabase;
}

function requireWifiForJarvis(label) {
    if (isNetworkOnline()) return true;
    showToast('Sem internet para usar o Jarvis' + (label ? ' (' + label + ')' : '') + '.');
    updateJarvisFabState();
    return false;
}

function updateJarvisFabState() {
    const fab = document.getElementById('nexus-ai-fab');
    if (!fab) return;
    const homeActive = !!document.getElementById('view-home')?.classList.contains('active-view');
    const ok = isNetworkOnline();
    fab.style.display = homeActive ? 'flex' : 'none';
    fab.classList.toggle('jarvis-disabled', !ok);
    fab.setAttribute('aria-disabled', ok ? 'false' : 'true');
    fab.title = ok ? 'Ligar para o Jarvis' : 'Internet necessária';
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

// ----------------------------------------------------
// Offline-First Database (LocalStorage)
// ----------------------------------------------------
class LocalDB {
    static get(table) {
        try {
            const raw = localStorage.getItem(`nexus_${table}`);
            if (raw === null) return [];
            return JSON.parse(raw);
        } catch(e) {
            return [];
        }
    }
    static set(table, data) {
        localStorage.setItem(`nexus_${table}`, JSON.stringify(data));
    }
    static getAll(table) {
        const rows = this.get(table);
        return Array.isArray(rows) ? rows : [];
    }
    static saveAll(table, data) {
        this.set(table, data);
    }
    static getSingle(table, id) {
        const rows = this.getAll(table);
        return rows.find(r => String(r.id) === String(id));
    }
    static upsert(table, record) {
        const rows = this.getAll(table);
        const idx = rows.findIndex(r => String(r.id) === String(record.id));
        const now = new Date().toISOString();
        record.updated_at = now;
        if (!record.created_at) record.created_at = now;
        if (!record.client_id) record.client_id = String(record.id || ('c_' + Date.now()));
        if (record.sync_status !== 'synced') record.sync_status = 'pending';
        if (idx > -1) {
            rows[idx] = { ...rows[idx], ...record };
        } else {
            if (!record.id) record.id = Date.now();
            rows.push(record);
        }
        this.set(table, rows);
        return record;
    }
    static patchRow(table, id, changes) {
        const existing = this.getSingle(table, id);
        if (!existing) return null;
        return this.upsert(table, { ...existing, ...changes });
    }
    static deleteRow(table, id) {
        return this.patchRow(table, id, { is_deleted: 1 });
    }
}

function setTextIfPresent(id, value) {
    const el = document.getElementById(id);
    if (el) el.innerText = value;
}

function showToast(message, duration = 2500) {
    let toast = document.getElementById('nexus-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'nexus-toast';
        toast.style.cssText = 'position:fixed;left:16px;right:16px;bottom:164px;z-index:99999;background:rgba(15,15,25,.96);color:#fff;border:1px solid rgba(255,255,255,.18);border-radius:12px;padding:12px 14px;text-align:center;font-size:.92rem;box-shadow:0 12px 30px rgba(0,0,0,.35);opacity:0;transition:opacity .2s ease;pointer-events:none';
        document.body.appendChild(toast);
    }
    toast.textContent = String(message || '');
    toast.style.opacity = '1';
    if (window.NexusAudio) {
        const msg = String(message || '').toLowerCase();
        if (msg.includes('erro') || msg.includes('falha')) window.NexusAudio.play('error');
        else window.NexusAudio.play('tap');
    }
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => { toast.style.opacity = '0'; }, duration);
}

function showInAppNotification(message, type = 'info') {
    showToast(message);
    if (window.AndroidNative && typeof window.AndroidNative.showNotification === 'function') {
        try {
            window.AndroidNative.showNotification(type === 'success' ? 'Nexus' : 'Nexus Mobile', String(message || ''));
        } catch (e) {
            console.warn('Native notification failed:', e);
        }
    }
}

window.showToast = window.showToast || showToast;
window.showInAppNotification = window.showInAppNotification || showInAppNotification;

function closeTransientMobileSurfaces() {
    [
        'goal-form-modal',
        'workout-form-modal',
        'subject-form-modal',
        'study-entity-edit-modal',
        'subtask-inline-modal',
        'habit-detail-modal',
        'task-detail-modal',
        'routine-runner-modal',
        'yt-modal',
        'note-link-modal',
        'color-picker-popup',
        'slash-menu'
    ].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });

    ['create-modal', 'settings-modal'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.classList.remove('show');
        }
    });

    const calendar = document.getElementById('nexus-calendar-modal');
    if (calendar) {
        calendar.classList.remove('show');
        calendar.style.display = 'none';
    }

    const overflow = document.getElementById('rt-overflow-menu');
    if (overflow) overflow.style.display = 'none';
}

window.closeTransientMobileSurfaces = closeTransientMobileSurfaces;

let jarvisCallActive = false;
let jarvisCallStartedAt = 0;
let jarvisCallTimerId = null;

function updateJarvisCallTimer() {
    const timer = document.getElementById('jarvis-call-timer');
    const timerOverlay = document.getElementById('jarvis-call-timer-overlay');
    if (!jarvisCallStartedAt) return;
    const elapsed = Math.floor((Date.now() - jarvisCallStartedAt) / 1000);
    const minutes = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const seconds = String(elapsed % 60).padStart(2, '0');
    const label = `${minutes}:${seconds}`;
    if (timer) timer.textContent = label;
    if (timerOverlay) timerOverlay.textContent = label;
}

// toggleJarvisCall / endJarvisCall — implementados em nexus-phase15.js (overlay + voz)

window.requestJarvisVision = function() {
    if (window.AndroidNative && typeof window.AndroidNative.captureScreenAndClipboard === 'function') {
        window.AndroidNative.captureScreenAndClipboard();
    } else {
        showToast('Visao nativa indisponivel neste ambiente.');
    }
};

window.receiveNativeVision = function(text) {
    if (typeof openJarvisPanel === 'function') openJarvisPanel('summarize_text');
    const prompt = document.getElementById('jarvis-prompt');
    if (prompt) prompt.value = text || '';
};

// ----------------------------------------------------
// Sync Engine (unified offline-first)
// ----------------------------------------------------
const SYNC_TABLES = [
    'nexus_user', 'habits', 'habit_logs', 'tasks', 'finance_transactions', 'finance_investments',
    'nexus_rewards', 'study_notes', 'study_notebooks', 'flashcards', 'nexus_goals',
    'fitness_workouts', 'nexus_videos', 'routines', 'journal_entries',
    'pomo_sessions', 'reading_books', 'reading_sessions', 'quiz_attempts',
    'jarvis_chat_messages', 'jarvis_call_sessions', 'jarvis_call_turns',
    'nexus_alarms', 'nexus_user_settings', 'iot_devices'
];
let syncInProgress = false;

function updateSyncIndicator(status, detail) {
    const textEl = document.getElementById('sync-status-text');
    const chip = document.getElementById('sync-status-chip');
    if (!textEl) return;
    const labels = {
        offline: 'Offline',
        syncing: 'Sincronizando...',
        synced: detail || 'Sincronizado',
        error: 'Erro de sync',
        conflicts: detail || 'Conflitos'
    };
    textEl.textContent = labels[status] || detail || 'Offline';
    if (chip) {
        chip.style.color = status === 'synced' ? 'var(--accent-green)'
            : status === 'syncing' ? 'var(--accent-blue)'
            : status === 'error' ? '#ff4757'
            : 'var(--text-secondary)';
    }
}

function mergeRemoteRow(table, remoteRow, localRows) {
    const idx = localRows.findIndex(r => String(r.id) === String(remoteRow.id));
    const localRow = idx > -1 ? localRows[idx] : null;
    if (remoteRow.is_deleted) {
        if (idx > -1) localRows.splice(idx, 1);
        return localRows;
    }
    const remoteTs = remoteRow.updated_at || '';
    const localTs = localRow?.updated_at || '';
    if (!localRow) {
        localRows.push({ ...remoteRow, sync_status: 'synced' });
    } else if (remoteTs > localTs) {
        if (localRow.sync_status === 'pending' && localTs >= remoteTs) {
            return localRows;
        }
        localRows[idx] = { ...localRow, ...remoteRow, sync_status: 'synced' };
    }
    return localRows;
}

async function syncData() {
    if (syncInProgress) return;
    const supabaseClient = window.nexusSupabase;
    if (!navigator.onLine || !supabaseClient) {
        updateSyncIndicator('offline');
        return;
    }
    syncInProgress = true;
    updateSyncIndicator('syncing');
    try {
        let lastSync = localStorage.getItem('nexus_last_sync') || '1970-01-01T00:00:00Z';
        let newSyncTime = lastSync;
        let conflictCount = 0;

        for (const table of SYNC_TABLES) {
            const { data: remoteData } = await supabaseClient
                .from(table).select('*').gt('updated_at', lastSync).order('updated_at', { ascending: true });
            if (remoteData?.length) {
                let localRows = LocalDB.get(table);
                remoteData.forEach(remoteRow => {
                    const before = localRows.length;
                    localRows = mergeRemoteRow(table, remoteRow, localRows);
                    if (remoteRow.updated_at > newSyncTime) newSyncTime = remoteRow.updated_at;
                });
                LocalDB.set(table, localRows);
            }

            let localRows = LocalDB.get(table);
            const toPush = localRows.filter(r =>
                (r.sync_status === 'pending' || (r.updated_at || '') > lastSync) && !r.is_deleted
            );
            for (const localRow of toPush) {
                const cleanRow = { ...localRow };
                delete cleanRow.sync_status;
                if (currentUser?.id) cleanRow.user_id = currentUser.id;
                if (cleanRow.id && typeof cleanRow.id === 'string' && isNaN(Number(cleanRow.id))) {
                    delete cleanRow.id;
                }
                const { error: pushErr } = await supabaseClient.from(table).upsert(cleanRow);
                if (!pushErr) {
                    const idx = localRows.findIndex(r => String(r.id) === String(localRow.id) || r.client_id === localRow.client_id);
                    if (idx > -1) {
                        localRows[idx].sync_status = 'synced';
                        if (localRow.updated_at > newSyncTime) newSyncTime = localRow.updated_at;
                    }
                } else {
                    console.error('Push error', table, pushErr);
                }
            }
            LocalDB.set(table, localRows);

            const tombstones = localRows.filter(r => r.is_deleted && r.sync_status === 'pending');
            for (const row of tombstones) {
                const cleanRow = { ...row, is_deleted: 1 };
                delete cleanRow.sync_status;
                const { error } = await supabaseClient.from(table).upsert(cleanRow);
                if (!error) row.sync_status = 'synced';
            }
            if (tombstones.length) LocalDB.set(table, localRows);
        }

        const conflicts = JSON.parse(localStorage.getItem('nexus_sync_conflicts') || '[]');
        conflictCount = conflicts.length;
        localStorage.setItem('nexus_last_sync', newSyncTime);
        const timeLabel = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
        updateSyncIndicator(conflictCount ? 'conflicts' : 'synced', conflictCount ? `${conflictCount} conflito(s)` : `Sync ${timeLabel}`);

        const activeView = document.querySelector('.active-view');
        if (activeView && typeof refreshViewContent === 'function') refreshViewContent(activeView.id);
        loadUserStats();
    } catch (e) {
        console.error('Sync error:', e);
        updateSyncIndicator('error');
    } finally {
        syncInProgress = false;
    }
}

async function backgroundSync() {
    return syncData();
}

window.syncData = syncData;
window.backgroundSync = backgroundSync;

// ----------------------------------------------------
// UI Logic — central view refresh (all modules)
// ----------------------------------------------------
window.refreshViewContent = function(viewId) {
    if (!viewId) return;
    try {
        switch (viewId) {
            case 'view-home':
                if (typeof loadTodayDashboard === 'function') loadTodayDashboard();
                break;
            case 'view-habits':
                if (typeof loadHabits === 'function') loadHabits();
                break;
            case 'view-finance':
                if (typeof loadFinances === 'function') loadFinances();
                break;
            case 'view-tasks':
                if (typeof loadTasks === 'function') loadTasks();
                break;
            case 'view-videos':
                if (typeof loadVideos === 'function') loadVideos();
                break;
            case 'view-shop':
                if (typeof loadShop === 'function') loadShop();
                break;
            case 'view-studies':
                if (typeof loadStudies === 'function') loadStudies();
                break;
            case 'view-goals':
                if (typeof loadGoals === 'function') loadGoals();
                break;
            case 'view-fitness':
                if (typeof switchFitnessTab === 'function') {
                    const treinosBtn = document.querySelector('#view-fitness .fitness-tab');
                    switchFitnessTab('treinos', treinosBtn);
                } else if (typeof loadFitness === 'function') {
                    loadFitness();
                }
                break;
            case 'view-routines':
                if (typeof loadRoutines === 'function') loadRoutines();
                break;
            case 'view-journal':
                if (typeof loadJournal === 'function') loadJournal();
                break;
            case 'view-alarms':
                if (typeof loadAlarms === 'function') loadAlarms();
                break;
            case 'view-iot':
                if (typeof discoverIoT === 'function') discoverIoT();
                break;
            case 'view-cleaner':
                if (typeof loadCleaner === 'function') loadCleaner();
                break;
            case 'view-jarvis-history':
                if (typeof loadJarvisPersistentHistory === 'function') loadJarvisPersistentHistory();
                break;
            case 'view-jarvis-calls':
                if (typeof loadJarvisCallHistory === 'function') loadJarvisCallHistory();
                break;
            case 'view-settings':
                if (typeof initAppPreferences === 'function') initAppPreferences();
                if (typeof updateSettingsUI === 'function') updateSettingsUI();
                break;
            default:
                break;
        }
    } catch (err) {
        console.error('[refreshViewContent]', viewId, err);
        if (typeof showToast === 'function') showToast('Erro ao carregar conteúdo da tela');
    }
};

const MODULE_NAV_KEYS = ['habits', 'finance', 'routines', 'tasks', 'videos', 'shop', 'studies', 'goals', 'fitness', 'iot', 'journal', 'alarms', 'cleaner'];

window.ensureModuleNavVisible = function() {
    let prefs = {};
    try { prefs = JSON.parse(localStorage.getItem('nexus_ui_prefs') || '{}'); } catch (_) {}
    const hidden = MODULE_NAV_KEYS.filter(mod => {
        const navItem = document.querySelector('.nav-item[data-target="view-' + mod + '"]');
        return navItem && navItem.style.display === 'none';
    });
    if (hidden.length >= MODULE_NAV_KEYS.length - 1) {
        MODULE_NAV_KEYS.forEach(mod => { prefs[mod] = true; });
        localStorage.setItem('nexus_ui_prefs', JSON.stringify(prefs));
        if (typeof showToast === 'function') showToast('Módulos restaurados na barra inferior.');
    }
    if (typeof applyModuleOrderAndVisibility === 'function') applyModuleOrderAndVisibility();
    else if (typeof applyUiPrefs === 'function') applyUiPrefs();
};

function activateMobileView(viewId, navItem) {
    if (typeof closeTransientMobileSurfaces === 'function') closeTransientMobileSurfaces();
    document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
    if (navItem) navItem.classList.add('active');
    document.querySelectorAll('.view').forEach(view => view.classList.remove('active-view'));
    const targetView = document.getElementById(viewId);
    if (!targetView) {
        console.warn('Missing mobile view:', viewId);
        if (typeof showToast === 'function') showToast('Tela não encontrada: ' + viewId);
        return false;
    }
    targetView.classList.add('active-view');
    if (typeof updateJarvisFabState === 'function') updateJarvisFabState();
    refreshViewContent(viewId);
    requestAnimationFrame(() => refreshViewContent(viewId));
    if (window.NexusAudio && typeof window.NexusAudio.play === 'function') window.NexusAudio.play('nav');
    return true;
}

function bindMobileNavItems() {
    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.dataset.navBound) return;
        item.dataset.navBound = '1';
        item.addEventListener('click', (e) => {
            e.preventDefault();
            if (typeof closeTransientMobileSurfaces === 'function') closeTransientMobileSurfaces();
            activateMobileView(item.getAttribute('data-target'), item);
        });
    });
}
bindMobileNavItems();

// ----------------------------------------------------
// Notifications
// ----------------------------------------------------
async function requestNotificationPermission() {
    if (!("Notification" in window)) return;
    if (Notification.permission === "granted") return;
    
    if (Notification.permission !== "denied") {
        await Notification.requestPermission();
    }
}

function notificationsEnabled() {
    return localStorage.getItem('nexus_notifications') !== 'false';
}
window.notificationsEnabled = notificationsEnabled;

function sendLocalNotification(title, body) {
    if (!notificationsEnabled()) return;
    if (window.AndroidNative && typeof window.AndroidNative.showNotification === 'function') {
        window.AndroidNative.showNotification(title, body);
        return;
    }
    if (!("Notification" in window) || !navigator.serviceWorker) return;
    if (Notification.permission === "granted") {
        navigator.serviceWorker.ready.then(registration => {
            registration.showNotification(title, {
                body: body,
                icon: 'https://cdn-icons-png.flaticon.com/512/8244/8244509.png',
                vibrate: [200, 100, 200]
            });
        });
    }
}

// ----------------------------------------------------
// Offline-First Data Operations
// ----------------------------------------------------

function syncUserStatsToNexusUser() {
    const stats = LocalDB.get('user_stats') || { xp: 0, points: 0, level: 1 };
    const user = LocalDB.getSingle('nexus_user', 1) || { id: 1, name: 'Comandante' };
    user.xp = stats.xp || 0;
    user.points = stats.points || 0;
    user.level = stats.level || 1;
    LocalDB.upsert('nexus_user', user);
}

function loadUserStats() {
    syncUserStatsToNexusUser();
    const stats = LocalDB.get('user_stats') || { xp: 0, level: 1, points: 0 };
    const user = LocalDB.getSingle('nexus_user', 1) || { name: 'Comandante' };
    setTextIfPresent('user-level', stats.level);
    setTextIfPresent('user-name', user.name || 'Comandante');
    setTextIfPresent('val-xp', stats.xp);
    setTextIfPresent('val-points', stats.points);
    updateAppVersionDebug();
}

window.updateAppVersionDebug = function() {
    const el = document.getElementById('app-version-debug');
    if (!el) return;
    let webVer = '—';
    try {
        const raw = localStorage.getItem('nexus_web_version');
        if (raw) webVer = JSON.parse(raw).version || raw;
    } catch (_) {}
    if (webVer === '—') {
        fetch('version.json').then(r => r.json()).then(j => {
            webVer = j.version || '—';
            localStorage.setItem('nexus_web_version', JSON.stringify(j));
            el.textContent = 'web ' + webVer + ' · apk ' + (window.__nexusApkVersion || '—');
        }).catch(() => {});
    }
    let apkVer = window.__nexusApkVersion || '—';
    if (window.AndroidNative && typeof window.AndroidNative.getAppInfo === 'function') {
        try {
            const info = JSON.parse(window.AndroidNative.getAppInfo());
            apkVer = info.versionName || info.version || apkVer;
            window.__nexusApkVersion = apkVer;
        } catch (_) {}
    }
    el.textContent = 'web ' + webVer + ' · apk ' + apkVer;
};

function loadVideos() {
    const container = document.getElementById('videos-list');
    if (!container) return;
    const data = LocalDB.get('nexus_videos').filter(v => !v.is_deleted);
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhum vídeo salvo offline.</div>';
    data.forEach(v => {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        const badgeClass = v.is_watched ? 'color: var(--accent-green);' : 'color: var(--accent-blue);';
        const badgeText = v.is_watched ? 'Assistido' : `+${v.xp_reward} XP`;
        
        el.innerHTML = `
            <div class="item-main" style="width: 100%;" onclick="window.open('${v.url}', '_blank')">
                <span class="item-title">${v.title}</span>
                <span class="item-subtitle" style="${badgeClass} font-weight:600;"><i class="fa-brands fa-${v.platform}"></i> ${badgeText}</span>
            </div>
        `;
        container.appendChild(el);
    });
}

function loadHabits() {
    if (typeof filterHabits === 'function') {
        const active = document.querySelector('#view-habits .study-chip.active');
        filterHabits(active?.dataset?.filter || 'all', active || null);
        return;
    }
    const container = document.getElementById('habits-list');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;">Nenhum hábito cadastrado.</div>';
}

window.toggleHabit = function(id) {
    toggleHabitDirect(id);
};

function loadTasks() {
    const container = document.getElementById('tasks-list');
    const data = LocalDB.get('tasks').filter(t => !t.done_at && !t.is_deleted);
    
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Sem tarefas ativas!</div>';
    data.forEach(t => {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        el.innerHTML = `<div class="item-main"><span class="item-title">${t.title}</span><span class="item-subtitle">+${t.points_reward} XP</span></div>
        <button class="item-action" onclick="completeTask(${t.id}, this)"><i class="fa-solid fa-check"></i></button>`;
        container.appendChild(el);
    });
}

window.completeTask = function(id, btn) {
    const task = LocalDB.getSingle('tasks', id);
    if (task) {
        task.done_at = new Date().toISOString();
        task.status = 'done';
        task.completed = 1;
        LocalDB.upsert('tasks', task);
        awardXP(task.points_reward || 10, 'Tarefa concluida');
        loadTasks();
        backgroundSync();
    }
};

function loadFinances() {
    renderFinanceSummary();
    const container = document.getElementById('finance-list');
    if (!container) return;
    const data = LocalDB.get('finance_transactions').filter(t => !t.is_deleted)
        .sort((a,b) => (b.occurred_at || b.created_at || '').localeCompare(a.occurred_at || a.created_at || ''));
    
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Sem transações.</div>';
    const catLabels = { food: 'Alimentação', transport: 'Transporte', health: 'Saúde', leisure: 'Lazer', bills: 'Contas', salary: 'Salário', other: 'Outros' };
    data.slice(0, 30).forEach(t => {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        el.style.cursor = 'pointer';
        el.onclick = () => { if (typeof openFinanceForm === 'function') openFinanceForm(t.id); };
        const isIncome = t.type === 'income';
        const dateStr = (t.occurred_at || t.created_at || '').slice(0, 10).split('-').reverse().join('/');
        el.innerHTML = `<div class="item-main"><span class="item-title">${escapeHtml(t.description || 'Transação')}</span>
            <span class="item-subtitle">${catLabels[t.category] || t.category || 'Outros'} · ${dateStr}</span></div>
            <span style="font-weight:700;color:${isIncome?'#34d399':'#fb7185'}">${isIncome?'+':'−'} R$ ${Number(t.amount).toFixed(2)}</span>`;
        container.appendChild(el);
    });
    if (typeof ensureChartJs === 'function') ensureChartJs().then(() => setTimeout(renderFinanceCharts, 80));
    if (typeof renderCategoryBudgets === 'function') renderCategoryBudgets();
    if (typeof loadInvestments === 'function') loadInvestments();
}

function renderFinanceSummary() {
    const month = new Date().toISOString().slice(0, 7);
    const txs = (LocalDB.get('finance_transactions') || []).filter(t => !t.is_deleted);
    const inMonth = txs.filter(t => (t.occurred_at || t.created_at || '').slice(0, 7) === month);
    const income = inMonth.filter(t => t.type === 'income').reduce((s, t) => s + Number(t.amount || 0), 0);
    const expense = inMonth.filter(t => t.type !== 'income').reduce((s, t) => s + Number(t.amount || 0), 0);
    const balance = income - expense;
    const fmt = v => 'R$ ' + v.toFixed(2).replace('.', ',');
    const balEl = document.getElementById('finance-balance-month');
    const incEl = document.getElementById('finance-income-month');
    const expEl = document.getElementById('finance-expense-month');
    if (balEl) { balEl.textContent = fmt(balance); balEl.style.color = balance >= 0 ? 'var(--accent-green)' : '#fb7185'; }
    if (incEl) incEl.textContent = fmt(income);
    if (expEl) expEl.textContent = fmt(expense);
}

window.switchFinanceTab = function(tab, btn) {
    ['transactions', 'investments', 'budgets'].forEach(t => {
        const panel = document.getElementById('finance-panel-' + t);
        if (panel) panel.style.display = t === tab ? 'block' : 'none';
    });
    document.querySelectorAll('#view-finance .fitness-tab').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (tab === 'investments' && typeof loadInvestments === 'function') loadInvestments();
    if (tab === 'budgets' && typeof renderCategoryBudgets === 'function') renderCategoryBudgets();
};

window.closeFinanceOverflow = function() {
    const p = document.getElementById('finance-overflow-popup');
    if (p) p.style.display = 'none';
};

const FINANCE_CATEGORY_LABELS = { food: 'Alimentação', transport: 'Transporte', health: 'Saúde', leisure: 'Lazer', bills: 'Contas', salary: 'Salário', other: 'Outros' };

function getCategoryBudgets() {
    try { return JSON.parse(localStorage.getItem('nexus_category_budgets') || '{}'); } catch (_) { return {}; }
}

window.renderCategoryBudgets = function() {
    const list = document.getElementById('finance-budgets-list');
    if (!list) return;
    const budgets = getCategoryBudgets();
    const month = new Date().toISOString().slice(0, 7);
    const spent = {};
    (LocalDB.get('finance_transactions') || []).filter(t => !t.is_deleted && t.type !== 'income')
        .filter(t => (t.occurred_at || '').slice(0, 7) === month)
        .forEach(t => { spent[t.category || 'other'] = (spent[t.category || 'other'] || 0) + Number(t.amount || 0); });
    list.innerHTML = Object.keys(FINANCE_CATEGORY_LABELS).map(cat => {
        const limit = budgets[cat] || 0;
        const used = spent[cat] || 0;
        const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
        const warn = limit > 0 && pct >= 80;
        return `<div class="glass" style="padding:12px;border-radius:12px;margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                <span style="font-weight:600">${FINANCE_CATEGORY_LABELS[cat]}</span>
                <span style="font-size:0.8rem;color:${warn?'#fb7185':'var(--text-secondary)'}">R$ ${used.toFixed(0)}${limit ? ' / R$ ' + limit : ''}</span>
            </div>
            <input type="number" min="0" step="50" value="${limit || ''}" placeholder="Limite mensal"
                onchange="saveCategoryBudget('${cat}', this.value)"
                style="width:100%;padding:8px;border-radius:8px;background:rgba(0,0,0,0.35);color:white;border:1px solid var(--border-glass);font-family:inherit">
            ${limit ? `<div style="margin-top:6px;background:rgba(255,255,255,0.08);border-radius:4px;height:6px"><div style="height:100%;width:${pct}%;border-radius:4px;background:${warn?'#fb7185':'var(--accent-primary)'}"></div></div>` : ''}
        </div>`;
    }).join('');
};

window.saveCategoryBudget = function(cat, val) {
    const budgets = getCategoryBudgets();
    const n = parseFloat(val);
    if (n > 0) budgets[cat] = n; else delete budgets[cat];
    localStorage.setItem('nexus_category_budgets', JSON.stringify(budgets));
    renderCategoryBudgets();
};

let editingInvestmentId = null;
window.loadInvestments = function() {
    const list = document.getElementById('finance-investments-list');
    const totalEl = document.getElementById('finance-investments-total');
    if (!list) return;
    const items = (LocalDB.get('finance_investments') || []).filter(i => !i.is_deleted);
    const typeIcons = { crypto: '₿', stock: '📈', cdb: '🏦', fund: '📊', other: '💼' };
    let total = 0;
    list.innerHTML = items.length ? items.map(i => {
        const price = Number(i.current_price || i.avg_price || 0);
        const qty = Number(i.quantity || 0);
        const value = price * qty;
        total += value;
        return `<div class="list-item glass" onclick="openInvestmentForm('${i.id}')" style="cursor:pointer">
            <div class="item-main"><span class="item-title">${typeIcons[i.type] || '💼'} ${escapeHtml(i.name)}</span>
            <span class="item-subtitle">${i.quantity} un · médio R$ ${Number(i.avg_price||0).toFixed(2)}</span></div>
            <span style="font-weight:700;color:var(--accent-blue)">R$ ${value.toFixed(2)}</span></div>`;
    }).join('') : '<div style="text-align:center;color:var(--text-secondary);padding:20px">Nenhum ativo. Toque em + Ativo.</div>';
    if (totalEl) totalEl.textContent = 'R$ ' + total.toFixed(2).replace('.', ',');
};

window.openInvestmentForm = function(id) {
    editingInvestmentId = id || null;
    const items = LocalDB.get('finance_investments') || [];
    const i = id ? items.find(x => String(x.id) === String(id)) : null;
    document.getElementById('investment-form-title').textContent = i ? 'Editar ativo' : 'Novo ativo';
    document.getElementById('investment-form-name').value = i?.name || '';
    document.getElementById('investment-form-type').value = i?.type || 'stock';
    document.getElementById('investment-form-qty').value = i?.quantity || '';
    document.getElementById('investment-form-price').value = i?.avg_price || '';
    document.getElementById('investment-form-current').value = i?.current_price || '';
    document.getElementById('investment-form-delete-btn').style.display = i ? 'block' : 'none';
    document.getElementById('investment-form-modal').style.display = 'flex';
};

window.closeInvestmentForm = function() {
    document.getElementById('investment-form-modal').style.display = 'none';
    editingInvestmentId = null;
};

window.saveInvestmentForm = function() {
    const name = document.getElementById('investment-form-name')?.value?.trim();
    const qty = parseFloat(document.getElementById('investment-form-qty')?.value || '0');
    const avg = parseFloat(document.getElementById('investment-form-price')?.value || '0');
    if (!name || !qty) { showToast('Nome e quantidade são obrigatórios.'); return; }
    LocalDB.upsert('finance_investments', {
        id: editingInvestmentId || Date.now(),
        name,
        type: document.getElementById('investment-form-type')?.value || 'other',
        quantity: qty,
        avg_price: avg,
        current_price: parseFloat(document.getElementById('investment-form-current')?.value || '0') || avg,
        updated_at: new Date().toISOString()
    });
    closeInvestmentForm();
    loadInvestments();
    if (typeof backgroundSync === 'function') backgroundSync();
    showToast('Ativo salvo.');
};

window.deleteInvestmentForm = function() {
    if (!editingInvestmentId || !confirm('Excluir este ativo?')) return;
    LocalDB.deleteRow('finance_investments', editingInvestmentId);
    closeInvestmentForm();
    loadInvestments();
};

window.exportFinanceCsv = function() {
    const txs = (LocalDB.get('finance_transactions') || []).filter(t => !t.is_deleted);
    const rows = [['data', 'tipo', 'categoria', 'descricao', 'valor'].join(',')];
    txs.forEach(t => {
        rows.push([(t.occurred_at||'').slice(0,10), t.type, t.category, '"' + (t.description||'').replace(/"/g,'""') + '"', t.amount].join(','));
    });
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'nexus-financas-' + todayISO() + '.csv';
    a.click();
    showToast('CSV exportado.');
};

// ----------------------------------------------------
// ----------------------------------------------------
// New Offline Modules
// ----------------------------------------------------

function loadShop() {
    const container = document.getElementById('shop-list');
    if (!container) return;
    ensureDefaultRewards();
    const data = LocalDB.get('nexus_rewards').filter(r => !r.is_deleted);
    if(data.length) {
        container.innerHTML = '';
        data.forEach(item => {
            const el = document.createElement('div');
            el.className = 'list-item glass';
            el.innerHTML = `
                <div class="item-main">
                    <span class="item-title">${item.name}</span>
                    <span class="item-subtitle">${item.description || ''}</span>
                </div>
                <button class="item-action" style="font-size:12px; width:auto; padding: 0 10px;" onclick="buyItem(${item.id}, '${item.name}', ${item.cost})">
                    ${item.cost} pts
                </button>
            `;
            container.appendChild(el);
        });
    } else {
        container.innerHTML = '<div style="text-align:center; color:var(--text-secondary); margin-top:20px; padding:20px;"><i class="fa-solid fa-store" style="font-size:2rem;opacity:0.4;margin-bottom:10px;display:block"></i>Nenhuma recompensa ainda.<br><button onclick="ensureDefaultRewards();loadShop()" style="margin-top:12px;background:var(--accent-primary);border:none;color:white;padding:10px 18px;border-radius:8px;cursor:pointer;font-family:inherit">Carregar recompensas padrão</button></div>';
    }
}

window.buyItem = function(id, name, cost) {
    const user = LocalDB.getSingle('nexus_user', 1);
    if (!user || user.points < cost) {
        alert("Pontos insuficientes!");
        return;
    }
    if (confirm(`Comprar '${name}' por ${cost} pontos?`)) {
        user.points -= cost;
        LocalDB.upsert('nexus_user', user);
        
        LocalDB.upsert('finance_transactions', {
            id: Date.now(),
            type: 'expense',
            amount: cost,
            category: 'Reward',
            description: 'Compra: ' + name,
            occurred_at: new Date().toISOString()
        });
        
        sendLocalNotification('Recompensa Comprada', `Aproveite seu(a) ${name}!`);
        loadUserStats();
        backgroundSync();
    }
};

function loadStudies() {
    const container = document.getElementById('studies-list');
    if(!container) return;
    const data = LocalDB.get('study_notes').filter(t => !t.is_deleted);
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhuma nota de estudo.</div>';
    data.forEach(t => {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        el.innerHTML = `<div class="item-main"><span class="item-title">${t.title}</span><span class="item-subtitle">${t.subject || 'Geral'}</span></div>`;
        container.appendChild(el);
    });
}

function loadGoals() {
    const container = document.getElementById('goals-list');
    if(!container) return;
    const data = LocalDB.get('nexus_goals').filter(t => !t.is_deleted && t.status !== 'achieved');
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px; padding:20px;"><i class="fa-solid fa-bullseye" style="font-size:2rem;opacity:0.4;margin-bottom:10px;display:block"></i>Sem metas ativas.<br><button onclick="promptAddGoal()" style="margin-top:12px;background:var(--accent-primary);border:none;color:white;padding:10px 18px;border-radius:8px;cursor:pointer;font-family:inherit">Criar primeira meta</button></div>';
    data.forEach(t => {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        el.innerHTML = `<div class="item-main"><span class="item-title">${t.name}</span><span class="item-subtitle">Progresso: ${t.progress || 0}%</span></div>
            <button class="item-action" style="width:auto;padding:0 12px" onclick="updateGoalProgress(${t.id})">+10%</button>`;
        container.appendChild(el);
    });
}

window.promptAddGoal = function() {
    const name = prompt('Nome da meta:');
    if (!name || !name.trim()) return;
    LocalDB.upsert('nexus_goals', {
        id: Date.now(),
        name: name.trim(),
        progress: 0,
        status: 'active'
    });
    loadGoals();
    showToast('Meta criada!');
};

window.updateGoalProgress = function(id) {
    const goals = LocalDB.get('nexus_goals');
    const goal = goals.find(g => g.id === id);
    if (!goal) return;
    goal.progress = Math.min(100, (goal.progress || 0) + 10);
    if (goal.progress >= 100) goal.status = 'achieved';
    LocalDB.upsert('nexus_goals', goal);
    loadGoals();
    showToast('Progresso atualizado!');
};

function updateFitnessStats() {
    const workouts = LocalDB.get('fitness_workouts').filter(t => !t.is_deleted);
    const now = new Date();
    const weekAgo = new Date(now);
    weekAgo.setDate(weekAgo.getDate() - 7);
    const weekCount = workouts.filter(w => {
        const d = new Date(w.date || w.created_at || 0);
        return d >= weekAgo;
    }).length;

    const dates = [...new Set(workouts.map(w => (w.date || w.created_at || '').split('T')[0]).filter(Boolean))].sort().reverse();
    let streak = 0;
    const today = now.toISOString().split('T')[0];
    for (let i = 0; i < 60; i++) {
        const d = new Date(now);
        d.setDate(d.getDate() - i);
        const ds = d.toISOString().split('T')[0];
        if (dates.includes(ds)) streak++;
        else if (i > 0) break;
    }
    if (!dates.includes(today) && streak === 0 && dates.length) {
        const last = dates[0];
        const diff = Math.floor((now - new Date(last)) / 86400000);
        if (diff === 1) streak = 1;
    }

    setTextIfPresent('fit-week-count', weekCount);
    setTextIfPresent('fit-streak', streak);
    setTextIfPresent('fit-total', workouts.length);
}

function loadFitness() {
    const container = document.getElementById('fitness-list');
    if (!container) return;
    updateFitnessStats();
    const data = LocalDB.get('fitness_workouts').filter(t => !t.is_deleted)
        .sort((a, b) => (b.date || b.created_at || '').localeCompare(a.date || a.created_at || ''));
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhum treino registrado.</div>';
    data.slice(0, 10).forEach(t => {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        const title = t.name || t.type || 'Treino';
        const sub = t.muscle_group || t.notes || '';
        const meta = t.duration_minutes ? `${t.duration_minutes} min` : (t.date || '').split('T')[0];
        el.innerHTML = `<div class="item-main"><span class="item-title">${escapeHtml(title)}</span><span class="item-subtitle">${escapeHtml(sub || meta)}</span></div>`;
        container.appendChild(el);
    });
}

window.loadVideos = window.loadVideos || loadVideos;
window.loadTasks = window.loadTasks || loadTasks;
window.loadFinances = window.loadFinances || loadFinances;
window.loadFinance = window.loadFinance || loadFinances;
window.loadShop = window.loadShop || loadShop;
window.loadStudies = window.loadStudies || loadStudies;
window.loadGoals = window.loadGoals || loadGoals;
window.loadFitness = window.loadFitness || loadFitness;
window.loadJournal = window.loadJournal || loadJournal;
window.loadRoutines = window.loadRoutines || loadRoutines;
window.loadCleaner = window.loadCleaner || loadCleaner;

window.ensureDefaultRewards = function() {
    const rewards = LocalDB.get('nexus_rewards').filter(r => !r.is_deleted);
    if (rewards.length > 0) return;
    const now = new Date().toISOString();
    LocalDB.set('nexus_rewards', [
        { id: 1, name: 'Pausa Café', cost: 50, description: '15 min de descanso merecido', created_at: now, updated_at: now, sync_status: 'pending' },
        { id: 2, name: 'Episódio Série', cost: 100, description: 'Assistir um episódio favorito', created_at: now, updated_at: now, sync_status: 'pending' },
        { id: 3, name: 'Jantar Especial', cost: 200, description: 'Comida favorita no fim de semana', created_at: now, updated_at: now, sync_status: 'pending' }
    ]);
};

window.discoverIoT = async function() {
    const container = document.getElementById('iot-list');
    if (!container) return;
    container.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-circle-notch fa-spin"></i> Buscando Bluetooth e Wi‑Fi...</div>';

    const manual = (LocalDB.get('iot_devices') || []).filter(d => !d.is_deleted);
    const devices = manual.map(d => ({ ...d, source: 'manual' }));

    if (window.AndroidNative && typeof AndroidNative.scanNearbyDevices === 'function') {
        try {
            const raw = AndroidNative.scanNearbyDevices();
            const scanned = typeof raw === 'string' ? JSON.parse(raw) : raw;
            if (Array.isArray(scanned)) scanned.forEach(d => devices.push(d));
        } catch (_) {}
    }

    if (isNetworkOnline() && window.location.protocol !== 'file:') {
        try {
            const res = await fetch('/api/nexus/iot/discover');
            const data = await res.json();
            if (data?.devices) data.devices.forEach(d => devices.push({ ...d, source: 'desktop' }));
        } catch (_) {}
    }

    if (!devices.length) {
        container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;padding:20px"><i class="fa-solid fa-wifi" style="font-size:2rem;margin-bottom:10px;opacity:0.5"></i><p>Nenhum dispositivo encontrado.<br>Toque + para adicionar manualmente ou ative Bluetooth/Wi‑Fi.</p></div>';
        return;
    }

    const typeIcons = { light: '💡', plug: '🔌', sensor: '📡', speaker: '🔊', bluetooth: '📶', wifi: '📡' };
    container.innerHTML = devices.map((dev, idx) => {
        const id = dev.id || dev.address || dev.ip || ('dev-' + idx);
        const name = dev.name || dev.title || 'Dispositivo';
        const addr = dev.address || dev.ip || dev.mac || '';
        const isOn = dev.status === 'LIGADO' || dev.on === true;
        const icon = typeIcons[dev.type] || typeIcons[dev.source] || '🏠';
        return `<div class="list-item glass">
            <div class="item-main"><span class="item-title">${icon} ${escapeHtml(name)}</span>
            <span class="item-subtitle">${escapeHtml(addr)} · ${dev.source || 'local'}</span></div>
            <button class="icon-btn ${isOn ? 'done' : ''}" onclick="toggleIoTDevice('${String(id).replace(/'/g, '')}', ${!isOn})"><i class="fa-solid fa-power-off"></i></button>
        </div>`;
    }).join('');
};

window.openAddDeviceSheet = function() {
    document.getElementById('device-form-name').value = '';
    document.getElementById('device-form-address').value = '';
    document.getElementById('add-device-modal').style.display = 'flex';
};

window.closeAddDeviceSheet = function() {
    document.getElementById('add-device-modal').style.display = 'none';
};

window.saveManualDevice = function() {
    const name = document.getElementById('device-form-name')?.value?.trim();
    const address = document.getElementById('device-form-address')?.value?.trim();
    if (!name) { showToast('Informe o nome do dispositivo.'); return; }
    LocalDB.upsert('iot_devices', {
        id: Date.now(),
        name,
        type: document.getElementById('device-form-type')?.value || 'other',
        address: address || '',
        status: 'DESLIGADO',
        created_at: new Date().toISOString()
    });
    closeAddDeviceSheet();
    discoverIoT();
    showToast('Dispositivo adicionado.');
};

window.toggleIoTDevice = function(deviceId, turnOn) {
    const devices = LocalDB.get('iot_devices') || [];
    const d = devices.find(x => String(x.id) === String(deviceId) || String(x.address) === String(deviceId));
    if (d) {
        d.status = turnOn ? 'LIGADO' : 'DESLIGADO';
        LocalDB.set('iot_devices', devices);
        showToast((d.name || 'Dispositivo') + (turnOn ? ' ligado' : ' desligado'));
        discoverIoT();
        return;
    }
    showToast('Controle remoto requer Nexus desktop na mesma rede.');
};

window.toggleIoT = window.toggleIoTDevice;

window.promptAddHabit = function() {
    const modal = document.getElementById('create-modal');
    const typeSel = document.getElementById('create-type');
    if (modal && typeSel) {
        typeSel.value = 'habit';
        document.getElementById('habit-options').style.display = 'flex';
        openCreateModal();
        return;
    }
    const name = prompt('Nome do hábito:');
    if (!name || !name.trim()) return;
    LocalDB.upsert('habits', { id: Date.now(), name: name.trim(), active: 1, current_streak: 0, period: 'all' });
    loadHabits();
    backgroundSync();
    showToast('Hábito criado!');
};

window.promptAddTask = function() {
    const modal = document.getElementById('create-modal');
    const typeSel = document.getElementById('create-type');
    if (modal && typeSel) {
        typeSel.value = 'task';
        document.getElementById('habit-options').style.display = 'none';
        openCreateModal();
        return;
    }
    const title = prompt('Título da tarefa:');
    if (!title || !title.trim()) return;
    LocalDB.upsert('tasks', { id: Date.now(), title: title.trim(), name: title.trim(), points_reward: 10 });
    loadTasks();
    backgroundSync();
    showToast('Tarefa criada!');
};

function appendChatBubble(role, text, loading) {
    const hist = document.getElementById('chat-history');
    if (!hist) return null;
    const div = document.createElement('div');
    div.className = 'chat-message ' + (role === 'user' ? 'user-msg' : 'jarvis-msg');
    div.style.cssText = role === 'user'
        ? 'align-self:flex-end;background:rgba(139,92,246,0.25);border:1px solid var(--accent-purple);padding:10px 15px;border-radius:12px;border-bottom-right-radius:2px;max-width:85%'
        : 'align-self:flex-start;background:rgba(0,206,201,0.15);border:1px solid var(--accent-blue);padding:10px 15px;border-radius:12px;border-bottom-left-radius:2px;max-width:85%';
    div.innerHTML = '<p style="margin:0;font-size:0.95rem;color:white">' + (loading ? '<i class="fa-solid fa-circle-notch fa-spin"></i> ' : '') + escapeHtml(text) + '</p>';
    hist.appendChild(div);
    hist.scrollTop = hist.scrollHeight;
    return div;
}

function tryLocalJarvisCommand(text) {
    const t = text.toLowerCase().trim();
    if (t.startsWith('/habito ') || t.startsWith('/hábito ')) {
        const name = text.split(/\s+/).slice(1).join(' ').trim();
        if (!name) return 'Use: /habito nome do hábito';
        LocalDB.upsert('habits', { id: Date.now(), name, active: 1, current_streak: 0, period: 'all' });
        loadHabits();
        backgroundSync();
        return `Hábito "${name}" criado.`;
    }
    if (t.startsWith('/tarefa ')) {
        const title = text.split(/\s+/).slice(1).join(' ').trim();
        if (!title) return 'Use: /tarefa nome da tarefa';
        LocalDB.upsert('tasks', { id: Date.now(), title, name: title, points_reward: 10 });
        loadTasks();
        backgroundSync();
        return `Tarefa "${title}" adicionada.`;
    }
    const goalMatch = t.match(/meta\s+(.+?)\s*([+-])\s*(\d+)/i);
    if (goalMatch) {
        const namePart = goalMatch[1].trim();
        const delta = (goalMatch[2] === '-' ? -1 : 1) * parseInt(goalMatch[3], 10);
        const goals = LocalDB.get('nexus_goals').filter(g => !g.is_deleted);
        const goal = goals.find(g => (g.name || '').toLowerCase().includes(namePart.toLowerCase()));
        if (goal && typeof adjustGoalProgress === 'function') {
            adjustGoalProgress(goal.id, delta);
            return `Progresso da meta "${goal.name}" ajustado em ${delta > 0 ? '+' : ''}${delta}%.`;
        }
    }
    if (/quantos\s+cards|srs|flashcard/.test(t)) {
        const cards = LocalDB.get('flashcards').filter(c => !c.is_deleted);
        const due = cards.filter(c => !c.next_review || c.next_review <= new Date().toISOString()).length;
        return `Você tem ${due} flashcards para revisar hoje (${cards.length} no total).`;
    }
    return null;
}

async function pollCommandResult(cmdId, timeoutMs) {
    const supabaseClient = window.nexusSupabase;
    if (!supabaseClient) return null;
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        const { data } = await supabaseClient.from('nexus_commands').select('status,result').eq('id', cmdId).maybeSingle();
        if (data?.status === 'completed' && data.result) {
            try {
                const parsed = JSON.parse(data.result);
                return parsed.reply || parsed.message || data.result;
            } catch (_) {
                return data.result;
            }
        }
        if (data?.status === 'error') return 'Erro ao processar no desktop. Tente novamente.';
        await new Promise(r => setTimeout(r, 2000));
    }
    return null;
}

window.sendChatMessage = async function() {
    const input = document.getElementById('chat-input');
    const text = input?.value?.trim();
    if (!text) return;
    appendChatBubble('user', text);
    input.value = '';
    const pending = appendChatBubble('jarvis', 'Processando...', true);

    const localReply = tryLocalJarvisCommand(text);
    if (localReply) {
        if (pending) pending.querySelector('p').innerHTML = escapeHtml(localReply);
        return;
    }

    if (!isNetworkOnline()) {
        if (pending) pending.querySelector('p').textContent = 'Sem internet. Use /habito e /tarefa offline.';
        return;
    }

    if (typeof callJarvisChat === 'function') {
        const history = [];
        document.querySelectorAll('#chat-history .chat-message').forEach(el => {
            const role = el.classList.contains('user-msg') ? 'user' : 'assistant';
            const content = el.querySelector('p')?.textContent?.trim();
            if (content && content !== 'Processando...') history.push({ role, content });
        });
        const reply = await callJarvisChat(text, history.slice(-8));
        if (reply) {
            if (pending) pending.querySelector('p').textContent = reply;
            return;
        }
    }

    if (pending) pending.querySelector('p').textContent = 'Jarvis indisponível. Verifique login Google e conexão.';
};

window.requestMorningBriefing = function() {
    const input = document.getElementById('chat-input');
    if (input) input.value = 'briefing do dia';
    sendChatMessage();
};

window.navigateTo = function(viewId) {
    const nav = document.querySelector(`.nav-item[data-target="${viewId}"]`);
    activateMobileView(viewId, nav || null);
};

function loadTodayDashboard() {
    const now = new Date();
    const today = now.toISOString().split('T')[0];
    const dateLabel = document.getElementById('hoje-date-label');
    if (dateLabel) {
        dateLabel.textContent = now.toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'short' });
    }

    const habits = LocalDB.get('habits').filter(h => h.active === 1 && !h.is_deleted);
    const logs = LocalDB.get('habit_logs');
    const doneToday = logs.filter(l => l.date === today).length;
    const tasks = LocalDB.get('tasks').filter(t => !t.done_at && !t.is_deleted);
    const cards = LocalDB.get('flashcards').filter(c => !c.is_deleted);
    const dueCards = cards.filter(c => {
        const nr = c.next_review || c.nextReviewDate;
        return !nr || nr <= now.toISOString();
    }).length;

    const brief = document.getElementById('hoje-briefing-text');
    if (brief) {
        brief.textContent = `${doneToday}/${habits.length} hábitos feitos · ${tasks.length} tarefas · ${dueCards} cards SRS para revisar.`;
    }

    const list = document.getElementById('hoje-habits-checklist');
    if (list) {
        const morning = habits.filter(h => !h.period || h.period === 'all' || h.period === 'morning').slice(0, 5);
        if (!morning.length) {
            list.innerHTML = '<div style="font-size:0.85rem;color:var(--text-secondary)">Nenhum hábito. Toque em + Hábito para começar.</div>';
        } else {
            list.innerHTML = morning.map(h => {
                const done = logs.some(l => String(l.habit_id) === String(h.id) && l.date === today);
                return `<div class="list-item glass" style="padding:10px 12px;display:flex;justify-content:space-between;align-items:center">
                    <span style="font-size:0.9rem">${escapeHtml(h.name)}</span>
                    <button class="icon-btn ${done ? 'done' : ''}" style="width:28px;height:28px" onclick="toggleHabitDirect('${h.id}');loadTodayDashboard()">
                        <i class="fa-solid fa-check"></i>
                    </button>
                </div>`;
            }).join('');
        }
    }
}

window.toggleIoT = function(ip, turnOn) {
    showToast('IoT disponível apenas com Nexus desktop na mesma rede.');
};

// ----------------------------------------------------
// Realtime Subscription
// ----------------------------------------------------
function setupRealtime() {
    const supabaseClient = window.nexusSupabase;
    if (!supabaseClient) return;
    supabaseClient.channel('custom-all-channel')
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'nexus_user' },
      (payload) => {
          backgroundSync();
      }
    ).on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'tasks' },
      (payload) => { backgroundSync(); }
    ).on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'habits' },
      (payload) => { backgroundSync(); }
    )
    .subscribe();
}

// App Initialization


// ================================================================
// STUDIES MODULE — Enhanced
// ================================================================

let currentNotebookId = null;
let notePreviewActive = false;
let editingNoteId = null;
let studySearchOpen = false;

const MOOD_EMOJIS = ['', '\u{1F613}', '\u{1F615}', '\u{1F610}', '\u{1F604}', '\u{1F929}'];
const MOOD_LABELS = ['', 'P\u00e9ssimo', 'Ruim', 'Neutro', 'Bom', '\u00d3timo'];
const MOOD_COLORS = ['', '#ef4444', '#f97316', '#6b7280', '#10b981', '#8b5cf6'];

function loadStudies() {
    loadStudyStats();
    loadNotebooksGrid();
    renderStudyNotesList('all', null);
}

function loadStudyStats() {
    const notes = LocalDB.get('study_notes').filter(n => !n.is_deleted);
    const cards = LocalDB.get('flashcards').filter(c => !c.is_deleted);
    const pomoLog = LocalDB.get('pomo_sessions') || [];
    const attempts = LocalDB.get('quiz_attempts') || [];

    const todayStr = new Date().toDateString();
    const pomoDate = (p) => p.session_date || p.date || p.created_at || '';
    const todayPomos = pomoLog.filter(p => {
        const d = pomoDate(p);
        return d && new Date(d).toDateString() === todayStr;
    }).length;

    let streak = 0;
    const now = new Date();
    for (let i = 0; i < 60; i++) {
        const d = new Date(now);
        d.setDate(d.getDate() - i);
        const ds = d.toDateString();
        const iso = d.toISOString().split('T')[0];
        const hadStudy = notes.some(n => n.created_at && new Date(n.created_at).toDateString() === ds) ||
                         pomoLog.some(p => String(pomoDate(p)).startsWith(iso)) ||
                         attempts.some(a => a.finished_at && new Date(a.finished_at).toDateString() === ds);
        if (hadStudy) streak++;
        else if (i > 0) break;
    }

    const recentScores = attempts.filter(a => a.score_pct != null).slice(-5);
    const avgQuiz = recentScores.length
        ? Math.round(recentScores.reduce((s, a) => s + Number(a.score_pct), 0) / recentScores.length)
        : null;

    const sv = document.getElementById('study-streak-val');
    const pv = document.getElementById('study-pomo-val');
    const nv = document.getElementById('study-notes-val');
    const cv = document.getElementById('study-cards-val');
    const qv = document.getElementById('study-quiz-val');
    if (sv) sv.textContent = streak;
    if (pv) pv.textContent = todayPomos;
    if (nv) nv.textContent = notes.length;
    if (cv) cv.textContent = cards.length;
    if (qv) qv.textContent = avgQuiz != null ? avgQuiz + '%' : '—';
}

function loadNotebooksGrid() {
    const grid = document.getElementById('notebooks-grid');
    if (!grid) return;
    
    const notebooks = LocalDB.get('study_notebooks');
    const notes = LocalDB.get('study_notes').filter(n => !n.is_deleted);
    
    if (!notebooks || notebooks.length === 0) {
        grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text-secondary);font-size:0.85rem;padding:20px">Sem cadernos ainda. Crie o primeiro!</div>';
        return;
    }
    
    const COLORS = [
        'linear-gradient(135deg,#6c5ce7,#a29bfe)',
        'linear-gradient(135deg,#00b894,#55efc4)',
        'linear-gradient(135deg,#fd79a8,#e17055)',
        'linear-gradient(135deg,#0984e3,#74b9ff)',
        'linear-gradient(135deg,#fdcb6e,#e17055)',
        'linear-gradient(135deg,#00cec9,#55efc4)',
    ];
    
    grid.innerHTML = notebooks.map((nb, i) => {
        const count = notes.filter(n => n.notebook_id === nb.id).length;
        const bg = nb.color || COLORS[i % COLORS.length];
        return `
        <div class="notebook-card" onclick="openNotebookDetail('${nb.id}')" style="background:${bg}">
            <div>
                <div class="notebook-name">${escapeHtml(nb.name)}</div>
                <div class="notebook-count">${count} nota${count !== 1 ? 's' : ''}</div>
            </div>
            <span class="notebook-icon">${nb.icon || '\u{1F4D3}'}</span>
        </div>`;
    }).join('');
}

window.openNewNotebook = function() {
    const name = prompt('Nome do caderno:');
    if (!name || !name.trim()) return;
    const icon = prompt('Emoji do caderno (ex: \u{1F4D3}, \u{1F4BB}, \u{1F9EA}):', '\u{1F4D3}') || '\u{1F4D3}';
    const nb = { id: Date.now().toString(), name: name.trim(), icon, created_at: new Date().toISOString() };
    const notebooks = LocalDB.get('study_notebooks');
    notebooks.push(nb);
    LocalDB.set('study_notebooks', notebooks);
    loadNotebooksGrid();
    showInAppNotification('Caderno criado!', 'success');
    console.info('[Studies] Novo caderno criado: ' + name);
};

window.openNotebookDetail = function(notebookId) {
    currentNotebookId = notebookId;
    const notebooks = LocalDB.get('study_notebooks');
    const nb = notebooks.find(n => n.id === notebookId);
    const detail = document.getElementById('notebook-detail-view');
    const titleEl = document.getElementById('notebook-detail-title');
    if (!detail || !nb) return;
    if (titleEl) titleEl.textContent = (nb.icon || '') + ' ' + nb.name;
    detail.style.display = 'block';
    renderNotebookNotes(notebookId);
};

function renderNotebookNotes(notebookId) {
    const list = document.getElementById('notebook-notes-list');
    if (!list) return;
    const notes = LocalDB.get('study_notes').filter(n => !n.is_deleted && n.notebook_id === notebookId);
    if (notes.length === 0) {
        list.innerHTML = '<div style="text-align:center;color:var(--text-secondary);padding:30px">Sem notas neste caderno.<br>Crie a primeira!</div>';
        return;
    }
    list.innerHTML = notes.sort((a,b) => (b.updated_at||b.created_at||'').localeCompare(a.updated_at||a.created_at||'')).map(renderNoteCard).join('');
}

window.closeNotebookDetail = function() {
    const detail = document.getElementById('notebook-detail-view');
    if (detail) detail.style.display = 'none';
    currentNotebookId = null;
};

function renderStudyNotesList(filter, query) {
    const list = document.getElementById('studies-list');
    if (!list) return;
    let notes = LocalDB.get('study_notes').filter(n => !n.is_deleted);
    
    if (query && query.trim()) {
        const q = query.toLowerCase();
        notes = notes.filter(n => 
            (n.title||'').toLowerCase().includes(q) ||
            (n.content||'').toLowerCase().includes(q) ||
            (n.tags||'').toLowerCase().includes(q)
        );
    }
    if (filter === 'pinned') notes = notes.filter(n => n.pinned);
    
    notes = notes.sort((a,b) => {
        if (a.pinned && !b.pinned) return -1;
        if (!a.pinned && b.pinned) return 1;
        return (b.updated_at||b.created_at||'').localeCompare(a.updated_at||a.created_at||'');
    });
    
    if (filter === 'recent') notes = notes.slice(0, 10);
    
    if (notes.length === 0) {
        list.innerHTML = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px">Nenhuma nota encontrada.</div>';
        return;
    }
    list.innerHTML = notes.map(renderNoteCard).join('');
}

window.openSubjectForm = function() {
    const modal = document.getElementById('subject-form-modal');
    if (!modal) { showToast('Formulário de matéria indisponível'); return; }
    document.getElementById('subject-form-name').value = '';
    document.getElementById('subject-form-icon').value = '📚';
    document.getElementById('subject-form-cover').value = '';
    document.getElementById('subject-form-description').value = '';
    document.getElementById('subject-form-color').value = '#6c5ce7';
    modal.style.display = 'flex';
};

window.closeSubjectForm = function() {
    const modal = document.getElementById('subject-form-modal');
    if (modal) modal.style.display = 'none';
};

window.saveSubjectForm = function() {
    const name = document.getElementById('subject-form-name')?.value?.trim();
    if (!name) { showToast('Digite o nome da matéria'); return; }
    const nb = {
        id: Date.now().toString(),
        name,
        icon: document.getElementById('subject-form-icon')?.value || '📚',
        cover_image: document.getElementById('subject-form-cover')?.value?.trim() || null,
        description: document.getElementById('subject-form-description')?.value?.trim() || '',
        color_bg: document.getElementById('subject-form-color')?.value || '#6c5ce7',
        color_text: '#ffffff',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
    };
    const notebooks = LocalDB.get('study_notebooks') || [];
    notebooks.push(nb);
    LocalDB.set('study_notebooks', notebooks);
    closeSubjectForm();
    if (typeof loadStudies === 'function') loadStudies();
    showToast('Matéria criada!');
};

function formatStudyDate(iso) {
    if (!iso) return '—';
    try {
        return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch (_) { return '—'; }
}

function stripHtmlText(html) {
    return String(html || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

function inferJarvisNoteSubject(title, content, notebookId, excludeId) {
    const text = (title + ' ' + stripHtmlText(content)).toLowerCase();
    const keywords = text.split(/\W+/).filter(w => w.length > 3);
    const notes = (LocalDB.get('study_notes') || []).filter(n =>
        !n.is_deleted && String(n.notebook_id) === String(notebookId) && String(n.id) !== String(excludeId));
    let bestSubject = null;
    let bestScore = 0;
    notes.forEach(n => {
        const subj = (n.jarvis_subject || n.subject || '').trim();
        if (!subj) return;
        const subWords = subj.toLowerCase().split(/\W+/);
        const score = keywords.filter(k => subWords.some(s => s.includes(k) || k.includes(s))).length;
        if (score > bestScore) { bestScore = score; bestSubject = subj; }
    });
    if (bestScore >= 2) return bestSubject;
    const fromTitle = (title || '').trim().split(/\s+/).slice(0, 5).join(' ');
    return fromTitle || 'Geral';
}

function renderStudyNoteTile(n) {
    const cover = n.cover_image
        ? `<div class="study-note-cover" style="background-image:url('${escapeHtml(n.cover_image)}')"></div>`
        : '';
    const desc = n.description || stripHtmlText(n.content).substring(0, 120);
    const created = formatStudyDate(n.created_at);
    const updated = formatStudyDate(n.updated_at || n.created_at);
    const jarvisSubject = n.jarvis_subject || n.subject || '';
    return `<div class="study-note-tile glass" onclick="openNoteEditor('${n.id}','${n.notebook_id || ''}')">
        ${cover}
        <div class="study-note-tile-body">
            <button type="button" class="card-menu-btn" onclick="openNoteMenu(event,'${n.id}')" aria-label="Opções"><i class="fa-solid fa-ellipsis-vertical"></i></button>
            <div class="study-note-tile-title">${escapeHtml(n.title || 'Sem título')}</div>
            ${desc ? `<div class="study-note-tile-desc">${escapeHtml(desc)}</div>` : ''}
            <div class="study-note-tile-meta"><span>Criado ${created}</span><span>·</span><span>Editado ${updated}</span></div>
            ${jarvisSubject ? `<div class="study-note-tile-subject" title="Assunto Jarvis">${escapeHtml(jarvisSubject)}</div>` : ''}
        </div>
    </div>`;
}

function renderSubjectFolderCard(nb) {
    const notes = (LocalDB.get('study_notes') || []).filter(n => !n.is_deleted && String(n.notebook_id) === String(nb.id));
    const bg = nb.color_bg || '#6c5ce7';
    const fg = nb.color_text || '#ffffff';
    const coverStyle = nb.cover_image
        ? `background-image:url('${nb.cover_image}')`
        : `background:linear-gradient(135deg,${bg},${bg}cc)`;
    return `<div class="subject-folder-card glass" style="--folder-bg:${bg};--folder-fg:${fg}" onclick="openSubjectDetail('${nb.id}')">
        <button type="button" class="card-menu-btn" onclick="openFolderMenu(event,'${nb.id}')" aria-label="Opções"><i class="fa-solid fa-ellipsis-vertical"></i></button>
        <div class="subject-folder-cover" style="${coverStyle}"></div>
        <div class="subject-folder-body">
            <div class="subject-folder-name">${nb.icon || '📚'} ${escapeHtml(nb.name)}</div>
            ${nb.description ? `<div class="subject-folder-desc">${escapeHtml(nb.description)}</div>` : ''}
            <div class="subject-folder-count">${notes.length} nota${notes.length !== 1 ? 's' : ''}</div>
        </div>
    </div>`;
}

window.openFolderMenu = function(ev, notebookId) {
    ev.stopPropagation();
    window._menuFolderId = notebookId;
    showStudyContextMenu('folder-menu-popup', ev);
};

window.openNoteMenu = function(ev, noteId) {
    ev.stopPropagation();
    window._menuNoteId = noteId;
    showStudyContextMenu('note-menu-popup', ev);
};

function showStudyContextMenu(popupId, ev) {
    const popup = document.getElementById(popupId);
    if (!popup) return;
    popup.style.display = 'block';
    const x = Math.min(Math.max(12, ev.clientX - 100), window.innerWidth - 180);
    const y = Math.min(Math.max(12, ev.clientY + 8), window.innerHeight - 200);
    popup.style.left = x + 'px';
    popup.style.top = y + 'px';
    setTimeout(() => document.addEventListener('click', closeStudyContextMenus, { once: true }), 30);
}

function closeStudyContextMenus() {
    ['folder-menu-popup', 'note-menu-popup', 'subject-menu-popup'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
}

window.openStudyEditSheet = function(type, id) {
    closeStudyContextMenus();
    const sheet = document.getElementById('study-entity-edit-modal');
    const title = document.getElementById('study-entity-edit-title');
    if (!sheet) return;
    window._studyEditType = type;
    window._studyEditId = id;
    const set = (fid, val) => { const el = document.getElementById(fid); if (el) el.value = val ?? ''; };
    const show = (fid, on) => { const el = document.getElementById(fid); if (el) el.parentElement.style.display = on ? '' : 'none'; };
    if (type === 'folder') {
        const nb = (LocalDB.get('study_notebooks') || []).find(n => String(n.id) === String(id));
        if (!nb) return;
        title.textContent = 'Editar matéria';
        set('study-edit-name', nb.name);
        set('study-edit-cover', nb.cover_image || '');
        set('study-edit-color', nb.color_bg || '#6c5ce7');
        set('study-edit-description', nb.description || '');
        set('study-edit-subject', '');
        show('study-edit-name', true); show('study-edit-cover', true); show('study-edit-color', true);
        show('study-edit-description', true); show('study-edit-subject', false);
    } else {
        const note = (LocalDB.get('study_notes') || []).find(n => String(n.id) === String(id));
        if (!note) return;
        title.textContent = 'Editar nota';
        set('study-edit-name', note.title || '');
        set('study-edit-cover', note.cover_image || '');
        set('study-edit-description', note.description || stripHtmlText(note.content).substring(0, 200));
        set('study-edit-subject', note.jarvis_subject || note.subject || '');
        show('study-edit-name', true); show('study-edit-cover', true); show('study-edit-color', false);
        show('study-edit-description', false); show('study-edit-subject', true);
    }
    sheet.style.display = 'flex';
};

window.closeStudyEditSheet = function() {
    const sheet = document.getElementById('study-entity-edit-modal');
    if (sheet) sheet.style.display = 'none';
};

window.saveStudyEditSheet = function() {
    const type = window._studyEditType;
    const id = window._studyEditId;
    if (!type || !id) return;
    const name = document.getElementById('study-edit-name')?.value?.trim();
    if (type === 'folder') {
        const notebooks = LocalDB.get('study_notebooks') || [];
        const idx = notebooks.findIndex(n => String(n.id) === String(id));
        if (idx === -1) return;
        notebooks[idx] = {
            ...notebooks[idx],
            name: name || notebooks[idx].name,
            cover_image: document.getElementById('study-edit-cover')?.value?.trim() || null,
            color_bg: document.getElementById('study-edit-color')?.value || '#6c5ce7',
            description: document.getElementById('study-edit-description')?.value?.trim() || '',
            updated_at: new Date().toISOString()
        };
        LocalDB.set('study_notebooks', notebooks);
        if (String(currentNotebookId) === String(id)) openSubjectDetail(id);
    } else {
        const notes = LocalDB.get('study_notes') || [];
        const idx = notes.findIndex(n => String(n.id) === String(id));
        if (idx === -1) return;
        notes[idx] = {
            ...notes[idx],
            title: name || notes[idx].title,
            cover_image: document.getElementById('study-edit-cover')?.value?.trim() || null,
            jarvis_subject: document.getElementById('study-edit-subject')?.value?.trim() || notes[idx].jarvis_subject,
            updated_at: new Date().toISOString()
        };
        LocalDB.set('study_notes', notes);
        if (currentNotebookId) openSubjectDetail(currentNotebookId);
    }
    closeStudyEditSheet();
    if (typeof loadStudies === 'function') loadStudies();
};

window.pickStudyCoverLocal = function(targetInputId) {
    const inp = document.createElement('input');
    inp.type = 'file';
    inp.accept = 'image/*';
    inp.onchange = (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            const el = document.getElementById(targetInputId);
            if (el) el.value = reader.result;
        };
        reader.readAsDataURL(file);
    };
    inp.click();
};

window.openSubjectDetail = function(notebookId) {
    currentNotebookId = notebookId;
    const nb = (LocalDB.get('study_notebooks') || []).find(n => String(n.id) === String(notebookId));
    const view = document.getElementById('subject-detail-view');
    if (!view || !nb) return;
    document.getElementById('subject-detail-title').textContent = (nb.icon || '') + ' ' + nb.name;
    view.style.display = 'block';
    const notes = (LocalDB.get('study_notes') || []).filter(n => !n.is_deleted && String(n.notebook_id) === String(notebookId))
        .sort((a, b) => (b.updated_at || b.created_at || '').localeCompare(a.updated_at || a.created_at || ''));
    const list = document.getElementById('subject-notes-list');
    list.className = 'notes-grid';
    list.innerHTML = notes.length
        ? notes.map(n => renderStudyNoteTile(n)).join('')
        : '<div style="grid-column:1/-1;text-align:center;padding:30px;color:var(--text-secondary)">Sem notas nesta matéria.</div>';
};

window.deleteFolderFromMenu = function() {
    const id = window._menuFolderId;
    if (!id || !confirm('Excluir esta matéria?')) return;
    const notebooks = (LocalDB.get('study_notebooks') || []).filter(n => String(n.id) !== String(id));
    LocalDB.set('study_notebooks', notebooks);
    if (String(currentNotebookId) === String(id)) closeSubjectDetail();
    closeStudyContextMenus();
    if (typeof loadStudies === 'function') loadStudies();
};

window.closeSubjectDetail = function() {
    const view = document.getElementById('subject-detail-view');
    if (view) view.style.display = 'none';
    currentNotebookId = null;
};

function loadSubjectsGrid() {
    const grid = document.getElementById('subjects-grid');
    if (!grid) return;
    const notebooks = LocalDB.get('study_notebooks') || [];
    if (!notebooks.length) {
        grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text-secondary);padding:20px">Sem matérias. Toque em + para criar.</div>';
        return;
    }
    grid.innerHTML = notebooks.map(nb => renderSubjectFolderCard(nb)).join('');
}

window.assignNoteToNotebookByJarvis = function(notePayload, notebookId) {
    const notes = LocalDB.get('study_notes') || [];
    const title = notePayload.title || 'Nova nota';
    const content = notePayload.content || '';
    const subject = inferJarvisNoteSubject(title, content, notebookId);
    const existing = notes.find(n => !n.is_deleted && String(n.notebook_id) === String(notebookId)
        && (n.jarvis_subject || n.subject) === subject && subject !== 'Geral');
    if (existing && notePayload.merge !== false) {
        existing.content = (existing.content || '') + '\n\n' + content;
        existing.updated_at = new Date().toISOString();
        LocalDB.set('study_notes', notes);
        return existing.id;
    }
    const id = Date.now().toString();
    notes.push({
        id,
        notebook_id: notebookId,
        title,
        content,
        jarvis_subject: subject,
        description: stripHtmlText(content).substring(0, 160),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
    });
    LocalDB.set('study_notes', notes);
    return id;
};

function renderNoteCard(n) {
    return renderStudyNoteTile(n);
}

window.filterNotes = function(filter, btn) {
    document.querySelectorAll('.study-chip').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    renderStudyNotesList(filter, null);
};

window.toggleStudySearch = function() {
    studySearchOpen = !studySearchOpen;
    const bar = document.getElementById('study-search-bar');
    if (bar) {
        bar.style.display = studySearchOpen ? 'block' : 'none';
        if (studySearchOpen) document.getElementById('study-search-input')?.focus();
    }
};

window.searchNotes = function(query) {
    const results = document.getElementById('search-results');
    if (!results) return;
    if (!query || !query.trim()) { results.innerHTML = ''; return; }
    renderStudyNotesList('all', query);
};

window.openNoteEditor = function(noteId, notebookId) {
    const nbId = notebookId || currentNotebookId;
    if (!nbId && !noteId) {
        showToast('Abra uma matéria e crie a nota dentro dela.');
        return;
    }
    const view = document.getElementById('note-editor-view');
    if (!view) return;
    view.style.display = 'flex';
    editingNoteId = noteId || null;
    currentNotebookId = nbId || currentNotebookId;
    
    // Populate notebook selector (hidden — notebook vem do grid atual)
    const sel = document.getElementById('note-notebook');
    if (sel) {
        const notebooks = LocalDB.get('study_notebooks');
        sel.innerHTML = '<option value="">Sem caderno...</option>' +
            notebooks.map(nb => `<option value="${nb.id}" ${String(nb.id) === String(nbId || currentNotebookId) ? 'selected' : ''}>${nb.icon||''} ${escapeHtml(nb.name)}</option>`).join('');
    }
    
    if (noteId) {
        const notes = LocalDB.get('study_notes');
        const note = notes.find(n => n.id === noteId);
        if (note) {
            if (document.getElementById('note-title')) document.getElementById('note-title').value = note.title || '';
            if (document.getElementById('note-content')) document.getElementById('note-content').value = note.content || '';
            if (document.getElementById('note-tags')) document.getElementById('note-tags').value = note.tags || '';
            if (document.getElementById('note-subject')) document.getElementById('note-subject').value = note.subject || '';
            if (sel && note.notebook_id) sel.value = note.notebook_id;
        }
    } else {
        ['note-title','note-content','note-tags','note-subject'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
    }
    notePreviewActive = false;
    const preview = document.getElementById('note-preview');
    const textarea = document.getElementById('note-content');
    if (preview) preview.style.display = 'none';
    if (textarea) textarea.style.display = 'block';
    console.info('[Studies] Note editor opened' + (noteId ? ' (editing: ' + noteId + ')' : ' (new)'));
};

window.toggleNotePreview = function() {
    notePreviewActive = !notePreviewActive;
    const preview = document.getElementById('note-preview');
    const textarea = document.getElementById('note-content');
    const btn = document.getElementById('note-preview-toggle');
    if (!preview || !textarea) return;
    if (notePreviewActive) {
        const md = textarea.value;
        preview.innerHTML = simpleMarkdown(md);
        preview.style.display = 'block';
        textarea.style.display = 'none';
        if (btn) btn.style.color = 'var(--accent-primary)';
    } else {
        preview.style.display = 'none';
        textarea.style.display = 'block';
        if (btn) btn.style.color = '';
    }
};

function simpleMarkdown(text) {
    return text
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
        .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`(.+?)`/g, '<code>$1</code>')
        .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
        .replace(/^---$/gm, '<hr>')
        .replace(/^- \[x\] (.+)$/gm, '<li><input type="checkbox" checked disabled> $1</li>')
        .replace(/^- \[ \] (.+)$/gm, '<li><input type="checkbox" disabled> $1</li>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/\n/g, '<br>');
}

window.insertMd = function(before, after) {
    const ta = document.getElementById('note-content');
    if (!ta) return;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const sel = ta.value.substring(start, end);
    ta.value = ta.value.substring(0, start) + before + sel + after + ta.value.substring(end);
    ta.selectionStart = ta.selectionEnd = start + before.length + sel.length + after.length;
    ta.focus();
};

window.saveNote = function() {
    const title = (document.getElementById('note-title')?.value || '').trim();
    const content = document.getElementById('note-content')?.value || '';
    const tags = document.getElementById('note-tags')?.value || '';
    const subject = document.getElementById('note-subject')?.value || '';
    const notebookId = document.getElementById('note-notebook')?.value || '';
    
    if (!title && !content) { showInAppNotification('Escreva algo primeiro!', 'warn'); return; }
    
    const notes = LocalDB.get('study_notes');
    const now = new Date().toISOString();
    
    if (editingNoteId) {
        const idx = notes.findIndex(n => n.id === editingNoteId);
        if (idx !== -1) {
            notes[idx] = {...notes[idx], title: title||'Sem titulo', content, tags, subject, notebook_id: notebookId, updated_at: now};
        }
    } else {
        notes.push({ id: Date.now().toString(), title: title||'Sem titulo', content, tags, subject, notebook_id: notebookId, created_at: now, updated_at: now });
        // Award XP for new note
        awardXP(15, 'Nova nota de estudo');
    }
    LocalDB.set('study_notes', notes);
    closeNoteEditor();
    loadStudies();
    showInAppNotification('Nota salva!', 'success');
    console.info('[Studies] Note saved: ' + (title||'Sem titulo'));
};

window.closeNoteEditor = function() {
    const view = document.getElementById('note-editor-view');
    if (view) view.style.display = 'none';
    editingNoteId = null;
    notePreviewActive = false;
};

// Focus Mode
window.openFocusMode = function() {
    const topic = prompt('Topico de estudo (opcional):') || '';
    let overlay = document.getElementById('focus-mode-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'focus-mode-overlay';
        overlay.style.cssText = 'display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:#000;z-index:300;flex-direction:column;align-items:center;justify-content:center;gap:20px;padding:40px 30px';
        overlay.innerHTML = `
            <div style="font-size:0.85rem;color:rgba(255,255,255,0.3);text-transform:uppercase;letter-spacing:2px">Modo Foco</div>
            <div class="focus-timer-display" id="focus-timer-val">00:00</div>
            <div id="focus-topic-label" style="font-size:1rem;color:rgba(255,255,255,0.5);text-align:center"></div>
            <div style="display:flex;gap:16px;margin-top:20px">
                <button onclick="endFocusMode()" style="background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);color:white;padding:14px 30px;border-radius:14px;font-size:1rem;cursor:pointer;font-family:inherit">Encerrar</button>
            </div>`;
        document.body.appendChild(overlay);
    }
    const topicEl = document.getElementById('focus-topic-label');
    if (topicEl) topicEl.textContent = topic;
    overlay.style.display = 'flex';
    
    let elapsed = 0;
    window._focusInterval = setInterval(() => {
        elapsed++;
        const m = String(Math.floor(elapsed/60)).padStart(2,'0');
        const s = String(elapsed%60).padStart(2,'0');
        const el = document.getElementById('focus-timer-val');
        if (el) el.textContent = m + ':' + s;
    }, 1000);
    console.info('[Studies] Focus mode started');
};

window.endFocusMode = function() {
    clearInterval(window._focusInterval);
    const overlay = document.getElementById('focus-mode-overlay');
    if (overlay) overlay.style.display = 'none';
    const timerEl = document.getElementById('focus-timer-val');
    if (timerEl) {
        const [m,s] = timerEl.textContent.split(':').map(Number);
        const mins = m * 60 + s;
        if (mins >= 5) {
            awardXP(Math.floor(mins/5) * 5, 'Sessao de foco de ' + m + 'min');
            showInAppNotification('Sessao de foco registrada! +' + Math.floor(mins/5)*5 + ' XP', 'success');
        }
    }
};

// Pomodoro improvements
const _origPomodoro = window.openPomodoro;
window.openPomodoro = function() {
    const view = document.getElementById('pomodoro-view');
    if (view) {
        view.style.display = 'flex';
        loadPomoHistory();
    }
};
window.closePomodoro = function() {
    const view = document.getElementById('pomodoro-view');
    if (view) view.style.display = 'none';
};

function loadPomoHistory() {
    const histEl = document.getElementById('pomo-history');
    if (!histEl) return;
    const sessions = (LocalDB.get('pomo_sessions') || []).slice(0, 10);
    if (!sessions.length) { histEl.innerHTML = '<div style="color:var(--text-secondary);font-size:0.8rem;text-align:center">Nenhuma sessao hoje ainda.</div>'; return; }
    histEl.innerHTML = sessions.map(s => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 10px;background:rgba(255,255,255,0.04);border-radius:8px">
            <span style="color:var(--accent-primary);font-weight:600">${s.type === 'break' ? 'Pausa' : 'Foco'}</span>
            <span style="color:var(--text-secondary);font-size:0.8rem">${s.duration}min &bull; ${new Date(s.date).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})}</span>
        </div>`).join('');
}

// Override startPomodoro to save history + award XP
const _origStartPomo = window.startPomodoro;
const _patchedPomoEnd = function() {
    const sessions = LocalDB.get('pomo_sessions') || [];
    sessions.unshift({ type: 'focus', duration: 25, date: new Date().toISOString() });
    if (sessions.length > 50) sessions.pop();
    LocalDB.set('pomo_sessions', sessions);
    awardXP(20, 'Sessao Pomodoro completa');
    showInAppNotification('+20 XP por completar um Pomodoro!', 'success');
    loadPomoHistory();
    loadStudyStats();
};

// ================================================================
// XP & GAMIFICATION SYSTEM
// ================================================================

function awardXP(amount, reason) {
    const stats = LocalDB.get('user_stats') || { xp: 0, points: 0, level: 1, xp_today: 0, last_xp_date: '' };
    const todayStr = new Date().toDateString();
    if (stats.last_xp_date !== todayStr) {
        stats.xp_today = 0;
        stats.last_xp_date = todayStr;
    }
    stats.xp = (stats.xp || 0) + amount;
    stats.xp_today = (stats.xp_today || 0) + amount;
    stats.points = (stats.points || 0) + Math.floor(amount * 0.5);
    
    const newLevel = Math.floor(stats.xp / 500) + 1;
    const leveledUp = newLevel > (stats.level || 1);
    stats.level = newLevel;
    
    LocalDB.set('user_stats', stats);
    syncUserStatsToNexusUser();
    
    // XP log
    const xpLog = LocalDB.get('xp_log') || [];
    xpLog.unshift({ amount, reason, date: new Date().toISOString() });
    if (xpLog.length > 200) xpLog.pop();
    LocalDB.set('xp_log', xpLog);
    
    if (leveledUp) {
        showInAppNotification('LEVEL UP! Voce chegou ao nivel ' + newLevel + '!', 'success');
        if (window.NexusAudio) window.NexusAudio.play('complete');
        if (navigator.vibrate) navigator.vibrate([100, 50, 100, 50, 200]);
    } else if (window.NexusAudio) {
        window.NexusAudio.play('progress');
    }
    
    loadXPPanel();
    loadTodayDashboard();
    console.info('[XP] +' + amount + ' XP: ' + reason + ' (total: ' + stats.xp + ')');
}

function loadXPPanel() {
    const stats = LocalDB.get('user_stats') || { xp: 0, points: 0, level: 1, xp_today: 0 };
    const xpForCurrentLevel = (stats.level - 1) * 500;
    const xpProgress = stats.xp - xpForCurrentLevel;
    const xpForNextLevel = 500;
    const pct = Math.min(100, Math.floor((xpProgress / xpForNextLevel) * 100));
    
    const xpEl = document.getElementById('stat-xp');
    const ptsEl = document.getElementById('stat-points');
    const barEl = document.getElementById('xp-progress-bar');
    const lvlEl = document.getElementById('xp-level-label');
    const streakBadge = document.getElementById('xp-streak-badge');
    
    if (xpEl) xpEl.textContent = stats.xp.toLocaleString('pt-BR');
    if (ptsEl) ptsEl.textContent = (stats.points || 0).toLocaleString('pt-BR');
    if (barEl) barEl.style.width = pct + '%';
    if (lvlEl) lvlEl.textContent = 'Nivel ' + (stats.level||1) + ' \u2022 ' + pct + '% para nivel ' + ((stats.level||1)+1);
    
    // Streak from habits
    const habits = LocalDB.get('habits').filter(h => h.active === 1 && !h.is_deleted);
    const logs = LocalDB.get('habit_logs');
    let globalStreak = 0;
    const now2 = new Date();
    for (let i = 0; i < 60; i++) {
        const d = new Date(now2); d.setDate(d.getDate() - i);
        const ds = d.toISOString().split('T')[0];
        const completed = habits.some(h => logs.some(l => l.habit_id === h.id && l.date === ds));
        if (completed) globalStreak++;
        else if (i > 0) break;
    }
    if (streakBadge) streakBadge.textContent = '\uD83D\uDD25 ' + globalStreak;
    
    // Habits today
    const todayStr = new Date().toISOString().split('T')[0];
    const todayLogs = logs.filter(l => l.date === todayStr);
    const habitsEl = document.getElementById('stat-habits-today');
    const habStreak = document.getElementById('habits-streak-label');
    if (habitsEl) habitsEl.textContent = todayLogs.length + '/' + habits.length;
    if (habStreak) habStreak.textContent = '\uD83D\uDD25 ' + globalStreak + ' dias';
    
    // Points today
    const pTodayEl = document.getElementById('points-today-label');
    if (pTodayEl) pTodayEl.textContent = '+' + (stats.xp_today || 0) + ' hoje';
    
    // Tasks
    const tasks = LocalDB.get('tasks').filter(t => !t.done_at && !t.is_deleted);
    const tasksEl = document.getElementById('stat-tasks-pending');
    if (tasksEl) tasksEl.textContent = tasks.length;
}

// Override loadUserStats to use our system
const _origLoadUserStats = window.loadUserStats;
window.loadUserStats = function() {
    if (_origLoadUserStats) _origLoadUserStats();
    loadXPPanel();
};

// ================================================================
// JOURNAL / MOOD MODULE
// ================================================================

let selectedEditorMood = 0;
let editingJournalId = null;

window.startJournalDictation = function() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const status = document.getElementById('journal-mic-status');
    const textarea = document.getElementById('journal-content');
    if (!textarea) return;
    if (!SpeechRecognition) {
        if (status) status.textContent = 'Ditado indisponível neste dispositivo';
        showToast('Ditado não suportado no WebView');
        return;
    }
    const rec = new SpeechRecognition();
    rec.lang = 'pt-BR';
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    if (status) status.textContent = 'Ouvindo... fale agora';
    rec.onresult = (e) => {
        const text = e.results[0][0].transcript;
        textarea.value = (textarea.value ? textarea.value + ' ' : '') + text;
        if (status) status.textContent = 'Texto adicionado!';
    };
    rec.onerror = () => {
        if (status) status.textContent = 'Erro no ditado — tente novamente';
        showToast('Erro no reconhecimento de voz');
    };
    rec.onend = () => {
        if (status && status.textContent === 'Ouvindo... fale agora') {
            status.textContent = 'Pressione para ditar';
        }
    };
    try { rec.start(); } catch (e) {
        if (status) status.textContent = 'Microfone indisponível';
        showToast('Permissão de microfone necessária');
    }
};

window.loadJournal = function() {
    loadMoodCalendarStrip();
    loadJournalList();
    loadTodayMood();
};

function loadTodayMood() {
    const todayStr = new Date().toISOString().split('T')[0];
    const entries = LocalDB.get('journal_entries');
    const today = entries.find(e => e.date === todayStr);
    if (today && today.mood) {
        document.querySelectorAll('.mood-btn').forEach(b => {
            b.classList.toggle('selected', parseInt(b.dataset.mood) === today.mood);
        });
        const label = document.getElementById('mood-selected-label');
        if (label) label.textContent = MOOD_EMOJIS[today.mood] + ' ' + MOOD_LABELS[today.mood];
    }
}

window.setTodayMood = function(mood) {
    const todayStr = new Date().toISOString().split('T')[0];
    const entries = LocalDB.get('journal_entries');
    let entry = entries.find(e => e.date === todayStr);
    if (entry) {
        entry.mood = mood;
    } else {
        entries.push({ id: Date.now().toString(), date: todayStr, mood, created_at: new Date().toISOString() });
        awardXP(5, 'Registro de humor');
    }
    LocalDB.set('journal_entries', entries);
    document.querySelectorAll('.mood-btn').forEach(b => b.classList.toggle('selected', parseInt(b.dataset.mood) === mood));
    const label = document.getElementById('mood-selected-label');
    if (label) label.textContent = MOOD_EMOJIS[mood] + ' ' + MOOD_LABELS[mood];
    loadMoodCalendarStrip();
    showInAppNotification('Humor registrado: ' + MOOD_LABELS[mood], 'info');
    console.info('[Journal] Mood set to ' + mood + ' (' + MOOD_LABELS[mood] + ')');
};

function loadMoodCalendarStrip() {
    const strip = document.getElementById('mood-calendar-strip');
    if (!strip) return;
    const entries = LocalDB.get('journal_entries');
    const avgEl = document.getElementById('mood-avg-label');
    
    let html = '';
    const moods = [];
    const days = ['D','S','T','Q','Q','S','S'];
    
    for (let i = 13; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        const ds = d.toISOString().split('T')[0];
        const entry = entries.find(e => e.date === ds);
        const mood = entry ? entry.mood : 0;
        if (mood) moods.push(mood);
        const color = mood ? MOOD_COLORS[mood] : 'rgba(255,255,255,0.05)';
        const emoji = mood ? MOOD_EMOJIS[mood] : '\u00b7';
        const dayLabel = days[d.getDay()];
        html += `<div class="mood-day-dot" style="background:${color}20;border:1px solid ${color}40" title="${ds}" onclick="openJournalEntry('${ds}')">
            <span class="mood-day-emoji">${emoji}</span>
            <span class="mood-day-label">${dayLabel}</span>
        </div>`;
    }
    strip.innerHTML = html;
    
    if (moods.length > 0 && avgEl) {
        const avg = (moods.reduce((a,b) => a+b, 0) / moods.length).toFixed(1);
        avgEl.textContent = 'Media: ' + avg + '/5';
    }
}

function loadJournalList() {
    const list = document.getElementById('journal-list');
    if (!list) return;
    const entries = LocalDB.get('journal_entries')
        .filter(e => e.content || e.best || e.challenge || e.gratitude)
        .sort((a,b) => b.date.localeCompare(a.date))
        .slice(0, 30);
    
    if (!entries.length) {
        list.innerHTML = '<div style="text-align:center;color:var(--text-secondary);padding:30px">Nenhuma entrada ainda. Comece seu diario!</div>';
        return;
    }
    list.innerHTML = entries.map(e => {
        const mood = e.mood || 0;
        const preview = (e.best || e.content || e.challenge || '').substring(0, 80);
        const dateStr = new Date(e.date + 'T12:00:00').toLocaleDateString('pt-BR', {weekday:'short', day:'2-digit', month:'short'});
        return `<div class="journal-entry-card" onclick="openJournalEntry('${e.date}')">
            <div class="journal-entry-emoji">${mood ? MOOD_EMOJIS[mood] : '\u{1F4D3}'}</div>
            <div style="flex:1;min-width:0">
                <div class="journal-entry-meta">${dateStr}</div>
                <div class="journal-entry-preview">${escapeHtml(preview)}${preview.length >= 80 ? '...' : ''}</div>
            </div>
        </div>`;
    }).join('');
}

window.openJournalEntry = function(dateStr) {
    const date = dateStr || new Date().toISOString().split('T')[0];
    const editor = document.getElementById('journal-entry-editor');
    if (!editor) return;
    editor.style.display = 'block';
    
    const dateEl = document.getElementById('journal-entry-date');
    if (dateEl) dateEl.textContent = new Date(date + 'T12:00:00').toLocaleDateString('pt-BR', {weekday:'long', day:'2-digit', month:'long', year:'numeric'});
    
    const entries = LocalDB.get('journal_entries');
    const existing = entries.find(e => e.date === date);
    editingJournalId = date;
    selectedEditorMood = existing ? (existing.mood || 0) : 0;
    
    ['journal-best','journal-challenge','journal-gratitude','journal-content'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    
    document.querySelectorAll('.mood-btn-sm').forEach(b => b.classList.remove('selected'));
    
    if (existing) {
        if (document.getElementById('journal-best')) document.getElementById('journal-best').value = existing.best || '';
        if (document.getElementById('journal-challenge')) document.getElementById('journal-challenge').value = existing.challenge || '';
        if (document.getElementById('journal-gratitude')) document.getElementById('journal-gratitude').value = existing.gratitude || '';
        if (document.getElementById('journal-content')) document.getElementById('journal-content').value = existing.content || '';
        if (existing.mood) {
            document.querySelectorAll('.mood-btn-sm').forEach(b => b.classList.toggle('selected', parseInt(b.dataset.mood) === existing.mood));
        }
    }
};

window.closeJournalEntry = function() {
    const editor = document.getElementById('journal-entry-editor');
    if (editor) editor.style.display = 'none';
    editingJournalId = null;
};

window.selectEditorMood = function(mood) {
    selectedEditorMood = mood;
    document.querySelectorAll('.mood-btn-sm').forEach(b => b.classList.toggle('selected', parseInt(b.dataset.mood) === mood));
};

window.saveJournalEntry = function() {
    const date = editingJournalId || new Date().toISOString().split('T')[0];
    const best = document.getElementById('journal-best')?.value || '';
    const challenge = document.getElementById('journal-challenge')?.value || '';
    const gratitude = document.getElementById('journal-gratitude')?.value || '';
    const content = document.getElementById('journal-content')?.value || '';
    
    if (!best && !challenge && !gratitude && !content && !selectedEditorMood) {
        showInAppNotification('Escreva algo antes de salvar!', 'warn');
        return;
    }
    
    const entries = LocalDB.get('journal_entries');
    const idx = entries.findIndex(e => e.date === date);
    const entry = { id: Date.now().toString(), date, mood: selectedEditorMood, best, challenge, gratitude, content, updated_at: new Date().toISOString() };
    
    if (idx !== -1) {
        entries[idx] = { ...entries[idx], ...entry };
    } else {
        entry.created_at = entry.updated_at;
        entries.push(entry);
        awardXP(10, 'Entrada de diario');
    }
    LocalDB.set('journal_entries', entries);
    
    // Sync mood with today card if editing today
    const todayStr = new Date().toISOString().split('T')[0];
    if (date === todayStr && selectedEditorMood) setTodayMood(selectedEditorMood);
    
    closeJournalEntry();
    loadJournal();
    showInAppNotification('Diario salvo!', 'success');
    console.info('[Journal] Entry saved for ' + date);
};

// ================================================================
// FITNESS MODULE — Enhanced
// ================================================================

window.switchFitnessTab = function(tab, btn) {
    ['treinos','dieta','medidas'].forEach(t => {
        const el = document.getElementById('fitness-tab-' + t);
        if (el) el.style.display = t === tab ? 'block' : 'none';
    });
    document.querySelectorAll('.fitness-tab').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (tab === 'dieta') loadDietToday();
    if (tab === 'medidas') loadMeasures();
    if (tab === 'treinos') loadFitness();
};

window.openWorkoutBuilder = function() {
    const name = prompt('Nome do treino (ex: Peito, Costas, Pernas):');
    if (!name || !name.trim()) return;
    const muscleGroup = prompt('Grupo muscular (ex: Peito e Ombro):') || '';
    
    const workout = {
        id: Date.now(),
        name: name.trim(),
        type: name.trim(),
        muscle_group: muscleGroup,
        exercises: [],
        date: new Date().toISOString().split('T')[0],
        created_at: new Date().toISOString()
    };
    LocalDB.upsert('fitness_workouts', workout);
    awardXP(25, 'Treino registrado: ' + name);
    loadFitness();
    showInAppNotification('Treino registrado! +25 XP', 'success');
    console.info('[Fitness] Workout added: ' + name);
};

window.openMealLogger = function() {
    const mealName = prompt('Nome da refeicao (ex: Alm0co, Proteina):');
    if (!mealName) return;
    const cal = parseInt(prompt('Calorias (kcal):') || '0');
    const protein = parseInt(prompt('Proteina (g):') || '0');
    const carb = parseInt(prompt('Carboidratos (g):') || '0');
    const fat = parseInt(prompt('Gorduras (g):') || '0');
    
    const meals = LocalDB.get('diet_meals') || [];
    meals.push({ id: Date.now().toString(), name: mealName, cal, protein, carb, fat, date: new Date().toISOString() });
    LocalDB.set('diet_meals', meals);
    loadDietToday();
    showInAppNotification('Refeicao registrada!', 'success');
};

function loadDietToday() {
    const todayStr = new Date().toISOString().split('T')[0];
    const meals = (LocalDB.get('diet_meals') || []).filter(m => m.date.startsWith(todayStr));
    
    const totalCal = meals.reduce((s, m) => s + (m.cal||0), 0);
    const totalProtein = meals.reduce((s, m) => s + (m.protein||0), 0);
    const totalCarb = meals.reduce((s, m) => s + (m.carb||0), 0);
    const totalFat = meals.reduce((s, m) => s + (m.fat||0), 0);
    const goal = 2000;
    
    const pct = Math.min(100, Math.round(totalCal / goal * 100));
    document.getElementById('diet-cal-text') && (document.getElementById('diet-cal-text').textContent = totalCal + ' / ' + goal + ' kcal');
    document.getElementById('diet-cal-bar') && (document.getElementById('diet-cal-bar').style.width = pct + '%');
    document.getElementById('diet-protein') && (document.getElementById('diet-protein').textContent = totalProtein + 'g');
    document.getElementById('diet-carb') && (document.getElementById('diet-carb').textContent = totalCarb + 'g');
    document.getElementById('diet-fat') && (document.getElementById('diet-fat').textContent = totalFat + 'g');
    
    const mealList = document.getElementById('diet-meals-list');
    if (mealList) {
        mealList.innerHTML = meals.length ? meals.map(m => `
            <div class="meal-card glass">
                <div class="meal-info">
                    <div class="meal-name">${escapeHtml(m.name)}</div>
                    <div class="meal-time">${new Date(m.date).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})}</div>
                </div>
                <div class="meal-cal">${m.cal} kcal</div>
            </div>`).join('') : '<div style="text-align:center;color:var(--text-secondary);padding:20px">Nenhuma refeicao registrada hoje.</div>';
    }
}

window.openBodyMeasurement = function() {
    const weight = prompt('Peso atual (kg):');
    if (!weight) return;
    const fatPct = prompt('% de gordura (opcional):') || '';
    
    const measures = LocalDB.get('body_measures') || [];
    measures.push({ id: Date.now().toString(), weight: parseFloat(weight)||0, fat_pct: parseFloat(fatPct)||0, date: new Date().toISOString() });
    LocalDB.set('body_measures', measures);
    loadMeasures();
    showInAppNotification('Medidas salvas!', 'success');
};

function loadMeasures() {
    const measures = (LocalDB.get('body_measures') || []).sort((a,b) => b.date.localeCompare(a.date));
    const latest = measures[0];
    
    if (latest) {
        document.getElementById('measure-weight-val') && (document.getElementById('measure-weight-val').textContent = latest.weight + ' kg');
        if (latest.fat_pct) document.getElementById('measure-fat-pct') && (document.getElementById('measure-fat-pct').textContent = latest.fat_pct + '%');
    }
    
    const list = document.getElementById('measures-list');
    if (list) {
        list.innerHTML = measures.slice(0,10).map(m => `
            <div class="list-item glass" style="gap:12px">
                <div class="item-main">
                    <div class="item-title">${m.weight} kg</div>
                    <div class="item-subtitle">${new Date(m.date).toLocaleDateString('pt-BR')}</div>
                </div>
                ${m.fat_pct ? '<div style="color:var(--accent-blue);font-weight:700">' + m.fat_pct + '% gord.</div>' : ''}
            </div>`).join('') || '<div style="text-align:center;color:var(--text-secondary);padding:20px">Sem medidas registradas.</div>';
    }
}

// ================================================================
// INIT — update DOMContentLoaded
// ================================================================

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Ensure LocalDB has new keys
const _origLocalDB_get = LocalDB.get.bind(LocalDB);
const _newDefaults = {
    study_notebooks: [], pomo_sessions: [], journal_entries: [], 
    diet_meals: [], body_measures: [], xp_log: [],
    user_stats: { xp: 0, points: 0, level: 1, xp_today: 0, last_xp_date: '' }
};
const _origGet = LocalDB.get;
LocalDB.get = function(key) {
    const val = _origGet.call(this, key);
    if (val === null || val === undefined || (Array.isArray(val) && val.length === 0 && _newDefaults[key] && !Array.isArray(_newDefaults[key]))) {
        return _newDefaults[key] !== undefined ? JSON.parse(JSON.stringify(_newDefaults[key])) : val;
    }
    return val;
};



// ================================================================
// HABITS MODULE — Enhanced (Phase 3)
// ================================================================

let currentHabitId = null;

function filterHabits(filter, btn) {
    document.querySelectorAll('#view-habits .study-chip').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    
    const container = document.getElementById('habits-list');
    if(!container) return;
    
    let habits = LocalDB.get('habits').filter(h => h.active === 1 && !h.is_deleted);
    if (filter === 'morning') habits = habits.filter(h => h.period === 'morning');
    else if (filter === 'afternoon') habits = habits.filter(h => h.period === 'afternoon');
    else if (filter === 'night') habits = habits.filter(h => h.period === 'night');
    
    const logs = LocalDB.get('habit_logs');
    const today = new Date().toISOString().split('T')[0];
    
    if (habits.length === 0) {
        container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;">Nenhum habito nesta categoria.</div>';
        return;
    }
    
    container.innerHTML = habits.map(h => {
        const isDone = logs.some(l => l.habit_id === h.id && l.date === today);
        let streak = 0;
        const now = new Date();
        for (let i = 0; i < 60; i++) {
            const d = new Date(now); d.setDate(d.getDate() - i);
            const ds = d.toISOString().split('T')[0];
            if (logs.some(l => l.habit_id === h.id && l.date === ds)) streak++;
            else if (i > 0) break;
        }
        
        return `
        <div class="list-item glass ${isDone ? 'done' : ''}" style="cursor:pointer" onclick="openHabitDetail('${h.id}')">
            <div class="item-main">
                <div class="item-title">${escapeHtml(h.name)}</div>
                <div class="item-subtitle">${h.period === 'morning' ? '\u2600 Manha' : h.period === 'afternoon' ? '\u26C5 Tarde' : h.period === 'night' ? '\uD83C\uDF19 Noite' : 'Qualquer horario'}</div>
            </div>
            <div style="display:flex;align-items:center;gap:12px">
                ${streak > 0 ? `<span style="font-size:0.75rem;font-weight:700;color:#f97316;background:rgba(249,115,22,0.15);padding:3px 8px;border-radius:10px">\uD83D\uDD25 ${streak}</span>` : ''}
                <button class="icon-btn ${isDone ? 'done' : ''}" style="background:var(--accent-primary);color:white;width:32px;height:32px;font-size:0.9rem" onclick="event.stopPropagation(); toggleHabitDirect('${h.id}')">
                    <i class="fa-solid ${isDone ? 'fa-check' : 'fa-plus'}"></i>
                </button>
            </div>
        </div>`;
    }).join('');
}

window.openHabitDetail = function(habitId) {
    currentHabitId = habitId;
    const habits = LocalDB.get('habits');
    const logs = LocalDB.get('habit_logs');
    const h = habits.find(x => x.id === habitId);
    if (!h) return;
    
    const today = new Date().toISOString().split('T')[0];
    const isDone = logs.some(l => l.habit_id === h.id && l.date === today);
    
    let streak = 0;
    const now = new Date();
    for (let i = 0; i < 60; i++) {
        const d = new Date(now); d.setDate(d.getDate() - i);
        const ds = d.toISOString().split('T')[0];
        if (logs.some(l => l.habit_id === h.id && l.date === ds)) streak++;
        else if (i > 0) break;
    }
    const total = logs.filter(l => l.habit_id === h.id).length;
    
    const modal = document.getElementById('habit-detail-modal');
    if (document.getElementById('habit-detail-name')) document.getElementById('habit-detail-name').textContent = h.name;
    if (document.getElementById('habit-detail-streak')) document.getElementById('habit-detail-streak').textContent = streak;
    if (document.getElementById('habit-detail-total')) document.getElementById('habit-detail-total').textContent = total;
    if (document.getElementById('habit-alarm-time')) document.getElementById('habit-alarm-time').value = h.alarm_time || '';
    
    const btn = document.getElementById('habit-detail-complete-btn');
    if (btn) {
        btn.innerHTML = isDone ? '<i class="fa-solid fa-xmark"></i> Desmarcar Hoje' : '<i class="fa-solid fa-check"></i> Feito Hoje';
        btn.style.background = isDone ? 'rgba(255,255,255,0.1)' : 'var(--accent-primary)';
    }
    
    if (modal) modal.style.display = 'flex';
};

window.closeHabitDetail = function() {
    const modal = document.getElementById('habit-detail-modal');
    if (modal) modal.style.display = 'none';
    currentHabitId = null;
};

window.toggleHabitDirect = function(habitId) {
    const logs = LocalDB.getAll('habit_logs');
    const today = new Date().toISOString().split('T')[0];
    const idx = logs.findIndex(l => String(l.habit_id) === String(habitId) && l.date === today && !l.is_deleted);
    if (idx !== -1) {
        logs.splice(idx, 1);
        LocalDB.set('habit_logs', logs);
    } else {
        const entry = {
            id: Date.now(),
            habit_id: habitId,
            date: today,
            completed_date: today
        };
        LocalDB.upsert('habit_logs', entry);
        logs.push(entry);
        LocalDB.set('habit_logs', logs);
        awardXP(5, 'Habito concluido');
    }
    filterHabits(document.querySelector('#view-habits .study-chip.active')?.dataset?.filter || 'all');
    loadXPPanel();
    backgroundSync();
};

window.completeCurrentHabit = function() {
    if (currentHabitId) {
        toggleHabitDirect(currentHabitId);
        closeHabitDetail();
    }
};

window.saveHabitAlarm = function() {
    if (!currentHabitId) return;
    const time = document.getElementById('habit-alarm-time')?.value;
    const habits = LocalDB.get('habits');
    const idx = habits.findIndex(h => String(h.id) === String(currentHabitId));
    if (idx !== -1) {
        habits[idx].alarm_time = time;
        habits[idx].target_time = time;
        LocalDB.set('habits', habits);
        syncHabitReminders();
        showInAppNotification(time ? 'Alarme configurado para ' + time : 'Alarme removido', 'success');
        
        // Request notification permission if enabling alarm
        if (time && "Notification" in window && Notification.permission !== "granted") {
            Notification.requestPermission();
        }
    }
};

window.deleteCurrentHabit = function() {
    if (!currentHabitId) return;
    if (!confirm('Deseja realmente excluir este habito? O historico sera perdido.')) return;
    const habits = LocalDB.get('habits');
    const idx = habits.findIndex(h => String(h.id) === String(currentHabitId));
    if (idx !== -1) {
        habits[idx].is_deleted = true;
        LocalDB.set('habits', habits);
        syncHabitReminders();
        closeHabitDetail();
        filterHabits('all');
        showInAppNotification('Habito excluido.', 'info');
    }
};

// Override original loadHabits to use our new filtered view
window.loadHabits = function() {
    // Also build the heatmap
    const heatmapContainer = document.getElementById('habit-heatmap-container');
    const habits = LocalDB.get('habits').filter(h => h.active === 1 && !h.is_deleted);
    const logs = LocalDB.get('habit_logs');
    
    if (heatmapContainer) {
        heatmapContainer.innerHTML = '';
        const now = new Date();
        for (let i = 29; i >= 0; i--) {
            const d = new Date(now);
            d.setDate(d.getDate() - i);
            const dateStr = d.toISOString().split('T')[0];
            const completedCount = logs.filter(l => l.date === dateStr && habits.some(h => String(h.id) === String(l.habit_id))).length;
            const level = completedCount === 0 ? 0 : completedCount < 3 ? 1 : completedCount < 5 ? 2 : 3;
            
            const box = document.createElement('div');
            box.className = 'heatmap-box level-' + level;
            box.title = dateStr + ': ' + completedCount + ' habitos';
            heatmapContainer.appendChild(box);
        }
    }
    filterHabits('all', document.querySelector('#view-habits .study-chip[data-filter="all"]'));
};


// ================================================================
// TASKS MODULE — Enhanced (Phase 4)
// ================================================================

let currentTaskId = null;
let taskKanbanMode = false;

window.toggleTaskKanban = function() {
    taskKanbanMode = !taskKanbanMode;
    const list = document.getElementById('tasks-list-view');
    const kanban = document.getElementById('tasks-kanban-view');
    const filters = document.querySelector('#view-tasks .habit-filters-scroll');
    if (list) list.style.display = taskKanbanMode ? 'none' : 'flex';
    if (kanban) kanban.style.display = taskKanbanMode ? 'flex' : 'none';
    if (filters) filters.style.display = taskKanbanMode ? 'none' : 'flex';
    if (taskKanbanMode) renderTaskKanban();
    else filterTasks(document.querySelector('#view-tasks .study-chip.active')?.dataset?.filter || 'all');
};

window.filterTasks = function(filter, btn) {
    if (btn) {
        document.querySelectorAll('#view-tasks .study-chip').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }
    
    if (taskKanbanMode) { renderTaskKanban(); return; }
    
    const container = document.getElementById('tasks-list-view');
    if(!container) return;
    
    let tasks = LocalDB.get('tasks').filter(t => !t.is_deleted);
    const today = new Date().toISOString().split('T')[0];
    
    if (filter === 'done') tasks = tasks.filter(t => t.done_at);
    else tasks = tasks.filter(t => !t.done_at);
    
    if (filter === 'today') tasks = tasks.filter(t => t.due_date === today);
    if (filter === 'high') tasks = tasks.filter(t => t.priority === 'high');
    
    tasks.sort((a,b) => {
        if (a.priority === 'high' && b.priority !== 'high') return -1;
        if (a.priority !== 'high' && b.priority === 'high') return 1;
        return (a.due_date||'9999').localeCompare(b.due_date||'9999');
    });
    
    if (tasks.length === 0) {
        container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;">Nenhuma tarefa encontrada.</div>';
        return;
    }
    
    container.innerHTML = tasks.map(t => {
        const isDone = !!t.done_at;
        const dueText = t.due_date ? '<i class="fa-regular fa-clock"></i> ' + new Date(t.due_date).toLocaleDateString('pt-BR') : '';
        const prioText = t.priority === 'high' ? '<span style="color:var(--accent-pink);font-weight:700;font-size:0.7rem">\uD83D\uDD25 ALTA</span>' : '';
        const subs = (t.subtasks || []).length;
        const subsDone = (t.subtasks || []).filter(s => s.done).length;
        const subText = subs > 0 ? `<span style="font-size:0.75rem;color:var(--text-secondary)"><i class="fa-solid fa-list-check"></i> ${subsDone}/${subs}</span>` : '';
        
        return `
        <div class="list-item glass ${isDone ? 'done' : ''}" style="cursor:pointer;opacity:${isDone?0.6:1}" onclick="openTaskDetail('${t.id}')">
            <div class="item-main">
                <div class="item-title" style="text-decoration:${isDone?'line-through':'none'}">${escapeHtml(t.name)}</div>
                <div class="item-subtitle" style="display:flex;gap:8px;align-items:center">
                    ${prioText}
                    ${subText}
                    ${dueText}
                </div>
            </div>
            <button class="icon-btn ${isDone ? 'done' : ''}" style="width:32px;height:32px;border:1px solid ${isDone?'var(--accent-green)':'var(--border-glass)'};color:${isDone?'var(--accent-green)':'white'}" onclick="event.stopPropagation(); toggleTaskDirect('${t.id}')">
                <i class="fa-solid ${isDone ? 'fa-check' : 'fa-minus'}"></i>
            </button>
        </div>`;
    }).join('');
}

function renderTaskKanban() {
    const tasks = LocalDB.get('tasks').filter(t => !t.is_deleted);
    const todo = tasks.filter(t => !t.done_at && t.status !== 'doing');
    const doing = tasks.filter(t => !t.done_at && t.status === 'doing');
    const done = tasks.filter(t => t.done_at);
    
    const renderCard = (t) => {
        const prioColor = t.priority === 'high' ? 'var(--accent-pink)' : t.priority === 'medium' ? '#f59e0b' : 'var(--text-secondary)';
        return `
        <div class="glass" style="padding:12px;border-radius:12px;cursor:pointer;border-left:3px solid ${prioColor}" onclick="openTaskDetail('${t.id}')">
            <div style="font-size:0.9rem;font-weight:600;margin-bottom:6px">${escapeHtml(t.name)}</div>
            ${t.due_date ? `<div style="font-size:0.7rem;color:var(--text-secondary)"><i class="fa-regular fa-clock"></i> ${new Date(t.due_date).toLocaleDateString('pt-BR')}</div>` : ''}
        </div>`;
    };
    
    const elTodo = document.getElementById('kanban-todo');
    const elDoing = document.getElementById('kanban-doing');
    const elDone = document.getElementById('kanban-done');
    
    if (elTodo) elTodo.innerHTML = todo.map(renderCard).join('') || '<div style="color:var(--text-secondary);font-size:0.8rem;text-align:center;padding:20px;border:1px dashed var(--border-glass);border-radius:8px">Vazio</div>';
    if (elDoing) elDoing.innerHTML = doing.map(renderCard).join('') || '<div style="color:var(--text-secondary);font-size:0.8rem;text-align:center;padding:20px;border:1px dashed var(--border-glass);border-radius:8px">Arraste tarefas para ca</div>';
    if (elDone) elDone.innerHTML = done.map(renderCard).join('') || '<div style="color:var(--text-secondary);font-size:0.8rem;text-align:center;padding:20px;border:1px dashed var(--border-glass);border-radius:8px">Vazio</div>';
}

window.openTaskDetail = function(taskId) {
    currentTaskId = taskId;
    const tasks = LocalDB.get('tasks');
    const t = tasks.find(x => x.id === taskId);
    if (!t) return;
    
    const modal = document.getElementById('task-detail-modal');
    if (document.getElementById('task-detail-name')) document.getElementById('task-detail-name').value = t.name || '';
    if (document.getElementById('task-detail-priority')) document.getElementById('task-detail-priority').value = t.priority || 'medium';
    if (document.getElementById('task-detail-due')) document.getElementById('task-detail-due').value = t.due_date || '';
    
    renderSubtasks(t.subtasks || []);
    
    if (modal) modal.style.display = 'flex';
};

window.closeTaskDetail = function() {
    const modal = document.getElementById('task-detail-modal');
    if (modal) modal.style.display = 'none';
    currentTaskId = null;
    if (taskKanbanMode) renderTaskKanban();
    else filterTasks(document.querySelector('#view-tasks .study-chip.active')?.dataset?.filter || 'all');
};

function renderSubtasks(subs) {
    const list = document.getElementById('task-subtasks-list');
    if (!list) return;
    list.innerHTML = subs.map((s, i) => `
        <div style="display:flex;align-items:center;gap:10px;background:rgba(255,255,255,0.04);padding:8px;border-radius:8px">
            <input type="checkbox" ${s.done ? 'checked' : ''} onchange="toggleSubtask(${i})" style="accent-color:var(--accent-primary)">
            <span style="flex:1;font-size:0.9rem;text-decoration:${s.done ? 'line-through' : 'none'};color:${s.done ? 'var(--text-secondary)' : 'white'}">${escapeHtml(s.name)}</span>
            <button onclick="removeSubtask(${i})" style="background:none;border:none;color:var(--text-secondary)"><i class="fa-solid fa-xmark"></i></button>
        </div>
    `).join('');
}

window.addSubtask = function() {
    const name = prompt('Nome da subtarefa:');
    if (!name || !currentTaskId) return;
    const tasks = LocalDB.get('tasks');
    const t = tasks.find(x => x.id === currentTaskId);
    if (t) {
        if (!t.subtasks) t.subtasks = [];
        t.subtasks.push({ name, done: false });
        LocalDB.set('tasks', tasks);
        renderSubtasks(t.subtasks);
    }
};

window.toggleSubtask = function(idx) {
    if (!currentTaskId) return;
    const tasks = LocalDB.get('tasks');
    const t = tasks.find(x => x.id === currentTaskId);
    if (t && t.subtasks && t.subtasks[idx]) {
        t.subtasks[idx].done = !t.subtasks[idx].done;
        LocalDB.set('tasks', tasks);
        renderSubtasks(t.subtasks);
    }
};

window.removeSubtask = function(idx) {
    if (!currentTaskId) return;
    const tasks = LocalDB.get('tasks');
    const t = tasks.find(x => x.id === currentTaskId);
    if (t && t.subtasks) {
        t.subtasks.splice(idx, 1);
        LocalDB.set('tasks', tasks);
        renderSubtasks(t.subtasks);
    }
};

window.saveTaskDetail = function() {
    if (!currentTaskId) return;
    const name = document.getElementById('task-detail-name')?.value;
    const prio = document.getElementById('task-detail-priority')?.value;
    const due = document.getElementById('task-detail-due')?.value;
    
    const tasks = LocalDB.get('tasks');
    const t = tasks.find(x => x.id === currentTaskId);
    if (t) {
        t.name = name;
        t.priority = prio;
        t.due_date = due;
        LocalDB.set('tasks', tasks);
    }
};

window.toggleTaskDirect = function(taskId) {
    const tasks = LocalDB.get('tasks');
    const t = tasks.find(x => x.id === taskId);
    if (t) {
        if (t.done_at) t.done_at = null;
        else {
            t.done_at = new Date().toISOString();
            awardXP(10, 'Tarefa concluida');
        }
        LocalDB.set('tasks', tasks);
        if (taskKanbanMode) renderTaskKanban();
        else filterTasks(document.querySelector('#view-tasks .study-chip.active')?.dataset?.filter || 'all');
        loadXPPanel();
    }
};

window.deleteCurrentTask = function() {
    if (!currentTaskId) return;
    if (!confirm('Excluir esta tarefa?')) return;
    const tasks = LocalDB.get('tasks');
    const t = tasks.find(x => String(x.id) === String(currentTaskId));
    if (t) {
        t.is_deleted = 1;
        LocalDB.set('tasks', tasks);
        if (typeof syncTaskReminders === 'function') syncTaskReminders();
        if (typeof backgroundSync === 'function') backgroundSync();
        closeTaskDetail();
        loadTasks();
        loadXPPanel();
    }
};

// Override original loadTasks to use our new view
window.loadTasks = function() {
    if (taskKanbanMode) renderTaskKanban();
    else filterTasks('all', document.querySelector('#view-tasks .study-chip[data-filter="all"]'));
};


// ================================================================
// ROUTINES MODULE (Phase 7)
// ================================================================

window.loadRoutines = function() {
    const list = document.getElementById('routines-list');
    if (!list) return;
    const routines = LocalDB.get('routines') || [];
    
    if (routines.length === 0) {
        list.innerHTML = '<div style="text-align:center;color:var(--text-secondary);padding:30px">Voce nao tem rotinas criadas.<br><br><button onclick="createDefaultRoutines()" style="background:var(--accent-primary);color:white;border:none;padding:10px 20px;border-radius:10px;font-weight:700">Criar Rotinas Padrao</button></div>';
        return;
    }
    
    list.innerHTML = routines.map(r => `
        <div class="list-item glass" style="cursor:pointer" onclick="openRoutineRunner('${r.id}')">
            <div class="item-main">
                <div class="item-title">${escapeHtml(r.name)}</div>
                <div class="item-subtitle"><i class="fa-regular fa-clock"></i> ${r.time || 'Sem horario'} \u2022 ${(r.steps || []).length} passos</div>
            </div>
            <button class="icon-btn" style="background:var(--accent-primary);color:white;width:40px;height:40px;font-size:1rem">
                <i class="fa-solid fa-play"></i>
            </button>
        </div>
    `).join('');
};

window.createDefaultRoutines = function() {
    const routines = LocalDB.get('routines') || [];
    routines.push({
        id: Date.now().toString() + '1', name: 'Rotina Matinal', time: '07:00',
        steps: [{name:'Beber agua', done:false}, {name:'Arrumar a cama', done:false}, {name:'Meditar 10min', done:false}, {name:'Ler 10 pags', done:false}]
    });
    routines.push({
        id: Date.now().toString() + '2', name: 'Rotina Noturna', time: '22:00',
        steps: [{name:'Largar celular', done:false}, {name:'Skincare', done:false}, {name:'Ler ficcao', done:false}, {name:'Dormir', done:false}]
    });
    LocalDB.set('routines', routines);
    loadRoutines();
    showInAppNotification('Rotinas padrao criadas!', 'success');
};

window.openNewRoutine = function() {
    const name = prompt('Nome da Rotina:');
    if (!name) return;
    const time = prompt('Horario de alerta (ex: 08:00):') || '';
    const routines = LocalDB.get('routines') || [];
    routines.push({ id: Date.now().toString(), name, time, steps: [] });
    LocalDB.set('routines', routines);
    loadRoutines();
    showInAppNotification('Rotina criada. Adicione passos na visualizacao!', 'success');
};

let currentRoutineId = null;

window.openRoutineRunner = function(id) {
    currentRoutineId = id;
    const routines = LocalDB.get('routines');
    const r = routines.find(x => x.id === id);
    if (!r) return;
    
    const modal = document.getElementById('routine-runner-modal');
    if (document.getElementById('runner-title')) document.getElementById('runner-title').textContent = r.name;
    
    // Reset steps
    r.steps = r.steps || [];
    r.steps.forEach(s => s.done = false);
    LocalDB.set('routines', routines);
    
    renderRoutineSteps(r.steps);
    if (modal) modal.style.display = 'flex';
};

window.closeRoutineRunner = function() {
    const modal = document.getElementById('routine-runner-modal');
    if (modal) modal.style.display = 'none';
    currentRoutineId = null;
    loadRoutines();
};

function renderRoutineSteps(steps) {
    const list = document.getElementById('runner-steps');
    if (!list) return;
    list.innerHTML = steps.map((s, i) => `
        <div class="glass" style="display:flex;align-items:center;gap:15px;padding:16px;border-radius:14px;border:1px solid ${s.done ? 'var(--accent-green)' : 'var(--border-glass)'};background:${s.done ? 'rgba(0,210,121,0.1)' : 'var(--bg-glass)'}" onclick="toggleRoutineStep(${i})">
            <div style="width:24px;height:24px;border-radius:12px;border:2px solid ${s.done ? 'var(--accent-green)' : 'var(--text-secondary)'};display:flex;align-items:center;justify-content:center;color:var(--accent-green)">
                ${s.done ? '<i class="fa-solid fa-check" style="font-size:0.8rem"></i>' : ''}
            </div>
            <span style="flex:1;font-size:1.1rem;font-weight:600;text-decoration:${s.done ? 'line-through' : 'none'};color:${s.done ? 'var(--text-secondary)' : 'white'}">${escapeHtml(s.name)}</span>
        </div>
    `).join('') + `
        <button onclick="addRoutineStep()" style="background:rgba(255,255,255,0.05);border:1px dashed var(--text-secondary);color:var(--text-secondary);padding:14px;border-radius:14px;font-weight:700;margin-top:10px">+ Novo Passo</button>
    `;
}

window.toggleRoutineStep = function(idx) {
    if (!currentRoutineId) return;
    const routines = LocalDB.get('routines');
    const r = routines.find(x => x.id === currentRoutineId);
    if (r && r.steps[idx]) {
        r.steps[idx].done = !r.steps[idx].done;
        LocalDB.set('routines', routines);
        renderRoutineSteps(r.steps);
        if (navigator.vibrate) navigator.vibrate(50);
    }
};

window.addRoutineStep = function() {
    if (!currentRoutineId) return;
    const name = prompt('Nome do passo:');
    if (!name) return;
    const routines = LocalDB.get('routines');
    const r = routines.find(x => x.id === currentRoutineId);
    if (r) {
        r.steps.push({ name, done: false });
        LocalDB.set('routines', routines);
        renderRoutineSteps(r.steps);
    }
};

window.finishRoutine = function() {
    if (!currentRoutineId) return;
    const routines = LocalDB.get('routines');
    const r = routines.find(x => x.id === currentRoutineId);
    if (r) {
        const total = r.steps.length;
        const done = r.steps.filter(s => s.done).length;
        if (done === total && total > 0) {
            awardXP(30, 'Rotina ' + r.name + ' completa');
            showInAppNotification('Rotina Completa! +30 XP', 'success');
        } else {
            showInAppNotification('Rotina finalizada parcialmente.', 'info');
        }
    }
    closeRoutineRunner();
};

// ================================================================
// AMOLED THEME (Phase 8)
// ================================================================

window.toggleAmoled = function() {
    const cb = document.getElementById('toggle-amoled');
    if (cb && cb.checked) {
        document.body.classList.add('theme-amoled');
        LocalDB.set('amoled_enabled', true);
        localStorage.setItem('nexus_amoled', '1');
    } else {
        document.body.classList.remove('theme-amoled');
        LocalDB.set('amoled_enabled', false);
        localStorage.removeItem('nexus_amoled');
    }
};

// Hook into initTheme to apply AMOLED on boot
const _origInitTheme = window.initTheme;
window.initTheme = function() {
    if (_origInitTheme) _origInitTheme();
    if (LocalDB.get('amoled_enabled')) {
        document.body.classList.add('theme-amoled');
        const cb = document.getElementById('toggle-amoled');
        if (cb) cb.checked = true;
    }
};


document.addEventListener('DOMContentLoaded', () => {
    ensureDefaultRewards();
    initAppPreferences();
    loadUserStats();
    loadHabits();
    loadTodayDashboard();
    if (typeof ensureModuleNavVisible === 'function') ensureModuleNavVisible();
    applyUiPrefs();
    bindMobileNavItems();
    updateJarvisFabState();
    updateNetworkSettingsUI();
    updateSyncIndicator(isNetworkOnline() && window.nexusSupabase ? 'synced' : 'offline');
    if (window.NexusAudio && typeof window.NexusAudio.initSettingsUI === 'function') window.NexusAudio.initSettingsUI();

    setTimeout(requestNotificationPermission, 2000);
    setTimeout(backgroundSync, 1000);
    setupRealtime();
    startSyncInterval();

    setTimeout(() => {
        const active = document.querySelector('.view.active-view');
        if (active && typeof refreshViewContent === 'function') refreshViewContent(active.id);
    }, 100);
});

// ----------------------------------------------------
// UI Preferences & Module Toggling
// ----------------------------------------------------
window.openSettingsView = function() {
    if (typeof closeSettingsModal === 'function') closeSettingsModal();
    document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
    document.querySelectorAll('.view').forEach(view => view.classList.remove('active-view'));
    const view = document.getElementById('view-settings');
    if (view) view.classList.add('active-view');
    updateNetworkSettingsUI();
    initAppPreferences();
    if (typeof updateSettingsUI === 'function') updateSettingsUI();
    const stats = typeof getNativeStorageStatsSync === 'function' ? getNativeStorageStatsSync() : null;
    if (stats && stats.cacheBytes != null && typeof updateStorageWarningBadge === 'function') {
        updateStorageWarningBadge(stats.cacheBytes);
    }
};

window.openSettingsModal = () => {
    const modal = document.getElementById('settings-modal');
    if (modal) modal.classList.add('show');
};

window.closeSettingsModal = () => {
    document.getElementById('settings-modal').classList.remove('show');
};

window.toggleModule = (moduleId) => {
    const isChecked = document.getElementById('toggle-' + moduleId).checked;
    const prefs = JSON.parse(localStorage.getItem('nexus_ui_prefs') || '{}');
    prefs[moduleId] = isChecked;
    localStorage.setItem('nexus_ui_prefs', JSON.stringify(prefs));
    applyUiPrefs();
};

function applyUiPrefs() {
    let prefs = {};
    try {
        prefs = JSON.parse(localStorage.getItem('nexus_ui_prefs')) || {};
    } catch(e) {}
    const modules = ['habits', 'finance', 'tasks', 'videos', 'shop', 'iot', 'studies', 'goals', 'fitness', 'journal', 'routines', 'alarms', 'cleaner'];
    
    modules.forEach(mod => {
        const isEnabled = prefs[mod] !== false;
        const cb = document.getElementById('toggle-' + mod);
        if (cb) cb.checked = isEnabled;
        const navItem = document.querySelector(`.nav-item[data-target="view-${mod}"]`);
        if (navItem) {
            navItem.style.display = isEnabled ? 'flex' : 'none';
        }
    });
    if (typeof applyModuleOrderAndVisibility === 'function') applyModuleOrderAndVisibility();
}

// Call applyUiPrefs on boot



// ================================================================
// RICH TEXT EDITOR — Notion-Style v2
// ================================================================

let _jarvisMode = 'summarize_text';
let _jarvisLastResult = '';
let _savedSelectionRange = null;

// ─── Core Rich Commands ──────────────────────────────────────────

function richCmd(cmd, value) {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    document.execCommand(cmd, false, value || null);
    updateToolbarState();
}

function richHeading(level) {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    if (level === 0) {
        document.execCommand('formatBlock', false, 'p');
    } else {
        document.execCommand('formatBlock', false, `h${level}`);
    }
}

function richInsertChecklist() {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    const item = document.createElement('div');
    item.className = 'rich-check-item';
    item.contentEditable = 'false';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.onchange = function() {
        span.style.textDecoration = cb.checked ? 'line-through' : 'none';
        span.style.opacity = cb.checked ? '0.5' : '1';
        saveNoteDebounced();
    };
    const span = document.createElement('span');
    span.contentEditable = 'true';
    span.textContent = '';
    span.style.flex = '1';
    span.style.outline = 'none';
    item.appendChild(cb);
    item.appendChild(span);
    insertNodeAtCursor(item);
    // Add a blank line after
    const br = document.createElement('p');
    br.innerHTML = '<br>';
    item.after(br);
    // Focus the span
    const sel = window.getSelection();
    const range = document.createRange();
    range.setStart(span, 0);
    range.collapse(true);
    sel.removeAllRanges();
    sel.addRange(range);
}

function richInsertDivider() {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    document.execCommand('insertHTML', false, '<hr><p><br></p>');
}

function richInsertCode() {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    document.execCommand('insertHTML', false, '<pre><code>// código aqui</code></pre><p><br></p>');
}

function richInsertQuote() {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    document.execCommand('formatBlock', false, 'blockquote');
}

function richInsertLink() {
    const url = prompt('URL do link:');
    if (!url) return;
    const text = prompt('Texto do link:', url);
    if (text === null) return;
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    document.execCommand('insertHTML', false, `<a href="${url}" target="_blank" rel="noopener">${text || url}</a>&nbsp;`);
}

function insertNodeAtCursor(node) {
    const sel = window.getSelection();
    if (!sel.rangeCount) return;
    const range = sel.getRangeAt(0);
    range.deleteContents();
    range.insertNode(node);
    range.setStartAfter(node);
    range.collapse(true);
    sel.removeAllRanges();
    sel.addRange(range);
}

// ─── Color Picker ────────────────────────────────────────────────

function toggleColorPicker(e) {
    e.stopPropagation();
    const popup = document.getElementById('color-picker-popup');
    if (!popup) return;
    if (popup.style.display === 'none' || !popup.style.display) {
        const rect = e.currentTarget.getBoundingClientRect();
        popup.style.display = 'block';
        popup.style.left = Math.min(rect.left, window.innerWidth - 180) + 'px';
        popup.style.top = (rect.bottom + 6) + 'px';
        // Save selection before click hides it
        const sel = window.getSelection();
        if (sel && sel.rangeCount) _savedSelectionRange = sel.getRangeAt(0).cloneRange();
    } else {
        popup.style.display = 'none';
    }
}

function applyTextColor(color) {
    const popup = document.getElementById('color-picker-popup');
    if (popup) popup.style.display = 'none';
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    // Restore saved selection
    if (_savedSelectionRange) {
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(_savedSelectionRange);
        _savedSelectionRange = null;
    }
    if (!color) {
        document.execCommand('removeFormat', false, null);
    } else {
        document.execCommand('foreColor', false, color);
    }
    // Update indicator
    const ind = document.getElementById('color-indicator');
    if (ind) ind.style.background = color || '#fff';
}

document.addEventListener('click', function(e) {
    const popup = document.getElementById('color-picker-popup');
    const btn = document.getElementById('color-picker-btn');
    if (popup && btn && !btn.contains(e.target) && !popup.contains(e.target)) {
        popup.style.display = 'none';
    }
});

// ─── Slash Menu ──────────────────────────────────────────────────

let _slashRange = null;
let _slashStartOffset = 0;

function openSlashMenu() {
    const editor = document.getElementById('note-content-rich');
    const menu = document.getElementById('slash-menu');
    if (!menu || !editor) return;
    // Position at center bottom of editor
    const rect = editor.getBoundingClientRect();
    menu.style.display = 'block';
    const menuWidth = 260;
    const left = Math.min(rect.left + 16, window.innerWidth - menuWidth - 8);
    menu.style.left = left + 'px';
    menu.style.top = (rect.top + 80) + 'px';
    // Trap outside clicks
    setTimeout(() => {
        document.addEventListener('click', closeSlashMenuOnClickOutside, { once: true });
    }, 50);
}

function closeSlashMenuOnClickOutside(e) {
    const menu = document.getElementById('slash-menu');
    if (menu && !menu.contains(e.target)) closeSlashMenu();
}

function closeSlashMenu() {
    const menu = document.getElementById('slash-menu');
    if (menu) menu.style.display = 'none';
    // Remove leftover '/' trigger character if present
    if (_slashRange) {
        try {
            _slashRange.deleteContents();
        } catch(e) {}
        _slashRange = null;
    }
}

// Keyboard listener on the rich editor for '/' trigger
function initRichEditorKeyListeners() {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;

    editor.addEventListener('keyup', function(e) {
        if (e.key === '/') {
            const sel = window.getSelection();
            if (!sel.rangeCount) return;
            const range = sel.getRangeAt(0).cloneRange();
            // Walk back 1 char to select the '/'
            range.setStart(range.endContainer, Math.max(0, range.endOffset - 1));
            _slashRange = range;
            openSlashMenu();
        }
        if (e.key === 'Escape') closeSlashMenu();
        updateToolbarState();
    });

    editor.addEventListener('input', function() {
        saveNoteDebounced();
        updateToolbarState();
    });

    editor.addEventListener('paste', handleNoteEditorPaste);

    // Prevent default tab behaviour
    editor.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            e.preventDefault();
            document.execCommand('insertHTML', false, '&nbsp;&nbsp;&nbsp;&nbsp;');
        }
    });
}

// ─── YouTube Embed ───────────────────────────────────────────────

function openYouTubeModal() {
    const modal = document.getElementById('yt-modal');
    if (modal) {
        modal.style.display = 'flex';
        const inp = document.getElementById('yt-url-input');
        if (inp) { inp.value = ''; setTimeout(() => inp.focus(), 100); }
    }
}

function closeYouTubeModal() {
    const modal = document.getElementById('yt-modal');
    if (modal) modal.style.display = 'none';
}

function getYouTubeEmbedOrigin() {
    const origin = window.location.origin;
    if (origin && origin !== 'null' && origin.startsWith('https://')) {
        return origin;
    }
    return null;
}

function getYouTubeEmbedSrc(videoId) {
    const origin = getYouTubeEmbedOrigin();
    if (origin) {
        const params = new URLSearchParams({
            rel: '0',
            playsinline: '1',
            origin: origin,
        });
        return `https://www.youtube-nocookie.com/embed/${videoId}?${params.toString()}`;
    }
    const remotePlayerUrl = 'https://mariagilda402-rgb.github.io/Project-AI/mobile/youtube-player.html';
    const configuredPlayerUrl = window.NEXUS_YOUTUBE_PLAYER_BASE;
    const playerBaseUrl = configuredPlayerUrl || remotePlayerUrl;
    return `${playerBaseUrl}?video=${encodeURIComponent(videoId)}`;
}

function insertYouTubeEmbed() {
    const raw = document.getElementById('yt-url-input')?.value?.trim();
    if (!raw) return;
    const ids = extractAllYouTubeIds(raw);
    if (!ids.length) {
        const single = extractYouTubeId(raw);
        if (single) ids.push(single);
    }
    if (!ids.length) {
        alert('URL do YouTube inválida!');
        return;
    }
    closeYouTubeModal();
    insertYouTubeEmbedsAtCursor(ids);
}

function extractAllYouTubeIds(text) {
    const compact = String(text || '').replace(/[\r\n\t]+/g, ' ').replace(/\s+/g, ' ');
    const patterns = [
        /(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})/gi,
        /(?:https?:\/\/)?youtu\.be\/([a-zA-Z0-9_-]{11})/gi,
        /(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/gi,
        /(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})/gi,
    ];
    const ids = [];
    patterns.forEach(p => {
        let m;
        while ((m = p.exec(compact)) !== null) {
            if (!ids.includes(m[1])) ids.push(m[1]);
        }
    });
    return ids;
}

function buildYouTubeEmbedHtml(videoId) {
    const embedSrc = getYouTubeEmbedSrc(videoId);
    return `<div class="yt-embed-block" contenteditable="false">
        <iframe
            src="${embedSrc}"
            title="YouTube video player"
            loading="lazy"
            referrerpolicy="strict-origin-when-cross-origin"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen></iframe>
    </div><p><br></p>`;
}

function insertYouTubeEmbedsAtCursor(videoIds) {
    const editor = document.getElementById('note-content-rich');
    if (!editor || !videoIds.length) return;
    editor.focus();
    const html = videoIds.map(id => buildYouTubeEmbedHtml(id)).join('');
    document.execCommand('insertHTML', false, html);
    if (typeof saveNoteDebounced === 'function') saveNoteDebounced();
}

function handleNoteEditorPaste(e) {
    const text = e.clipboardData?.getData('text/plain') || '';
    const ids = extractAllYouTubeIds(text);
    if (!ids.length) return;
    e.preventDefault();
    insertYouTubeEmbedsAtCursor(ids);
}

function extractYouTubeId(url) {
    const compact = String(url || '').replace(/\s+/g, '');
    const patterns = [
        /(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})/,
        /(?:youtu\.be\/)([a-zA-Z0-9_-]{11})/,
        /(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
        /(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})/,
    ];
    for (const p of patterns) {
        const m = compact.match(p);
        if (m) return m[1];
    }
    return null;
}

// ─── Image Picker ────────────────────────────────────────────────

function openImagePicker() {
    const inp = document.getElementById('note-image-input');
    if (inp) inp.click();
}

function handleImageFile(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
        alert('Imagem muito grande (máx 2MB). Redimensione antes de inserir.');
        return;
    }
    const reader = new FileReader();
    reader.onload = function(e) {
        const editor = document.getElementById('note-content-rich');
        if (!editor) return;
        editor.focus();
        document.execCommand('insertHTML', false,
            `<img src="${e.target.result}" class="rich-image-block" alt="imagem"><p><br></p>`);
        saveNoteDebounced();
    };
    reader.readAsDataURL(file);
    // Reset input so same file can be picked again
    event.target.value = '';
}

// ─── Note Link Picker ────────────────────────────────────────────

function richInsertNoteLink() {
    const modal = document.getElementById('note-link-modal');
    if (!modal) return;
    modal.style.display = 'flex';
    // Populate list
    const search = document.getElementById('note-link-search');
    if (search) { search.value = ''; }
    filterNoteLinkList('');
}

function closeNoteLinkModal() {
    const modal = document.getElementById('note-link-modal');
    if (modal) modal.style.display = 'none';
}

function filterNoteLinkList(query) {
    const container = document.getElementById('note-link-list');
    if (!container) return;
    const notes = LocalDB.getAll('notes') || [];
    const filtered = query
        ? notes.filter(n => (n.title || '').toLowerCase().includes(query.toLowerCase()))
        : notes;
    container.innerHTML = '';
    if (!filtered.length) {
        container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);padding:20px;font-size:0.9rem">Nenhuma nota encontrada</div>';
        return;
    }
    filtered.forEach(note => {
        const el = document.createElement('div');
        el.className = 'slash-item';
        el.innerHTML = `<span class="slash-icon">📎</span><div><b>${note.title || 'Sem título'}</b><div style="font-size:0.75rem;color:var(--text-secondary)">${note.subject || note.tags || ''}</div></div>`;
        el.onclick = () => {
            const editor = document.getElementById('note-content-rich');
            if (editor) {
                editor.focus();
                document.execCommand('insertHTML', false,
                    `<a class="note-link-block" onclick="openNoteById('${note.id}')" href="#" data-note-id="${note.id}">📎 ${note.title || 'Nota'}</a>&nbsp;`);
            }
            closeNoteLinkModal();
        };
        container.appendChild(el);
    });
}

function openNoteById(id) {
    const notes = LocalDB.getAll('notes') || [];
    const note = notes.find(n => n.id === id);
    if (note) openNoteEditor(note, note.notebookId || null);
}

// ─── Toolbar State ───────────────────────────────────────────────

function updateToolbarState() {
    const btns = document.querySelectorAll('.rt-btn');
    btns.forEach(btn => btn.classList.remove('active'));
}

// ─── Jarvis AI Panel ─────────────────────────────────────────────

function openJarvisPanel(mode) {
    if (!requireWifiForJarvis('IA nas notas')) return;
    const panel = document.getElementById('jarvis-panel');
    if (!panel) return;
    panel.style.display = 'flex';
    if (mode) setJarvisMode(mode, null);
    // Pre-fill with selected text if summarizing
    if (_jarvisMode === 'summarize_text') {
        const editor = document.getElementById('note-content-rich');
        const sel = window.getSelection();
        if (sel && sel.toString().trim()) {
            const prompt = document.getElementById('jarvis-prompt');
            if (prompt) prompt.value = sel.toString().trim();
        }
    }
    // Reset result
    document.getElementById('jarvis-result').style.display = 'none';
    document.getElementById('jarvis-loading').style.display = 'none';
    document.getElementById('jarvis-input-area').style.display = 'block';
}

function closeJarvisPanel() {
    const panel = document.getElementById('jarvis-panel');
    if (panel) panel.style.display = 'none';
}

function setJarvisMode(mode, btn) {
    _jarvisMode = mode;
    document.querySelectorAll('.jarvis-tab').forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');
    // Update placeholder
    const prompt = document.getElementById('jarvis-prompt');
    if (!prompt) return;
    const placeholders = {
        summarize_text: 'Cole ou escreva o texto para resumir...',
        summarize_video: 'Cole a URL do vídeo do YouTube aqui...',
        deep_search: 'Qual assunto você quer pesquisar na web?',
        generate_image: 'Descreva a imagem que quer gerar...',
        expand_text: 'Cole o texto para expandir/detalhar...',
        translate: 'Cole o texto para traduzir para Português...',
    };
    prompt.placeholder = placeholders[mode] || 'Digite o prompt...';
    prompt.value = '';
    document.getElementById('jarvis-result').style.display = 'none';
}

async function runJarvisAction() {
    const prompt = document.getElementById('jarvis-prompt')?.value?.trim();
    if (!prompt) {
        alert('Por favor, insira um texto ou URL.');
        return;
    }
    if (!requireWifiForJarvis('IA nas notas')) {
        return;
    }
    document.getElementById('jarvis-input-area').style.display = 'none';
    document.getElementById('jarvis-loading').style.display = 'block';
    document.getElementById('jarvis-result').style.display = 'none';

    try {
        let result = '';
        // Try calling backend Jarvis API
        const payload = { action: _jarvisMode, content: prompt };

        if (_jarvisMode === 'summarize_video') {
            payload.youtube_url = prompt;
        }

        let apiResponse = null;
        if (window.nexusSupabase && typeof window.nexusSupabase.functions?.invoke === 'function') {
            try {
                const { data, error } = await window.nexusSupabase.functions.invoke('jarvis-note-action', {
                    body: payload
                });
                if (!error && data?.result) {
                    result = data.result;
                    apiResponse = data;
                } else if (error) {
                    console.warn('jarvis-note-action:', error);
                }
            } catch (fnErr) {
                console.warn('jarvis-note-action invoke:', fnErr);
            }
        }
        if (!result) {
            try {
                const res = await fetch('/api/nexus/jarvis/note-action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                    signal: AbortSignal.timeout(30000)
                });
                if (res.ok) {
                    const data = await res.json();
                    result = data.result || data.text || JSON.stringify(data);
                    apiResponse = data;
                }
            } catch (fetchErr) {
                console.warn('desktop jarvis API:', fetchErr);
            }
        }
        if (!result) {
            result = jarvisSimulate(_jarvisMode, prompt);
        }

        _jarvisLastResult = result;
        _jarvisLastApiResponse = apiResponse;

        document.getElementById('jarvis-loading').style.display = 'none';
        document.getElementById('jarvis-result').style.display = 'block';
        document.getElementById('jarvis-result-text').innerHTML =
            _jarvisMode === 'generate_image' && apiResponse?.image_url
                ? `<img src="${apiResponse.image_url}" style="max-width:100%;border-radius:10px">`
                : escapeHtmlLight(result).replace(/\n/g, '<br>');
        document.getElementById('jarvis-input-area').style.display = 'block';

    } catch(e) {
        document.getElementById('jarvis-loading').style.display = 'none';
        document.getElementById('jarvis-input-area').style.display = 'block';
        alert('Erro ao processar com Jarvis: ' + e.message);
    }
}

function jarvisSimulate(mode, content) {
    const simulations = {
        summarize_text: `📋 **Resumo do Texto:**\n\n${content.slice(0, 200)}...\n\n**Pontos principais:**\n• Conteúdo relevante identificado\n• Informações estruturadas\n• Pronto para revisão\n\n_[Conecte o backend Jarvis para resumos reais]_`,
        summarize_video: `🎬 **Resumo do Vídeo YouTube:**\n\nURL: ${content}\n\n**Tópicos do vídeo:**\n1. Introdução ao assunto\n2. Desenvolvimento dos conceitos\n3. Conclusões e insights\n\n_[Conecte o backend para transcrições reais]_`,
        deep_search: `🔍 **Pesquisa Web: "${content}"**\n\n**Fontes consultadas:**\n• Wikipedia, artigos acadêmicos e blogs especializados\n\n**Resumo:**\n${content} é um tema que abrange diversas perspectivas. Conecte o Jarvis ao backend para resultados reais da web.\n\n_[Backend necessário para pesquisa real]_`,
        generate_image: `✨ Imagem gerada para: "${content}"\n\n_[Conecte o backend Gemini para gerar imagens reais]_`,
        expand_text: `📝 **Texto Expandido:**\n\n${content}\n\nPara elaborar ainda mais este conteúdo, considere aprofundar cada ponto com exemplos práticos, dados e referências relevantes ao contexto estudado.\n\n_[Backend necessário para expansão avançada]_`,
        translate: `🌐 **Tradução para Português:**\n\n${content}\n\n_[Backend necessário para tradução real]_`,
    };
    return simulations[mode] || 'Resultado simulado. Conecte o backend Jarvis.';
}

function escapeHtmlLight(text) {
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function insertJarvisResult() {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();

    // Check if it's an image response
    if (_jarvisLastApiResponse?.image_url) {
        document.execCommand('insertHTML', false,
            `<img src="${_jarvisLastApiResponse.image_url}" class="rich-image-block ai-image-block" alt="Imagem gerada por IA">
            <p class="ai-image-label">✨ Gerado pelo Gemini</p><p><br></p>`);
    } else {
        // Insert as formatted quote block
        const formatted = `<blockquote><strong>🤖 Jarvis:</strong><br>${escapeHtmlLight(_jarvisLastResult).replace(/\n/g, '<br>')}</blockquote><p><br></p>`;
        document.execCommand('insertHTML', false, formatted);
    }
    closeJarvisPanel();
    saveNoteDebounced();
}

function copyJarvisResult() {
    if (!_jarvisLastResult) return;
    navigator.clipboard.writeText(_jarvisLastResult).then(() => {
        showToast('Copiado para a área de transferência!');
    });
}

let _jarvisLastApiResponse = null;

// ─── Save & Load (Rich Editor) ───────────────────────────────────

let _saveNoteTimeout = null;
function saveNoteDebounced() {
    clearTimeout(_saveNoteTimeout);
    _saveNoteTimeout = setTimeout(() => {
        const editor = document.getElementById('note-content-rich');
        const hidden = document.getElementById('note-content');
        if (editor && hidden) {
            hidden.value = editor.innerHTML;
        }
    }, 1000);
}

// Override saveNote to grab from rich editor
const _origSaveNote = window.saveNote;
window.saveNote = function() {
    const editor = document.getElementById('note-content-rich');
    const hidden = document.getElementById('note-content');
    if (editor && hidden) {
        hidden.value = editor.innerHTML;
    }
    if (typeof _origSaveNote === 'function') _origSaveNote();
};

// ─── openNoteEditor override — populate rich editor ──────────────

const _origOpenNoteEditor = window.openNoteEditor;
window.openNoteEditor = function(note, notebookId) {
    // Call original
    if (typeof _origOpenNoteEditor === 'function') _origOpenNoteEditor(note, notebookId);

    // Now populate rich editor
    setTimeout(() => {
        const editor = document.getElementById('note-content-rich');
        const hidden = document.getElementById('note-content');
        if (!editor) return;

        let content = '';
        if (hidden) content = hidden.value || '';

        // If content looks like plain markdown (no HTML tags), convert it
        if (content && !content.includes('<') && content.includes('\n')) {
            content = markdownToHtml(content);
        }

        editor.innerHTML = content || '';
        initRichEditorKeyListeners();
    }, 80);
};

// ─── Basic Markdown → HTML converter (for legacy notes) ─────────

function markdownToHtml(md) {
    if (!md) return '';
    let html = md
        // Headings
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        // Bold / italic
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Code
        .replace(/`(.+?)`/g, '<code>$1</code>')
        // Blockquote
        .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
        // HR
        .replace(/^---$/gm, '<hr>')
        // Checklist
        .replace(/^- \[x\] (.+)$/gm, '<div class="rich-check-item"><input type="checkbox" checked onchange="this.nextSibling.style.textDecoration=this.checked?\'line-through\':\'none\'"><span style="flex:1;text-decoration:line-through;opacity:0.5">$1</span></div>')
        .replace(/^- \[ \] (.+)$/gm, '<div class="rich-check-item"><input type="checkbox" onchange="this.nextSibling.style.textDecoration=this.checked?\'line-through\':\'none\'"><span style="flex:1">$1</span></div>')
        // Unordered list
        .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
        // Numbered list
        .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
        // Paragraphs
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    // Wrap loose <li> in <ul>
    html = html.replace(/(<li>.*?<\/li>)+/gs, '<ul>$&</ul>');
    return `<p>${html}</p>`;
}

// ─── Init on DOMContentLoaded ────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // Close modals on backdrop click
    const ytModal = document.getElementById('yt-modal');
    if (ytModal) ytModal.addEventListener('click', function(e) {
        if (e.target === ytModal) closeYouTubeModal();
    });

    const jarvisPanel = document.getElementById('jarvis-panel');
    if (jarvisPanel) jarvisPanel.addEventListener('click', function(e) {
        if (e.target === jarvisPanel) closeJarvisPanel();
    });

    const noteLinkModal = document.getElementById('note-link-modal');
    if (noteLinkModal) noteLinkModal.addEventListener('click', function(e) {
        if (e.target === noteLinkModal) closeNoteLinkModal();
    });

    // Init if editor view is open
    const editorView = document.getElementById('note-editor-view');
    if (editorView && editorView.style.display !== 'none') {
        initRichEditorKeyListeners();
    }
});


document.addEventListener('DOMContentLoaded', () => {
    applyUiPrefs();
});

// ----------------------------------------------------
// Quick Add Logic (FAB)
// ----------------------------------------------------
window.openCreateModal = () => {
    document.getElementById('create-title').value = '';
    document.getElementById('create-desc').value = '';
    document.getElementById('create-time').value = '08:00';
    document.getElementById('create-modal').classList.add('show');
};

window.closeCreateModal = () => {
    document.getElementById('create-modal').classList.remove('show');
};

document.getElementById('create-type').addEventListener('change', (e) => {
    const opts = document.getElementById('habit-options');
    opts.style.display = e.target.value === 'habit' ? 'flex' : 'none';
});

window.saveQuickAdd = () => {
    const type = document.getElementById('create-type').value;
    const title = document.getElementById('create-title').value.trim();
    if (!title) {
        alert('O título é obrigatório.');
        return;
    }

    if (type === 'task') {
        const newTask = {
            id: Date.now(),
            title: title,
            completed: 0,
            points_reward: 10,
            created_at: new Date().toISOString()
        };
        LocalDB.upsert('tasks', newTask);
        loadTasks();
        sendLocalNotification('Tarefa Criada', 'Sua nova tarefa foi salva offline.');
    } else {
        const time = document.getElementById('create-time').value;
        const desc = document.getElementById('create-desc').value;
        const newHabit = {
            id: Date.now(),
            name: title,
            description: desc,
            active: 1,
            target_time: time,
            current_streak: 0,
            xp_reward: 50,
            created_at: new Date().toISOString()
        };
        LocalDB.upsert('habits', newHabit);
        loadHabits();
        sendLocalNotification('Hábito Criado', 'Seu novo hábito foi salvo offline.');
    }

    closeCreateModal();
    backgroundSync();
};

// ----------------------------------------------------
// Pomodoro Timer Logic
// ----------------------------------------------------
let pomoInterval = null;
let pomoTimeLeft = 25 * 60; // 25 minutes in seconds
let pomoActive = false;

function formatPomoTime(secs) {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return m + ":" + s;
}

window.startPomodoro = () => {
    if (typeof startPomodoro === 'function' && document.getElementById('pomo-time')) {
        startPomodoro();
        return;
    }
    if (pomoActive) return;
    pomoActive = true;
    playBeep(400, 100);
    pomoInterval = setInterval(() => {
        if (pomoTimeLeft > 0) {
            pomoTimeLeft--;
            const el = document.getElementById('pomodoro-timer');
            if (el) el.innerText = formatPomoTime(pomoTimeLeft);
        } else {
            clearInterval(pomoInterval);
            pomoActive = false;
            LocalDB.upsert('pomo_sessions', {
                id: Date.now(),
                type: 'focus',
                duration_minutes: 25,
                session_date: new Date().toISOString().split('T')[0]
            });
            awardXP(20, 'Sessao Pomodoro completa');
            sendLocalNotification('Foco Concluido!', 'Voce ganhou +20 XP por 25 minutos de estudo.');
            playBeep(800, 500);
            pomoTimeLeft = 25 * 60;
            const el = document.getElementById('pomodoro-timer');
            if (el) el.innerText = formatPomoTime(pomoTimeLeft);
        }
    }, 1000);
};

window.pausePomodoro = () => {
    pomoActive = false;
    clearInterval(pomoInterval);
};

window.resetPomodoro = () => {
    pomoActive = false;
    clearInterval(pomoInterval);
    pomoTimeLeft = 25 * 60;
    document.getElementById('pomodoro-timer').innerText = formatPomoTime(pomoTimeLeft);
};

// ----------------------------------------------------
// Habit Alarms (Local checks)
// ----------------------------------------------------
function playBeep(freq, duration) {
    if (!notificationsEnabled()) return;
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(freq, audioCtx.currentTime);
        oscillator.connect(audioCtx.destination);
        oscillator.start();
        setTimeout(() => oscillator.stop(), duration);
    } catch(e) { }
}

let lastCheckedMin = -1;
function checkHabitAlarms() {
    const now = new Date();
    const currentMin = now.getMinutes();
    
    // Evita checar duas vezes no mesmo minuto
    if (currentMin === lastCheckedMin) return;
    lastCheckedMin = currentMin;
    
    const timeStr = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
    
    const activeHabits = LocalDB.get('habits').filter(h => h.active === 1 && !h.is_deleted);
    activeHabits.forEach(habit => {
        if (habit.target_time && habit.target_time.substring(0, 5) === timeStr) {
            // Verifica se j foi feito hoje (simplificado, precisaria de uma checkagem real nos logs)
            sendLocalNotification('Hora do Hábito!', habit.name);
            playBeep(600, 300);
            setTimeout(() => playBeep(600, 300), 500);
        }
    });
}

// Habit/task alarm web fallback (native scheduling in syncHabitReminders)
setInterval(function () {
    if (typeof window.checkHabitAlarms === 'function') window.checkHabitAlarms();
}, 30000);




// ================================================================
// FLASHCARDS (SRS - Anki Style) & POMODORO TIMER
// ================================================================

let _pomoInterval = null;
let _pomoTimeLeft = 25 * 60;
let _isPomoRunning = false;

// ─── Pomodoro Timer ──────────────────────────────────────────────

function initPomodoroUI() {
    const timeEl = document.getElementById('pomo-time');
    if (timeEl) {
        const m = Math.floor(_pomoTimeLeft / 60).toString().padStart(2, '0');
        const s = (_pomoTimeLeft % 60).toString().padStart(2, '0');
        timeEl.textContent = `${m}:${s}`;
    }
}

function startPomodoro() {
    if (_isPomoRunning) return;
    _isPomoRunning = true;
    document.getElementById('pomo-btn-start').style.display = 'none';
    document.getElementById('pomo-btn-pause').style.display = 'block';

    _pomoInterval = setInterval(() => {
        _pomoTimeLeft--;
        initPomodoroUI();
        if (_pomoTimeLeft <= 0) {
            finishPomodoro();
        }
    }, 1000);
}

function pausePomodoro() {
    _isPomoRunning = false;
    clearInterval(_pomoInterval);
    document.getElementById('pomo-btn-start').style.display = 'block';
    document.getElementById('pomo-btn-pause').style.display = 'none';
}

function resetPomodoro() {
    pausePomodoro();
    _pomoTimeLeft = 25 * 60;
    initPomodoroUI();
}

function finishPomodoro() {
    pausePomodoro();
    _pomoTimeLeft = 5 * 60;
    initPomodoroUI();
    const label = document.getElementById('pomo-mode-label');
    if (label) label.textContent = 'DESCANSO';

    LocalDB.upsert('pomo_sessions', {
        id: Date.now(),
        type: 'focus',
        duration_minutes: 25,
        session_date: new Date().toISOString().split('T')[0]
    });
    awardXP(20, 'Sessao Pomodoro completa');
    showToast('Pomodoro concluido! +20 XP');
    renderPomodoroHistory();
}

function renderPomodoroHistory() {
    const list = document.getElementById('pomo-history');
    if (!list) return;
    const ph = LocalDB.getAll('pomodoros') || [];
    const today = new Date().toISOString().split('T')[0];
    const todayPomos = ph.filter(p => p.date.startsWith(today));
    
    list.innerHTML = '';
    if (!todayPomos.length) {
        list.innerHTML = '<div style="color:var(--text-secondary);font-size:0.85rem">Nenhum pomodoro hoje ainda.</div>';
        return;
    }
    todayPomos.forEach((p, i) => {
        list.innerHTML += `<div style="background:rgba(255,255,255,0.05);padding:8px 12px;border-radius:8px;font-size:0.85rem;color:white;display:flex;justify-content:space-between">
            <span>🍅 Sessão ${i+1}</span>
            <span style="color:var(--accent-green)">+50 XP</span>
        </div>`;
    });
    const dots = document.getElementById('pomo-dots');
    if (dots) {
        dots.innerHTML = todayPomos.map(() => '<i class="fa-solid fa-circle" style="color:var(--accent-pink);font-size:0.6rem"></i>').join('');
    }
}

function closePomodoro() {
    document.getElementById('pomodoro-view').style.display = 'none';
}

// Intercept old showPomodoro if exists
const _oldShowPomodoro = window.showPomodoro;
window.showPomodoro = function() {
    document.getElementById('pomodoro-view').style.display = 'flex';
    initPomodoroUI();
    renderPomodoroHistory();
};

// ─── Flashcards (SuperMemo-2 SRS) ────────────────────────────────

let _flashcardQueue = [];
let _currentCardIndex = 0;
let _fcKnown = 0;
let _fcUnknown = 0;
let _fcShowingBack = false;

function initFlashcardsDB() {
    if (!localStorage.getItem('flashcards')) {
        LocalDB.saveAll('flashcards', []);
    }
}

function createFlashcard(front, back, noteId = null) {
    LocalDB.upsert('flashcards', {
        id: 'fc_' + Date.now() + Math.floor(Math.random() * 1000),
        note_id: noteId,
        noteId: noteId,
        front: front,
        back: back,
        interval: 0,
        repetition: 0,
        repetitions: 0,
        efactor: 2.5,
        ease_factor: 2.5,
        next_review: new Date().toISOString(),
        nextReviewDate: new Date().toISOString()
    });
}

function normalizeFlashcard(card) {
    if (!card.nextReviewDate && card.next_review) card.nextReviewDate = card.next_review;
    if (!card.next_review && card.nextReviewDate) card.next_review = card.nextReviewDate;
    return card;
}

function getDueFlashcards() {
    const cards = (LocalDB.getAll('flashcards') || []).map(normalizeFlashcard);
    const now = new Date().toISOString();
    return cards.filter(c => !c.is_deleted && (!c.nextReviewDate || c.nextReviewDate <= now));
}

window.showFlashcards = function() {
    initFlashcardsDB();
    _flashcardQueue = getDueFlashcards();

    if (!LocalDB.getAll('flashcards').filter(c => !c.is_deleted).length) {
        showToast('Nenhum flashcard. Crie via notas ou Quiz ENEM.');
        return;
    }
    if (!_flashcardQueue.length) {
        showToast('Nenhum card pendente hoje. Volte amanhã!');
        return;
    }

    _currentCardIndex = 0;
    _fcKnown = 0;
    _fcUnknown = 0;
    
    document.getElementById('flashcard-view').style.display = 'flex';
    renderCurrentFlashcard();
};

window.closeFlashcards = function() {
    document.getElementById('flashcard-view').style.display = 'none';
};

function renderCurrentFlashcard() {
    const frontEl = document.getElementById('fc-front');
    const backEl = document.getElementById('fc-back');
    const counter = document.getElementById('fc-counter');
    
    document.getElementById('fc-known-count').textContent = _fcKnown;
    document.getElementById('fc-unknown-count').textContent = _fcUnknown;
    
    if (_currentCardIndex >= _flashcardQueue.length) {
        frontEl.innerHTML = "🎉<br><br>Você revisou todos os flashcards pendentes!";
        backEl.style.display = 'none';
        counter.textContent = "Finalizado";
        return;
    }
    
    const card = _flashcardQueue[_currentCardIndex];
    counter.textContent = `${_currentCardIndex + 1} / ${_flashcardQueue.length}`;
    
    frontEl.innerHTML = card.front.replace(/\n/g, '<br>');
    backEl.innerHTML = card.back.replace(/\n/g, '<br>');
    backEl.style.display = 'none';
    _fcShowingBack = false;
    
    // Reset card UI
    const cardDiv = document.getElementById('flashcard-card');
    cardDiv.style.transform = 'none';
    cardDiv.style.border = '1px solid var(--accent-purple)';
}

window.flipFlashcard = function() {
    if (_currentCardIndex >= _flashcardQueue.length) return;
    const backEl = document.getElementById('fc-back');
    const cardDiv = document.getElementById('flashcard-card');
    
    if (!_fcShowingBack) {
        _fcShowingBack = true;
        backEl.style.display = 'block';
        cardDiv.style.transform = 'scale(1.02)';
        cardDiv.style.border = '1px solid var(--accent-blue)';
    }
};

window.answerFlashcard = function(isCorrect) {
    if (_currentCardIndex >= _flashcardQueue.length) return;
    if (!_fcShowingBack) {
        // Must flip before answering
        window.flipFlashcard();
        return;
    }
    
    const card = _flashcardQueue[_currentCardIndex];
    
    // SM-2 Algorithm Implementation
    let quality = isCorrect ? 4 : 0; // Simplified quality (0=blackout, 4=good)
    
    if (quality >= 3) {
        if (card.repetition === 0) {
            card.interval = 1;
        } else if (card.repetition === 1) {
            card.interval = 6;
        } else {
            card.interval = Math.round(card.interval * card.efactor);
        }
        card.repetition++;
        _fcKnown++;
        if (typeof addXP === 'function') addXP(5); // +5 XP for correct
    } else {
        card.repetition = 0;
        card.interval = 1;
        _fcUnknown++;
    }
    
    card.efactor = card.efactor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02));
    if (card.efactor < 1.3) card.efactor = 1.3;
    
    // Calculate next review date
    const nextDate = new Date();
    nextDate.setDate(nextDate.getDate() + card.interval);
    card.nextReviewDate = nextDate.toISOString();
    card.next_review = card.nextReviewDate;
    card.ease_factor = card.efactor;
    card.repetitions = card.repetition;
    LocalDB.upsert('flashcards', card);

    const cardDiv = document.getElementById('flashcard-card');
    cardDiv.classList.add(isCorrect ? 'fc-swipe-right' : 'fc-swipe-left');
    
    setTimeout(() => {
        cardDiv.classList.remove('fc-swipe-right', 'fc-swipe-left');
        _currentCardIndex++;
        renderCurrentFlashcard();
    }, 300);
};

// ─── Generate Flashcards via Jarvis ──────────────────────────────

function insertGenerateFlashcardsButton() {
    const jarvisTabs = document.querySelector('#jarvis-panel .jarvis-tab') ? document.querySelector('#jarvis-panel .jarvis-tab').parentElement : null;
    if (jarvisTabs && !document.getElementById('btn-jarvis-fc')) {
        const btn = document.createElement('button');
        btn.id = 'btn-jarvis-fc';
        btn.className = 'jarvis-tab';
        btn.innerHTML = '<i class="fa-solid fa-clone"></i> Criar Cards';
        btn.onclick = () => {
            setJarvisMode('generate_flashcards', btn);
        };
        jarvisTabs.appendChild(btn);
    }
}

// Intercept runJarvisAction to handle flashcard generation
const _origRunJarvisAction = window.runJarvisAction;
window.runJarvisAction = async function() {
    if (typeof _jarvisMode !== 'undefined' && _jarvisMode === 'generate_flashcards') {
        const prompt = document.getElementById('jarvis-prompt')?.value?.trim();
        if (!prompt) { alert('Insira o texto base para gerar os flashcards.'); return; }
        
        document.getElementById('jarvis-input-area').style.display = 'none';
        document.getElementById('jarvis-loading').style.display = 'block';
        
        // MOCK AI GENERATION
        setTimeout(() => {
            const cards = [
                { f: `O que é: "${prompt.slice(0,10)}..."?`, b: "Conceito chave extraído do texto." },
                { f: "Quais os 3 pontos principais?", b: "1. Ponto A\n2. Ponto B\n3. Ponto C" }
            ];
            
            cards.forEach(c => createFlashcard(c.f, c.b));
            
            document.getElementById('jarvis-loading').style.display = 'none';
            document.getElementById('jarvis-result').style.display = 'block';
            document.getElementById('jarvis-result-text').innerHTML = `✅ ${cards.length} Flashcards gerados e adicionados ao seu baralho!`;
            document.getElementById('jarvis-input-area').style.display = 'block';
        }, 2000);
        return;
    }
    
    if (typeof _origRunJarvisAction === 'function') {
        _origRunJarvisAction();
    }
};

// ─── Notifications & Startup ──────────────────────────────────────

function checkPendingFlashcards() {
    const due = getDueFlashcards();
    if (due.length > 0) {
        showToast(`📚 Você tem ${due.length} flashcards pendentes para revisar!`, 5000);
        if ("Notification" in window && Notification.permission === 'granted') {
            new Notification('Nexus Studies', { body: `Você tem ${due.length} flashcards para revisar hoje!` });
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initFlashcardsDB();
    insertGenerateFlashcardsButton();
    
    // Request notification permission if not asked
    if ("Notification" in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
    
    setTimeout(checkPendingFlashcards, 3000);
});


// ================================================================
// STUDIES 3.0: NOTION COVERS & OBSIDIAN GRAPH VIEW
// ================================================================

// ─── Covers & Icons (Notion Style) ───────────────────────────────

function changeNoteCover() {
    // Create an invisible file input
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        if (file.size > 2 * 1024 * 1024) {
            alert('A capa deve ter no máximo 2MB.');
            return;
        }
        const reader = new FileReader();
        reader.onload = (ev) => {
            const dataUrl = ev.target.result;
            // Update UI
            document.getElementById('note-cover-container').style.display = 'block';
            document.getElementById('note-cover-container').style.backgroundImage = `url(${dataUrl})`;
            document.getElementById('add-cover-btn').style.display = 'none';
            // Save to LocalDB immediately if it's an existing note
            const titleEl = document.getElementById('note-title');
            if (titleEl && titleEl.dataset.noteId) {
                const notes = LocalDB.getAll('notes') || [];
                const n = notes.find(x => x.id === titleEl.dataset.noteId);
                if (n) {
                    n.coverImage = dataUrl;
                    LocalDB.saveAll('notes', notes);
                }
            } else {
                // If new note, save temporarily in a global var so saveNote grabs it
                window._tempCoverImage = dataUrl;
            }
        };
        reader.readAsDataURL(file);
    };
    input.click();
}

function removeNoteCover() {
    document.getElementById('note-cover-container').style.display = 'none';
    document.getElementById('note-cover-container').style.backgroundImage = 'none';
    document.getElementById('add-cover-btn').style.display = 'inline-block';
    
    const titleEl = document.getElementById('note-title');
    if (titleEl && titleEl.dataset.noteId) {
        const notes = LocalDB.getAll('notes') || [];
        const n = notes.find(x => x.id === titleEl.dataset.noteId);
        if (n) {
            delete n.coverImage;
            LocalDB.saveAll('notes', notes);
        }
    }
    window._tempCoverImage = null;
}

function changeNoteIcon() {
    const icon = prompt('Digite um Emoji para usar de ícone:');
    if (icon) {
        // Grab only the first character or emoji
        const firstEmoji = Array.from(icon)[0];
        document.getElementById('note-icon-display').textContent = firstEmoji;
        
        const titleEl = document.getElementById('note-title');
        if (titleEl && titleEl.dataset.noteId) {
            const notes = LocalDB.getAll('notes') || [];
            const n = notes.find(x => x.id === titleEl.dataset.noteId);
            if (n) {
                n.icon = firstEmoji;
                LocalDB.saveAll('notes', notes);
            }
        } else {
            window._tempIcon = firstEmoji;
        }
    }
}

// Hook into openNoteEditor to load covers and icons
const _origOpenNoteEditorForCover = window.openNoteEditor;
window.openNoteEditor = function(note, notebookId) {
    if (typeof _origOpenNoteEditorForCover === 'function') _origOpenNoteEditorForCover(note, notebookId);
    
    // Clear temp variables
    window._tempCoverImage = null;
    window._tempIcon = null;
    
    setTimeout(() => {
        const titleEl = document.getElementById('note-title');
        if (titleEl) {
            titleEl.dataset.noteId = note ? note.id : '';
        }
        
        // Render Cover
        const coverContainer = document.getElementById('note-cover-container');
        const addBtn = document.getElementById('add-cover-btn');
        if (note && note.coverImage) {
            coverContainer.style.display = 'block';
            coverContainer.style.backgroundImage = `url(${note.coverImage})`;
            addBtn.style.display = 'none';
        } else {
            coverContainer.style.display = 'none';
            coverContainer.style.backgroundImage = 'none';
            addBtn.style.display = 'inline-block';
        }
        
        // Render Icon
        const iconDisplay = document.getElementById('note-icon-display');
        if (note && note.icon) {
            iconDisplay.textContent = note.icon;
        } else {
            iconDisplay.textContent = '📄';
        }
        
        // Scan for backlinks
        renderBacklinks(note ? note.id : null);
        
    }, 100);
};

// Hook into saveNote to include cover and icon
const _origSaveNoteForCover = window.saveNote;
window.saveNote = function() {
    // Before saving, ensure we don't lose the cover/icon on new notes
    if (typeof _origSaveNoteForCover === 'function') _origSaveNoteForCover();
    
    // After save, the note is in LocalDB. If it was new, it has no ID attached to titleEl yet,
    // but the saveNote function should have created it. We need to find the latest note.
    const notes = LocalDB.getAll('notes') || [];
    const titleEl = document.getElementById('note-title');
    let currentNote = null;
    
    if (titleEl && titleEl.dataset.noteId) {
        currentNote = notes.find(n => n.id === titleEl.dataset.noteId);
    } else {
        // It was a new note. Find it by title and content (heuristic)
        const t = titleEl ? titleEl.value : '';
        currentNote = notes.find(n => n.title === t);
        if (currentNote && titleEl) titleEl.dataset.noteId = currentNote.id;
    }
    
    if (currentNote) {
        let changed = false;
        if (window._tempCoverImage) { currentNote.coverImage = window._tempCoverImage; changed = true; window._tempCoverImage = null; }
        if (window._tempIcon) { currentNote.icon = window._tempIcon; changed = true; window._tempIcon = null; }
        if (changed) { LocalDB.saveAll('notes', notes); }
    }
};

// ─── Backlinks (Linked Mentions) ─────────────────────────────────

function renderBacklinks(noteId) {
    const panel = document.getElementById('backlinks-panel');
    const list = document.getElementById('backlinks-list');
    if (!panel || !list) return;
    
    if (!noteId) {
        panel.style.display = 'none';
        return;
    }
    
    const notes = LocalDB.getAll('notes') || [];
    // A backlink exists if another note's content contains our noteId in a data-note-id attribute
    const backlinks = notes.filter(n => n.id !== noteId && n.content && n.content.includes(noteId));
    
    if (backlinks.length === 0) {
        panel.style.display = 'none';
        return;
    }
    
    panel.style.display = 'block';
    list.innerHTML = '';
    
    backlinks.forEach(bl => {
        const item = document.createElement('div');
        item.style.padding = '12px';
        item.style.background = 'rgba(255,255,255,0.05)';
        item.style.borderRadius = '8px';
        item.style.border = '1px solid var(--border-glass)';
        item.style.cursor = 'pointer';
        item.innerHTML = `
            <div style="font-weight:bold;color:var(--accent-blue);margin-bottom:4px">${bl.icon || '📄'} ${bl.title || 'Sem título'}</div>
            <div style="font-size:0.8rem;color:var(--text-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${(bl.content || '').replace(/<[^>]+>/g, ' ').substring(0, 100)}...</div>
        `;
        item.onclick = () => {
            closeNoteEditor();
            setTimeout(() => openNoteEditor(bl, bl.notebookId), 300);
        };
        list.appendChild(item);
    });
}

// ─── Graph View (Obsidian Style) ─────────────────────────────────

let _graphAnimation = null;
let _graphNodes = [];
let _graphEdges = [];
let _graphCamera = { x: 0, y: 0, zoom: 1 };
let _isDraggingGraph = false;
let _draggedNode = null;
let _lastMousePos = { x: 0, y: 0 };

function openGraphView() {
    const view = document.getElementById('graph-view');
    if (!view) return;
    view.style.display = 'block';
    initGraphData();
    startGraphPhysics();
}

function closeGraphView() {
    document.getElementById('graph-view').style.display = 'none';
    if (_graphAnimation) cancelAnimationFrame(_graphAnimation);
}

function initGraphData() {
    const notes = LocalDB.getAll('notes') || [];
    const canvas = document.getElementById('graph-canvas');
    if (!canvas) return;
    const w = window.innerWidth;
    const h = window.innerHeight;
    
    _graphNodes = notes.map(n => ({
        id: n.id,
        title: n.title || 'Nota',
        icon: n.icon || '📄',
        x: w/2 + (Math.random() - 0.5) * 200,
        y: h/2 + (Math.random() - 0.5) * 200,
        vx: 0, vy: 0,
        radius: 12
    }));
    
    _graphEdges = [];
    notes.forEach(n => {
        if (!n.content) return;
        notes.forEach(target => {
            if (n.id !== target.id && n.content.includes(target.id)) {
                _graphEdges.push({ source: n.id, target: target.id });
            }
        });
    });
    
    _graphCamera = { x: 0, y: 0, zoom: 1 };
    
    // Bind events
    canvas.width = w;
    canvas.height = h;
    canvas.onmousedown = handleGraphPointerDown;
    canvas.onmousemove = handleGraphPointerMove;
    canvas.onmouseup = handleGraphPointerUp;
    canvas.onmouseleave = handleGraphPointerUp;
    canvas.ontouchstart = (e) => handleGraphPointerDown(e.touches[0]);
    canvas.ontouchmove = (e) => handleGraphPointerMove(e.touches[0]);
    canvas.ontouchend = handleGraphPointerUp;
    
    // Canvas wheel zoom
    canvas.onwheel = (e) => {
        e.preventDefault();
        _graphCamera.zoom -= e.deltaY * 0.001;
        if (_graphCamera.zoom < 0.2) _graphCamera.zoom = 0.2;
        if (_graphCamera.zoom > 3) _graphCamera.zoom = 3;
    };
}

function startGraphPhysics() {
    const canvas = document.getElementById('graph-canvas');
    const ctx = canvas.getContext('2d');
    
    function draw() {
        // Physics Loop (Force Directed)
        const k = 0.05; // spring constant
        const repulse = 1000; // repulsion strength
        const damping = 0.85;
        
        // 1. Repulsion between nodes
        for (let i = 0; i < _graphNodes.length; i++) {
            for (let j = i + 1; j < _graphNodes.length; j++) {
                const n1 = _graphNodes[i];
                const n2 = _graphNodes[j];
                const dx = n2.x - n1.x;
                const dy = n2.y - n1.y;
                const distSq = dx*dx + dy*dy;
                if (distSq < 0.1) continue;
                const dist = Math.sqrt(distSq);
                const force = repulse / distSq;
                const fx = (dx/dist) * force;
                const fy = (dy/dist) * force;
                n1.vx -= fx; n1.vy -= fy;
                n2.vx += fx; n2.vy += fy;
            }
        }
        
        // 2. Attraction along edges
        _graphEdges.forEach(e => {
            const n1 = _graphNodes.find(n => n.id === e.source);
            const n2 = _graphNodes.find(n => n.id === e.target);
            if (!n1 || !n2) return;
            const dx = n2.x - n1.x;
            const dy = n2.y - n1.y;
            const dist = Math.sqrt(dx*dx + dy*dy);
            const force = (dist - 80) * k;
            const fx = (dx/dist) * force;
            const fy = (dy/dist) * force;
            n1.vx += fx; n1.vy += fy;
            n2.vx -= fx; n2.vy -= fy;
        });
        
        // 3. Central gravity
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        _graphNodes.forEach(n => {
            const dx = cx - n.x;
            const dy = cy - n.y;
            n.vx += dx * 0.005;
            n.vy += dy * 0.005;
            
            // Apply velocity
            if (_draggedNode !== n) {
                n.x += n.vx;
                n.y += n.vy;
            }
            // Damping
            n.vx *= damping;
            n.vy *= damping;
        });
        
        // Rendering
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        ctx.save();
        ctx.translate(canvas.width/2 + _graphCamera.x, canvas.height/2 + _graphCamera.y);
        ctx.scale(_graphCamera.zoom, _graphCamera.zoom);
        ctx.translate(-canvas.width/2, -canvas.height/2);
        
        // Draw edges
        ctx.strokeStyle = 'rgba(108, 92, 231, 0.4)';
        ctx.lineWidth = 1.5;
        _graphEdges.forEach(e => {
            const n1 = _graphNodes.find(n => n.id === e.source);
            const n2 = _graphNodes.find(n => n.id === e.target);
            if (!n1 || !n2) return;
            ctx.beginPath();
            ctx.moveTo(n1.x, n1.y);
            ctx.lineTo(n2.x, n2.y);
            ctx.stroke();
        });
        
        // Draw nodes
        ctx.font = '12px "Inter", sans-serif';
        _graphNodes.forEach(n => {
            // Node circle
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
            ctx.fillStyle = _draggedNode === n ? '#fd79a8' : '#6c5ce7';
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // Icon
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#fff';
            ctx.fillText(n.icon, n.x, n.y);
            
            // Title
            ctx.fillStyle = 'rgba(255,255,255,0.85)';
            ctx.fillText(n.title.substring(0, 15), n.x, n.y + 22);
        });
        
        ctx.restore();
        
        _graphAnimation = requestAnimationFrame(draw);
    }
    
    draw();
}

function handleGraphPointerDown(e) {
    const canvas = document.getElementById('graph-canvas');
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    
    // Convert to world coordinates
    const wx = (mx - canvas.width/2 - _graphCamera.x) / _graphCamera.zoom + canvas.width/2;
    const wy = (my - canvas.height/2 - _graphCamera.y) / _graphCamera.zoom + canvas.height/2;
    
    _lastMousePos = { x: mx, y: my };
    
    // Check if clicked a node
    for (const n of _graphNodes) {
        const dx = wx - n.x;
        const dy = wy - n.y;
        if (dx*dx + dy*dy < 400) {
            _draggedNode = n;
            return;
        }
    }
    _isDraggingGraph = true;
}

function handleGraphPointerMove(e) {
    if (!_isDraggingGraph && !_draggedNode) return;
    
    const mx = e.clientX;
    const my = e.clientY;
    const dx = mx - _lastMousePos.x;
    const dy = my - _lastMousePos.y;
    _lastMousePos = { x: mx, y: my };
    
    if (_draggedNode) {
        _draggedNode.x += dx / _graphCamera.zoom;
        _draggedNode.y += dy / _graphCamera.zoom;
    } else if (_isDraggingGraph) {
        _graphCamera.x += dx;
        _graphCamera.y += dy;
    }
}

function handleGraphPointerUp(e) {
    if (_draggedNode && !e.movementX && !e.movementY && (!e.touches || e.touches.length === 0)) {
        // If not much movement, consider it a click
        closeGraphView();
        const note = LocalDB.getAll('notes').find(n => n.id === _draggedNode.id);
        if (note) openNoteEditor(note, note.notebookId);
    }
    _isDraggingGraph = false;
    _draggedNode = null;
}

function centerGraph() {
    _graphCamera = { x: 0, y: 0, zoom: 1 };
}


// ================================================================
// ANALYTICS & CHARTS DASHBOARD (Chart.js)
// ================================================================

window._chartInstances = window._chartInstances || {};
let _chartInstances = window._chartInstances;

function initChartDefaults() {
    if (typeof Chart !== 'undefined') {
        Chart.defaults.color = 'rgba(255, 255, 255, 0.6)';
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.scale.grid.color = 'rgba(255, 255, 255, 0.05)';
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 15, 25, 0.9)';
        Chart.defaults.plugins.tooltip.titleColor = '#fff';
        Chart.defaults.plugins.tooltip.bodyColor = '#ccc';
        Chart.defaults.plugins.tooltip.borderColor = 'rgba(108, 92, 231, 0.3)';
        Chart.defaults.plugins.tooltip.borderWidth = 1;
        Chart.defaults.plugins.tooltip.cornerRadius = 8;
        Chart.defaults.plugins.tooltip.padding = 10;
    }
}

function safeDestroyChart(id) {
    window._chartInstances = window._chartInstances || {};
    _chartInstances = window._chartInstances;

    const trackedChart = _chartInstances[id];
    if (trackedChart && typeof trackedChart.destroy === 'function') {
        try {
            trackedChart.destroy();
        } catch (error) {
            console.warn('Chart destroy failed for tracked instance:', id, error);
        }
    }

    const canvas = document.getElementById(id);
    const registeredChart = canvas && typeof Chart !== 'undefined' && typeof Chart.getChart === 'function'
        ? Chart.getChart(canvas)
        : null;
    if (registeredChart && registeredChart !== trackedChart && typeof registeredChart.destroy === 'function') {
        try {
            registeredChart.destroy();
        } catch (error) {
            console.warn('Chart destroy failed for registry instance:', id, error);
        }
    }

    delete window._chartInstances[id];
    delete _chartInstances[id];
}

// ─── Finance Charts ──────────────────────────────────────────────

function renderFinanceCharts() {
    if (typeof Chart === 'undefined') return;
    initChartDefaults();
    
    const raw = (LocalDB.get('finance_transactions') || []).filter(t => !t.is_deleted);
    const txDate = t => (t.occurred_at || t.date || t.created_at || '').slice(0, 10);
    const transactions = raw.map(t => ({
        ...t,
        date: txDate(t),
        amount: Number(t.amount) || 0
    }));
    
    // 1. PIE CHART: Expenses by Category (Current Month)
    const now = new Date();
    const currMonth = now.toISOString().slice(0, 7); // YYYY-MM
    
    const expensesThisMonth = transactions.filter(t => t.type === 'expense' && t.date.startsWith(currMonth));
    const catTotals = {};
    expensesThisMonth.forEach(t => {
        catTotals[t.category] = (catTotals[t.category] || 0) + t.amount;
    });
    
    const catLabels = Object.keys(catTotals);
    const catData = Object.values(catTotals);
    
    safeDestroyChart('finance-pie-chart');
    const pieCtx = document.getElementById('finance-pie-chart');
    if (pieCtx && catLabels.length > 0) {
        _chartInstances['finance-pie-chart'] = new Chart(pieCtx, {
            type: 'doughnut',
            data: {
                labels: catLabels,
                datasets: [{
                    data: catData,
                    backgroundColor: ['#22d3ee', '#a78bfa', '#fb923c', '#fb7185', '#34d399', '#fbbf24', '#94a3b8'],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: { position: 'right', labels: { boxWidth: 12, usePointStyle: true, font: {size: 11} } }
                }
            }
        });
    }

    // 2. BAR CHART: Last 6 Months (Income vs Expense)
    const months = [];
    for (let i = 5; i >= 0; i--) {
        const d = new Date();
        d.setMonth(d.getMonth() - i);
        months.push(d.toISOString().slice(0, 7)); // YYYY-MM
    }
    
    const incomeData = months.map(m => {
        return transactions.filter(t => t.type === 'income' && t.date.startsWith(m)).reduce((s,t) => s + t.amount, 0);
    });
    const expenseData = months.map(m => {
        return transactions.filter(t => t.type === 'expense' && t.date.startsWith(m)).reduce((s,t) => s + t.amount, 0);
    });
    
    const monthLabels = months.map(m => {
        const [yy, mm] = m.split('-');
        const names = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
        return names[parseInt(mm)-1];
    });

    safeDestroyChart('finance-bar-chart');
    const barCtx = document.getElementById('finance-bar-chart');
    if (barCtx) {
        _chartInstances['finance-bar-chart'] = new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: monthLabels,
                datasets: [
                    { label: 'Receitas', data: incomeData, backgroundColor: '#34d399', borderRadius: 4 },
                    { label: 'Despesas', data: expenseData, backgroundColor: '#fb7185', borderRadius: 4 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { grid: { display: false } },
                    y: { border: { display: false }, ticks: { maxTicksLimit: 5 } }
                },
                plugins: { legend: { display: true, position: 'top', labels: { usePointStyle: true, boxWidth: 8, font: {size: 11} } } }
            }
        });
    }
}

// ─── Habits Chart ────────────────────────────────────────────────

function renderHabitCharts() {
    if (typeof Chart === 'undefined') return;
    initChartDefaults();
    
    const habits = LocalDB.getAll('habits') || [];
    const days = 14;
    const labels = [];
    const percentages = [];
    
    for (let i = days - 1; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        const iso = d.toISOString().split('T')[0];
        labels.push(d.getDate() + '/' + (d.getMonth()+1));
        
        let totalActive = 0;
        let totalDone = 0;
        
        habits.forEach(h => {
            // Very simplified: assuming all habits are daily for the chart
            totalActive++;
            if (h.history && h.history.includes(iso)) totalDone++;
        });
        
        percentages.push(totalActive === 0 ? 0 : Math.round((totalDone / totalActive) * 100));
    }
    
    safeDestroyChart('habits-line-chart');
    const ctx = document.getElementById('habits-line-chart');
    if (ctx) {
        _chartInstances['habits-line-chart'] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Aderência (%)',
                    data: percentages,
                    borderColor: '#a78bfa',
                    backgroundColor: 'rgba(167, 139, 250, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#a78bfa',
                    pointRadius: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { grid: { display: false }, ticks: { maxTicksLimit: 7 } },
                    y: { min: 0, max: 100, border: { display: false }, ticks: { stepSize: 25 } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }
}

// ─── Studies Chart ───────────────────────────────────────────────

function renderStudyCharts() {
    if (typeof Chart === 'undefined') return;
    initChartDefaults();

    const pomos = LocalDB.get('pomo_sessions') || [];
    const pomoDate = (p) => p.session_date || p.date || (p.created_at || '').split('T')[0];

    const days = 7;
    const labels = [];
    const pomoData = [];

    for (let i = days - 1; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        const iso = d.toISOString().split('T')[0];
        labels.push(d.toLocaleDateString('pt-BR', { weekday: 'short' }));
        const count = pomos.filter(p => String(pomoDate(p)).startsWith(iso)).length;
        pomoData.push(count);
    }
    
    safeDestroyChart('studies-bar-chart');
    const ctx = document.getElementById('studies-bar-chart');
    if (ctx) {
        _chartInstances['studies-bar-chart'] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Pomodoros',
                    data: pomoData,
                    backgroundColor: '#fb923c',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { grid: { display: false } },
                    y: { border: { display: false }, ticks: { stepSize: 1 } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }
}

// Intercept the loaders to trigger chart rendering
const _origLoadFinanceForCharts = window.loadFinance;
window.loadFinance = function() {
    if (typeof _origLoadFinanceForCharts === 'function') _origLoadFinanceForCharts();
    ensureChartJs().then(() => setTimeout(renderFinanceCharts, 100));
};

const _origLoadHabitsForCharts = window.loadHabits;
window.loadHabits = function() {
    if (typeof _origLoadHabitsForCharts === 'function') _origLoadHabitsForCharts();
    ensureChartJs().then(() => setTimeout(renderHabitCharts, 100));
};

const _origLoadStudiesForCharts = window.loadStudies;
window.loadStudies = function() {
    if (typeof _origLoadStudiesForCharts === 'function') _origLoadStudiesForCharts();
    ensureChartJs().then(() => setTimeout(renderStudyCharts, 100));
};


// ================================================================
// MULTI-USER AUTH & SETTINGS
// ================================================================

let currentUser = null;

// Listen for auth changes
if (window.nexusSupabase) {
    window.nexusSupabase.auth.onAuthStateChange((event, session) => {
        currentUser = session ? session.user : null;
        updateSettingsUI();
        if (event === 'SIGNED_IN') {
            forceSyncData();
        }
    });
    
    // Initial check
    window.nexusSupabase.auth.getSession().then(({ data: { session } }) => {
        currentUser = session ? session.user : null;
        updateSettingsUI();
    });
}

function updateSettingsUI() {
    const title = document.getElementById('auth-status-title');
    const desc = document.getElementById('auth-status-desc');
    const icon = document.getElementById('auth-status-icon');
    const btnLogin = document.getElementById('btn-login-google');
    const btnLogout = document.getElementById('btn-logout');
    
    if (!title) return;

    if (currentUser) {
        icon.innerHTML = '<i class="fa-solid fa-cloud-check" style="color:var(--accent-green)"></i>';
        title.textContent = `Logado como: ${currentUser.user_metadata?.full_name || currentUser.email}`;
        desc.textContent = 'Seus dados estão sendo sincronizados na nuvem.';
        btnLogin.style.display = 'none';
        btnLogout.style.display = 'block';
    } else {
        icon.innerHTML = '<i class="fa-solid fa-cloud-offline" style="color:var(--text-secondary)"></i>';
        title.textContent = 'Offline (Conta Local)';
        desc.textContent = 'Seus dados estão salvos apenas neste dispositivo.';
        btnLogin.style.display = 'flex';
        btnLogout.style.display = 'none';
    }
}

function getOAuthRedirectUrl() {
    if (window.NexusAndroid && typeof window.NexusAndroid.getOAuthRedirect === 'function') {
        return window.NexusAndroid.getOAuthRedirect();
    }
    if (window.location.protocol === 'file:') {
        return 'com.nexus.mobile://auth/callback';
    }
    return window.location.origin + window.location.pathname;
}

window.handleOAuthCallback = async function(callbackUrl) {
    closeOAuthOverlay();
    if (!window.nexusSupabase || !callbackUrl) return;
    try {
        const parsed = new URL(callbackUrl.replace('com.nexus.mobile://', 'https://local/'));
        const code = parsed.searchParams.get('code');
        if (code) {
            const { error } = await window.nexusSupabase.auth.exchangeCodeForSession(code);
            if (error) showToast('Erro OAuth: ' + error.message);
            else {
                showToast('Login realizado com sucesso!');
                if (typeof forceSyncData === 'function') forceSyncData();
            }
            return;
        }
        const hashIdx = callbackUrl.indexOf('#');
        if (hashIdx > -1) {
            const hashParams = new URLSearchParams(callbackUrl.substring(hashIdx + 1));
            const access_token = hashParams.get('access_token');
            const refresh_token = hashParams.get('refresh_token');
            if (access_token && refresh_token) {
                const { error } = await window.nexusSupabase.auth.setSession({ access_token, refresh_token });
                if (error) showToast('Erro OAuth: ' + error.message);
                else showToast('Login realizado com sucesso!');
            }
        }
    } catch (e) {
        console.error('OAuth callback error:', e);
        showToast('Falha ao processar login.');
    }
};

async function loginWithGoogle() {
    if (!isNetworkOnline()) {
        showToast("Sem conexão com a internet.");
        return;
    }
    if (!window.nexusSupabase) {
        showToast("Servidor indisponível (Offline).");
        return;
    }
    const redirectTo = getOAuthRedirectUrl();
    const { data, error } = await window.nexusSupabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
            redirectTo,
            skipBrowserRedirect: true
        }
    });
    if (error) {
        showToast("Erro no login: " + error.message);
        return;
    }
    if (!data?.url) {
        showToast("Não foi possível iniciar login Google.");
        return;
    }
    // Google bloqueia OAuth em WebView/iframe (erro 403). Abre Custom Tab / navegador e volta via deep link.
    if (window.NexusAndroid && typeof window.NexusAndroid.openOAuthUrl === 'function') {
        window.NexusAndroid.openOAuthUrl(data.url);
        showToast("Complete o login na janela que abriu...");
        return;
    }
    window.location.href = data.url;
}

function openOAuthOverlay(url) {
    let overlay = document.getElementById('oauth-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'oauth-overlay';
        overlay.className = 'oauth-overlay';
        overlay.innerHTML = `
            <div class="oauth-overlay-panel glass">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                    <strong style="color:white">Entrar com Google</strong>
                    <button type="button" class="icon-btn" id="oauth-overlay-close" aria-label="Fechar"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <iframe id="oauth-overlay-frame" title="Login Google" referrerpolicy="no-referrer-when-downgrade"></iframe>
            </div>`;
        document.body.appendChild(overlay);
        overlay.querySelector('#oauth-overlay-close').onclick = closeOAuthOverlay;
        overlay.addEventListener('click', (e) => { if (e.target === overlay) closeOAuthOverlay(); });
    }
    const frame = document.getElementById('oauth-overlay-frame');
    if (frame) frame.src = url;
    overlay.style.display = 'flex';
}

function closeOAuthOverlay() {
    const overlay = document.getElementById('oauth-overlay');
    if (overlay) overlay.style.display = 'none';
    const frame = document.getElementById('oauth-overlay-frame');
    if (frame) frame.src = 'about:blank';
}

async function logoutGoogle() {
    if (!window.nexusSupabase) return;
    const { error } = await window.nexusSupabase.auth.signOut();
    if (!error) {
        currentUser = null;
        updateSettingsUI();
        showToast("Você saiu da conta.");
    }
}

// Intercept pushChangesToSupabase — unified via syncData
window.pushChangesToSupabase = syncData;

function forceSyncData() {
    if (!isNetworkOnline()) {
        showToast("Sem conexão — sincronização indisponível.");
        return;
    }
    showToast("Sincronizando com a Nuvem...");
    syncData().then(() => {
        showToast("Sincronização concluída!");
    }).catch(() => {
        showToast("Sincronização indisponível — modo offline ativo.");
    });
}

window.forceSyncData = forceSyncData;
window.loginWithGoogle = loginWithGoogle;
window.logoutGoogle = logoutGoogle;
window.handleOAuthCallback = window.handleOAuthCallback;

window.triggerOcrCamera = function() {
    if (window.AndroidNative && typeof window.AndroidNative.openNativeCamera === 'function') {
        window.AndroidNative.openNativeCamera();
        showToast('Abrindo câmera...');
    } else {
        showToast('Câmera disponível apenas no app Android.');
    }
};

window.onNativeCameraResult = function(dataUrl) {
    if (!dataUrl) return;
    const editor = document.getElementById('note-content-rich');
    if (editor) {
        const img = document.createElement('img');
        img.src = dataUrl;
        img.style.maxWidth = '100%';
        img.style.borderRadius = '8px';
        editor.appendChild(img);
        showToast('Foto inserida na nota.');
    } else {
        showToast('Foto capturada — abra o editor de notas para inserir.');
    }
};

// ─── ENEM Quiz (mobile) ───────────────────────────────────────────

const ENEM_QUIZ_QUESTIONS = [
    { area: 'Matemática', stem: 'Uma família reduziu o consumo mensal de energia de 240 kWh para 204 kWh. Qual foi a redução percentual?', options: ['12%', '15%', '18%', '36%'], correct_index: 1, explanation: 'A redução foi de 36 kWh. 36/240 = 15%.' },
    { area: 'Matemática', stem: 'Em uma função afim f(x)=2x+3, qual é o valor de f(5)?', options: ['10', '11', '13', '15'], correct_index: 2, explanation: 'f(5)=2*5+3=13.' },
    { area: 'Matemática', stem: 'Um reservatório comporta 1200 litros e está com 35% da capacidade. Quantos litros faltam para enchê-lo?', options: ['420', '650', '780', '900'], correct_index: 2, explanation: '35% de 1200 = 420. Faltam 780 litros.' },
    { area: 'Português', stem: "Na frase 'Ela estudou muito, portanto foi bem na prova', a palavra 'portanto' indica:", options: ['oposição', 'conclusão', 'adição', 'condição'], correct_index: 1, explanation: "'Portanto' introduz uma conclusão." },
    { area: 'Português', stem: 'Em textos dissertativo-argumentativos, a tese é:', options: ['um exemplo secundário', 'a opinião central defendida', 'a citação obrigatória', 'o resumo final'], correct_index: 1, explanation: 'A tese é o ponto de vista central do texto.' },
    { area: 'Português', stem: "A expressão 'chuva de ideias' é um exemplo de linguagem:", options: ['literal', 'figurada', 'técnica', 'jurídica'], correct_index: 1, explanation: 'Usa sentido figurado.' },
    { area: 'Ciências da Natureza', stem: 'Durante a fotossíntese, a fase clara produz principalmente:', options: ['glicose e oxigênio', 'ATP e NADPH', 'DNA e RNA', 'sais minerais'], correct_index: 1, explanation: 'A fase clara produz ATP e NADPH.' },
    { area: 'Ciências da Natureza', stem: 'Ao ligar vários aparelhos em uma mesma tomada, o risco de aquecimento aumenta por:', options: ['da queda da gravidade', 'do aumento da corrente elétrica', 'da redução da frequência', 'da ausência de tensão'], correct_index: 1, explanation: 'Mais aparelhos = maior corrente = mais aquecimento.' },
    { area: 'Ciências da Natureza', stem: 'A mitocôndria é associada principalmente à:', options: ['digestão intracelular', 'respiração celular', 'fotossíntese', 'síntese de proteínas'], correct_index: 1, explanation: 'Mitocôndrias produzem ATP via respiração celular.' },
    { area: 'Ciências Humanas', stem: 'A Revolução Industrial intensificou a urbanização porque:', options: ['eliminou todas as fábricas', 'concentrou empregos nas cidades', 'proibiu o comércio', 'reduziu a produção'], correct_index: 1, explanation: 'Fábricas nas cidades atraíram trabalhadores.' },
    { area: 'Ciências Humanas', stem: 'No Brasil, a política do café com leite relacionava-se a elites de:', options: ['São Paulo e Minas Gerais', 'Amazonas e Pará', 'Bahia e Pernambuco', 'Rio Grande do Sul e Ceará'], correct_index: 0, explanation: 'Café (SP) e leite (MG).' },
    { area: 'Ciências Humanas', stem: 'O conceito de cidadania envolve direitos:', options: ['apenas privados', 'civis, políticos e sociais', 'somente comerciais', 'exclusivos de governantes'], correct_index: 1, explanation: 'Cidadania = direitos + deveres na vida coletiva.' }
];

let _quizQuestions = [], _quizIdx = 0, _quizCorrect = 0, _quizAttemptId = null, _quizTimerId = null, _quizSeconds = 0, _quizAnswers = [];

function formatQuizTime(s) {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return (m < 10 ? '0' : '') + m + ':' + (sec < 10 ? '0' : '') + sec;
}

window.openQuiz = function() {
    document.getElementById('quiz-view').style.display = 'flex';
    document.getElementById('quiz-setup').style.display = 'block';
    document.getElementById('quiz-play').style.display = 'none';
    document.getElementById('quiz-done').style.display = 'none';
};

window.closeQuiz = function() {
    if (_quizTimerId) clearInterval(_quizTimerId);
    document.getElementById('quiz-view').style.display = 'none';
};

window.startQuiz = function() {
    const area = document.getElementById('quiz-area-sel')?.value || '';
    const count = parseInt(document.getElementById('quiz-mode-sel')?.value || '5', 10);
    let pool = ENEM_QUIZ_QUESTIONS.slice();
    if (area) pool = pool.filter(q => q.area === area);
    pool.sort(() => Math.random() - 0.5);
    _quizQuestions = pool.slice(0, Math.min(count, pool.length));
    if (!_quizQuestions.length) {
        showToast('Nenhuma questão para esta área.');
        return;
    }
    _quizIdx = 0;
    _quizCorrect = 0;
    _quizSeconds = 0;
    _quizAnswers = [];
    _quizAttemptId = 'qa_' + Date.now();
    if (_quizTimerId) clearInterval(_quizTimerId);
    _quizTimerId = setInterval(() => {
        _quizSeconds++;
        const t = document.getElementById('quiz-timer');
        if (t) t.textContent = formatQuizTime(_quizSeconds);
    }, 1000);
    document.getElementById('quiz-setup').style.display = 'none';
    document.getElementById('quiz-play').style.display = 'block';
    document.getElementById('quiz-done').style.display = 'none';
    renderQuizQuestion();
};

function renderQuizQuestion() {
    const play = document.getElementById('quiz-play');
    if (_quizIdx >= _quizQuestions.length) {
        finishQuiz();
        return;
    }
    const q = _quizQuestions[_quizIdx];
    play.innerHTML = `
        <div class="quiz-card glass">
            <div class="quiz-meta">
                <span>Questão ${_quizIdx + 1}/${_quizQuestions.length} · ${escapeHtml(q.area)}</span>
                <span id="quiz-timer" class="quiz-timer">${formatQuizTime(_quizSeconds)}</span>
            </div>
            <p class="quiz-stem">${escapeHtml(q.stem)}</p>
            <div class="quiz-options">
                ${q.options.map((o, i) => `<button type="button" class="quiz-opt" data-i="${i}">${escapeHtml(o)}</button>`).join('')}
            </div>
        </div>`;
    play.querySelectorAll('.quiz-opt').forEach(btn => {
        btn.onclick = () => onQuizPick(parseInt(btn.dataset.i, 10));
    });
}

function onQuizPick(chosen) {
    const q = _quizQuestions[_quizIdx];
    const ok = chosen === q.correct_index;
    if (ok) _quizCorrect++;
    _quizAnswers.push({ question: q.stem, area: q.area, chosen, correct_index: q.correct_index, ok, explanation: q.explanation });
    _quizIdx++;
    renderQuizQuestion();
}

function finishQuiz() {
    if (_quizTimerId) clearInterval(_quizTimerId);
    const total = _quizQuestions.length;
    const score = total ? Math.round((_quizCorrect / total) * 100) : 0;
    const attempt = {
        id: _quizAttemptId,
        area: document.getElementById('quiz-area-sel')?.value || 'Todas',
        score_pct: score,
        correct_count: _quizCorrect,
        total_count: total,
        duration_sec: _quizSeconds,
        finished_at: new Date().toISOString(),
        answers_json: JSON.stringify(_quizAnswers)
    };
    LocalDB.upsert('quiz_attempts', attempt);
    awardXP(Math.round(score / 5), 'Quiz ENEM: ' + score + '%');
    loadStudyStats();

    document.getElementById('quiz-play').style.display = 'none';
    const done = document.getElementById('quiz-done');
    done.style.display = 'block';
    const cls = score >= 70 ? 'good' : score >= 50 ? 'mid' : 'bad';
    const wrong = _quizAnswers.filter(a => !a.ok);
    done.innerHTML = `
        <div class="quiz-result glass">
            <h3>Resultado</h3>
            <div class="quiz-score ${cls}">${score}%</div>
            <p>${_quizCorrect}/${total} acertos · ${formatQuizTime(_quizSeconds)}</p>
            ${wrong.length ? `<div class="quiz-review">${wrong.slice(0, 3).map(w => `
                <div class="quiz-review-item">
                    <p>${escapeHtml(w.question)}</p>
                    <small>${escapeHtml(w.explanation)}</small>
                </div>`).join('')}</div>` : '<p style="color:var(--accent-green)">Perfeito! 🎉</p>'}
            <div class="quiz-result-actions">
                <button class="quiz-btn" onclick="quizToFlashcards()"><i class="fa-solid fa-clone"></i> Cards dos erros</button>
                <button class="quiz-btn secondary" onclick="startQuiz()">De novo</button>
                <button class="quiz-btn ghost" onclick="closeQuiz()">Fechar</button>
            </div>
        </div>`;
}

window.quizToFlashcards = function() {
    const wrong = _quizAnswers.filter(a => !a.ok);
    if (!wrong.length) { showToast('Nenhum erro para revisar.'); return; }
    wrong.forEach(w => {
        createFlashcard(w.question, w.explanation + ' (Resposta: ' + (ENEM_QUIZ_QUESTIONS.find(q => q.stem === w.question)?.options[w.correct_index] || '') + ')', null);
    });
    showToast(wrong.length + ' flashcards criados!');
    closeQuiz();
    showFlashcards();
};

window.ensureChartJs = async function() {
    if (typeof Chart !== 'undefined') return true;
    return new Promise((resolve) => {
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/chart.js';
        s.onload = () => resolve(true);
        s.onerror = () => resolve(false);
        document.head.appendChild(s);
    });
};

// ─── Settings: Appearance & Local Data ───────────────────────────

function changeThemeColor(colorHex) {
    document.documentElement.style.setProperty('--accent-primary', colorHex);
    document.documentElement.style.setProperty('--accent-blue', colorHex);
    document.documentElement.style.setProperty('--accent-purple', colorHex);
    localStorage.setItem('nexus_theme_color', colorHex);
    
    // Attempt to re-render charts to pick up new colors if active
    if (typeof renderFinanceCharts === 'function') renderFinanceCharts();
    if (typeof renderHabitCharts === 'function') renderHabitCharts();
    if (typeof renderStudyCharts === 'function') renderStudyCharts();
}

// Load saved theme on startup
document.addEventListener('DOMContentLoaded', () => {
    const savedColor = localStorage.getItem('nexus_theme_color');
    if (savedColor) changeThemeColor(savedColor);
});

function exportLocalDB() {
    const keys = Object.keys(localStorage);
    const dump = {};
    keys.forEach(k => {
        if (k.startsWith('nexus_') || k === 'habits' || k === 'tasks' || k === 'transactions' || k === 'notes') {
            dump[k] = localStorage.getItem(k);
        }
    });
    const blob = new Blob([JSON.stringify(dump, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nexus_backup_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
}

function importLocalDB(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const dump = JSON.parse(e.target.result);
            Object.keys(dump).forEach(k => {
                localStorage.setItem(k, dump[k]);
            });
            alert("Backup Restaurado com Sucesso! O aplicativo será recarregado.");
            window.location.reload();
        } catch (err) {
            alert("Erro ao importar arquivo JSON: Arquivo inválido.");
        }
    };
    reader.readAsText(file);
}

function clearLocalDB() {
    if (confirm("ATENÇÃO: Você está prestes a apagar TODOS os seus dados locais. Se eles não estiverem na nuvem, você os perderá para sempre. Tem certeza?")) {
        localStorage.clear();
        alert("Dados locais apagados.");
        window.location.reload();
    }
}

// ================================================================
// SPRINT 4 — NexusCalendar, CRUD forms, reminders, studies redesign
// ================================================================

(function() {
    const MONTH_NAMES = ['Janeiro','Fevereiro','Marco','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
    const todayISO = () => new Date().toISOString().split('T')[0];

    function getDailyBudget() {
        const el = document.getElementById('nexus_daily_budget');
        const fromEl = el && el.value ? parseFloat(el.value) : null;
        if (fromEl && fromEl > 0) return fromEl;
        const stored = parseFloat(localStorage.getItem('nexus_daily_budget') || '0');
        return stored > 0 ? stored : 100;
    }

    window.saveDailyBudget = function(val) {
        localStorage.setItem('nexus_daily_budget', String(val || 100));
        const el = document.getElementById('nexus_daily_budget');
        if (el) el.value = val;
    };

    function habitScheduledOnDay(habit, dateISO) {
        const dow = new Date(dateISO + 'T12:00:00').getDay();
        const days = habit.days_of_week || [1,2,3,4,5];
        if (Array.isArray(days) && days.length) return days.map(Number).includes(dow);
        return true;
    }

    function ratioColor(ratio, hasData) {
        if (!hasData) return 'hm-gray';
        if (ratio >= 1) return 'hm-green';
        if (ratio >= 0.5) return 'hm-orange';
        if (ratio > 0) return 'hm-orange';
        return 'hm-red';
    }

    function getFitnessPlanDays() {
        try {
            const parsed = JSON.parse(localStorage.getItem('nexus_fitness_plan_days') || '[1,2,3,4,5]');
            return Array.isArray(parsed) ? parsed.map(Number) : [1,2,3,4,5];
        } catch (e) { return [1,2,3,4,5]; }
    }

    window.NexusCalendar = {
        selectedDateISO: todayISO(),
        currentYear: new Date().getFullYear(),
        currentMonth: new Date().getMonth() + 1,
        activeModule: 'habits',
        onSelectCallback: null,
        _monthCache: null,

        getSelectedDate() { return this.selectedDateISO; },

        open(opts) {
            opts = opts || {};
            this.activeModule = opts.module || 'habits';
            this.onSelectCallback = opts.onSelect || null;
            const modal = document.getElementById('nexus-calendar-modal');
            if (modal) modal.style.display = 'flex';
            this.render();
        },

        close() {
            const modal = document.getElementById('nexus-calendar-modal');
            if (modal) modal.style.display = 'none';
        },

        changeMonth(delta) {
            this.currentMonth += delta;
            if (this.currentMonth < 1) { this.currentMonth = 12; this.currentYear--; }
            else if (this.currentMonth > 12) { this.currentMonth = 1; this.currentYear++; }
            this.render();
        },

        goToday() {
            this.currentYear = new Date().getFullYear();
            this.currentMonth = new Date().getMonth() + 1;
            this.selectDay(todayISO());
        },

        selectDay(dateISO) {
            this.selectedDateISO = dateISO;
            this.close();
            this.updateDateLabels();
            if (typeof this.onSelectCallback === 'function') this.onSelectCallback(dateISO);
        },

        updateDateLabels() {
            const d = new Date(this.selectedDateISO + 'T12:00:00');
            const label = this.selectedDateISO === todayISO() ? 'Hoje' : d.toLocaleDateString('pt-BR', { day: 'numeric', month: 'short' });
            ['habits-date-label','tasks-date-label','finance-date-label','fitness-date-label'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.textContent = label;
            });
        },

        buildMonthSummary(module, year, month) {
            const daysInMonth = new Date(year, month, 0).getDate();
            const summary = {};
            for (let d = 1; d <= daysInMonth; d++) {
                const dateISO = `${year}-${String(month).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
                summary[dateISO] = { color: 'hm-gray', ratio: 0, hasData: false };
            }

            if (module === 'habits') {
                const habits = (LocalDB.get('habits') || []).filter(h => h.active === 1 && !h.is_deleted);
                const logs = LocalDB.get('habit_logs') || [];
                const logsByDate = {};
                logs.forEach(l => {
                    if (!l.date || l.is_deleted) return;
                    if (!logsByDate[l.date]) logsByDate[l.date] = new Set();
                    logsByDate[l.date].add(String(l.habit_id));
                });
                Object.keys(summary).forEach(dateISO => {
                    const scheduled = habits.filter(h => habitScheduledOnDay(h, dateISO));
                    if (!scheduled.length) { summary[dateISO].color = 'hm-gray'; return; }
                    const done = scheduled.filter(h => logsByDate[dateISO] && logsByDate[dateISO].has(String(h.id))).length;
                    const ratio = done / scheduled.length;
                    summary[dateISO] = { ratio, hasData: true, color: ratioColor(ratio, true) };
                });
            } else if (module === 'tasks') {
                const tasks = (LocalDB.get('tasks') || []).filter(t => !t.is_deleted && t.due_date);
                Object.keys(summary).forEach(dateISO => {
                    const due = tasks.filter(t => t.due_date === dateISO);
                    if (!due.length) return;
                    const done = due.filter(t => t.done_at || t.status === 'done').length;
                    const ratio = done / due.length;
                    summary[dateISO] = { ratio, hasData: true, color: ratioColor(ratio, true) };
                });
            } else if (module === 'finance') {
                const budget = getDailyBudget();
                const tx = (LocalDB.get('finance_transactions') || []).filter(t => !t.is_deleted && t.type === 'expense');
                Object.keys(summary).forEach(dateISO => {
                    const spent = tx.filter(t => (t.occurred_at || t.date || t.created_at || '').split('T')[0] === dateISO)
                        .reduce((s, t) => s + Math.abs(Number(t.amount) || 0), 0);
                    if (spent <= 0) return;
                    const ratio = budget > 0 ? spent / budget : 1;
                    let color = 'hm-green';
                    if (ratio >= 1) color = 'hm-red';
                    else if (ratio >= 0.5) color = 'hm-orange';
                    summary[dateISO] = { ratio, hasData: true, color };
                });
            } else if (module === 'fitness') {
                const planDays = getFitnessPlanDays();
                const workouts = (LocalDB.get('fitness_workouts') || []).filter(w => !w.is_deleted);
                const workoutDates = new Set(workouts.map(w => (w.date || w.created_at || '').split('T')[0]).filter(Boolean));
                Object.keys(summary).forEach(dateISO => {
                    const dow = new Date(dateISO + 'T12:00:00').getDay();
                    const planned = planDays.includes(dow);
                    const logged = workoutDates.has(dateISO);
                    if (!planned && !logged) return;
                    if (planned && logged) summary[dateISO] = { ratio: 1, hasData: true, color: 'hm-green' };
                    else if (planned && !logged) summary[dateISO] = { ratio: 0, hasData: true, color: 'hm-red' };
                    else summary[dateISO] = { ratio: 0, hasData: true, color: 'hm-gray' };
                });
            }
            return summary;
        },

        render() {
            const grid = document.getElementById('nexus-cal-grid');
            const label = document.getElementById('nexus-cal-month-label');
            if (!grid) return;
            if (label) label.textContent = `${MONTH_NAMES[this.currentMonth - 1]} ${this.currentYear}`;
            this._monthCache = this.buildMonthSummary(this.activeModule, this.currentYear, this.currentMonth);
            grid.innerHTML = '';
            const firstDay = new Date(this.currentYear, this.currentMonth - 1, 1).getDay();
            const daysInMonth = new Date(this.currentYear, this.currentMonth, 0).getDate();
            for (let i = 0; i < firstDay; i++) {
                const empty = document.createElement('div');
                grid.appendChild(empty);
            }
            for (let d = 1; d <= daysInMonth; d++) {
                const dateISO = `${this.currentYear}-${String(this.currentMonth).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
                const dayData = this._monthCache[dateISO] || { color: 'hm-gray' };
                const box = document.createElement('button');
                box.type = 'button';
                box.className = 'nexus-cal-day ' + dayData.color + (dateISO === this.selectedDateISO ? ' active-day' : '');
                box.textContent = d;
                box.onclick = () => this.selectDay(dateISO);
                grid.appendChild(box);
            }
        }
    };

    // --- Habit fixes ---
    function getSelectedDate() {
        return (window.NexusCalendar && NexusCalendar.getSelectedDate()) || todayISO();
    }

    window.toggleHabitDirect = function(habitId, dateISO) {
        const targetDate = dateISO || getSelectedDate();
        const logs = LocalDB.getAll('habit_logs');
        const idx = logs.findIndex(l => String(l.habit_id) === String(habitId) && l.date === targetDate && !l.is_deleted);
        if (idx !== -1) {
            logs.splice(idx, 1);
            LocalDB.set('habit_logs', logs);
        } else {
            const entry = { id: Date.now(), habit_id: habitId, date: targetDate, completed_date: targetDate };
            LocalDB.upsert('habit_logs', entry);
            awardXP(5, 'Habito concluido');
        }
        if (typeof filterHabits === 'function') filterHabits(document.querySelector('#view-habits .study-chip.active')?.dataset?.filter || 'all');
        loadXPPanel();
        backgroundSync();
    };

    window.openHabitForm = function(habitId) {
        currentHabitId = habitId || null;
        const modal = document.getElementById('habit-detail-modal');
        const habits = LocalDB.get('habits') || [];
        const h = habitId ? habits.find(x => String(x.id) === String(habitId)) : null;
        document.getElementById('habit-form-title').textContent = h ? 'Editar Habito' : 'Novo Habito';
        document.getElementById('habit-form-name').value = h ? h.name : '';
        document.getElementById('habit-form-desc').value = h ? (h.description || '') : '';
        document.getElementById('habit-form-xp').value = h ? (h.xp_reward || 50) : 50;
        document.getElementById('habit-form-period').value = h ? (h.period || 'all') : 'morning';
        const reminder = h ? (h.alarm_time || h.target_time || '') : '';
        document.getElementById('habit-alarm-time').value = reminder ? reminder.substring(0, 5) : '';
        const days = h && h.days_of_week ? h.days_of_week.map(Number) : [1,2,3,4,5];
        document.querySelectorAll('#habit-form-dow .dow-btn').forEach(btn => {
            btn.classList.toggle('selected', days.includes(Number(btn.dataset.d)));
        });
        if (h) openHabitDetailStats(h);
        if (modal) modal.style.display = 'flex';
    };

    window.openHabitDetail = function(habitId) { openHabitForm(habitId); };

    function openHabitDetailStats(h) {
        const logs = LocalDB.get('habit_logs') || [];
        const sel = getSelectedDate();
        let streak = 0;
        const now = new Date();
        for (let i = 0; i < 60; i++) {
            const d = new Date(now); d.setDate(d.getDate() - i);
            const ds = d.toISOString().split('T')[0];
            if (logs.some(l => String(l.habit_id) === String(h.id) && l.date === ds)) streak++;
            else if (i > 0) break;
        }
        const total = logs.filter(l => String(l.habit_id) === String(h.id)).length;
        const isDone = logs.some(l => String(l.habit_id) === String(h.id) && l.date === sel);
        if (document.getElementById('habit-detail-streak')) document.getElementById('habit-detail-streak').textContent = streak;
        if (document.getElementById('habit-detail-total')) document.getElementById('habit-detail-total').textContent = total;
        const btn = document.getElementById('habit-detail-complete-btn');
        if (btn) {
            btn.innerHTML = isDone ? '<i class="fa-solid fa-xmark"></i> Desmarcar' : '<i class="fa-solid fa-check"></i> Feito';
        }
    }

    window.saveHabitForm = function() {
        const name = document.getElementById('habit-form-name')?.value?.trim();
        if (!name) { showToast('Nome obrigatorio'); return; }
        const days = [];
        document.querySelectorAll('#habit-form-dow .dow-btn.selected').forEach(b => days.push(Number(b.dataset.d)));
        const time = document.getElementById('habit-alarm-time')?.value || '';
        const payload = {
            name,
            description: document.getElementById('habit-form-desc')?.value || '',
            xp_reward: parseInt(document.getElementById('habit-form-xp')?.value || '50', 10),
            period: document.getElementById('habit-form-period')?.value || 'all',
            days_of_week: days.length ? days : [1,2,3,4,5],
            alarm_time: time,
            target_time: time,
            active: 1
        };
        if (currentHabitId) {
            const habits = LocalDB.get('habits');
            const idx = habits.findIndex(h => String(h.id) === String(currentHabitId));
            if (idx !== -1) { habits[idx] = { ...habits[idx], ...payload }; LocalDB.set('habits', habits); }
        } else {
            LocalDB.upsert('habits', { id: Date.now(), ...payload, created_at: new Date().toISOString() });
        }
        syncHabitReminders();
        closeHabitDetail();
        loadHabits();
        backgroundSync();
        showToast('Habito salvo!');
    };

    document.querySelectorAll('#habit-form-dow .dow-btn').forEach(btn => {
        btn.addEventListener('click', () => btn.classList.toggle('selected'));
    });

    window.saveHabitAlarm = function() {
        if (!currentHabitId) return;
        const time = document.getElementById('habit-alarm-time')?.value || '';
        const habits = LocalDB.get('habits');
        const idx = habits.findIndex(h => String(h.id) === String(currentHabitId));
        if (idx !== -1) {
            habits[idx].alarm_time = time;
            habits[idx].target_time = time;
            LocalDB.set('habits', habits);
            syncHabitReminders();
        }
    };

    window.filterHabits = function(filter, btn) {
        document.querySelectorAll('#view-habits .study-chip').forEach(b => b.classList.remove('active'));
        if (btn) btn.classList.add('active');
        const container = document.getElementById('habits-list');
        if (!container) return;
        let habits = (LocalDB.get('habits') || []).filter(h => !h.is_deleted);
        if (filter === 'archived') habits = habits.filter(h => h.active === 0);
        else habits = habits.filter(h => h.active === 1);
        if (filter === 'morning') habits = habits.filter(h => h.period === 'morning');
        else if (filter === 'afternoon') habits = habits.filter(h => h.period === 'afternoon');
        else if (filter === 'night') habits = habits.filter(h => h.period === 'night');
        const logs = LocalDB.get('habit_logs') || [];
        const sel = getSelectedDate();
        if (!habits.length) {
            container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;">Nenhum habito nesta categoria.</div>';
            return;
        }
        container.innerHTML = habits.map(h => {
            const isDone = logs.some(l => String(l.habit_id) === String(h.id) && l.date === sel);
            const streak = computeHabitStreak(h.id, logs);
            const rate = computeHabitCompletionRate(h.id, logs, 30);
            return `<div class="list-item glass ${isDone ? 'done' : ''}" style="cursor:pointer" onclick="openHabitDetail('${h.id}')">
                <div class="item-main"><div class="item-title">${escapeHtml(h.name)}</div>
                <div class="item-subtitle">🔥 ${streak} dias · ${rate}% (30d) · ${sel === todayISO() ? 'Hoje' : sel}</div></div>
                <button class="icon-btn" onclick="event.stopPropagation();openHabitDetail('${h.id}')" aria-label="Editar"><i class="fa-solid fa-pen"></i></button>
                <button class="icon-btn" onclick="event.stopPropagation();deleteHabitFromGrid('${h.id}')" aria-label="Excluir" style="color:var(--accent-pink)"><i class="fa-solid fa-trash"></i></button>
                <button class="icon-btn ${isDone ? 'done' : ''}" onclick="event.stopPropagation();toggleHabitDirect('${h.id}')"><i class="fa-solid ${isDone ? 'fa-check' : 'fa-plus'}"></i></button>
            </div>`;
        }).join('');
    };

    function computeHabitStreak(habitId, logs) {
        logs = logs || LocalDB.get('habit_logs') || [];
        let streak = 0;
        const d = new Date();
        for (let i = 0; i < 365; i++) {
            const iso = d.toISOString().split('T')[0];
            if (logs.some(l => String(l.habit_id) === String(habitId) && l.date === iso)) streak++;
            else if (i > 0) break;
            d.setDate(d.getDate() - 1);
        }
        return streak;
    }

    function computeHabitCompletionRate(habitId, logs, days) {
        logs = logs || LocalDB.get('habit_logs') || [];
        const habits = LocalDB.get('habits') || [];
        const h = habits.find(x => String(x.id) === String(habitId));
        let scheduled = 0, done = 0;
        const d = new Date();
        for (let i = 0; i < days; i++) {
            const iso = d.toISOString().split('T')[0];
            if (h && typeof habitScheduledOnDay === 'function' && habitScheduledOnDay(h, iso)) {
                scheduled++;
                if (logs.some(l => String(l.habit_id) === String(habitId) && l.date === iso)) done++;
            }
            d.setDate(d.getDate() - 1);
        }
        return scheduled ? Math.round((done / scheduled) * 100) : 0;
    }

    function renderHabitChartsFixed() {
        if (typeof Chart === 'undefined') return;
        if (typeof initChartDefaults === 'function') initChartDefaults();
        const habits = (LocalDB.get('habits') || []).filter(h => h.active === 1 && !h.is_deleted);
        const logs = LocalDB.get('habit_logs') || [];
        const labels = [], percentages = [];
        for (let i = 13; i >= 0; i--) {
            const d = new Date(); d.setDate(d.getDate() - i);
            const iso = d.toISOString().split('T')[0];
            labels.push(d.getDate() + '/' + (d.getMonth()+1));
            const scheduled = habits.filter(h => habitScheduledOnDay(h, iso));
            if (!scheduled.length) { percentages.push(0); continue; }
            const done = scheduled.filter(h => logs.some(l => String(l.habit_id) === String(h.id) && l.date === iso)).length;
            percentages.push(Math.round((done / scheduled.length) * 100));
        }
        if (typeof safeDestroyChart === 'function') safeDestroyChart('habits-line-chart');
        const ctx = document.getElementById('habits-line-chart');
        if (ctx && typeof Chart !== 'undefined') {
            window._chartInstances = window._chartInstances || {};
            window._chartInstances['habits-line-chart'] = new Chart(ctx, {
                type: 'line',
                data: { labels, datasets: [{ label: 'Aderencia (%)', data: percentages, borderColor: '#a78bfa', backgroundColor: 'rgba(167,139,250,0.1)', fill: true, tension: 0.4 }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100 } } }
            });
        }
    }
    window.renderHabitCharts = renderHabitChartsFixed;

    // --- Task enhancements ---
    window.openTaskForm = function() {
        LocalDB.upsert('tasks', { id: Date.now(), name: 'Nova tarefa', title: 'Nova tarefa', priority: 'medium', status: 'todo', created_at: new Date().toISOString() });
        const tasks = LocalDB.get('tasks');
        const t = tasks[tasks.length - 1];
        openTaskDetail(t.id);
    };

    window.completeCurrentTask = function() {
        if (!currentTaskId) return;
        toggleTaskDirect(currentTaskId);
        closeTaskDetail();
    };

    window.addSubtaskInline = function() {
        const modal = document.getElementById('subtask-inline-modal');
        if (modal) { modal.style.display = 'flex'; document.getElementById('subtask-inline-name').value = ''; }
    };

    window.confirmSubtaskInline = function() {
        const name = document.getElementById('subtask-inline-name')?.value?.trim();
        if (!name || !currentTaskId) return;
        const tasks = LocalDB.get('tasks');
        const t = tasks.find(x => String(x.id) === String(currentTaskId));
        if (t) {
            if (!t.subtasks) t.subtasks = [];
            t.subtasks.push({ name, done: false });
            if (t.subtasks_json) t.subtasks_json = t.subtasks;
            LocalDB.set('tasks', tasks);
            renderSubtasks(t.subtasks);
        }
        document.getElementById('subtask-inline-modal').style.display = 'none';
    };

    window.addSubtask = window.addSubtaskInline;

    const _saveTaskDetailOrig = window.saveTaskDetail;
    window.saveTaskDetail = function() {
        if (!currentTaskId) return;
        const tasks = LocalDB.get('tasks');
        const t = tasks.find(x => String(x.id) === String(currentTaskId));
        if (!t) return;
        t.name = document.getElementById('task-detail-name')?.value || t.name;
        t.title = t.name;
        t.priority = document.getElementById('task-detail-priority')?.value || 'medium';
        t.status = document.getElementById('task-detail-status')?.value || 'todo';
        t.due_date = document.getElementById('task-detail-due')?.value || null;
        t.description = document.getElementById('task-detail-description')?.value || '';
        t.notify_enabled = document.getElementById('task-detail-notify-enabled')?.checked ? 1 : 0;
        const notifyAt = document.getElementById('task-detail-notify-at')?.value;
        t.notify_at = notifyAt ? new Date(notifyAt).toISOString() : null;
        t.subtasks_json = t.subtasks || [];
        LocalDB.set('tasks', tasks);
        syncTaskReminders();
        if (typeof _saveTaskDetailOrig === 'function') _saveTaskDetailOrig();
    };

    const _openTaskDetailOrig = window.openTaskDetail;
    window.openTaskDetail = function(taskId) {
        currentTaskId = taskId;
        const tasks = LocalDB.get('tasks');
        const t = tasks.find(x => String(x.id) === String(taskId));
        if (!t) return;
        const modal = document.getElementById('task-detail-modal');
        document.getElementById('task-detail-name').value = t.name || t.title || '';
        document.getElementById('task-detail-description').value = t.description || '';
        document.getElementById('task-detail-priority').value = t.priority || 'medium';
        document.getElementById('task-detail-status').value = t.status || (t.done_at ? 'done' : 'todo');
        document.getElementById('task-detail-due').value = t.due_date || '';
        document.getElementById('task-detail-notify-enabled').checked = !!t.notify_enabled;
        if (t.notify_at) {
            const nd = new Date(t.notify_at);
            document.getElementById('task-detail-notify-at').value = nd.toISOString().slice(0, 16);
        }
        const subs = t.subtasks || t.subtasks_json || [];
        t.subtasks = Array.isArray(subs) ? subs : [];
        renderSubtasks(t.subtasks);
        if (modal) modal.style.display = 'flex';
    };

    window.filterTasks = function(filter, btn) {
        if (btn) {
            document.querySelectorAll('#view-tasks .study-chip').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        }
        if (taskKanbanMode) { renderTaskKanban(); return; }
        const container = document.getElementById('tasks-list-view');
        if (!container) return;
        let tasks = (LocalDB.get('tasks') || []).filter(t => !t.is_deleted);
        const sel = getSelectedDate();
        if (filter === 'done') tasks = tasks.filter(t => t.done_at);
        else tasks = tasks.filter(t => !t.done_at);
        if (filter === 'today') tasks = tasks.filter(t => t.due_date === sel || t.due_date === todayISO());
        if (filter === 'high') tasks = tasks.filter(t => t.priority === 'high');
        if (NexusCalendar.activeModule === 'tasks' && sel !== todayISO()) {
            tasks = tasks.filter(t => t.due_date === sel);
        }
        if (!tasks.length) {
            container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;">Nenhuma tarefa.</div>';
            return;
        }
        container.innerHTML = tasks.map(t => {
            const isDone = !!t.done_at;
            return `<div class="list-item glass" onclick="openTaskDetail('${t.id}')">
                <div class="item-main"><div class="item-title" style="text-decoration:${isDone?'line-through':'none'}">${escapeHtml(t.name || t.title)}</div></div>
                <button class="icon-btn" onclick="event.stopPropagation();openTaskDetail('${t.id}')" aria-label="Editar"><i class="fa-solid fa-pen"></i></button>
                <button class="icon-btn" onclick="event.stopPropagation();deleteTaskFromGrid('${t.id}')" aria-label="Excluir" style="color:var(--accent-pink)"><i class="fa-solid fa-trash"></i></button>
                <button class="icon-btn" onclick="event.stopPropagation();toggleTaskDirect('${t.id}')"><i class="fa-solid fa-check"></i></button>
            </div>`;
        }).join('');
    };

    window.completeCurrentHabit = function() {
        if (!currentHabitId) return;
        toggleHabitDirect(currentHabitId, getSelectedDate());
        closeHabitDetail();
    };

    window.deleteHabitFromGrid = function(habitId) {
        if (!confirm('Excluir este hábito?')) return;
        const habits = LocalDB.get('habits') || [];
        const h = habits.find(x => String(x.id) === String(habitId));
        if (h) {
            h.is_deleted = 1;
            h.active = 0;
            LocalDB.set('habits', habits);
            if (typeof syncHabitReminders === 'function') syncHabitReminders();
            if (typeof backgroundSync === 'function') backgroundSync();
        }
        if (typeof loadHabits === 'function') loadHabits();
    };

    window.deleteTaskFromGrid = function(taskId) {
        currentTaskId = taskId;
        if (typeof deleteCurrentTask === 'function') deleteCurrentTask();
    };

    // --- Native reminders ---
    function scheduleNativeReminder(id, title, body, triggerAtMs, isAlarm) {
        if (window.AndroidNative && typeof AndroidNative.scheduleAlarm === 'function') {
            AndroidNative.scheduleAlarm(id, title, body, triggerAtMs, !!isAlarm, 5, 3);
        } else if (window.AndroidNative && typeof AndroidNative.scheduleReminder === 'function') {
            AndroidNative.scheduleReminder(id, title, body, triggerAtMs);
        }
    }

    function cancelNativeReminder(id) {
        if (window.AndroidNative && typeof AndroidNative.cancelReminder === 'function') {
            AndroidNative.cancelReminder(id);
        }
    }

    window.syncTaskReminders = function() {
        const tasks = (LocalDB.get('tasks') || []).filter(t => !t.is_deleted);
        tasks.forEach(t => {
            const rid = parseInt(String(t.id).replace(/\D/g,'').slice(-7) || '0', 10) || Math.abs(Number(t.id) % 100000);
            if (t.notify_enabled && t.notify_at && !t.done_at) {
                const ms = new Date(t.notify_at).getTime();
                if (ms > Date.now()) scheduleNativeReminder(rid, t.name || 'Tarefa', t.description || 'Lembrete de tarefa', ms, false);
                else cancelNativeReminder(rid);
            } else cancelNativeReminder(rid);
        });
    };

    window.syncHabitReminders = function() {
        const habits = (LocalDB.get('habits') || []).filter(h => h.active === 1 && !h.is_deleted);
        const logs = LocalDB.get('habit_logs') || [];
        const td = todayISO();
        habits.forEach(h => {
            const time = h.alarm_time || h.target_time;
            if (!time) return;
            const rid = 200000 + (parseInt(String(h.id).replace(/\D/g,'').slice(-5) || '0', 10) % 50000);
            const doneToday = logs.some(l => String(l.habit_id) === String(h.id) && l.date === td);
            if (doneToday) { cancelNativeReminder(rid); return; }
            const [hh, mm] = time.substring(0, 5).split(':').map(Number);
            const trigger = new Date();
            trigger.setHours(hh, mm, 0, 0);
            if (trigger.getTime() <= Date.now()) trigger.setDate(trigger.getDate() + 1);
            scheduleNativeReminder(rid, 'Hora do Habito', h.name, trigger.getTime(), false);
        });
    };

    const _pendingReminders = [];
    window.checkPendingReminders = function() {
        const now = Date.now();
        const tasks = (LocalDB.get('tasks') || []).filter(t => t.notify_enabled && t.notify_at && !t.done_at && !t.is_deleted);
        tasks.forEach(t => {
            const ms = new Date(t.notify_at).getTime();
            const key = 'task-' + t.id;
            if (ms <= now && ms > now - 60000 && !_pendingReminders.includes(key)) {
                _pendingReminders.push(key);
                sendLocalNotification(t.name || 'Tarefa', t.description || 'Lembrete');
            }
        });
    };

    function checkHabitAlarmsFixed() {
        if (typeof notificationsEnabled === 'function' && !notificationsEnabled()) return;
        const now = new Date();
        const timeStr = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
        const td = todayISO();
        const dow = now.getDay();
        const logs = LocalDB.get('habit_logs') || [];
        (LocalDB.get('habits') || []).filter(h => h.active === 1 && !h.is_deleted).forEach(habit => {
            const t = habit.alarm_time || habit.target_time;
            if (!t || t.substring(0, 5) !== timeStr) return;
            let days = [0,1,2,3,4,5,6];
            if (Array.isArray(habit.days_of_week)) days = habit.days_of_week;
            else if (habit.days_of_week) { try { days = JSON.parse(habit.days_of_week); } catch (_) {} }
            if (!days.includes(dow)) return;
            if (logs.some(l => String(l.habit_id) === String(habit.id) && l.date === td)) return;
            sendLocalNotification('Hora do Habito!', habit.name);
            playBeep(600, 300);
        });
        checkPendingReminders();
    }
    window.checkHabitAlarms = checkHabitAlarmsFixed;

    // --- saveQuickAdd fix ---
    window.saveQuickAdd = function() {
        const type = document.getElementById('create-type').value;
        const title = document.getElementById('create-title').value.trim();
        if (!title) { alert('O titulo e obrigatorio.'); return; }
        if (type === 'task') {
            LocalDB.upsert('tasks', {
                id: Date.now(),
                name: title,
                title: title,
                priority: 'medium',
                status: 'todo',
                points_reward: 10,
                created_at: new Date().toISOString()
            });
            loadTasks();
        } else {
            const time = document.getElementById('create-time')?.value || '';
            const desc = document.getElementById('create-desc')?.value || '';
            const freq = document.getElementById('create-freq')?.value || 'daily';
            const icon = document.getElementById('create-icon')?.value || 'fa-fire';
            const xp = parseInt(document.getElementById('create-xp')?.value || '50', 10);
            let days = [1,2,3,4,5];
            if (freq === 'weekdays') days = [1,2,3,4,5];
            else if (freq === 'weekends') days = [0,6];
            else days = [0,1,2,3,4,5,6];
            LocalDB.upsert('habits', {
                id: Date.now(),
                name: title,
                description: desc,
                active: 1,
                target_time: time,
                alarm_time: time,
                icon,
                xp_reward: xp,
                days_of_week: days,
                period: 'morning',
                created_at: new Date().toISOString()
            });
            loadHabits();
            syncHabitReminders();
        }
        closeCreateModal();
        backgroundSync();
    };

    // --- Goals form ---
    let editingGoalId = null;
    window.openGoalForm = function(goalId) {
        editingGoalId = goalId || null;
        const goals = LocalDB.get('nexus_goals') || [];
        const g = goalId ? goals.find(x => String(x.id) === String(goalId)) : null;
        document.getElementById('goal-form-title').textContent = g ? 'Editar Meta' : 'Nova Meta';
        document.getElementById('goal-form-name').value = g ? g.name : '';
        document.getElementById('goal-form-description').value = g ? (g.description || '') : '';
        document.getElementById('goal-form-target-date').value = g ? (g.target_date || '') : '';
        document.getElementById('goal-form-progress').value = g ? (g.progress || 0) : 0;
        document.getElementById('goal-form-progress-label').textContent = g ? (g.progress || 0) : 0;
        document.getElementById('goal-form-status').value = g ? (g.status || 'active') : 'active';
        document.getElementById('goal-form-delete-btn').style.display = g ? 'block' : 'none';
        document.getElementById('goal-form-modal').style.display = 'flex';
    };

    window.closeGoalForm = function() {
        editingGoalId = null;
        const modal = document.getElementById('goal-form-modal');
        if (modal) modal.style.display = 'none';
    };

    window.saveGoalForm = function() {
        const name = document.getElementById('goal-form-name')?.value?.trim();
        if (!name) return;
        const payload = {
            name,
            description: document.getElementById('goal-form-description')?.value || '',
            target_date: document.getElementById('goal-form-target-date')?.value || null,
            progress: parseInt(document.getElementById('goal-form-progress')?.value || '0', 10),
            status: document.getElementById('goal-form-status')?.value || 'active'
        };
        if (payload.progress >= 100) payload.status = 'achieved';
        if (editingGoalId) {
            const goals = LocalDB.get('nexus_goals');
            const idx = goals.findIndex(g => String(g.id) === String(editingGoalId));
            if (idx !== -1) { goals[idx] = { ...goals[idx], ...payload }; LocalDB.set('nexus_goals', goals); }
        } else {
            LocalDB.upsert('nexus_goals', { id: Date.now(), ...payload });
        }
        document.getElementById('goal-form-modal').style.display = 'none';
        editingGoalId = null;
        loadGoals();
    };

    window.deleteGoalForm = function() {
        if (!editingGoalId) return;
        const goals = LocalDB.get('nexus_goals');
        const idx = goals.findIndex(g => String(g.id) === String(editingGoalId));
        if (idx !== -1) { goals[idx].is_deleted = true; LocalDB.set('nexus_goals', goals); }
        document.getElementById('goal-form-modal').style.display = 'none';
        editingGoalId = null;
        loadGoals();
    };

    window.promptAddGoal = function() { openGoalForm(); };

    window.loadGoals = function() {
        const container = document.getElementById('goals-list');
        if (!container) return;
        const all = (LocalDB.get('nexus_goals') || []).filter(t => !t.is_deleted);
        const active = all.filter(t => t.status !== 'achieved');
        const archived = all.filter(t => t.status === 'achieved');
        container.innerHTML = active.length ? active.map(t => `
            <div class="list-item glass" onclick="openGoalForm(${t.id})" style="cursor:pointer">
                <div class="item-main"><span class="item-title">${escapeHtml(t.name)}</span>
                <span class="item-subtitle">${t.progress || 0}% · ${t.description || ''}</span></div>
            </div>`).join('') : '<div style="text-align:center;color:var(--text-secondary);padding:20px">Sem metas ativas.<button onclick="openGoalForm()" style="margin-top:12px;background:var(--accent-primary);border:none;color:white;padding:10px 18px;border-radius:8px">Criar meta</button></div>';
        const archSec = document.getElementById('goals-archived-section');
        const archList = document.getElementById('goals-archived-list');
        if (archived.length && archSec && archList) {
            archSec.style.display = 'block';
            archList.innerHTML = archived.map(t => `<div class="list-item glass" onclick="openGoalForm(${t.id})" style="opacity:0.7;cursor:pointer"><div class="item-main"><span class="item-title">${escapeHtml(t.name)}</span></div></div>`).join('');
        } else if (archSec) archSec.style.display = 'none';
    };

    // --- Workout form ---
    let editingWorkoutId = null;
    window.openWorkoutForm = function(workoutId) {
        editingWorkoutId = workoutId || null;
        const workouts = LocalDB.get('fitness_workouts') || [];
        const w = workoutId ? workouts.find(x => String(x.id) === String(workoutId)) : null;
        document.getElementById('workout-form-title').textContent = w ? 'Editar Treino' : 'Novo Treino';
        document.getElementById('workout-form-name').value = w ? (w.name || '') : '';
        document.getElementById('workout-form-muscle').value = w ? (w.muscle_group || '') : '';
        document.getElementById('workout-form-date').value = w ? (w.date || todayISO()) : todayISO();
        document.getElementById('workout-form-duration').value = w ? (w.duration_minutes || '') : '';
        document.getElementById('workout-form-calories').value = w ? (w.calories || '') : '';
        document.getElementById('workout-form-notes').value = w ? (w.notes || '') : '';
        renderWorkoutExercises(w ? (w.exercises || []) : []);
        document.getElementById('workout-form-delete-btn').style.display = w ? 'block' : 'none';
        document.getElementById('workout-form-modal').style.display = 'flex';
    };

    window.openWorkoutBuilder = function() { openWorkoutForm(); };

    window.closeWorkoutForm = function() {
        document.getElementById('workout-form-modal').style.display = 'none';
        editingWorkoutId = null;
    };

    let editingFinanceId = null;
    window.openFinanceForm = function(txId) {
        editingFinanceId = txId || null;
        const txs = LocalDB.get('finance_transactions') || [];
        const t = txId ? txs.find(x => String(x.id) === String(txId)) : null;
        document.getElementById('finance-form-title').textContent = t ? 'Editar Transação' : 'Nova Transação';
        document.getElementById('finance-form-desc').value = t ? (t.description || '') : '';
        document.getElementById('finance-form-amount').value = t ? (t.amount || '') : '';
        document.getElementById('finance-form-type').value = t ? (t.type || 'expense') : 'expense';
        document.getElementById('finance-form-category').value = t ? (t.category || 'other') : 'other';
        document.getElementById('finance-form-date').value = t
            ? (t.occurred_at || t.created_at || '').split('T')[0]
            : todayISO();
        document.getElementById('finance-form-delete-btn').style.display = t ? 'block' : 'none';
        document.getElementById('finance-form-modal').style.display = 'flex';
    };

    window.closeFinanceForm = function() {
        document.getElementById('finance-form-modal').style.display = 'none';
        editingFinanceId = null;
    };

    window.saveFinanceForm = function() {
        const desc = document.getElementById('finance-form-desc')?.value?.trim();
        const amount = parseFloat(document.getElementById('finance-form-amount')?.value || '0');
        if (!desc || !amount) { showToast('Preencha descrição e valor.'); return; }
        const payload = {
            description: desc,
            amount,
            category: document.getElementById('finance-form-category')?.value || 'other',
            type: document.getElementById('finance-form-type')?.value || 'expense',
            occurred_at: (document.getElementById('finance-form-date')?.value || todayISO()) + 'T12:00:00'
        };
        if (editingFinanceId) {
            const txs = LocalDB.get('finance_transactions');
            const idx = txs.findIndex(x => String(x.id) === String(editingFinanceId));
            if (idx !== -1) { txs[idx] = { ...txs[idx], ...payload }; LocalDB.set('finance_transactions', txs); }
        } else {
            LocalDB.upsert('finance_transactions', { id: Date.now(), ...payload, created_at: new Date().toISOString() });
        }
        closeFinanceForm();
        loadFinances();
        if (typeof backgroundSync === 'function') backgroundSync();
    };

    window.deleteFinanceForm = function() {
        if (!editingFinanceId) return;
        const txs = LocalDB.get('finance_transactions');
        const idx = txs.findIndex(x => String(x.id) === String(editingFinanceId));
        if (idx !== -1) { txs[idx].is_deleted = 1; LocalDB.set('finance_transactions', txs); }
        closeFinanceForm();
        loadFinances();
    };

    function renderWorkoutExercises(exs) {
        const list = document.getElementById('workout-exercises-list');
        if (!list) return;
        window._workoutExercises = exs || [];
        list.innerHTML = window._workoutExercises.map((e, i) => `
            <div style="background:rgba(255,255,255,0.04);padding:10px;border-radius:8px;margin-bottom:6px">
                <div style="display:flex;gap:8px;align-items:center;margin-bottom:6px">
                    <span style="flex:1;font-size:0.85rem;font-weight:600">${escapeHtml(e.name || e)}</span>
                    <button onclick="removeWorkoutExercise(${i})" style="background:none;border:none;color:var(--text-secondary)"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px">
                    <input type="number" min="1" placeholder="Séries" value="${e.sets || ''}" onchange="updateWorkoutExercise(${i},'sets',this.value)" style="padding:6px;border-radius:6px;background:rgba(0,0,0,0.3);color:white;border:1px solid var(--border-glass);font-size:0.8rem">
                    <input type="number" min="1" placeholder="Reps" value="${e.reps || ''}" onchange="updateWorkoutExercise(${i},'reps',this.value)" style="padding:6px;border-radius:6px;background:rgba(0,0,0,0.3);color:white;border:1px solid var(--border-glass);font-size:0.8rem">
                    <input type="number" min="0" step="0.5" placeholder="Kg" value="${e.weight || ''}" onchange="updateWorkoutExercise(${i},'weight',this.value)" style="padding:6px;border-radius:6px;background:rgba(0,0,0,0.3);color:white;border:1px solid var(--border-glass);font-size:0.8rem">
                </div>
            </div>`).join('');
    }

    window.updateWorkoutExercise = function(i, field, val) {
        if (!window._workoutExercises || !window._workoutExercises[i]) return;
        window._workoutExercises[i][field] = field === 'weight' ? parseFloat(val) : parseInt(val, 10);
    };

    window.addWorkoutExercise = function() {
        const name = prompt('Nome do exercicio:');
        if (!name) return;
        window._workoutExercises = window._workoutExercises || [];
        window._workoutExercises.push({ name: name.trim(), sets: 3, reps: 10, weight: 0 });
        renderWorkoutExercises(window._workoutExercises);
    };

    window.removeWorkoutExercise = function(i) {
        window._workoutExercises.splice(i, 1);
        renderWorkoutExercises(window._workoutExercises);
    };

    window.saveWorkoutForm = function() {
        const name = document.getElementById('workout-form-name')?.value?.trim();
        if (!name) return;
        const payload = {
            name,
            muscle_group: document.getElementById('workout-form-muscle')?.value || '',
            date: document.getElementById('workout-form-date')?.value || todayISO(),
            duration_minutes: parseInt(document.getElementById('workout-form-duration')?.value || '0', 10) || null,
            calories: parseInt(document.getElementById('workout-form-calories')?.value || '0', 10) || null,
            notes: document.getElementById('workout-form-notes')?.value || '',
            exercises: window._workoutExercises || []
        };
        if (editingWorkoutId) {
            const workouts = LocalDB.get('fitness_workouts');
            const idx = workouts.findIndex(w => String(w.id) === String(editingWorkoutId));
            if (idx !== -1) { workouts[idx] = { ...workouts[idx], ...payload }; LocalDB.set('fitness_workouts', workouts); }
        } else {
            LocalDB.upsert('fitness_workouts', { id: Date.now(), ...payload, created_at: new Date().toISOString() });
            awardXP(25, 'Treino registrado');
        }
        document.getElementById('workout-form-modal').style.display = 'none';
        editingWorkoutId = null;
        loadFitness();
    };

    window.deleteWorkoutForm = function() {
        if (!editingWorkoutId) return;
        const workouts = LocalDB.get('fitness_workouts');
        const idx = workouts.findIndex(w => String(w.id) === String(editingWorkoutId));
        if (idx !== -1) { workouts[idx].is_deleted = true; LocalDB.set('fitness_workouts', workouts); }
        document.getElementById('workout-form-modal').style.display = 'none';
        editingWorkoutId = null;
        loadFitness();
    };

    window.loadFitness = function() {
        const container = document.getElementById('fitness-list');
        if (!container) return;
        if (typeof renderWorkoutTemplates === 'function') renderWorkoutTemplates();
        updateFitnessStats();
        const data = (LocalDB.get('fitness_workouts') || []).filter(t => !t.is_deleted)
            .sort((a, b) => (b.date || b.created_at || '').localeCompare(a.date || a.created_at || ''));
        container.innerHTML = data.length ? data.slice(0, 15).map(t => `
            <div class="list-item glass" onclick="openWorkoutForm(${t.id})" style="cursor:pointer">
                <div class="item-main"><span class="item-title">${escapeHtml(t.name || 'Treino')}</span>
                <span class="item-subtitle">${escapeHtml(t.muscle_group || '')} · ${t.duration_minutes || ''} min</span></div>
            </div>`).join('') : '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;">Nenhum treino.</div>';
    };

    // --- Studies: subjects grid (usa funções globais renderSubjectFolderCard / openSubjectDetail) ---
    window.loadSubjectsGrid = loadSubjectsGrid;

    window.openNewNotebook = window.openSubjectForm;

    window.openSubjectMenu = function(ev) {
        if (!currentNotebookId) return;
        openFolderMenu(ev, currentNotebookId);
    };

    window.changeSubjectCover = function() {
        if (currentNotebookId) openStudyEditSheet('folder', currentNotebookId);
        closeStudyContextMenus();
    };

    window.renameSubject = function() {
        if (currentNotebookId) openStudyEditSheet('folder', currentNotebookId);
        closeStudyContextMenus();
    };

    window.deleteSubject = function() {
        if (!currentNotebookId || !confirm('Excluir matéria? As notas ficam sem pasta.')) return;
        const notebooks = (LocalDB.get('study_notebooks') || []).filter(n => String(n.id) !== String(currentNotebookId));
        LocalDB.set('study_notebooks', notebooks);
        closeSubjectDetail();
        loadStudies();
        closeStudyContextMenus();
    };

    window.deleteStudyNote = function() {
        const id = window._menuNoteId;
        if (!id || !confirm('Excluir esta nota?')) return;
        const notes = LocalDB.get('study_notes') || [];
        const idx = notes.findIndex(n => String(n.id) === String(id));
        if (idx !== -1) { notes[idx].is_deleted = 1; LocalDB.set('study_notes', notes); }
        closeStudyContextMenus();
        if (currentNotebookId) openSubjectDetail(currentNotebookId);
        loadStudies();
    };

    function extractNoteTitleFromEditor() {
        const editor = document.getElementById('note-content-rich');
        if (!editor) return 'Sem titulo';
        const h1 = editor.querySelector('h1');
        if (h1 && h1.textContent.trim()) return h1.textContent.trim();
        const text = (editor.innerText || '').trim().split('\n').find(l => l.trim());
        return text ? text.substring(0, 80) : 'Sem titulo';
    }

    window.saveNote = function() {
        const editor = document.getElementById('note-content-rich');
        const hidden = document.getElementById('note-content');
        if (editor && hidden) hidden.value = editor.innerHTML;
        const title = extractNoteTitleFromEditor();
        const content = hidden ? hidden.value : '';
        const tags = document.getElementById('note-tags')?.value || '';
        let jarvisSubject = document.getElementById('note-subject')?.value?.trim() || '';
        const notebookId = document.getElementById('note-notebook')?.value || currentNotebookId || '';
        if (!title && !content) { showInAppNotification('Escreva algo primeiro!', 'warn'); return; }
        const notes = LocalDB.get('study_notes') || [];
        const now = new Date().toISOString();
        if (!jarvisSubject && notebookId && typeof inferJarvisNoteSubject === 'function') {
            jarvisSubject = inferJarvisNoteSubject(title, content, notebookId, editingNoteId);
        }
        const description = stripHtmlText(content).substring(0, 160);
        if (editingNoteId) {
            const idx = notes.findIndex(n => String(n.id) === String(editingNoteId));
            if (idx !== -1) notes[idx] = {
                ...notes[idx], title, content, tags, subject: jarvisSubject, jarvis_subject: jarvisSubject,
                description, notebook_id: notebookId, updated_at: now
            };
        } else {
            notes.push({
                id: Date.now().toString(), title, content, tags, subject: jarvisSubject, jarvis_subject: jarvisSubject,
                description, notebook_id: notebookId, created_at: now, updated_at: now
            });
            awardXP(15, 'Nova nota');
        }
        LocalDB.set('study_notes', notes);
        if (window._tempCoverImage || window._tempIcon) {
            const saved = editingNoteId ? notes.find(n => String(n.id) === String(editingNoteId)) : notes[notes.length - 1];
            if (saved) {
                if (window._tempCoverImage) { saved.cover_image = window._tempCoverImage; window._tempCoverImage = null; }
                if (window._tempIcon) { saved.icon = window._tempIcon; window._tempIcon = null; }
                LocalDB.set('study_notes', notes);
            }
        }
        closeNoteEditor();
        loadStudies();
        showInAppNotification('Nota salva!', 'success');
    };

    window.insertYouTubeEmbed = function() {
        const raw = document.getElementById('yt-url-input')?.value?.trim();
        if (!raw) return;
        const ids = extractAllYouTubeIds(raw);
        if (!ids.length) {
            const single = extractYouTubeId(raw);
            if (single) ids.push(single);
        }
        if (!ids.length) { alert('URL invalida'); return; }
        closeYouTubeModal();
        insertYouTubeEmbedsAtCursor(ids);
    };

    window.filterNoteLinkList = function(query) {
        const container = document.getElementById('note-link-list');
        if (!container) return;
        const notes = LocalDB.getAll('study_notes') || [];
        const filtered = query ? notes.filter(n => (n.title || '').toLowerCase().includes(query.toLowerCase())) : notes;
        container.innerHTML = filtered.length ? filtered.map(note => `
            <div class="slash-item" onclick="openNoteById('${note.id}')"><span class="slash-icon">📎</span><div><b>${escapeHtml(note.title || 'Sem titulo')}</b></div></div>`).join('') : '<div style="padding:20px;text-align:center;color:var(--text-secondary)">Nenhuma nota</div>';
    };

    window.openNoteById = function(id) {
        const notes = LocalDB.getAll('study_notes') || [];
        const note = notes.find(n => String(n.id) === String(id));
        if (note) openNoteEditor(note.id, note.notebook_id || null);
    };

    function renderBacklinksFixed(noteId) {
        const panel = document.getElementById('backlinks-panel');
        const list = document.getElementById('backlinks-list');
        if (!panel || !list || !noteId) { if (panel) panel.style.display = 'none'; return; }
        const notes = LocalDB.getAll('study_notes') || [];
        const backlinks = notes.filter(n => String(n.id) !== String(noteId) && n.content && n.content.includes(String(noteId)));
        if (!backlinks.length) { panel.style.display = 'none'; return; }
        panel.style.display = 'block';
        list.innerHTML = backlinks.map(bl => `<div style="padding:10px;background:rgba(255,255,255,0.05);border-radius:8px;cursor:pointer" onclick="openNoteById('${bl.id}')">${escapeHtml(bl.title || 'Nota')}</div>`).join('');
    }
    window.renderBacklinks = renderBacklinksFixed;

    window.toggleToolbarOverflow = function(ev) {
        ev.stopPropagation();
        const menu = document.getElementById('rt-overflow-menu');
        if (menu) menu.style.display = menu.style.display === 'none' ? 'flex' : 'none';
    };

    const _loadStudiesOrig = window.loadStudies;
    window.loadStudies = function() {
        if (typeof _loadStudiesOrig === 'function') _loadStudiesOrig();
        loadSubjectsGrid();
        if (typeof loadNotebooksGrid === 'function') loadNotebooksGrid();
        if (typeof ensureChartJs === 'function') ensureChartJs().then(() => setTimeout(renderStudyCharts, 100));
    };

    window.openFinanceOverflow = function(ev) {
        ev.stopPropagation();
        const popup = document.getElementById('finance-overflow-popup');
        if (!popup) return;
        popup.style.display = 'block';
        popup.style.top = (ev.clientY + 8) + 'px';
        popup.style.right = '16px';
        popup.style.left = 'auto';
        setTimeout(() => document.addEventListener('click', closeFinanceOverflowOnce, { once: true }), 0);
    };
    function closeFinanceOverflowOnce() { closeFinanceOverflow(); }

    const WORKOUT_TEMPLATES = [
        { name: 'Peito & Tríceps', muscle: 'Peito', exercises: [{ name: 'Supino reto', sets: 4, reps: 10, weight: 0 }, { name: 'Crucifixo', sets: 3, reps: 12, weight: 0 }, { name: 'Tríceps pulley', sets: 3, reps: 15, weight: 0 }] },
        { name: 'Costas & Bíceps', muscle: 'Costas', exercises: [{ name: 'Puxada frontal', sets: 4, reps: 10, weight: 0 }, { name: 'Remada curvada', sets: 3, reps: 10, weight: 0 }, { name: 'Rosca direta', sets: 3, reps: 12, weight: 0 }] },
        { name: 'Pernas', muscle: 'Pernas', exercises: [{ name: 'Agachamento', sets: 4, reps: 8, weight: 0 }, { name: 'Leg press', sets: 3, reps: 12, weight: 0 }, { name: 'Cadeira extensora', sets: 3, reps: 15, weight: 0 }] },
        { name: 'Full Body', muscle: 'Corpo inteiro', exercises: [{ name: 'Burpee', sets: 3, reps: 10, weight: 0 }, { name: 'Flexão', sets: 3, reps: 15, weight: 0 }, { name: 'Prancha', sets: 3, reps: 60, weight: 0 }] }
    ];

    window.renderWorkoutTemplates = function() {
        const row = document.getElementById('workout-templates-row');
        if (!row) return;
        row.innerHTML = WORKOUT_TEMPLATES.map((t, i) =>
            `<button class="study-chip" onclick="startWorkoutFromTemplate(${i})" style="white-space:nowrap">${escapeHtml(t.name)}</button>`
        ).join('');
    };

    window.startWorkoutFromTemplate = function(idx) {
        const t = WORKOUT_TEMPLATES[idx];
        if (!t) return;
        openWorkoutForm();
        document.getElementById('workout-form-name').value = t.name;
        document.getElementById('workout-form-muscle').value = t.muscle;
        renderWorkoutExercises(t.exercises.slice());
    };

    // Boot: sync reminders + load budget
    document.addEventListener('DOMContentLoaded', () => {
        const budgetEl = document.getElementById('nexus_daily_budget');
        const stored = localStorage.getItem('nexus_daily_budget');
        if (budgetEl && stored) budgetEl.value = stored;
        syncTaskReminders();
        syncHabitReminders();
        NexusCalendar.updateDateLabels();
    });

    setInterval(checkPendingReminders, 30000);

})();

// ================================================================
// PHONE CLEANER MODULE — native bridge + local heuristics
// ================================================================

function formatBytes(bytes) {
    const n = Number(bytes) || 0;
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
    if (n < 1024 * 1024 * 1024) return (n / (1024 * 1024)).toFixed(1) + ' MB';
    return (n / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

function parseNativeJson(raw) {
    if (!raw) return null;
    try {
        return typeof raw === 'string' ? JSON.parse(raw) : raw;
    } catch (_) {
        return null;
    }
}

function getLocalStorageFootprint() {
    let total = 0;
    const large = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        const val = localStorage.getItem(key) || '';
        const size = (key.length + val.length) * 2;
        total += size;
        if (size > 50000) large.push({ key, size });
    }
    large.sort((a, b) => b.size - a.size);
    return { total, large: large.slice(0, 5) };
}

function findOrphanedHabitLogs() {
    const habits = (LocalDB.get('habits') || []).filter(h => !h.is_deleted);
    const habitIds = new Set(habits.map(h => String(h.id)));
    const logs = LocalDB.get('habit_logs') || [];
    return logs.filter(l => !habitIds.has(String(l.habit_id)));
}

function findStaleSyncData() {
    const conflicts = JSON.parse(localStorage.getItem('nexus_sync_conflicts') || '[]');
    const lastSync = localStorage.getItem('nexus_last_sync');
    const stale = [];
    if (conflicts.length > 10) stale.push({ type: 'sync_conflicts', count: conflicts.length });
    if (lastSync) {
        const age = Date.now() - new Date(lastSync).getTime();
        if (age > 30 * 24 * 60 * 60 * 1000) stale.push({ type: 'old_sync_marker', ageDays: Math.floor(age / 86400000) });
    }
    return stale;
}

function scanJsStorageCategories() {
    const ls = getLocalStorageFootprint();
    const orphans = findOrphanedHabitLogs();
    const stale = findStaleSyncData();
    const categories = [];

    categories.push({
        id: 'localStorage',
        name: 'Dados locais (localStorage)',
        bytes: ls.total,
        desc: ls.large.length ? ls.large.length + ' entradas grandes' : 'Dados do app offline',
        cleanable: false
    });

    if (orphans.length) {
        categories.push({
            id: 'orphan_logs',
            name: 'Logs de habitos orfaos',
            bytes: orphans.length * 120,
            desc: orphans.length + ' registros sem habito',
            cleanable: true,
            count: orphans.length
        });
    }

    if (stale.length) {
        categories.push({
            id: 'stale_sync',
            name: 'Dados de sync antigos',
            bytes: stale.reduce((s, x) => s + (x.count || 1) * 200, 0),
            desc: 'Conflitos ou metadados desatualizados',
            cleanable: true
        });
    }

    const nativeStats = getNativeStorageStatsSync();
    if (nativeStats) {
        if (nativeStats.cacheBytes > 0) {
            categories.push({
                id: 'native_cache',
                name: 'Cache nativo (Android)',
                bytes: nativeStats.cacheBytes,
                desc: 'Cache WebView e arquivos temporarios',
                cleanable: true
            });
        }
        if (nativeStats.tempBytes > 0) {
            categories.push({
                id: 'native_temp',
                name: 'Arquivos temporarios',
                bytes: nativeStats.tempBytes,
                desc: 'Pasta temp do app',
                cleanable: true
            });
        }
        if (nativeStats.bundleBytes > 1024 * 1024) {
            categories.push({
                id: 'web_bundle',
                name: 'Bundle web baixado',
                bytes: nativeStats.bundleBytes,
                desc: 'Atualizacao OTA da interface (limpeza profunda)',
                cleanable: true,
                deepOnly: true
            });
        }
    }

    if (window.AndroidNative && typeof AndroidNative.scanLargeDownloads === 'function') {
        try {
            const dl = parseNativeJson(AndroidNative.scanLargeDownloads());
            if (dl && dl.totalBytes > 0) {
                categories.push({
                    id: 'large_downloads',
                    name: 'Downloads grandes (5MB+)',
                    bytes: dl.totalBytes,
                    desc: (dl.files?.length || 0) + ' arquivos na pasta Downloads',
                    cleanable: false
                });
            }
        } catch (_) {}
    }

    return categories;
}

function getNativeStorageStatsSync() {
    if (!window.AndroidNative || typeof AndroidNative.getStorageStats !== 'function') return null;
    try {
        return parseNativeJson(AndroidNative.getStorageStats());
    } catch (_) {
        return null;
    }
}

function getNativeDiagnosticsSync() {
    if (!window.AndroidNative || typeof AndroidNative.getDeviceDiagnostics !== 'function') return null;
    try {
        return parseNativeJson(AndroidNative.getDeviceDiagnostics());
    } catch (_) {
        return null;
    }
}

function renderCleanerCategories(categories) {
    const container = document.getElementById('cleaner-scan-results');
    if (!container) return;
    if (!categories.length) {
        container.innerHTML = '<div class="glass" style="padding:14px;border-radius:12px;text-align:center;color:var(--text-secondary);font-size:0.85rem">Nada para limpar. Toque em Escanear.</div>';
        return;
    }
    container.innerHTML = categories.map(c => `
        <div class="cleaner-cat-item">
            <div>
                <div class="cleaner-cat-name">${escapeHtml(c.name)}</div>
                <div class="cleaner-cat-desc">${escapeHtml(c.desc || '')}</div>
            </div>
            <span class="cleaner-cat-size">${formatBytes(c.bytes)}</span>
        </div>`).join('');
}

function renderCleanerTips(categories, diag) {
    const list = document.getElementById('cleaner-tips-list');
    if (!list) return;
    const tips = [
        'Feche apps em segundo plano para liberar RAM.',
        'Mantenha pelo menos 10% de armazenamento livre para o Android funcionar bem.',
        'Desative animacoes pesadas em Configuracoes > Experiencia se o app estiver lento.'
    ];
    if (diag && diag.lowMemory) tips.unshift('Memoria baixa detectada — use Limpeza Rapida agora.');
    if (diag && diag.batteryPercent != null && diag.batteryPercent < 20) {
        tips.push('Bateria abaixo de 20% — ative economia de energia nas configuracoes do Android.');
    }
    const bigCache = categories.find(c => c.id === 'native_cache' && c.bytes > 50 * 1024 * 1024);
    if (bigCache) tips.unshift('Cache acima de 50 MB — recomendamos Limpeza Rapida.');
    list.innerHTML = tips.map(t => `<div class="cleaner-tip"><i class="fa-solid fa-circle-info" style="margin-right:6px;color:var(--accent-blue)"></i>${escapeHtml(t)}</div>`).join('');
}

function updateStorageWarningBadge(cacheBytes) {
    const badge = document.getElementById('storage-warning-badge');
    const hint = document.getElementById('settings-storage-hint');
    const threshold = 30 * 1024 * 1024;
    const show = cacheBytes > threshold;
    if (badge) badge.style.display = show ? 'block' : 'none';
    if (hint) hint.textContent = 'Cache: ' + formatBytes(cacheBytes || 0) + (show ? ' — considere limpar' : '');
}

function setCleanerProgress(pct, label) {
    const wrap = document.getElementById('cleaner-progress');
    const bar = document.getElementById('cleaner-progress-bar');
    const lbl = document.getElementById('cleaner-progress-label');
    if (wrap) wrap.style.display = pct >= 0 ? 'block' : 'none';
    if (bar) bar.style.width = Math.min(100, Math.max(0, pct)) + '%';
    if (lbl && label) lbl.textContent = label;
}

function showCleanerResults(text) {
    const box = document.getElementById('cleaner-results');
    const txt = document.getElementById('cleaner-results-text');
    if (box) box.style.display = 'block';
    if (txt) txt.textContent = text;
}

function cleanJsCategories(deep) {
    let freed = 0;
    const details = [];

    const orphans = findOrphanedHabitLogs();
    if (orphans.length) {
        const valid = (LocalDB.get('habit_logs') || []).filter(l => {
            const habits = (LocalDB.get('habits') || []).filter(h => !h.is_deleted);
            return habits.some(h => String(h.id) === String(l.habit_id));
        });
        freed += orphans.length * 120;
        LocalDB.set('habit_logs', valid);
        details.push(orphans.length + ' logs orfaos removidos');
    }

    const conflicts = JSON.parse(localStorage.getItem('nexus_sync_conflicts') || '[]');
    if (deep && conflicts.length > 20) {
        localStorage.setItem('nexus_sync_conflicts', JSON.stringify(conflicts.slice(-5)));
        freed += (conflicts.length - 5) * 200;
        details.push('Conflitos de sync antigos limpos');
    }

    if (deep) {
        const ls = getLocalStorageFootprint();
        ls.large.forEach(entry => {
            if (entry.key.startsWith('nexus_chart_') || entry.key.startsWith('nexus_temp_')) {
                const before = (entry.key.length + (localStorage.getItem(entry.key) || '').length) * 2;
                localStorage.removeItem(entry.key);
                freed += before;
                details.push('Cache ' + entry.key);
            }
        });
    }

    return { freed, details };
}

function runNativeClean(mode) {
    if (!window.AndroidNative || typeof AndroidNative.runNativeClean !== 'function') {
        let freed = 0;
        if (typeof AndroidNative.clearAppCache === 'function') freed += Number(AndroidNative.clearAppCache()) || 0;
        if (typeof AndroidNative.clearTempFiles === 'function') freed += Number(AndroidNative.clearTempFiles()) || 0;
        return { totalFreed: freed, cacheFreed: freed, tempFreed: 0, mode };
    }
    return parseNativeJson(AndroidNative.runNativeClean(mode)) || { totalFreed: 0 };
}

window.scanPhoneStorage = async function() {
    setCleanerProgress(10, 'Escaneando armazenamento...');
    const stats = getNativeStorageStatsSync();
    const diag = getNativeDiagnosticsSync();
    const categories = scanJsStorageCategories();

    if (stats && !stats.error) {
        const usedEl = document.getElementById('cleaner-storage-used');
        const freeEl = document.getElementById('cleaner-storage-free');
        const cacheEl = document.getElementById('cleaner-cache-size');
        const bar = document.getElementById('cleaner-storage-bar');
        if (usedEl) usedEl.textContent = formatBytes(stats.usedBytes);
        if (freeEl) freeEl.textContent = formatBytes(stats.freeBytes) + ' livres';
        if (cacheEl) cacheEl.textContent = formatBytes(stats.cacheBytes);
        if (bar && stats.totalBytes) bar.style.width = Math.round((stats.usedBytes / stats.totalBytes) * 100) + '%';
        updateStorageWarningBadge(stats.cacheBytes);
    } else {
        const ls = getLocalStorageFootprint();
        const usedEl = document.getElementById('cleaner-storage-used');
        const cacheEl = document.getElementById('cleaner-cache-size');
        if (usedEl) usedEl.textContent = formatBytes(ls.total);
        if (cacheEl) cacheEl.textContent = formatBytes(ls.total);
        updateStorageWarningBadge(ls.total);
    }

    if (diag && !diag.error) {
        const ramEl = document.getElementById('cleaner-ram-info');
        const procEl = document.getElementById('cleaner-process-count');
        if (ramEl && diag.availRamBytes) {
            ramEl.textContent = formatBytes(diag.availRamBytes) + ' livre';
        }
        if (procEl) procEl.textContent = String(diag.runningProcesses || '—');
    }

    renderCleanerCategories(categories);
    renderCleanerTips(categories, diag);
    setCleanerProgress(-1, '');
    window._cleanerLastScan = { stats, diag, categories, at: Date.now() };
};

window.runQuickClean = async function() {
    setCleanerProgress(15, 'Limpando cache...');
    const native = runNativeClean('quick');
    setCleanerProgress(55, 'Removendo dados orfaos...');
    const js = cleanJsCategories(false);
    setCleanerProgress(90, 'Finalizando...');
    const totalFreed = (native.totalFreed || 0) + js.freed;
    const parts = [];
    if (native.totalFreed) parts.push(formatBytes(native.totalFreed) + ' cache nativo');
    if (js.freed) parts.push(formatBytes(js.freed) + ' dados locais');
    if (js.details.length) parts.push(js.details.join(', '));
    showCleanerResults(totalFreed > 0
        ? 'Liberados ' + formatBytes(totalFreed) + (parts.length ? ' (' + parts.join(' · ') + ')' : '')
        : 'Nada significativo para limpar agora.');
    setCleanerProgress(100, 'Concluido!');
    setTimeout(() => setCleanerProgress(-1, ''), 1200);
    showToast('Limpeza rapida: ' + formatBytes(totalFreed) + ' liberados');
    await scanPhoneStorage();
};

window.runDeepClean = async function() {
    if (!confirm('Limpeza profunda remove cache, temporarios, logs orfaos e metadados antigos. Continuar?')) return;
    setCleanerProgress(10, 'Limpeza profunda em andamento...');
    const native = runNativeClean('deep');
    setCleanerProgress(50, 'Limpando dados locais...');
    const js = cleanJsCategories(true);
    setCleanerProgress(85, 'Otimizando...');
    const totalFreed = (native.totalFreed || 0) + js.freed;
    showCleanerResults('Limpeza profunda concluida. Liberados ' + formatBytes(totalFreed) + '.');
    setCleanerProgress(100, 'Concluido!');
    setTimeout(() => setCleanerProgress(-1, ''), 1500);
    showToast('Limpeza profunda: ' + formatBytes(totalFreed) + ' liberados');
    await scanPhoneStorage();
};

window.getCleanerSuggestions = function() {
    const scan = window._cleanerLastScan;
    if (!scan) return ['Execute um escaneamento primeiro.'];
    const suggestions = [];
    scan.categories.filter(c => c.cleanable).forEach(c => {
        suggestions.push('Limpar ' + c.name + ' (' + formatBytes(c.bytes) + ')');
    });
    if (!suggestions.length) suggestions.push('Armazenamento em bom estado.');
    return suggestions;
};

window.requestCleanerAiAdvice = async function() {
    const adviceEl = document.getElementById('cleaner-ai-advice');
    const scan = window._cleanerLastScan || {};
    const localTips = getCleanerSuggestions();

    if (!isWifiConnected()) {
        if (adviceEl) {
            adviceEl.style.display = 'block';
            adviceEl.textContent = 'Offline — sugestoes locais: ' + localTips.join(' · ');
        }
        return;
    }

    if (adviceEl) {
        adviceEl.style.display = 'block';
        adviceEl.textContent = 'Analisando...';
    }

    const report = {
        storage: scan.stats,
        diagnostics: scan.diag,
        categories: (scan.categories || []).map(c => ({ name: c.name, size: formatBytes(c.bytes), cleanable: c.cleanable })),
        localSuggestions: localTips
    };

    if (window.nexusSupabase && typeof sendChatMessage === 'function') {
        const prompt = document.getElementById('chat-input');
        if (prompt) {
            prompt.value = 'Analise este relatorio de armazenamento do Nexus Mobile e sugira o que limpar (resposta curta em portugues): ' + JSON.stringify(report);
            sendChatMessage();
            if (adviceEl) adviceEl.textContent = 'Pedido enviado ao Jarvis Chat — veja a resposta na tela inicial.';
            return;
        }
    }

    if (adviceEl) {
        adviceEl.textContent = localTips.join(' · ');
    }
};

window.loadCleaner = function() {
    renderCleanerTips([], null);
    scanPhoneStorage();
};

window.openCleanerView = function() {
    navigateTo('view-cleaner');
};

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        const stats = getNativeStorageStatsSync();
        if (stats && stats.cacheBytes) updateStorageWarningBadge(stats.cacheBytes);
        else updateStorageWarningBadge(getLocalStorageFootprint().total);
    }, 1500);
});
