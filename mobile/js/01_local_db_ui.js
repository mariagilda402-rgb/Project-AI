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
    if (!timer || !jarvisCallStartedAt) return;
    const elapsed = Math.floor((Date.now() - jarvisCallStartedAt) / 1000);
    const minutes = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const seconds = String(elapsed % 60).padStart(2, '0');
    timer.textContent = `${minutes}:${seconds}`;
}

window.toggleJarvisCall = function() {
    if (jarvisCallActive) {
        window.endJarvisCall();
        return;
    }
    if (!requireWifiForJarvis('ligação')) return;
    if (!window.nexusSupabase) {
        showToast('Entre com Google nas configurações para usar o Jarvis.');
        return;
    }
    jarvisCallActive = true;
    jarvisCallStartedAt = Date.now();
    const banner = document.getElementById('jarvis-call-banner');
    const fab = document.getElementById('nexus-ai-fab');
    if (banner) banner.style.display = 'flex';
    if (fab) fab.classList.add('active');
    updateJarvisCallTimer();
    jarvisCallTimerId = setInterval(updateJarvisCallTimer, 1000);
    if (window.AndroidNative && typeof window.AndroidNative.startJarvisCall === 'function') {
        window.AndroidNative.startJarvisCall();
    } else {
        showToast('Ligacao Jarvis indisponivel no modo web.');
    }
};

window.endJarvisCall = function() {
    jarvisCallActive = false;
    jarvisCallStartedAt = 0;
    clearInterval(jarvisCallTimerId);
    jarvisCallTimerId = null;
    const banner = document.getElementById('jarvis-call-banner');
    const fab = document.getElementById('nexus-ai-fab');
    const timer = document.getElementById('jarvis-call-timer');
    if (banner) banner.style.display = 'none';
    if (fab) fab.classList.remove('active');
    if (timer) timer.textContent = '00:00';
    if (window.AndroidNative && typeof window.AndroidNative.stopJarvisCall === 'function') {
        window.AndroidNative.stopJarvisCall();
    }
};

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

