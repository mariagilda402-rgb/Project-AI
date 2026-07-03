/** Nexus Mobile — nexus-core.js */
window.NEXUS_WEB_VERSION = window.NEXUS_WEB_VERSION || '2026.06.16.2';

window.onerror = function(msg, url, line) {
    console.error("JS Error:", msg, "at", url, "line", line);
    if (typeof showToast === 'function') showToast("Erro: " + msg);
    return true;
};

function todayISO() {
    return new Date().toISOString().split('T')[0];
}
window.todayISO = todayISO;

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
window.escapeHtml = escapeHtml;

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
    if (isWifiConnected()) return true;
    if (!isNetworkOnline()) {
        showToast('Sem internet para usar o Jarvis' + (label ? ' (' + label + ')' : '') + '.');
    } else {
        showToast('Jarvis requer Wi-Fi' + (label ? ' (' + label + ')' : '') + '. Conecte-se a uma rede Wi-Fi.');
    }
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

function getUserStats() {
    let stats = LocalDB.get('user_stats');
    if (!stats || typeof stats !== 'object' || Array.isArray(stats)) {
        stats = { xp: 0, points: 0, level: 1, xp_today: 0, last_xp_date: '' };
    }
    stats.xp = Number(stats.xp) || 0;
    stats.points = Number(stats.points) || 0;
    stats.level = Math.max(1, Number(stats.level) || 1);
    stats.xp_today = Number(stats.xp_today) || 0;
    return stats;
}
window.getUserStats = getUserStats;

function ensureDefaultUserStats() {
    const stats = getUserStats();
    LocalDB.set('user_stats', stats);
    return stats;
}

function ensureDefaultRewards() {
    const rewards = LocalDB.get('nexus_rewards').filter(r => !r.is_deleted);
    if (rewards.length > 0) return;
    const now = new Date().toISOString();
    LocalDB.set('nexus_rewards', [
        { id: 1, name: 'Pausa Café', cost: 50, description: '15 min de descanso merecido', created_at: now, updated_at: now, sync_status: 'pending' },
        { id: 2, name: 'Episódio Série', cost: 100, description: 'Assistir um episódio favorito', created_at: now, updated_at: now, sync_status: 'pending' },
        { id: 3, name: 'Jantar Especial', cost: 200, description: 'Comida favorita no fim de semana', created_at: now, updated_at: now, sync_status: 'pending' }
    ]);
}
window.ensureDefaultRewards = ensureDefaultRewards;

const _origLocalDbGet = LocalDB.get;
LocalDB.get = function(key) {
    const objectDefaults = {
        study_notebooks: [], pomo_sessions: [], journal_entries: [],
        diet_meals: [], body_measures: [], xp_log: [],
        user_stats: { xp: 0, points: 0, level: 1, xp_today: 0, last_xp_date: '' }
    };
    const val = _origLocalDbGet.call(this, key);
    if (val === null || val === undefined || (Array.isArray(val) && val.length === 0 && objectDefaults[key] && !Array.isArray(objectDefaults[key]))) {
        return objectDefaults[key] !== undefined ? JSON.parse(JSON.stringify(objectDefaults[key])) : val;
    }
    return val;
};

function bootNexusMobileCore() {
    ensureDefaultUserStats();
    ensureDefaultRewards();
    if (typeof loadUserStats === 'function') loadUserStats();
    else {
        setTextIfPresent('user-level', 1);
        if (typeof updateAppVersionDebug === 'function') updateAppVersionDebug();
    }
    updateSyncIndicator('offline');
    updateJarvisFabState();
    updateNetworkSettingsUI();
}
window.bootNexusMobileCore = bootNexusMobileCore;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootNexusMobileCore);
} else {
    bootNexusMobileCore();
}

function setTextIfPresent(id, value) {
    const el = document.getElementById(id);
    if (el && value != null && value !== '') el.textContent = String(value);
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

async function hasAuthenticatedSession() {
    const supabaseClient = window.nexusSupabase;
    if (!supabaseClient) return false;
    try {
        const { data: { session } } = await supabaseClient.auth.getSession();
        if (session?.user) {
            if (typeof currentUser !== 'undefined') currentUser = session.user;
            return true;
        }
    } catch (e) {
        console.warn('Session check failed:', e);
    }
    return false;
}

async function syncData() {
    if (syncInProgress) return;
    const supabaseClient = window.nexusSupabase;
    if (!navigator.onLine || !supabaseClient) {
        updateSyncIndicator('offline');
        return;
    }
    if (!(await hasAuthenticatedSession())) {
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
    if (!navigator.onLine || !window.nexusSupabase) {
        updateSyncIndicator('offline');
        return;
    }
    if (!(await hasAuthenticatedSession())) {
        updateSyncIndicator('offline');
        return;
    }
    return syncData();
}

window.syncData = syncData;
window.backgroundSync = backgroundSync;

// ----------------------------------------------------
// UI Logic — central view refresh (all modules)
// ----------------------------------------------------
window.refreshViewContent = function(viewId) {
    if (!viewId) return;
    const run = (label, fn) => {
        if (typeof fn !== 'function') {
            console.warn('[refreshViewContent] missing loader:', viewId, label);
            return;
        }
        try { fn(); } catch (err) { console.error('[refreshViewContent]', viewId, label, err); }
    };
    switch (viewId) {
            case 'view-home':
                run('loadTodayDashboard', loadTodayDashboard);
                break;
            case 'view-habits':
                run('loadHabits', window.loadHabits);
                break;
            case 'view-finance':
                run('loadFinances', window.loadFinances);
                break;
            case 'view-tasks':
                run('loadTasks', window.loadTasks);
                break;
            case 'view-videos':
                run('loadVideos', window.loadVideos);
                break;
            case 'view-shop':
                run('loadShop', window.loadShop);
                break;
            case 'view-studies':
                run('loadStudies', window.loadStudies);
                break;
            case 'view-goals':
                run('loadGoals', window.loadGoals);
                break;
            case 'view-fitness':
                if (typeof switchFitnessTab === 'function') {
                    try {
                        const treinosBtn = document.querySelector('#view-fitness .fitness-tab');
                        switchFitnessTab('treinos', treinosBtn);
                    } catch (err) { console.error('[refreshViewContent]', viewId, 'switchFitnessTab', err); }
                } else {
                    run('loadFitness', window.loadFitness);
                }
                break;
            case 'view-routines':
                run('loadRoutines', window.loadRoutines);
                break;
            case 'view-journal':
                run('loadJournal', window.loadJournal);
                break;
            case 'view-alarms':
                run('loadAlarms', window.loadAlarms);
                break;
            case 'view-iot':
                run('discoverIoT', window.discoverIoT);
                break;
            case 'view-cleaner':
                run('loadCleaner', window.loadCleaner);
                break;
            case 'view-jarvis-history':
                run('loadJarvisPersistentHistory', window.loadJarvisPersistentHistory);
                break;
            case 'view-jarvis-calls':
                run('loadJarvisCallHistory', window.loadJarvisCallHistory);
                break;
            case 'view-settings':
                run('initAppPreferences', initAppPreferences);
                run('updateSettingsUI', updateSettingsUI);
                break;
            default:
                break;
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
    const stats = getUserStats();
    const user = LocalDB.getSingle('nexus_user', 1) || { id: 1, name: 'Comandante' };
    user.xp = stats.xp;
    user.points = stats.points;
    user.level = stats.level;
    LocalDB.upsert('nexus_user', user);
}

function loadUserStats() {
    const stats = ensureDefaultUserStats();
    syncUserStatsToNexusUser();
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
    let webVer = window.NEXUS_WEB_VERSION || '—';
    try {
        const raw = localStorage.getItem('nexus_web_version');
        if (raw) webVer = JSON.parse(raw).version || raw;
    } catch (_) {}
    const applyLabel = (wv, av) => {
        el.textContent = 'web ' + (wv || '—') + ' · apk ' + (av || '—');
    };
    applyLabel(webVer, window.__nexusApkVersion || '—');
    if (webVer === '—' || !window.__nexusApkVersion) {
        fetch('version.json').then(r => r.ok ? r.json() : null).then(j => {
            if (j && j.version) {
                webVer = j.version;
                window.NEXUS_WEB_VERSION = j.version;
                localStorage.setItem('nexus_web_version', JSON.stringify(j));
            }
            let apkVer = window.__nexusApkVersion || '—';
            if (window.AndroidNative && typeof window.AndroidNative.getAppInfo === 'function') {
                try {
                    const info = JSON.parse(window.AndroidNative.getAppInfo());
                    apkVer = info.versionName || info.version || apkVer;
                    window.__nexusApkVersion = apkVer;
                } catch (_) {}
            } else if (window.AndroidNative && typeof window.AndroidNative.getShellInfo === 'function') {
                try {
                    const info = JSON.parse(window.AndroidNative.getShellInfo());
                    apkVer = info.versionName || info.version || apkVer;
                    window.__nexusApkVersion = apkVer;
                } catch (_) {}
            }
            applyLabel(webVer, apkVer);
        }).catch(() => applyLabel(webVer, window.__nexusApkVersion || '—'));
    }
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
                <button class="item-action" style="font-size:12px; width:auto; padding: 0 10px;" data-reward-id="${item.id}" data-reward-name="${escapeHtml(item.name)}" data-reward-cost="${item.cost}">
                    ${item.cost} pts
                </button>
            `;
            container.appendChild(el);
        });
        container.querySelectorAll('[data-reward-id]').forEach(btn => {
            btn.addEventListener('click', () => {
                buyItem(
                    parseInt(btn.getAttribute('data-reward-id'), 10),
                    btn.getAttribute('data-reward-name') || '',
                    parseInt(btn.getAttribute('data-reward-cost'), 10) || 0
                );
            });
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
window.loadGoals = window.loadGoals || loadGoals;
window.loadFitness = window.loadFitness || loadFitness;
window.updateFitnessStats = window.updateFitnessStats || updateFitnessStats;

window.loadRoutines = window.loadRoutines || function() {
    const list = document.getElementById('routines-list');
    if (!list) return;
    const routines = LocalDB.get('routines') || [];
    if (!routines.length) {
        list.innerHTML = '<div style="text-align:center;color:var(--text-secondary);padding:30px">Voce nao tem rotinas criadas.<br><br><button onclick="createDefaultRoutines()" style="background:var(--accent-primary);color:white;border:none;padding:10px 20px;border-radius:10px;font-weight:700">Criar Rotinas Padrao</button></div>';
        return;
    }
    list.innerHTML = routines.map(r => `
        <div class="list-item glass" style="cursor:pointer" onclick="openRoutineRunner('${r.id}')">
            <div class="item-main"><div class="item-title">${escapeHtml(r.name)}</div>
            <div class="item-subtitle"><i class="fa-regular fa-clock"></i> ${r.time || 'Sem horario'} · ${(r.steps || []).length} passos</div></div>
            <button class="icon-btn" style="background:var(--accent-primary);color:white;width:40px;height:40px"><i class="fa-solid fa-play"></i></button>
        </div>`).join('');
};

window.loadJournal = window.loadJournal || function() {
    const list = document.getElementById('journal-list');
    if (list) {
        const entries = (LocalDB.get('journal_entries') || [])
            .filter(e => e.content || e.best || e.challenge || e.gratitude)
            .sort((a, b) => (b.date || '').localeCompare(a.date || ''));
        list.innerHTML = entries.length ? entries.map(e => `
            <div class="list-item glass" onclick="openJournalEntry('${e.date}')" style="cursor:pointer">
                <div class="item-main"><span class="item-title">${escapeHtml(e.date)}</span>
                <span class="item-subtitle">${escapeHtml((e.content || '').slice(0, 80))}</span></div>
            </div>`).join('') : '<div style="text-align:center;color:var(--text-secondary);padding:24px">Registre seu humor e toque + para escrever.</div>';
    }
};

window.loadAlarms = window.loadAlarms || function() {
    const list = document.getElementById('alarms-list');
    if (!list) return;
    const alarms = (LocalDB.get('nexus_alarms') || []).filter(a => !a.is_deleted);
    list.innerHTML = alarms.length ? alarms.map(a => `
        <div class="list-item glass" style="padding:14px;margin-bottom:10px">
            <div class="item-main"><div class="item-title">${escapeHtml(a.title || 'Alarme')}</div>
            <div style="font-size:0.8rem;color:var(--text-secondary)">${escapeHtml(a.alarm_time || '')}</div></div>
        </div>`).join('') : '<div style="text-align:center;color:var(--text-secondary);padding:24px">Nenhum alarme agendado. Toque + para criar.</div>';
};

window.loadCleaner = window.loadCleaner || function() {
    if (typeof scanPhoneStorage === 'function') scanPhoneStorage();
    else {
        const el = document.getElementById('cleaner-scan-results');
        if (el) el.innerHTML = '<div style="color:var(--text-secondary);padding:16px">Toque em escanear para analisar o armazenamento.</div>';
    }
};

// loadStudies — no módulo nexus-studies.js

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

    const habits = LocalDB.get('habits').filter(h => h.active !== 0 && !h.is_deleted);
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

// Form handler stubs (real implementations in nexus-forms.js)
function deferToFormHandler(name, args) {
    const real = window[name];
    if (typeof real === 'function' && real !== window['__stub_' + name]) {
        return real.apply(window, args);
    }
    showToast('Carregando formulários...');
    setTimeout(() => {
        const fn = window[name];
        if (typeof fn === 'function' && fn !== window['__stub_' + name]) fn.apply(window, args);
        else showToast('Formulário indisponível — atualize o bundle web (Configurações → OTA).');
    }, 400);
}

window.__stub_openFinanceForm = function(txId) { deferToFormHandler('openFinanceForm', [txId]); };
window.__stub_openHabitForm = function(habitId) { deferToFormHandler('openHabitForm', [habitId]); };
window.__stub_openSubjectForm = function() { deferToFormHandler('openSubjectForm', []); };
window.openFinanceForm = window.openFinanceForm || window.__stub_openFinanceForm;
window.openHabitForm = window.openHabitForm || window.__stub_openHabitForm;
window.openSubjectForm = window.openSubjectForm || window.__stub_openSubjectForm;
