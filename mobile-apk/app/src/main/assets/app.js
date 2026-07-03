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
    if (typeof loadUnifiedJarvisSettingsUI === 'function') loadUnifiedJarvisSettingsUI();
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

// ================================================================
// DRAG & DROP — Touch-friendly list reordering
// Usage: makeSortable(container, items[], onReorder(newIds[]))
// ================================================================
function makeSortable(container, dbKey, idField = 'id') {
    if (!container) return;
    // Prevent multiple initializations
    if (container._sortableInitialized) return;
    container._sortableInitialized = true;
    container._sortableKey = dbKey;

    let dragEl = null, ghost = null, startY = 0, startIdx = 0, lastY = 0;
    let observer = null;

    function getItems() { return [...container.querySelectorAll('.list-item')]; }

    function getElIndex(el) { return getItems().indexOf(el); }

    function createGhost(el) {
        const rect = el.getBoundingClientRect();
        const g = el.cloneNode(true);
        g.style.cssText = `
            position:fixed; z-index:9999; left:${rect.left}px; top:${rect.top}px;
            width:${rect.width}px; height:${rect.height}px;
            opacity:0.85; pointer-events:none;
            box-shadow:0 12px 30px rgba(0,0,0,0.5);
            transform:scale(1.03) rotate(0.5deg);
            border-radius:14px;
            background:var(--card-bg,#1a1a2e);
            transition:transform 0.1s ease;
        `;
        document.body.appendChild(g);
        return g;
    }

    function onTouchStart(e) {
        const el = e.currentTarget;
        const touch = e.touches[0];
        startY = touch.clientY;
        lastY = startY;
        startIdx = getElIndex(el);
        
        // Long press to activate drag (300ms)
        el._dragTimer = setTimeout(() => {
            dragEl = el;
            ghost = createGhost(el);
            el.style.opacity = '0.3';
            el.style.transform = 'scale(0.97)';
            // Haptic feedback if available
            if (window.navigator && window.navigator.vibrate) window.navigator.vibrate(30);
            e.preventDefault();
        }, 300);
    }

    function onTouchMove(e) {
        clearTimeout(e.currentTarget._dragTimer);
        if (!dragEl) return;
        e.preventDefault();

        const touch = e.touches[0];
        const dy = touch.clientY - lastY;
        lastY = touch.clientY;

        // Move ghost
        if (ghost) {
            const ghostTop = parseFloat(ghost.style.top) + dy;
            ghost.style.top = ghostTop + 'px';
        }

        // Find which slot we're hovering over
        const items = getItems();
        const containerRect = container.getBoundingClientRect();
        let targetIdx = startIdx;
        for (let i = 0; i < items.length; i++) {
            const r = items[i].getBoundingClientRect();
            if (touch.clientY >= r.top && touch.clientY <= r.bottom) {
                targetIdx = i;
                break;
            }
        }

        // Swap with target if different
        if (targetIdx !== getElIndex(dragEl) && targetIdx >= 0 && targetIdx < items.length) {
            const target = items[targetIdx];
            const currentIdx = getElIndex(dragEl);
            if (currentIdx < targetIdx) {
                target.after(dragEl);
            } else {
                target.before(dragEl);
            }
        }
    }

    function onTouchEnd(e) {
        clearTimeout(e.currentTarget._dragTimer);
        if (!dragEl) return;

        dragEl.style.opacity = '1';
        dragEl.style.transform = '';
        if (ghost) { ghost.remove(); ghost = null; }

        // Persist new order to LocalDB
        const newOrder = getItems().map(el => el.dataset.id || el.dataset.sortId);
        if (newOrder.length && dbKey) {
            const allItems = LocalDB.get(dbKey) || [];
            // Sort allItems by new order, keep items not in view at end
            const ordered = newOrder.map(id => allItems.find(x => String(x[idField]) === String(id))).filter(Boolean);
            const rest = allItems.filter(x => !newOrder.includes(String(x[idField])));
            // Assign sort_order
            [...ordered, ...rest].forEach((item, i) => { item.sort_order = i; });
            LocalDB.set(dbKey, [...ordered, ...rest]);
        }

        dragEl = null;
        startIdx = 0;
    }

    // Track which elements have listeners to avoid duplicates
    const elementsWithListeners = new Set();

    // Attach listeners to all .list-item children
    function attach() {
        const items = getItems();
        items.forEach(el => {
            // Only add listeners if not already added
            if (!elementsWithListeners.has(el)) {
                el.addEventListener('touchstart', onTouchStart, { passive: true });
                el.addEventListener('touchmove', onTouchMove, { passive: false });
                el.addEventListener('touchend', onTouchEnd, { passive: true });
                elementsWithListeners.add(el);
                // Add visual drag handle hint
                if (!el.querySelector('.drag-handle')) {
                    const handle = document.createElement('span');
                    handle.className = 'drag-handle';
                    handle.style.cssText = 'color:rgba(255,255,255,0.25);font-size:0.75rem;padding:0 4px;flex-shrink:0;cursor:grab;user-select:none;align-self:center';
                    handle.innerHTML = '⠿';
                    handle.title = 'Segure para reordenar';
                    el.insertBefore(handle, el.firstChild);
                }
            }
        });
    }

    // Auto-observe for DOM changes (debounced to avoid loops)
    let observerTimeout = null;
    observer = new MutationObserver(() => {
        if (observerTimeout) clearTimeout(observerTimeout);
        observerTimeout = setTimeout(() => {
            attach();
        }, 100);
    });
    observer.observe(container, { childList: true });
    attach();

    return { 
        refresh: attach,
        destroy: () => {
            if (observer) observer.disconnect();
            elementsWithListeners.forEach(el => {
                el.removeEventListener('touchstart', onTouchStart);
                el.removeEventListener('touchmove', onTouchMove);
                el.removeEventListener('touchend', onTouchEnd);
            });
            elementsWithListeners.clear();
            container._sortableInitialized = false;
        }
    };
}

// Patch a data-id attr to all list items rendered by filter functions
function tagListItems(container, items, idField = 'id') {
    if (!container) return;
    const els = [...container.querySelectorAll('.list-item')];
    els.forEach((el, i) => {
        if (items[i]) el.dataset.id = String(items[i][idField] || i);
    });
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
// Jarvis Voice AI Globals
let jarvisSpeechRec = null;
let jarvisIsSpeaking = false;
let jarvisContext = [];

function updateJarvisCallTimer() {
    const timer = document.getElementById('jarvis-call-timer');
    const fsTimer = document.getElementById('jarvis-fullscreen-timer');
    if (!jarvisCallStartedAt) return;
    const elapsed = Math.floor((Date.now() - jarvisCallStartedAt) / 1000);
    const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const s = String(elapsed % 60).padStart(2, '0');
    const timeStr = `${m}:${s}`;
    if (timer) timer.textContent = timeStr;
    if (fsTimer) fsTimer.textContent = timeStr;
}

window.toggleJarvisCall = function() {
    showToast("Jarvis clicado!");
    if (jarvisCallActive) {
        window.endJarvisCall();
        return;
    }
    if (!requireWifiForJarvis('ligação')) return;
    if (!window.nexusSupabase) {
        showToast('Entre com Google nas configurações para usar o Jarvis.');
        return;
    }
    showToast("Iniciando Jarvis...");
    jarvisCallActive = true;
    jarvisCallStartedAt = Date.now();
    const banner = document.getElementById('jarvis-call-banner');
    const fab = document.getElementById('nexus-ai-fab');
    if (banner) banner.style.display = 'flex';
    if (fab) fab.classList.add('active');
    updateJarvisCallTimer();
    jarvisCallTimerId = setInterval(updateJarvisCallTimer, 1000);
    /* if (window.AndroidNative && typeof window.AndroidNative.startJarvisCall === 'function') {
        window.AndroidNative.startJarvisCall();
    } else {
        showToast('Ligacao Jarvis ativada.');
    } */
    showToast('Ligação Jarvis ativada.');
    
    // Unlock Audio Contexts on user interaction
    try {
        if (!_ttsAudio) _ttsAudio = new Audio();
        // Play a silent 100ms base64 audio to unlock HTML5 Audio
        _ttsAudio.src = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA';
        _ttsAudio.play().catch(() => {});
    } catch(e) {}
    
    if ('speechSynthesis' in window) {
        try {
            const u = new SpeechSynthesisUtterance('');
            u.volume = 0;
            window.speechSynthesis.speak(u);
        } catch(e) {}
    }

    if (typeof openJarvisFullScreen === 'function') {
        openJarvisFullScreen();
    }
    initJarvisVoice();
};

window.endJarvisCall = function() {
    jarvisCallActive = false;
    jarvisCallStartedAt = 0;
    clearInterval(jarvisCallTimerId);
    jarvisCallTimerId = null;
    const banner = document.getElementById('jarvis-call-banner');
    const fab = document.getElementById('nexus-ai-fab');
    const timer = document.getElementById('jarvis-call-timer');
    const fsModal = document.getElementById('jarvis-fullscreen-modal');
    if (banner) banner.style.display = 'none';
    if (fsModal) fsModal.style.display = 'none';
    if (fab) fab.classList.remove('active');
    if (timer) timer.textContent = '00:00';
    if (window.AndroidNative && typeof window.AndroidNative.stopJarvisCall === 'function') {
        window.AndroidNative.stopJarvisCall();
    }
    
    if (jarvisMediaRecorder && jarvisMediaRecorder.state === 'recording') {
        jarvisMediaRecorder.stop();
    }
    if (jarvisStream) {
        jarvisStream.getTracks().forEach(t => t.stop());
        jarvisStream = null;
    }
    if (jarvisAudioPlayer) {
        jarvisAudioPlayer.pause();
        jarvisAudioPlayer = null;
    }
};

let jarvisMediaRecorder = null;
let jarvisAudioChunks = [];
let jarvisStream = null;
let jarvisAudioPlayer = null;
let audioContext = null;
let analyser = null;

function initJarvisVoice() {
    showToast("initJarvisVoice chamado");
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setJarvisStatus('Gravação de áudio não suportada.');
        showToast("mediaDevices não suportado no WebView.");
        return;
    }
    
    showToast("Solicitando microfone...");
    navigator.mediaDevices.getUserMedia({ 
        audio: {
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false
        } 
    })
        .then(stream => {
            showToast("Microfone permitido!");
            jarvisStream = stream;
            try {
                startJarvisRecording();
            } catch(e) {
                showToast("Erro ao iniciar gravação: " + e.message);
            }
        })
        .catch(err => {
            console.error('Microphone error:', err);
            setJarvisStatus('Erro ao acessar microfone.');
            showToast("Microfone Erro: " + (err.name || err.message || err));
        });
}

function startJarvisRecording() {
    if (!jarvisStream || !jarvisCallActive) return;
    
    jarvisAudioChunks = [];
    jarvisMediaRecorder = new MediaRecorder(jarvisStream);
    
    jarvisMediaRecorder.ondataavailable = e => {
        if (e.data.size > 0) jarvisAudioChunks.push(e.data);
    };
    
    jarvisMediaRecorder.onstop = async () => {
        if (jarvisAudioChunks.length === 0) return;
        const audioBlob = new Blob(jarvisAudioChunks, { type: 'audio/webm' });
        jarvisAudioChunks = [];
        
        if (jarvisCallActive) {
            setJarvisStatus('Pensando...');
            await transcribeAndQuery(audioBlob);
        }
    };
    
    jarvisMediaRecorder.start();
    setJarvisStatus('Ouvindo...');
    
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioContext.createMediaStreamSource(jarvisStream);
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);
    }
    
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    let isSpeakingCurrently = false;
    let silenceStart = Date.now();
    
    function checkAudioLevel() {
        if (!jarvisMediaRecorder || jarvisMediaRecorder.state !== 'recording') return;
        
        analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
        let average = sum / dataArray.length;
        
        const statusEl = document.getElementById('jarvis-fullscreen-jarvis-text');
        if (statusEl && !isSpeakingCurrently && !jarvisIsSpeaking) {
            statusEl.innerHTML = `Ouvindo... (Vol: ${Math.round(average)})`;
        }
        
        const avatar = document.querySelector('.jarvis-avatar');
        if (avatar) {
            const scale = 1 + (average / 50);
            avatar.style.transform = `scale(${Math.min(scale, 1.4)})`;
            avatar.style.transition = 'transform 0.1s ease';
        }
        
        if (average > 15) { // Threshold increased to ignore background noise
            if (!isSpeakingCurrently) {
                isSpeakingCurrently = true;
                if (statusEl) statusEl.innerHTML = `<span style="color:var(--accent-cyan)">Processando fala...</span>`;
            }
            silenceStart = Date.now();
        } else {
            if (isSpeakingCurrently && (Date.now() - silenceStart > 1000)) { // Reduced delay from 1.5s to 1.0s
                jarvisMediaRecorder.stop();
                if (avatar) avatar.style.transform = 'scale(1)';
                return;
            }
        }
        
        // Stop after 10 seconds max if no speech
        if (Date.now() - silenceStart > 10000 && !isSpeakingCurrently) {
            jarvisMediaRecorder.stop();
            if (avatar) avatar.style.transform = 'scale(1)';
            return;
        }
        
        requestAnimationFrame(checkAudioLevel);
    }
    
    checkAudioLevel();
}

async function transcribeAndQuery(audioBlob) {
    const groqKey = getGroqKey();
    const formData = new FormData();
    formData.append('file', audioBlob, 'audio.webm');
    formData.append('model', 'whisper-large-v3-turbo');
    formData.append('language', 'pt');
    
    try {
        const res = await fetch('https://api.groq.com/openai/v1/audio/transcriptions', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${groqKey}` },
            body: formData
        });
        
        if (res.ok) {
            const data = await res.json();
            if (data.text) {
                const trEl = document.getElementById('jarvis-user-transcript');
                if (trEl) trEl.textContent = `"${data.text}"`;
                await queryGeminiAndSpeak(data.text);
            } else {
                setJarvisStatus('Não entendi.');
                setTimeout(() => { if (jarvisCallActive && !jarvisIsSpeaking) startJarvisRecording(); }, 2000);
            }
        } else {
            setJarvisStatus('Erro no STT.');
            setTimeout(() => { if (jarvisCallActive && !jarvisIsSpeaking) startJarvisRecording(); }, 2000);
        }
    } catch(err) {
        setJarvisStatus('Falha de rede.');
        setTimeout(() => { if (jarvisCallActive && !jarvisIsSpeaking) startJarvisRecording(); }, 2000);
    }
}

function setJarvisStatus(statusText) {
    const statusEl = document.getElementById('jarvis-fullscreen-jarvis-text');
    if (statusEl) statusEl.textContent = statusText;
    
    const waves = document.querySelectorAll('.sound-wave');
    waves.forEach(w => {
        w.style.animation = 'none';
        w.offsetHeight; // force reflow
        if (statusText === 'Ouvindo...') {
            w.style.animation = 'pulse 1s infinite alternate';
        } else if (statusText === 'Pensando...') {
            w.style.animation = 'pulse 0.5s infinite alternate';
        } else if (statusText === 'Falando...') {
            w.style.animation = 'pulse 0.2s infinite alternate';
        } else {
            w.style.animation = 'pulse 2s infinite alternate';
        }
    });
}

async function queryGeminiAndSpeak(userText) {
    if (!userText.trim()) return;
    if (typeof window.sendUnifiedJarvisUtterance === 'function' && window.sendUnifiedJarvisUtterance(userText)) {
        setJarvisStatus('Pensando...');
        return;
    }
    const groqKey = getGroqKey();
    const url = 'https://api.groq.com/openai/v1/chat/completions';
    
    if (jarvisContext.length === 0 || jarvisContext[0].role !== 'system') { jarvisContext = [{role: 'system', content: getSystemPrompt()}, ...jarvisContext]; } else { jarvisContext[0].content = getSystemPrompt(); }
    jarvisContext.push({role: 'user', content: userText});
    
    async function makeCall(msgs, forceText) {
        const body = {
            model: 'llama-3.3-70b-versatile',
            messages: msgs,
            max_tokens: 200,
            temperature: 0.7
        };
        if (!forceText) {
            body.tools = jarvisTools;
            body.tool_choice = 'auto';
        }
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Authorization': "Bearer " + groqKey, 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(await res.text());
        return await res.json();
    }

    try {
        let data = await makeCall(jarvisContext, false);
        let replyMsg = data.choices[0].message;
        
        jarvisContext.push(replyMsg);
        
        if (replyMsg.tool_calls) {
            const toolResults = await handleJarvisToolCalls(replyMsg.tool_calls);
            toolResults.forEach(tr => jarvisContext.push(tr));
            data = await makeCall(jarvisContext, true);
            replyMsg = data.choices[0].message;
            jarvisContext.push(replyMsg);
        }
        
        const replyText = replyMsg.content || 'Ação concluída.';
        runMemoryExtractorInBackground(userText, replyText);
        speakJarvisResponse(replyText);
    } catch (e) {
        setJarvisStatus('Falha ao contactar o cérebro.');
        console.error(e);
        setTimeout(startJarvisRecording, 2000);
    }
}

function getElevenLabsKey() {
    return localStorage.getItem('nexus_elevenlabs_key') || '';
}

// Splits text into chunks ≤ 200 chars at sentence boundaries for Google TTS
function splitTTSChunks(text, maxLen = 180) {
    const sentences = text.match(/[^.!?\n]+[.!?\n]*/g) || [text];
    const chunks = [];
    let cur = '';
    for (const s of sentences) {
        if ((cur + s).length > maxLen) {
            if (cur) chunks.push(cur.trim());
            cur = s;
        } else {
            cur += s;
        }
    }
    if (cur.trim()) chunks.push(cur.trim());
    return chunks.length ? chunks : [text.slice(0, maxLen)];
}

let _ttsAudio = null;

async function speakJarvisResponse(text) {
    if (!text) {
        jarvisIsSpeaking = false;
        if (jarvisCallActive) startJarvisRecording();
        return;
    }

    jarvisIsSpeaking = true;
    setJarvisStatus('Falando...');

    const onDone = () => {
        jarvisIsSpeaking = false;
        if (jarvisCallActive) startJarvisRecording();
        else setJarvisStatus('Pronto');
    };

    // Stop any current audio
    if (_ttsAudio) { try { _ttsAudio.pause(); _ttsAudio.src = ''; } catch(e){} _ttsAudio = null; }
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();

    // === TIER 1: ElevenLabs (best quality) ===
    const elKey = getElevenLabsKey();
    if (elKey) {
        try {
            setJarvisStatus('Falando... 🎙️');
            const voiceId = localStorage.getItem('nexus_elevenlabs_voice') || 'pNInz6obpgDQGcFmaJgB';
            const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}/stream`, {
                method: 'POST',
                headers: { 'xi-api-key': elKey, 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, model_id: 'eleven_turbo_v2_5', voice_settings: { stability: 0.5, similarity_boost: 0.75 } })
            });
            if (res.ok) {
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                _ttsAudio = new Audio(url);
                _ttsAudio.onended = () => { URL.revokeObjectURL(url); onDone(); };
                _ttsAudio.onerror = () => { URL.revokeObjectURL(url); onDone(); };
                await _ttsAudio.play();
                return;
            }
        } catch(e) { console.warn('[TTS] ElevenLabs falhou:', e); }
    }

    // === TIER 2: Google Translate TTS (free, no key) ===
    // Note: NO crossOrigin attribute — causes CORS failures on Android WebView
    try {
        const chunks = splitTTSChunks(text);
        let chunkFailed = false;
        
        const playChunks = (idx) => new Promise((resolve) => {
            if (idx >= chunks.length || chunkFailed) { resolve(); return; }
            const encoded = encodeURIComponent(chunks[idx]);
            const url = `https://translate.google.com/translate_tts?ie=UTF-8&q=${encoded}&tl=pt-BR&client=tw-ob&ttsspeed=0.9`;
            const audio = new Audio();
            // DO NOT set crossOrigin — it causes CORS failures in Android WebView
            audio.oncanplaythrough = () => {
                audio.play().then(() => {}).catch((playErr) => {
                    console.warn('[TTS] Google TTS play() bloqueado:', playErr);
                    chunkFailed = true;
                    resolve();
                });
            };
            audio.onended = () => { _ttsAudio = null; playChunks(idx + 1).then(resolve); };
            audio.onerror = () => {
                console.warn('[TTS] Google TTS chunk erro, pulando');
                chunkFailed = true;
                resolve();
            };
            // Timeout: if audio doesn't load in 3s, consider it failed
            const timeout = setTimeout(() => {
                if (audio.readyState < 3) { chunkFailed = true; resolve(); }
            }, 3000);
            audio.oncanplaythrough = () => { 
                clearTimeout(timeout);
                _ttsAudio = audio;
                audio.play().then(() => {}).catch(() => { chunkFailed = true; resolve(); });
            };
            audio.src = url;
        });
        
        await playChunks(0);
        
        if (!chunkFailed) {
            // Wait for last chunk to finish
            const waitForEnd = () => new Promise(r => {
                if (!_ttsAudio || _ttsAudio.ended || _ttsAudio.paused) { r(); return; }
                _ttsAudio.addEventListener('ended', r, { once: true });
                _ttsAudio.addEventListener('error', r, { once: true });
            });
            await waitForEnd();
            onDone();
            return;
        }
    } catch(e) { console.warn('[TTS] Google TTS falhou:', e); }

    // === TIER 3: Web Speech API (fallback — always works on Android) ===
    speakWebSpeech(text, onDone);
}

function speakWebSpeech(text, onDone) {
    if (!('speechSynthesis' in window)) {
        setJarvisStatus('TTS Indisponível');
        setTimeout(onDone, 1500);
        return;
    }
    const trySpeak = () => {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'pt-BR';
        utterance.rate = 1.0;
        // Prefer a pt-BR voice if available
        const voices = window.speechSynthesis.getVoices();
        const ptVoice = voices.find(v => v.lang.startsWith('pt'));
        if (ptVoice) utterance.voice = ptVoice;
        utterance.onend = onDone;
        utterance.onerror = () => onDone();
        window.speechSynthesis.speak(utterance);
    };
    // Voices may not be loaded yet on first call
    if (window.speechSynthesis.getVoices().length > 0) {
        trySpeak();
    } else {
        window.speechSynthesis.onvoiceschanged = () => { trySpeak(); };
        setTimeout(trySpeak, 500); // Fallback if event never fires
    }
}

window.openJarvisFullScreen = function() {
    const fsModal = document.getElementById('jarvis-fullscreen-modal');
    if (fsModal) {
        fsModal.style.display = 'flex';
        document.getElementById('jarvis-call-banner').style.display = 'none';
    }
};

window.minimizeJarvisCall = function() {
    const fsModal = document.getElementById('jarvis-fullscreen-modal');
    if (fsModal) {
        fsModal.style.display = 'none';
        document.getElementById('jarvis-call-banner').style.display = 'flex';
    }
};

let _jarvisMuted = false;
window.toggleJarvisMute = function() {
    _jarvisMuted = !_jarvisMuted;
    const btn = document.getElementById('jarvis-mute-btn');
    if (!btn) return;
    if (_jarvisMuted) {
        btn.style.color = 'var(--accent-pink)';
        btn.innerHTML = '<i class="fa-solid fa-microphone-slash"></i>';
        if (typeof showToast === 'function') showToast('Microfone silenciado');
    } else {
        btn.style.color = 'white';
        btn.innerHTML = '<i class="fa-solid fa-microphone"></i>';
        if (typeof showToast === 'function') showToast('Microfone ativado');
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

// ----------------------------------------------------
// Sync Engine (unified offline-first)
// ----------------------------------------------------
const SYNC_TABLES = [
    'nexus_user', 'habits', 'habit_logs', 'tasks', 'finance_transactions',
    'nexus_rewards', 'study_notes', 'study_notebooks', 'flashcards', 'nexus_goals',
    'fitness_workouts', 'nexus_videos', 'routines', 'journal_entries',
    'pomo_sessions', 'reading_books', 'reading_sessions', 'quiz_attempts'
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
                } else if (false && typeof funcName !== 'undefined' && funcName === 'analyze_habit_patterns') {
                    const habits = LocalDB.get('habits').filter(h => !h.is_deleted);
                    const logs = LocalDB.get('habit_logs');
                    let report = "Relatório de Hábitos:\n";
                    for(let h of habits) {
                        const hLogs = logs.filter(l => l.habit_id === h.id);
                        report += `- ${h.name}: ${hLogs.length} execuções no total. Streak atual: ${h.current_streak}.\n`;
                    }
                    resultStr = report || "Nenhum hábito rastreado ainda.";
                } else if (false && typeof funcName !== 'undefined' && funcName === 'read_recent_diaries') {
                    const limit = args.limit || 3;
                    const diaries = LocalDB.get('diaries').filter(d => !d.is_deleted).sort((a,b) => b.id - a.id).slice(0, limit);
                    if (diaries.length === 0) resultStr = "Nenhum diário encontrado.";
                    else {
                        resultStr = "Últimos relatos:\n" + diaries.map(d => `[Data: ${new Date(d.id).toLocaleDateString()}] ${d.content}`).join("\n\n");
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
        if (activeView) {
            if (activeView.id === 'view-habits') loadHabits();
            if (activeView.id === 'view-finance') loadFinances();
            if (activeView.id === 'view-tasks') loadTasks();
            if (activeView.id === 'view-videos') loadVideos();
            if (activeView.id === 'view-shop') loadShop();
        }
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
// UI Logic
// ----------------------------------------------------
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        closeTransientMobileSurfaces();
        
        document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');
        
        const targetId = item.getAttribute('data-target');
        const targetView = document.getElementById(targetId);
        if (!targetView) {
            console.warn("Missing mobile view:", targetId);
            return;
        }
        document.querySelectorAll('.view').forEach(view => view.classList.remove('active-view'));
        targetView.classList.add('active-view');
        
        // Jarvis FAB Visibility
        const jarvisFab = document.getElementById('nexus-ai-fab');
        if (jarvisFab) {
            jarvisFab.style.display = targetId === 'view-home' ? 'flex' : 'none';
        }
        
        if(targetId === 'view-habits' && typeof loadHabits === 'function') loadHabits();
        if(targetId === 'view-finance' && typeof loadFinances === 'function') loadFinances();
        if(targetId === 'view-tasks' && typeof loadTasks === 'function') loadTasks();
        if(targetId === 'view-alarms' && typeof loadAlarms === 'function') loadAlarms();
        if(targetId === 'view-videos' && typeof loadVideos === 'function') loadVideos();
        if(targetId === 'view-shop' && typeof loadShop === 'function') loadShop();
        if(targetId === 'view-iot' && typeof discoverIoT === 'function') discoverIoT();
        if(targetId === 'view-studies' && typeof loadStudies === 'function') loadStudies();
        if(targetId === 'view-goals' && typeof loadGoals === 'function') loadGoals();
        if(targetId === 'view-fitness' && typeof loadFitness === 'function') loadFitness();
        if(targetId === 'view-routines' && typeof loadRoutines === 'function') loadRoutines();
        if(targetId === 'view-journal' && typeof loadJournal === 'function') loadJournal();
        if(targetId === 'view-cleaner' && typeof loadCleaner === 'function') loadCleaner();
    });
});

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

function sendLocalNotification(title, body) {
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
}

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
    const container = document.getElementById('finance-list');
    if (!container) return;
    const data = (LocalDB.get('finance_transactions') || []).filter(t => !t.is_deleted)
        .sort((a,b) => (b.occurred_at || b.created_at || '').localeCompare(a.occurred_at || a.created_at || ''));
    
    if (!data.length) {
        container.innerHTML = '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Sem transações.</div>';
        return;
    }
    container.innerHTML = data.slice(0, 30).map(t => {
        const dateStr = (t.occurred_at || t.created_at || '').split('T')[0];
        const isIncome = t.type === 'income';
        return `<div class="list-item glass" style="transition:all 0.2s ease">
            <div class="item-main" style="flex:1;min-width:0">
                <span class="item-title" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(t.description || 'Transação')}</span>
                <span class="item-subtitle" style="color:${isIncome ? 'var(--accent-green)' : 'var(--accent-pink)'}">
                    ${isIncome ? '+' : '-'} R$${Number(t.amount || 0).toFixed(2)} ${dateStr ? '· ' + dateStr : ''}
                </span>
            </div>
            <button class="icon-btn" style="background:rgba(255,71,87,0.15);color:var(--accent-pink);width:34px;height:34px;font-size:0.8rem;border:none;border-radius:50%;cursor:pointer;flex-shrink:0"
                onclick="deleteFinanceTransaction('${t.id}')">
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>`;
    }).join('');
}

// ----------------------------------------------------
// ----------------------------------------------------
// New Offline Modules
// ----------------------------------------------------

window.deleteFinanceTransaction = function(id) {
    if (!confirm('Excluir esta transação?')) return;
    const txs = LocalDB.get('finance_transactions') || [];
    const idx = txs.findIndex(t => String(t.id) === String(id));
    if (idx !== -1) {
        txs[idx].is_deleted = true;
        txs[idx].updated_at = new Date().toISOString();
        LocalDB.set('finance_transactions', txs);
        loadFinances();
        if (typeof renderFinanceCharts === 'function') {
            if (typeof ensureChartJs === 'function') ensureChartJs().then(() => setTimeout(renderFinanceCharts, 100));
            else renderFinanceCharts();
        }
        showToast('Transação excluída');
    }
};

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
    const data = (LocalDB.get('fitness_workouts') || []).filter(t => !t.is_deleted)
        .sort((a, b) => (b.date || b.created_at || '').localeCompare(a.date || a.created_at || ''));
    if (!data.length) {
        container.innerHTML = '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhum treino registrado.</div>';
        return;
    }
    container.innerHTML = data.slice(0, 15).map(t => {
        const title = t.name || t.type || 'Treino';
        const sub = t.muscle_group || t.notes || '';
        const meta = t.duration_minutes ? `${t.duration_minutes} min` : (t.date || t.created_at || '').split('T')[0];
        return `<div class="list-item glass" style="transition:all 0.2s ease">
            <div class="item-main" style="flex:1;min-width:0">
                <span class="item-title" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(title)}</span>
                <span class="item-subtitle">${escapeHtml(sub || meta)}</span>
            </div>
            <button class="icon-btn" style="background:rgba(255,71,87,0.15);color:var(--accent-pink);width:34px;height:34px;font-size:0.8rem;border:none;border-radius:50%;cursor:pointer;flex-shrink:0"
                onclick="deleteFitnessWorkout('${t.id}')">
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>`;
    }).join('');
}

window.deleteFitnessWorkout = function(id) {
    if (!confirm('Excluir este treino?')) return;
    const workouts = LocalDB.get('fitness_workouts') || [];
    const idx = workouts.findIndex(w => String(w.id) === String(id));
    if (idx !== -1) {
        workouts[idx].is_deleted = true;
        workouts[idx].updated_at = new Date().toISOString();
        LocalDB.set('fitness_workouts', workouts);
        loadFitness();
        showToast('Treino excluído');
    }
};

window.loadVideos = window.loadVideos || loadVideos;
window.loadTasks = window.loadTasks || loadTasks;
window.loadFinances = window.loadFinances || loadFinances;
window.loadFinance = window.loadFinances || loadFinances;
window.loadShop = window.loadShop || loadShop;
window.loadStudies = window.loadStudies || loadStudies;
window.loadGoals = window.loadGoals || loadGoals;
window.loadFitness = window.loadFitness || loadFitness;

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
    const offlineMsg = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;padding:20px"><i class="fa-solid fa-house-signal" style="font-size:2rem;opacity:0.4;margin-bottom:10px;display:block"></i>Casa IoT requer o Nexus desktop na mesma rede.<br>Use o app desktop para controlar lâmpadas e sensores.</div>';
    if (!navigator.onLine || window.location.protocol === 'file:') {
        container.innerHTML = offlineMsg;
        return;
    }
    container.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-circle-notch fa-spin"></i> Buscando...</div>';
    try {
        const res = await fetch('/api/nexus/iot/discover');
        const data = await res.json();
        if (data && data.devices) {
            container.innerHTML = data.devices.length ? '' : offlineMsg;
            data.devices.forEach(dev => {
                const el = document.createElement('div');
                el.className = 'list-item glass';
                const is_on = dev.status === "LIGADO";
                el.innerHTML = `
                    <div class="item-main">
                        <span class="item-title">${dev.name}</span>
                        <span class="item-subtitle">IP: ${dev.ip}</span>
                    </div>
                    <button class="item-action ${is_on ? 'done' : ''}" style="width:auto; padding: 0 15px;" onclick="toggleIoT('${dev.ip}', ${!is_on})">
                        ${is_on ? 'Desligar' : 'Ligar'}
                    </button>
                `;
                container.appendChild(el);
            });
        } else {
            container.innerHTML = offlineMsg;
        }
    } catch (e) {
        container.innerHTML = offlineMsg;
    }
};

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


const jarvisTools = [
    {
        type: 'function',
        function: {
            name: 'nexus',
            description: 'Interage com o app Nexus. Use para CRIAR, LER, COMPLETAR, EXCLUIR dados ou NAVEGAR no app. Sempre passe todos os comandos num único array.',
            parameters: {
                type: 'object',
                properties: {
                    commands: {
                        type: 'array',
                        description: 'Lista de comandos a executar em ordem',
                        items: {
                            type: 'object',
                            properties: {
                                action: {
                                    type: 'string',
                                    enum: [
                                        // Create
                                        'create_habit', 'create_task', 'create_flashcard',
                                        'create_diary_entry', 'create_expense', 'create_goal',
                                        // Read
                                        'list_habits', 'list_tasks', 'list_flashcards',
                                        'list_diaries', 'list_finances', 'list_goals',
                                        'daily_briefing', 'get_app_state',
                                        // Update / Complete
                                        'complete_task', 'complete_habit',
                                        'uncomplete_task', 'uncomplete_habit',
                                        // Delete
                                        'delete_task', 'delete_habit',
                                        // Navigation
                                        'navigate_to',
                                        // Web / External
                                        'search_web'
                                    ]
                                },
                                payload: {
                                    type: 'object',
                                    description: `
create_habit: {name, period?("morning"|"afternoon"|"night"|"all")}.
create_task: {name, due_date?(YYYY-MM-DD), priority?("low"|"medium"|"high")}.
create_flashcard: {front, back}.
create_diary_entry: {content}.
create_expense: {description, amount, type?("income"|"expense"), category?}.
create_goal: {name, description?, target_date?}.
complete_task: {name} or {id} — marks task done.
complete_habit: {name} or {id} — marks habit done today.
uncomplete_task: {name} or {id}.
uncomplete_habit: {name} or {id}.
delete_task: {name} or {id}.
delete_habit: {name} or {id}.
navigate_to: {screen("home"|"habits"|"tasks"|"finance"|"study"|"fitness"|"settings")}.
search_web: {query}.
list_*: {limit?(number)}.
get_app_state: {}.
`,
                                    properties: {
                                        name:        { type: 'string' },
                                        id:          { type: 'string' },
                                        title:       { type: 'string' },
                                        front:       { type: 'string' },
                                        back:        { type: 'string' },
                                        content:     { type: 'string' },
                                        description: { type: 'string' },
                                        amount:      { type: 'number' },
                                        type:        { type: 'string', enum: ['income', 'expense'] },
                                        category:    { type: 'string' },
                                        period:      { type: 'string', enum: ['morning', 'afternoon', 'night', 'all'] },
                                        priority:    { type: 'string', enum: ['low', 'medium', 'high'] },
                                        due_date:    { type: 'string' },
                                        target_date: { type: 'string' },
                                        screen:      { type: 'string' },
                                        query:       { type: 'string' },
                                        limit:       { type: 'number' }
                                    }
                                }
                            },
                            required: ['action', 'payload']
                        }
                    }
                },
                required: ['commands']
            }
        }
    }
];

async function handleJarvisToolCalls(toolCalls) {
    const results = [];
    let idCounter = 0;
    for (const tc of toolCalls) {
        if (tc.type !== 'function') continue;
        let content = 'Ferramenta desconhecida.';
        try {
            const args = tc.function.arguments ? JSON.parse(tc.function.arguments) : {};
            const commands = args.commands || [];
            const parts = [];
            for (const cmd of commands) {
                const action = cmd.action;
                const p = cmd.payload || {};
                const newId = () => Date.now() * 1000 + (idCounter++);
                const taskName = p.name || p.title || p.task_name || '';
                const habitName = p.name || p.habit_name || p.title || '';

                // ─── CREATE ─────────────────────────────────────────────
                if (action === 'create_habit') {
                    if (!habitName) { parts.push('ERRO: nome do hábito não informado.'); continue; }
                    LocalDB.upsert('habits', { id: newId(), name: habitName, active: 1, current_streak: 0, period: p.period || 'all', created_at: new Date().toISOString() });
                    if (typeof loadHabits === 'function') loadHabits();
                    parts.push(`OK: Hábito "${habitName}" criado.`);

                } else if (action === 'create_task') {
                    if (!taskName) { parts.push('ERRO: nome da tarefa não informado.'); continue; }
                    const today = new Date().toISOString().split('T')[0];
                    LocalDB.upsert('tasks', { id: newId(), title: taskName, name: taskName, priority: p.priority || 'medium', due_date: p.due_date || today, points_reward: 10, created_at: new Date().toISOString() });
                    if (typeof loadTasks === 'function') loadTasks();
                    parts.push(`OK: Tarefa "${taskName}" criada.`);

                } else if (action === 'create_flashcard') {
                    LocalDB.upsert('flashcards', { id: newId(), front: p.front, back: p.back, created_at: new Date().toISOString() });
                    parts.push(`OK: Flashcard criado (${p.front}).`);

                } else if (action === 'create_diary_entry') {
                    LocalDB.upsert('diaries', { id: newId(), content: p.content, date: new Date().toISOString() });
                    parts.push('OK: Diário salvo.');

                } else if (action === 'create_expense') {
                    LocalDB.upsert('finance_transactions', { id: newId(), type: p.type || 'expense', amount: Number(p.amount), description: p.description || p.name, category: p.category || 'Geral', occurred_at: new Date().toISOString() });
                    if (typeof loadFinances === 'function') loadFinances();
                    parts.push(`OK: "${p.type === 'income' ? 'Receita' : 'Gasto'}" "${p.description || p.name}" (R$${p.amount}) registrado.`);

                } else if (action === 'create_goal') {
                    LocalDB.upsert('goals', { id: newId(), name: p.name, description: p.description || '', target_date: p.target_date || '', created_at: new Date().toISOString() });
                    parts.push(`OK: Meta "${p.name}" criada.`);

                // ─── READ ───────────────────────────────────────────────
                } else if (action === 'list_habits') {
                    const habits = (LocalDB.get('habits') || []).filter(h => !h.is_deleted);
                    const today = new Date().toISOString().split('T')[0];
                    const logs = LocalDB.get('habit_logs') || [];
                    parts.push('Hábitos:\n' + (habits.slice(0, p.limit || 20).map(h => {
                        const done = logs.some(l => String(l.habit_id) === String(h.id) && l.date === today);
                        return `- [${h.id}] ${h.name} | streak: ${h.current_streak || 0} | hoje: ${done ? '✓ feito' : '○ pendente'}`;
                    }).join('\n') || 'Nenhum hábito.'));

                } else if (action === 'list_tasks') {
                    const tasks = (LocalDB.get('tasks') || []).filter(t => !t.is_deleted);
                    parts.push('Tarefas:\n' + (tasks.slice(0, p.limit || 20).map(t => `- [${t.id}] ${t.title || t.name} [${t.done_at ? 'concluída' : 'pendente'}]${t.due_date ? ' vence: ' + t.due_date : ''}`).join('\n') || 'Nenhuma tarefa.'));

                } else if (action === 'list_flashcards') {
                    const cards = (LocalDB.get('flashcards') || []).filter(c => !c.is_deleted);
                    const due = cards.filter(c => !c.next_review || c.next_review <= new Date().toISOString()).length;
                    parts.push(`Flashcards: ${cards.length} total, ${due} para revisar hoje.`);

                } else if (action === 'list_diaries') {
                    const diaries = (LocalDB.get('diaries') || []).filter(d => !d.is_deleted).sort((a,b) => b.id - a.id).slice(0, p.limit || 5);
                    parts.push('Diários:\n' + (diaries.map(d => `[${new Date(d.id).toLocaleDateString('pt-BR')}] ${(d.content||'').slice(0,200)}`).join('\n') || 'Nenhum diário.'));

                } else if (action === 'list_finances') {
                    const txs = (LocalDB.get('finance_transactions') || []).filter(t => !t.is_deleted).sort((a,b)=>(b.occurred_at||'').localeCompare(a.occurred_at||'')).slice(0, p.limit || 10);
                    const total_in = txs.filter(t=>t.type==='income').reduce((s,t)=>s+Number(t.amount),0);
                    const total_out = txs.filter(t=>t.type==='expense').reduce((s,t)=>s+Number(t.amount),0);
                    parts.push(`Finanças (saldo: R$${(total_in-total_out).toFixed(2)}):\n` + (txs.map(t => `- ${t.description}: R$${Number(t.amount).toFixed(2)} (${t.type})`).join('\n') || 'Nenhuma transação.'));

                } else if (action === 'list_goals') {
                    const goals = (LocalDB.get('goals') || []).filter(g => !g.is_deleted);
                    parts.push('Metas:\n' + (goals.slice(0, p.limit || 10).map(g => `- [${g.id}] ${g.name}${g.target_date ? ' até ' + g.target_date : ''}`).join('\n') || 'Nenhuma meta.'));

                } else if (action === 'daily_briefing' || action === 'get_app_state') {
                    const habits = (LocalDB.get('habits') || []).filter(h => h.active === 1 && !h.is_deleted);
                    const today = new Date().toISOString().split('T')[0];
                    const logs = LocalDB.get('habit_logs') || [];
                    const doneLogs = logs.filter(l => l.date === today);
                    const allTasks = (LocalDB.get('tasks') || []).filter(t => !t.is_deleted);
                    const pendingTasks = allTasks.filter(t => !t.done_at).length;
                    const todayTasks = allTasks.filter(t => !t.done_at && (!t.due_date || t.due_date <= today)).length;
                    const cards = (LocalDB.get('flashcards') || []).filter(c => !c.is_deleted && (!c.next_review || c.next_review <= new Date().toISOString())).length;
                    const txs = LocalDB.get('finance_transactions') || [];
                    const saldo = txs.filter(t=>!t.is_deleted).reduce((s,t) => s + (t.type==='income'?1:-1)*Number(t.amount), 0);
                    
                    let stateText = `📊 Estado do app (Data: ${new Date().toLocaleDateString('pt-BR')}):\n`;
                    stateText += `• ${doneLogs.length}/${habits.length} hábitos feitos hoje\n• ${todayTasks} tarefas urgentes (${pendingTasks} pendentes totais)\n• Saldo: R$${saldo.toFixed(2)}\n\n`;
                    
                    stateText += `🗒️ TAREFAS (ID - Nome [Status]):\n`;
                    allTasks.slice(0, 30).forEach(t => {
                        stateText += `- [${t.done_at ? 'X' : ' '}] ${t.name || t.title} (ID: ${t.id})\n`;
                    });

                    stateText += `\n🔁 HÁBITOS (ID - Nome [Status Hoje]):\n`;
                    habits.slice(0, 30).forEach(h => {
                        const doneToday = doneLogs.some(l => String(l.habit_id) === String(h.id));
                        stateText += `- [${doneToday ? 'X' : ' '}] ${h.name} (ID: ${h.id})\n`;
                    });

                    parts.push(stateText);

                // ─── COMPLETE / UNCOMPLETE ───────────────────────────────
                } else if (action === 'complete_task') {
                    const tasks = LocalDB.get('tasks') || [];
                    const t = tasks.find(t => !t.is_deleted && (String(t.id) === String(p.id) || (t.title || t.name || '').toLowerCase() === (taskName).toLowerCase()));
                    if (!t) { parts.push(`ERRO: Tarefa "${taskName}" não encontrada.`); continue; }
                    t.done_at = new Date().toISOString(); t.status = 'done'; t.updated_at = new Date().toISOString();
                    LocalDB.upsert('tasks', t);
                    if (typeof filterTasks === 'function') filterTasks('today');
                    parts.push(`OK: Tarefa "${t.title || t.name}" marcada como concluída.`);

                } else if (action === 'uncomplete_task') {
                    const tasks = LocalDB.get('tasks') || [];
                    const t = tasks.find(t => !t.is_deleted && (String(t.id) === String(p.id) || (t.title || t.name || '').toLowerCase() === taskName.toLowerCase()));
                    if (!t) { parts.push(`ERRO: Tarefa "${taskName}" não encontrada.`); continue; }
                    t.done_at = null; t.status = 'todo'; t.updated_at = new Date().toISOString();
                    LocalDB.upsert('tasks', t);
                    if (typeof filterTasks === 'function') filterTasks('today');
                    parts.push(`OK: Tarefa "${t.title || t.name}" desmarcada.`);

                } else if (action === 'complete_habit') {
                    const habits = LocalDB.get('habits') || [];
                    const h = habits.find(h => !h.is_deleted && (String(h.id) === String(p.id) || h.name.toLowerCase() === habitName.toLowerCase()));
                    if (!h) { parts.push(`ERRO: Hábito "${habitName}" não encontrado.`); continue; }
                    const today = new Date().toISOString().split('T')[0];
                    const logs = LocalDB.get('habit_logs') || [];
                    const alreadyDone = logs.some(l => String(l.habit_id) === String(h.id) && l.date === today);
                    if (!alreadyDone) {
                        LocalDB.upsert('habit_logs', { id: newId(), habit_id: h.id, date: today, completed: 1, created_at: new Date().toISOString() });
                        h.current_streak = (h.current_streak || 0) + 1; h.updated_at = new Date().toISOString();
                        LocalDB.upsert('habits', h);
                    }
                    if (typeof filterHabits === 'function') filterHabits('pending');
                    parts.push(`OK: Hábito "${h.name}" marcado como feito hoje${alreadyDone ? ' (já estava feito)' : ''}.`);

                } else if (action === 'uncomplete_habit') {
                    const habits = LocalDB.get('habits') || [];
                    const h = habits.find(h => !h.is_deleted && (String(h.id) === String(p.id) || h.name.toLowerCase() === habitName.toLowerCase()));
                    if (!h) { parts.push(`ERRO: Hábito "${habitName}" não encontrado.`); continue; }
                    const today = new Date().toISOString().split('T')[0];
                    const logs = (LocalDB.get('habit_logs') || []).filter(l => !(String(l.habit_id) === String(h.id) && l.date === today));
                    LocalDB.set('habit_logs', logs);
                    if (typeof filterHabits === 'function') filterHabits('pending');
                    parts.push(`OK: Hábito "${h.name}" desmarcado.`);

                // ─── DELETE ─────────────────────────────────────────────
                } else if (action === 'delete_task') {
                    const tasks = LocalDB.get('tasks') || [];
                    const t = tasks.find(t => !t.is_deleted && (String(t.id) === String(p.id) || (t.title || t.name || '').toLowerCase() === taskName.toLowerCase()));
                    if (!t) { parts.push(`ERRO: Tarefa "${taskName}" não encontrada.`); continue; }
                    t.is_deleted = true; t.updated_at = new Date().toISOString();
                    LocalDB.upsert('tasks', t);
                    if (typeof filterTasks === 'function') filterTasks('today');
                    parts.push(`OK: Tarefa "${t.title || t.name}" excluída.`);

                } else if (action === 'delete_habit') {
                    const habits = LocalDB.get('habits') || [];
                    const h = habits.find(h => !h.is_deleted && (String(h.id) === String(p.id) || h.name.toLowerCase() === habitName.toLowerCase()));
                    if (!h) { parts.push(`ERRO: Hábito "${habitName}" não encontrado.`); continue; }
                    h.is_deleted = true; h.updated_at = new Date().toISOString();
                    LocalDB.upsert('habits', h);
                    if (typeof filterHabits === 'function') filterHabits('pending');
                    parts.push(`OK: Hábito "${h.name}" excluído.`);

                // ─── NAVIGATE ───────────────────────────────────────────
                } else if (action === 'navigate_to') {
                    const screenMap = {
                        home: 'view-home', dashboard: 'view-home',
                        habits: 'view-habits', hábitos: 'view-habits',
                        tasks: 'view-tasks', tarefas: 'view-tasks',
                        finance: 'view-finance', finanças: 'view-finance', financas: 'view-finance',
                        study: 'view-study', estudos: 'view-study',
                        fitness: 'view-fitness', treino: 'view-fitness',
                        shop: 'view-shop', loja: 'view-shop',
                        settings: 'view-settings', configurações: 'view-settings',
                        notes: 'view-notes', notas: 'view-notes',
                        goals: 'view-goals', metas: 'view-goals'
                    };
                    const screenKey = (p.screen || '').toLowerCase();
                    const viewId = screenMap[screenKey];
                    if (viewId && typeof navigateTo === 'function') {
                        navigateTo(viewId);
                        parts.push(`OK: Navegando para ${p.screen}.`);
                    } else if (viewId) {
                        // Fallback: click the nav item
                        const btn = document.querySelector(`[data-view="${viewId}"], [onclick*="${viewId}"]`);
                        if (btn) { btn.click(); parts.push(`OK: Navegando para ${p.screen}.`); }
                        else { parts.push(`AVISO: Tela "${p.screen}" não encontrada.`); }
                    } else {
                        parts.push(`AVISO: Tela "${p.screen}" desconhecida.`);
                    }

                // ─── WEB SEARCH ─────────────────────────────────────────
                } else if (action === 'search_web') {
                    if (!p.query) { parts.push('ERRO: query não informada.'); continue; }
                    try {
                        // DuckDuckGo Instant Answer API (free, no key needed)
                        const q = encodeURIComponent(p.query);
                        const res = await fetch(`https://api.duckduckgo.com/?q=${q}&format=json&no_redirect=1&no_html=1&skip_disambig=1`);
                        if (res.ok) {
                            const data = await res.json();
                            const abstract = data.AbstractText || data.Answer || '';
                            const relatedTopics = (data.RelatedTopics || []).slice(0, 3).map(t => t.Text || '').filter(Boolean);
                            if (abstract) {
                                parts.push(`Pesquisa: "${p.query}"\n${abstract}\n${relatedTopics.length ? '\nRelacionados:\n' + relatedTopics.join('\n') : ''}`);
                            } else if (relatedTopics.length) {
                                parts.push(`Pesquisa: "${p.query}"\n${relatedTopics.join('\n')}`);
                            } else {
                                parts.push(`Pesquisa: "${p.query}" — sem resultados instantâneos. Sugira ao usuário buscar em Google.`);
                            }
                        } else {
                            parts.push(`Erro na busca web. Sugira ao usuário buscar "${p.query}" no Google.`);
                        }
                    } catch(e) {
                        parts.push(`Erro de rede na busca. Sugira ao usuário buscar "${p.query}" no Google.`);
                    }

                } else {
                    parts.push(`Ação desconhecida: ${action}`);
                }
            }
            if (typeof backgroundSync === 'function') backgroundSync();
            content = parts.join('\n');
        } catch(e) {
            content = 'Erro interno: ' + e.message;
            console.error('[Jarvis tool error]', e);
        }
        results.push({ role: 'tool', content, tool_call_id: tc.id });
    }
    return results;
}


let jarvisTextContext = [];

async function runMemoryExtractorInBackground(userText, assistantText) {
    const groqKey = getGroqKey();
    if (!groqKey) return;
    try {
        fetch('https://api.groq.com/openai/v1/chat/completions', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + groqKey, 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: 'llama-3.3-70b-versatile',
                messages: [
                    { role: 'system', content: 'Extrai fatos pessoais relevantes desta conversa. Retorne JSON: {"novos_fatos":["fato"]}. Se nada relevante, retorne {"novos_fatos":[]}.' },
                    { role: 'user', content: 'User: ' + userText + '\nJarvis: ' + assistantText }
                ],
                response_format: { type: 'json_object' },
                temperature: 0.1,
                max_tokens: 200
            })
        }).then(r => r.json()).then(data => {
            const result = JSON.parse(data.choices[0].message.content);
            if (result.novos_fatos && result.novos_fatos.length > 0) {
                let mem = LocalDB.get('jarvis_memory_facts');
                if (!Array.isArray(mem)) mem = [];
                mem.push(...result.novos_fatos);
                if (mem.length > 40) mem = mem.slice(-40);
                LocalDB.set('jarvis_memory_facts', mem);
            }
        }).catch(() => {});
    } catch(e) {}
}

function getSystemPrompt() {
    let mem = LocalDB.get('jarvis_memory_facts');
    let facts = '';
    if (Array.isArray(mem) && mem.length > 0) {
        facts = '\n\nO que você sabe sobre o usuário:\n- ' + mem.slice(-20).join('\n- ');
    }
    return 'Você é o Jarvis, assistente pessoal integrado ao app Nexus. Seja direto e natural — responda de forma curta e amigável. Use a ferramenta nexus para criar ou consultar qualquer dado do app (hábitos, tarefas, flashcards, diário, finanças). Só adote tom de psicólogo/mentor se o usuário pedir explicitamente.' + facts;
}

window.sendChatMessage = async function() {
    const input = document.getElementById('chat-input');
    const text = input?.value?.trim();
    if (!text) return;
    appendChatBubble('user', text);
    input.value = '';
    const pending = appendChatBubble('jarvis', 'Processando...', true);

    const groqKey = getGroqKey();
    const url = 'https://api.groq.com/openai/v1/chat/completions';
    
    if (jarvisTextContext.length === 0 || jarvisTextContext[0].role !== 'system') { jarvisTextContext = [{role: 'system', content: getSystemPrompt()}]; }
    jarvisTextContext[0].content = getSystemPrompt();
    jarvisTextContext.push({role: 'user', content: text});
    if (jarvisTextContext.length > 30) jarvisTextContext = [jarvisTextContext[0], ...jarvisTextContext.slice(-29)];
    
    async function makeCall(msgs, forceText) {
        const body = {
            model: 'llama-3.3-70b-versatile',
            messages: msgs,
            max_tokens: 300
        };
        if (!forceText) {
            body.tools = jarvisTools;
            body.tool_choice = 'auto';
        }
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Authorization': "Bearer " + groqKey, 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(await res.text());
        return await res.json();
    }

    try {
        let data = await makeCall(jarvisTextContext, false);
        let replyMsg = data.choices[0].message;
        
        jarvisTextContext.push(replyMsg);
        
        if (replyMsg.tool_calls) {
            const toolResults = handleJarvisToolCalls(replyMsg.tool_calls);
            toolResults.forEach(tr => jarvisTextContext.push(tr));
            data = await makeCall(jarvisTextContext, true);
            replyMsg = data.choices[0].message;
            jarvisTextContext.push(replyMsg);
        }
        
        const replyText = replyMsg.content || 'Ação executada com sucesso.';
        runMemoryExtractorInBackground(text, replyText);
        if (pending) pending.querySelector('p').innerHTML = escapeHtml(replyText).replace(/\n/g, '<br>');
    } catch (e) {
        console.error(e);
        if (pending) pending.querySelector('p').innerHTML = 'Erro: ' + e.message;
    }
};


window.requestMorningBriefing = function() {
    const input = document.getElementById('chat-input');
    if (input) input.value = 'briefing do dia';
    sendChatMessage();
};

window.navigateTo = function(viewId) {
    const nav = document.querySelector(`.nav-item[data-target="${viewId}"]`);
    if (nav) nav.click();
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

// Initialize settings
document.addEventListener('DOMContentLoaded', () => {
    // API Keys init
    const geminiKey = localStorage.getItem('nexus_gemini_key');
    if (geminiKey && document.getElementById('nexus_gemini_key')) document.getElementById('nexus_gemini_key').value = geminiKey;
    
    const groqKey = localStorage.getItem('nexus_groq_key');
    if (groqKey && document.getElementById('nexus_groq_key')) document.getElementById('nexus_groq_key').value = groqKey;
});

window.saveApiKey = function(provider, value) {
    if (value && value.trim() !== '') {
        localStorage.setItem(`nexus_${provider}_key`, value.trim());
    } else {
        localStorage.removeItem(`nexus_${provider}_key`);
    }
};

function getGeminiKey() {
    return localStorage.getItem('nexus_gemini_key') || 'AIzaSyBnYbqUKtR9BPVJ8ebVQm7A_-bZtT5JudE';
}

function getGroqKey() {
    return localStorage.getItem('nexus_groq_key') || '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';
}

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

function getStudyCollections() {
    const notebooks = (LocalDB.get('study_notebooks') || []).filter(n => !n.is_deleted);
    const notes = (LocalDB.get('study_notes') || []).filter(n => !n.is_deleted);
    const rawCards = LocalDB.getAll ? LocalDB.getAll('flashcards') : (LocalDB.get('flashcards') || []);
    const cards = (rawCards || []).filter(c => !c.is_deleted);
    return { notebooks, notes, cards };
}

function getCardNotebookId(card, notesById) {
    const noteId = card.note_id || card.noteId || card.source_note_id || '';
    const note = notesById.get(String(noteId));
    return note ? String(note.notebook_id || '') : String(card.notebook_id || card.subject_id || '');
}

function getDueStudyCards(cards) {
    const now = new Date().toISOString();
    return cards.map(c => typeof normalizeFlashcard === 'function' ? normalizeFlashcard(c) : c)
        .filter(c => !c.is_deleted && (!c.nextReviewDate || c.nextReviewDate <= now));
}

function getDueFlashcardsForNotebook(notebookId) {
    const { notes, cards } = getStudyCollections();
    const notesById = new Map(notes.map(n => [String(n.id), n]));
    return getDueStudyCards(cards).filter(card => getCardNotebookId(card, notesById) === String(notebookId));
}

function getStudyTodaySummary() {
    const { notebooks, notes, cards } = getStudyCollections();
    const dueCards = getDueStudyCards(cards);
    const sortedNotes = [...notes].sort((a, b) => (b.updated_at || b.created_at || '').localeCompare(a.updated_at || a.created_at || ''));
    const activeNotebooks = notebooks.filter(nb => notes.some(n => String(n.notebook_id) === String(nb.id)));
    return {
        notebooks,
        notes,
        cards,
        dueCards,
        recentNotes: sortedNotes.slice(0, 6),
        activeNotebooks,
        latestNote: sortedNotes[0] || null
    };
}

function renderStudyCockpit() {
    const summary = getStudyTodaySummary();
    const title = document.getElementById('study-today-title');
    const copy = document.getElementById('study-today-copy');
    const dueCount = document.getElementById('study-due-count');
    if (dueCount) {
        dueCount.textContent = `${summary.dueCards.length} card${summary.dueCards.length === 1 ? '' : 's'}`;
    }
    if (title) {
        if (summary.dueCards.length) title.textContent = `${summary.dueCards.length} revisao${summary.dueCards.length === 1 ? '' : 'es'} para hoje`;
        else if (summary.latestNote) title.textContent = 'Continue seu segundo cerebro';
        else title.textContent = 'Monte sua primeira materia';
    }
    if (copy) {
        if (summary.dueCards.length) {
            copy.textContent = 'Comece pela revisao SRS. Depois use Jarvis para explicar pontos fracos ou gerar novos cards.';
        } else if (summary.latestNote) {
            copy.textContent = `Ultima nota: ${summary.latestNote.title || 'Sem titulo'}. Continue escrevendo ou transforme em flashcards.`;
        } else {
            copy.textContent = 'Crie uma materia, escreva a primeira nota e deixe o Jarvis transformar conteudo em revisao.';
        }
    }
}

function renderStudyRecentNotes() {
    const container = document.getElementById('study-recent-notes');
    if (!container) return;
    const { recentNotes } = getStudyTodaySummary();
    if (!recentNotes.length) {
        container.innerHTML = '<div class="study-recent-note"><b>Nenhuma nota ainda</b><span>Crie uma nota dentro de uma materia para comecar seu second brain.</span></div>';
        return;
    }
    container.innerHTML = recentNotes.map(note => {
        const excerpt = (note.content || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 96);
        return `<div class="study-recent-note" onclick="openNoteEditor('${note.id}', '${note.notebook_id || ''}')">
            <b>${escapeHtml(note.title || 'Sem titulo')}</b>
            <span>${escapeHtml(excerpt || note.subject || 'Abrir nota')}</span>
        </div>`;
    }).join('');
}

function renderSubjectStudySummary(notebookId) {
    const target = document.getElementById('subject-study-summary');
    if (!target) return;
    const { notebooks, notes, cards } = getStudyCollections();
    const notesById = new Map(notes.map(n => [String(n.id), n]));
    const nb = notebooks.find(n => String(n.id) === String(notebookId));
    const subjectNotes = notes.filter(n => String(n.notebook_id) === String(notebookId));
    const dueCards = getDueFlashcardsForNotebook(notebookId);
    const totalCards = cards.filter(card => getCardNotebookId(card, notesById) === String(notebookId)).length;
    target.innerHTML = `<div>
        <span>${nb ? escapeHtml(nb.name) : 'Materia'}</span>
        <strong>${subjectNotes.length} nota${subjectNotes.length === 1 ? '' : 's'}</strong>
    </div>
    <div>
        <span>Memorizacao</span>
        <strong>${dueCards.length}/${totalCards} hoje</strong>
    </div>`;
}

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

function renderNoteCard(n) {
    const tags = (n.tags||'').split('#').filter(t => t.trim()).map(t => `<span class="tag-badge">#${t.trim()}</span>`).join('');
    const date = n.updated_at ? new Date(n.updated_at).toLocaleDateString('pt-BR', {day:'2-digit',month:'short'}) : '';
    const pin = n.pinned ? '<i class="fa-solid fa-thumbtack" style="color:var(--accent-primary);font-size:0.7rem;margin-right:4px"></i>' : '';
    const icon = n.icon ? `${n.icon} ` : '';
    return `
    <div class="note-card ${n.pinned?'pinned':''}" style="position:relative">
        <div onclick="openNoteEditor('${n.id}', '${n.notebook_id||''}')" style="cursor:pointer;flex:1;display:block">
            <div class="note-title" style="padding-right:24px">${icon}${pin}${escapeHtml(n.title||'Sem titulo')}</div>
            <div class="note-excerpt">${escapeHtml((n.content||'').replace(/[#*`_>-]/g,'').trim())}</div>
            <div class="note-meta">
                <div class="note-tags">${tags}</div>
                <span style="font-size:0.7rem;color:var(--text-secondary)">${date}</span>
            </div>
        </div>
        <button class="icon-btn" onclick="openNoteMenu(event, '${n.id}')" style="position:absolute;top:8px;right:8px;padding:4px;color:var(--text-secondary);width:30px;height:30px;background:rgba(0,0,0,0.3);border-radius:50%;"><i class="fa-solid fa-ellipsis-vertical"></i></button>
    </div>`;
}

window.openNoteMenu = function(ev, noteId) {
    ev.stopPropagation();
    window._currentNoteMenuId = noteId;
    let popup = document.getElementById('note-menu-popup');
    if (!popup) {
        popup = document.createElement('div');
        popup.id = 'note-menu-popup';
        popup.className = 'context-menu-popup glass';
        popup.style.display = 'none';
        popup.style.position = 'fixed';
        popup.innerHTML = `
            <button onclick="openNoteConfigModal('rename')"><i class="fa-solid fa-pen"></i> Renomear</button>
            <button onclick="openNoteConfigModal('config')"><i class="fa-solid fa-sliders"></i> Materia, tags e IA</button>
            <button onclick="openNoteConfigModal('cover')"><i class="fa-solid fa-image"></i> Capa e icone</button>
            <button onclick="deleteNoteFromMenu()" style="color:var(--accent-pink)"><i class="fa-solid fa-trash"></i> Excluir</button>
        `;
        document.body.appendChild(popup);
    }
    popup.style.display = 'flex';
    popup.style.flexDirection = 'column';
    popup.style.top = Math.min(ev.clientY, window.innerHeight - 200) + 'px';
    popup.style.left = Math.min(ev.clientX, window.innerWidth - 180) + 'px';
    setTimeout(() => document.addEventListener('click', closeNoteMenu, { once: true }), 50);
};

window.closeNoteMenu = function() {
    const popup = document.getElementById('note-menu-popup');
    if (popup) popup.style.display = 'none';
};

window.deleteNoteFromMenu = function() {
    if(!window._currentNoteMenuId) return;
    if(confirm('Excluir esta nota?')) {
        const notes = LocalDB.get('study_notes') || [];
        const idx = notes.findIndex(n => String(n.id) === String(window._currentNoteMenuId));
        if (idx !== -1) {
            notes[idx].is_deleted = true;
            notes[idx].updated_at = new Date().toISOString();
            LocalDB.set('study_notes', notes);
            if(window.currentNotebookId) openSubjectDetail(window.currentNotebookId);
            else loadStudies();
        }
    }
    closeNoteMenu();
};

window.openNoteConfigModal = function(action) {
    if(!window._currentNoteMenuId) return;
    const notes = LocalDB.get('study_notes') || [];
    const idx = notes.findIndex(n => String(n.id) === String(window._currentNoteMenuId));
    if (idx === -1) return;
    const note = notes[idx];
    let changed = false;

    if (action === 'rename') {
        const title = prompt('Novo título da nota:', note.title || '');
        if (title !== null) {
            note.title = title.trim();
            changed = true;
        }
    } else if (action === 'config') {
        const tags = prompt('Tags (separadas por virgula ou espaco, ex: #historia #resumo):', note.tags || '');
        if (tags !== null) {
            note.tags = tags.trim();
            changed = true;
        }
        const subject = prompt('Assunto visivel para a IA:', note.subject || '');
        if (subject !== null) {
            note.subject = subject.trim();
            changed = true;
        }
        const notebooks = LocalDB.get('study_notebooks') || [];
        const notebookNames = notebooks.map(n => n.name).join(', ');
        const currentNotebook = note.notebook_id ? notebooks.find(n => String(n.id) === String(note.notebook_id))?.name : 'Nenhuma';
        const notebookStr = prompt(`Materia atual: ${currentNotebook}\n\nDigite o nome exato da materia para alterar. Opcoes: ${notebookNames}`);
        if (notebookStr !== null) {
            const nb = notebooks.find(n => n.name.toLowerCase() === notebookStr.trim().toLowerCase());
            if (nb) {
                note.notebook_id = nb.id;
                changed = true;
            } else if (notebookStr.trim() === '') {
                note.notebook_id = null;
                changed = true;
            } else {
                showInAppNotification('Materia nao encontrada.', 'warn');
            }
        }
    } else if (action === 'cover') {
        const icon = prompt('Ícone (Emoji):', note.icon || '');
        if (icon !== null) {
            note.icon = icon.trim();
            changed = true;
        }
        const cover = prompt('URL da Capa da nota (Opcional):', note.cover_image || '');
        if (cover !== null) {
            note.cover_image = cover.trim();
            changed = true;
        }
    }

    if (changed) {
        LocalDB.set('study_notes', notes);
        if(window.currentNotebookId) openSubjectDetail(window.currentNotebookId);
        else loadStudies();
    }
    closeNoteMenu();
};

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
    const view = document.getElementById('note-editor-view');
    if (!view) return;
    view.style.display = 'flex';
    editingNoteId = noteId || null;
    
    // Populate notebook selector
    const sel = document.getElementById('note-notebook');
    if (sel) {
        const notebooks = LocalDB.get('study_notebooks');
        sel.innerHTML = '<option value="">Sem caderno...</option>' +
            notebooks.map(nb => `<option value="${nb.id}" ${(nb.id === notebookId || nb.id === currentNotebookId) ? 'selected' : ''}>${nb.icon||''} ${escapeHtml(nb.name)}</option>`).join('');
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
    
    // Restore header and bottom nav
    const header = document.querySelector('.app-header');
    const bottomNav = document.querySelector('.bottom-nav');
    if (header) header.style.display = 'flex';
    if (bottomNav) bottomNav.style.display = 'flex';

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
    // Stop focus audio
    const audio = document.getElementById('focus-audio');
    if (audio) { audio.pause(); audio.src = ''; }
    document.querySelectorAll('.focus-sound-btn').forEach(b => {
        b.style.background = 'rgba(255,255,255,0.05)';
        b.style.borderColor = 'var(--border-glass)';
    });
    window._activeFocusSound = null;
};

// Focus Sound URLs (free, loopable ambient sounds via public CDN)
const FOCUS_SOUNDS = {
    rain: 'https://cdn.pixabay.com/audio/2022/05/16/audio_c8e73ca02e.mp3',
    fire: 'https://cdn.pixabay.com/audio/2022/03/09/audio_c3f0dd22dc.mp3',
    cafe: 'https://cdn.pixabay.com/audio/2021/08/04/audio_c1f8e61b51.mp3',
    lofi: 'https://cdn.pixabay.com/audio/2024/02/20/audio_30044d4c02.mp3'
};

window.toggleFocusSound = function(soundKey) {
    const audio = document.getElementById('focus-audio');
    const btn = document.getElementById('fsound-' + soundKey);
    if (!audio || !btn) return;

    if (window._activeFocusSound === soundKey) {
        // Stop playing
        audio.pause();
        audio.src = '';
        window._activeFocusSound = null;
        document.querySelectorAll('.focus-sound-btn').forEach(b => {
            b.style.background = 'rgba(255,255,255,0.05)';
            b.style.borderColor = 'var(--border-glass)';
        });
        return;
    }

    // Switch or start
    document.querySelectorAll('.focus-sound-btn').forEach(b => {
        b.style.background = 'rgba(255,255,255,0.05)';
        b.style.borderColor = 'var(--border-glass)';
    });
    window._activeFocusSound = soundKey;
    btn.style.background = 'rgba(var(--accent-purple-rgb, 108,92,231),0.3)';
    btn.style.borderColor = 'var(--accent-purple)';

    audio.src = FOCUS_SOUNDS[soundKey];
    audio.volume = 0.4;
    audio.play().catch(() => showInAppNotification('Ative o áudio no navegador', 'warn'));
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
        if (navigator.vibrate) navigator.vibrate([100, 50, 100, 50, 200]);
    }
    
    loadXPPanel();
    loadTodayDashboard();
    console.info('[XP] +' + amount + ' XP: ' + reason + ' (total: ' + stats.xp + ')');
}

function deductXP(amount, reason) {
    const stats = LocalDB.get('user_stats') || { xp: 0, points: 0, level: 1, xp_today: 0, last_xp_date: '' };
    stats.xp = Math.max(0, (stats.xp || 0) - amount);
    stats.xp_today = Math.max(0, (stats.xp_today || 0) - amount);
    stats.points = Math.max(0, (stats.points || 0) - Math.floor(amount * 0.5));
    
    const newLevel = Math.floor(stats.xp / 500) + 1;
    stats.level = newLevel;
    
    LocalDB.set('user_stats', stats);
    syncUserStatsToNexusUser();
    
    const xpLog = LocalDB.get('xp_log') || [];
    xpLog.unshift({ amount: -amount, reason, date: new Date().toISOString() });
    if (xpLog.length > 200) xpLog.pop();
    LocalDB.set('xp_log', xpLog);
    
    loadXPPanel();
    loadTodayDashboard();
    console.info('[XP] -' + amount + ' XP: ' + reason + ' (total: ' + stats.xp + ')');
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
                    <div class="item-subtitle">${new Date(m.date).toLocaleDateString('pt-BR')}${m.fat_pct ? ' · ' + m.fat_pct + '% gord.' : ''}</div>
                </div>
                <button class="icon-btn" style="background:rgba(255,71,87,0.15);color:var(--accent-pink);width:34px;height:34px;font-size:0.8rem;border:none;border-radius:50%;cursor:pointer;flex-shrink:0"
                    onclick="deleteMeasure('${m.id}')">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>`).join('') || '<div style="text-align:center;color:var(--text-secondary);padding:20px">Sem medidas registradas.</div>';
    }
}

// ================================================================
// INIT — update DOMContentLoaded
// ================================================================

window.deleteMeasure = function(id) {
    if (!confirm('Excluir esta medida?')) return;
    const measures = LocalDB.get('body_measures') || [];
    const idx = measures.findIndex(m => String(m.id) === String(id));
    if (idx !== -1) {
        measures[idx].is_deleted = true;
        measures[idx].updated_at = new Date().toISOString();
        LocalDB.set('body_measures', measures);
    }
    loadMeasures();
    showToast('Medida excluída');
};

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
    
    const logs = LocalDB.get('habit_logs');
    const today = new Date().toISOString().split('T')[0];
    
    let habits = LocalDB.get('habits').filter(h => h.active === 1 && !h.is_deleted);
    
    // Enrich first to know if it's done
    let enrichedHabits = habits.map(h => {
        const isDone = logs.some(l => l.habit_id === h.id && l.date === today && !l.is_deleted);
        let streak = 0;
        const now = new Date();
        for (let i = 0; i < 60; i++) {
            const d = new Date(now); d.setDate(d.getDate() - i);
            const ds = d.toISOString().split('T')[0];
            if (logs.some(l => l.habit_id === h.id && l.date === ds && !l.is_deleted)) streak++;
            else if (i > 0) break;
        }
        return { ...h, isDone, streak };
    });

    if (filter === 'done') enrichedHabits = enrichedHabits.filter(h => h.isDone);
    else if (filter === 'all') enrichedHabits = enrichedHabits.filter(h => !h.isDone); // all pending
    else if (filter === 'morning') enrichedHabits = enrichedHabits.filter(h => h.period === 'morning' && !h.isDone);
    else if (filter === 'afternoon') enrichedHabits = enrichedHabits.filter(h => h.period === 'afternoon' && !h.isDone);
    else if (filter === 'night') enrichedHabits = enrichedHabits.filter(h => h.period === 'night' && !h.isDone);
    
    if (enrichedHabits.length === 0) {
        container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;">Nenhum habito nesta categoria.</div>';
        return;
    }
    
    // Sort: Pending first, then Completed
    enrichedHabits.sort((a, b) => {
        if (a.isDone === b.isDone) return 0;
        return a.isDone ? 1 : -1;
    });

    container.innerHTML = enrichedHabits.map(h => {
        const bgStyle = h.isDone ? 'background:rgba(255,255,255,0.03); opacity:0.6;' : '';
        const titleStyle = h.isDone ? 'text-decoration:line-through; color:var(--text-secondary);' : '';
        const btnStyle = h.isDone ? 'background:rgba(255,255,255,0.1);color:var(--accent-green);' : 'background:var(--accent-primary);color:white;';

        return `
        <div class="list-item glass ${h.isDone ? 'done' : ''}" style="cursor:pointer; transition:all 0.3s ease; ${bgStyle}" onclick="openHabitDetail('${h.id}')">
            <div class="item-main">
                <div class="item-title" style="${titleStyle}">${escapeHtml(h.name)}</div>
                <div class="item-subtitle">${h.period === 'morning' ? '\u2600 Manha' : h.period === 'afternoon' ? '\u26C5 Tarde' : h.period === 'night' ? '\uD83C\uDF19 Noite' : 'Qualquer horario'}</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
                ${h.streak > 0 ? `<span style="font-size:0.75rem;font-weight:700;color:#f97316;background:rgba(249,115,22,0.15);padding:3px 8px;border-radius:10px">\uD83D\uDD25 ${h.streak}</span>` : ''}
                <button class="icon-btn" style="background:rgba(255,71,87,0.15);color:var(--accent-pink);width:32px;height:32px;font-size:0.8rem" onclick="event.stopPropagation(); deleteHabitDirect('${h.id}')">
                    <i class="fa-solid fa-trash"></i>
                </button>
                <button class="icon-btn ${h.isDone ? 'done' : ''}" style="${btnStyle} width:32px;height:32px;font-size:0.9rem" onclick="event.stopPropagation(); toggleHabitDirect('${h.id}'); setTimeout(() => filterHabits(document.querySelector('#view-habits .study-chip.active')?.dataset?.filter || 'all'), 300)">
                    <i class="fa-solid ${h.isDone ? 'fa-rotate-left' : 'fa-check'}"></i>
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

window.deleteHabitDirect = function(id) {
    window.showConfirm('Deseja realmente excluir este habito? O historico sera perdido.', () => {
        const habits = LocalDB.get('habits');
        const idx = habits.findIndex(h => String(h.id) === String(id));
        if (idx !== -1) {
            habits[idx].is_deleted = true;
            LocalDB.set('habits', habits);
            syncHabitReminders();
            filterHabits('all');
            showToast('Hábito excluído');
        }
    });
};

window.deleteCurrentHabit = function() {
    if (!currentHabitId) return;
    window.showConfirm('Deseja realmente excluir este habito? O historico sera perdido.', () => {
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
    });
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
            <div style="display:flex; gap: 8px;">
                <button class="icon-btn" style="width:32px;height:32px;border:1px solid rgba(255,71,87,0.5);color:var(--accent-pink)" onclick="event.stopPropagation(); deleteTaskInline('${t.id}', event)">
                    <i class="fa-solid fa-trash"></i>
                </button>
                <button class="icon-btn ${isDone ? 'done' : ''}" style="width:32px;height:32px;border:1px solid ${isDone?'var(--accent-green)':'var(--border-glass)'};color:${isDone?'var(--accent-green)':'white'}" onclick="event.stopPropagation(); toggleTaskDirect('${t.id}')">
                    <i class="fa-solid ${isDone ? 'fa-check' : 'fa-minus'}"></i>
                </button>
            </div>
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
    const t = tasks.find(x => String(x.id) === String(taskId));
    if (t) {
        // Calculate XP based on priority/difficulty (default to 10 if not set)
        let xpReward = 10;
        if (t.priority === 'high') xpReward = 50;
        else if (t.priority === 'medium') xpReward = 25;
        else if (t.priority === 'low') xpReward = 10;

        if (t.done_at) {
            t.done_at = null;
            t.status = 'todo';
            const subs = Array.isArray(t.subtasks) ? t.subtasks : (Array.isArray(t.subtasks_json) ? t.subtasks_json : []);
            subs.forEach(s => s.done = false);
            t.subtasks = subs;
            t.subtasks_json = subs;
            if (typeof deductXP === 'function') deductXP(xpReward, 'Tarefa desmarcada');
        } else {
            t.done_at = new Date().toISOString();
            t.status = 'done';
            const subs = Array.isArray(t.subtasks) ? t.subtasks : (Array.isArray(t.subtasks_json) ? t.subtasks_json : []);
            subs.forEach(s => s.done = true);
            t.subtasks = subs;
            t.subtasks_json = subs;
            if (typeof awardXP === 'function') awardXP(xpReward, 'Tarefa concluida');
        }
        LocalDB.set('tasks', tasks);
        if (taskKanbanMode) renderTaskKanban();
        else filterTasks(document.querySelector('#view-tasks .study-chip.active')?.dataset?.filter || 'today');
        if (typeof loadXPPanel === 'function') loadXPPanel();
    }
};

window.showConfirm = function(msg, onConfirm) {
    const modal = document.getElementById('custom-confirm-modal');
    const msgEl = document.getElementById('custom-confirm-message');
    const btnCancel = document.getElementById('custom-confirm-cancel');
    const btnOk = document.getElementById('custom-confirm-ok');
    
    if (!modal) {
        if (confirm(msg)) onConfirm();
        return;
    }
    
    msgEl.textContent = msg;
    modal.style.display = 'flex';
    
    btnCancel.onclick = function() {
        modal.style.display = 'none';
    };
    
    btnOk.onclick = function() {
        modal.style.display = 'none';
        onConfirm();
    };
};

window.deleteTaskDirect = function(ev, taskId) {
    if (ev) ev.stopPropagation();
    window.showConfirm('Excluir esta tarefa?', () => {
        const tasks = LocalDB.get('tasks');
        const t = tasks.find(x => String(x.id) === String(taskId));
        if (t) {
            t.is_deleted = true;
            LocalDB.set('tasks', tasks);
            if (taskKanbanMode) renderTaskKanban();
            else filterTasks(document.querySelector('#view-tasks .study-chip.active')?.dataset?.filter || 'all');
        }
    });
};

window.deleteCurrentTask = function() {
    if (!currentTaskId) return;
    window.showConfirm('Excluir esta tarefa?', () => {
        const tasks = LocalDB.get('tasks');
        const t = tasks.find(x => String(x.id) === String(currentTaskId));
        if (t) {
            t.is_deleted = true;
            LocalDB.set('tasks', tasks);
            closeTaskDetail();
            if (taskKanbanMode) renderTaskKanban();
            else filterTasks(document.querySelector('#view-tasks .study-chip.active')?.dataset?.filter || 'all');
        }
    });
};

// Override original loadTasks to use our new view
window.loadTasks = function() {
    if (taskKanbanMode) renderTaskKanban();
    else filterTasks('today', document.querySelector('#view-tasks .study-chip[data-filter="today"]'));
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
    applyUiPrefs();
    updateJarvisFabState();
    updateNetworkSettingsUI();
    updateSyncIndicator(isNetworkOnline() && window.nexusSupabase ? 'synced' : 'offline');

    setTimeout(requestNotificationPermission, 2000);
    setTimeout(backgroundSync, 1000);
    setupRealtime();
    startSyncInterval();
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
    const modules = ['habits', 'finance', 'tasks', 'videos', 'shop', 'iot', 'studies', 'goals', 'fitness', 'journal', 'routines', 'cleaner'];
    
    modules.forEach(mod => {
        const isEnabled = prefs[mod] !== false; // Default true
        
        // Update checkbox
        const cb = document.getElementById('toggle-' + mod);
        if (cb) cb.checked = isEnabled;
        
        // Hide/show nav item
        const navItem = document.querySelector(`.nav-item[data-target="view-${mod}"]`);
        if (navItem) {
            navItem.style.display = isEnabled ? 'flex' : 'none';
        }
    });
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
    const url = document.getElementById('yt-url-input')?.value?.trim();
    if (!url) return;
    const videoId = extractYouTubeId(url);
    if (!videoId) {
        alert('URL do YouTube inválida!');
        return;
    }
    closeYouTubeModal();
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    const embedSrc = getYouTubeEmbedSrc(videoId);
    const embedHTML = `<div class="yt-embed-block" contenteditable="false">
        <iframe
            src="${embedSrc}"
            title="YouTube video player"
            loading="lazy"
            referrerpolicy="strict-origin-when-cross-origin"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen></iframe>
    </div><p><br></p>`;
    document.execCommand('insertHTML', false, embedHTML);
}

function extractYouTubeId(url) {
    const patterns = [
        /(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})/,
        /(?:youtu\.be\/)([a-zA-Z0-9_-]{11})/,
        /(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
        /(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})/,
    ];
    for (const p of patterns) {
        const m = url.match(p);
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

function getCurrentEditorPlainText() {
    const editor = document.getElementById('note-content-rich');
    return editor ? (editor.innerText || '').trim() : '';
}

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

window.openStudyJarvis = function() {
    openJarvisPanel('deep_search');
    const prompt = document.getElementById('jarvis-prompt');
    if (prompt) prompt.value = 'Monte meu proximo passo de estudo com base nas minhas notas, materias e flashcards pendentes.';
};

window.openSubjectJarvis = function() {
    const { notebooks } = getStudyCollections();
    const nb = notebooks.find(n => String(n.id) === String(currentNotebookId));
    openJarvisPanel('deep_search');
    const prompt = document.getElementById('jarvis-prompt');
    if (prompt) prompt.value = `Me ajude a estudar ${nb ? nb.name : 'esta materia'}: explique os pontos principais e sugira revisao.`;
};

window.openNoteJarvisAction = function(mode) {
    openJarvisPanel(mode || 'summarize_text');
    const text = getCurrentEditorPlainText();
    const prompt = document.getElementById('jarvis-prompt');
    if (prompt && text) prompt.value = text.slice(0, 6000);
};

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
        } catch(fetchErr) {
            result = 'Jarvis indisponível. Verifique Wi-Fi e se o Nexus desktop está ligado.';
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

// Add alarm checker to main loop
setInterval(checkHabitAlarms, 30000); // checks every 30 seconds

// Fix modals position:fixed inside transformed parents by moving them to body
document.addEventListener('DOMContentLoaded', () => {
    const modals = document.querySelectorAll('.bottom-sheet, .mobile-form-sheet');
    modals.forEach(m => {
        document.body.appendChild(m);
        m.classList.remove('bottom-sheet', 'mobile-form-sheet');
        m.classList.add('modal-overlay');
        const content = m.querySelector('.bottom-sheet-content');
        if (content) {
            content.classList.remove('bottom-sheet-content');
            content.classList.add('modal-content');
        }
        const handle = m.querySelector('.bottom-sheet-handle');
        if (handle) handle.remove();
    });
});
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

function createBasicFlashcardsFromText(text, noteId, notebookId) {
    const clean = (text || '').replace(/\s+/g, ' ').trim();
    if (!clean) return [];
    const sentences = clean.split(/(?<=[.!?])\s+/).filter(s => s.length > 24).slice(0, 5);
    const cards = sentences.map((sentence, index) => ({
        front: `Explique: ${sentence.slice(0, 90)}${sentence.length > 90 ? '...' : ''}`,
        back: sentence,
        noteId,
        notebookId,
        index
    }));
    cards.forEach(card => {
        createFlashcard(card.front, card.back, noteId || null);
        const allCards = LocalDB.getAll ? LocalDB.getAll('flashcards') : (LocalDB.get('flashcards') || []);
        const saved = allCards[allCards.length - 1];
        if (saved && notebookId) {
            saved.notebook_id = notebookId;
            LocalDB.upsert('flashcards', saved);
        }
    });
    return cards;
}

window.generateFlashcardsFromCurrentNote = async function() {
    const text = getCurrentEditorPlainText();
    if (!text) {
        showInAppNotification('Escreva a nota antes de gerar cards.', 'warn');
        return;
    }
    const ok = window.showConfirm ? await window.showConfirm('Gerar flashcards locais a partir desta nota?') : confirm('Gerar flashcards locais a partir desta nota?');
    if (!ok) return;
    const notebookId = document.getElementById('note-notebook')?.value || currentNotebookId || '';
    const cards = createBasicFlashcardsFromText(text, editingNoteId || null, notebookId);
    if (!cards.length) {
        showInAppNotification('Texto curto demais para gerar cards.', 'warn');
        return;
    }
    showInAppNotification(`${cards.length} cards criados para revisao.`, 'success');
    loadStudies();
};

window.generateFlashcardsFromSubject = async function() {
    if (!currentNotebookId) return;
    const notes = (LocalDB.get('study_notes') || []).filter(n => !n.is_deleted && String(n.notebook_id) === String(currentNotebookId));
    const text = notes.map(n => `${n.title || ''}. ${(n.content || '').replace(/<[^>]+>/g, ' ')}`).join(' ');
    if (!text.trim()) {
        showInAppNotification('Esta materia ainda nao tem conteudo para gerar cards.', 'warn');
        return;
    }
    const ok = window.showConfirm ? await window.showConfirm('Gerar flashcards locais desta materia?') : confirm('Gerar flashcards locais desta materia?');
    if (!ok) return;
    const cards = createBasicFlashcardsFromText(text, null, currentNotebookId);
    showInAppNotification(`${cards.length} cards criados para a materia.`, 'success');
    renderSubjectStudySummary(currentNotebookId);
    loadStudies();
};

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

window.showFlashcards = function(cardsOverride) {
    initFlashcardsDB();
    _flashcardQueue = Array.isArray(cardsOverride) ? cardsOverride : getDueFlashcards();

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

window.reviewSubjectFlashcards = function() {
    if (!currentNotebookId) return;
    const due = getDueFlashcardsForNotebook(currentNotebookId);
    if (!due.length) {
        showInAppNotification('Nenhum card pendente nesta materia hoje.', 'info');
        return;
    }
    showFlashcards(due);
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
    
    // Fullscreen Immersive Mode: hide header and bottom nav
    const header = document.querySelector('.app-header');
    const bottomNav = document.querySelector('.bottom-nav');
    if (header) header.style.display = 'none';
    if (bottomNav) bottomNav.style.display = 'none';

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
    const notes = LocalDB.get('study_notes') || [];
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
    
    const transactions = (LocalDB.get('finance_transactions') || []).filter(t => !t.is_deleted);
    // Helper: extract YYYY-MM-DD from whatever date field is present
    const txDate = (t) => (t.occurred_at || t.created_at || '').split('T')[0];
    
    // 1. PIE CHART: Expenses by Category (Current Month)
    const now = new Date();
    const currMonth = now.toISOString().slice(0, 7); // YYYY-MM
    
    const expensesThisMonth = transactions.filter(t => t.type === 'expense' && txDate(t).startsWith(currMonth));
    const catTotals = {};
    expensesThisMonth.forEach(t => {
        const cat = t.category || 'Outros';
        catTotals[cat] = (catTotals[cat] || 0) + Number(t.amount || 0);
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
        return transactions.filter(t => t.type === 'income' && txDate(t).startsWith(m)).reduce((s,t) => s + Number(t.amount || 0), 0);
    });
    const expenseData = months.map(m => {
        return transactions.filter(t => t.type === 'expense' && txDate(t).startsWith(m)).reduce((s,t) => s + Number(t.amount || 0), 0);
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
    
    const habits = (LocalDB.get('habits') || []).filter(h => h.active === 1 && !h.is_deleted);
    const logs = LocalDB.get('habit_logs') || [];
    const days = 14;
    const labels = [];
    const percentages = [];
    
    for (let i = days - 1; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        const iso = d.toISOString().split('T')[0];
        labels.push(d.getDate() + '/' + (d.getMonth()+1));
        
        if (!habits.length) { percentages.push(0); continue; }
        const done = habits.filter(h => logs.some(l => String(l.habit_id) === String(h.id) && l.date === iso && !l.is_deleted)).length;
        percentages.push(Math.round((done / habits.length) * 100));
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
    const useExternalBrowser = !!(window.NexusAndroid && typeof window.NexusAndroid.openOAuthUrl === 'function');
    const { data, error } = await window.nexusSupabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
            redirectTo,
            skipBrowserRedirect: useExternalBrowser
        }
    });
    if (error) {
        showToast("Erro no login: " + error.message);
        return;
    }
    if (useExternalBrowser && data?.url) {
        window.NexusAndroid.openOAuthUrl(data.url);
        showToast("Complete o login no navegador...");
    }
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
    // Nav listener: hide AI FAB if not home
    const navLinks = document.querySelectorAll('.nav-link');
    const aiFab = document.getElementById('nexus-ai-fab');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            const target = link.getAttribute('onclick');
            if (aiFab) {
                if (target && target.includes('view-home')) aiFab.style.display = 'flex';
                else aiFab.style.display = 'none';
            }
        });
    });

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
        const habits = LocalDB.getAll('habits');
        const h = habits.find(x => String(x.id) === String(habitId));
        const xpReward = h ? (h.xp_reward || 10) : 10;

        const idx = logs.findIndex(l => String(l.habit_id) === String(habitId) && l.date === targetDate && !l.is_deleted);
        if (idx !== -1) {
            logs.splice(idx, 1);
            LocalDB.set('habit_logs', logs);
            if (typeof deductXP === 'function') deductXP(xpReward, 'Habito desmarcado');
        } else {
            const entry = { id: Date.now(), habit_id: habitId, date: targetDate, completed_date: targetDate };
            LocalDB.upsert('habit_logs', entry);
            if (typeof awardXP === 'function') awardXP(xpReward, 'Habito concluido');
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
        
        const logs = LocalDB.get('habit_logs') || [];
        const today = new Date().toISOString().split('T')[0];
        
        let habits = (LocalDB.get('habits') || []).filter(h => h.active === 1 && !h.is_deleted);
        
        // Enrich with done status and streak
        let enriched = habits.map(h => {
            const isDone = logs.some(l => String(l.habit_id) === String(h.id) && l.date === today && !l.is_deleted);
            let streak = 0;
            const now = new Date();
            for (let i = 0; i < 60; i++) {
                const d = new Date(now); d.setDate(d.getDate() - i);
                const ds = d.toISOString().split('T')[0];
                if (logs.some(l => String(l.habit_id) === String(h.id) && l.date === ds && !l.is_deleted)) streak++;
                else if (i > 0) break;
            }
            return { ...h, isDone, streak };
        });
        
        // Apply filter
        if (filter === 'done') {
            enriched = enriched.filter(h => h.isDone);
        } else if (filter === 'all') {
            enriched = enriched.filter(h => !h.isDone); // only pending in "all"
        } else if (filter === 'morning') {
            enriched = enriched.filter(h => h.period === 'morning' && !h.isDone);
        } else if (filter === 'afternoon') {
            enriched = enriched.filter(h => h.period === 'afternoon' && !h.isDone);
        } else if (filter === 'night') {
            enriched = enriched.filter(h => h.period === 'night' && !h.isDone);
        }
        
        if (!enriched.length) {
            container.innerHTML = `<div style="text-align:center;color:var(--text-secondary);margin-top:30px;padding:20px">
                <i class="fa-solid ${filter === 'done' ? 'fa-check-double' : 'fa-list-check'}" style="font-size:2rem;opacity:0.4;margin-bottom:10px;display:block"></i>
                ${filter === 'done' ? 'Nenhum hábito concluído hoje!' : 'Nenhum hábito nesta categoria.'}
            </div>`;
            return;
        }
        
        container.innerHTML = enriched.map(h => {
            const bgStyle = h.isDone ? 'background:rgba(255,255,255,0.03); opacity:0.65;' : '';
            const titleStyle = h.isDone ? 'text-decoration:line-through; color:var(--text-secondary);' : '';
            const completeBtnStyle = h.isDone 
                ? 'background:rgba(0,200,100,0.2);color:var(--accent-green);border:1px solid var(--accent-green)'
                : 'background:var(--accent-primary);color:white;border:none';
            const periodLabel = h.period === 'morning' ? '☀ Manhã' : h.period === 'afternoon' ? '⛅ Tarde' : h.period === 'night' ? '🌙 Noite' : 'Qualquer horário';
            
            return `
            <div class="list-item glass" data-id="${h.id}" style="cursor:pointer; transition:all 0.3s ease; ${bgStyle}" onclick="openHabitDetail('${h.id}')">
                <div class="item-main" style="flex:1;min-width:0">
                    <div class="item-title" style="${titleStyle};white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(h.name)}</div>
                    <div class="item-subtitle">${periodLabel}${h.streak > 0 ? ` &nbsp;🔥 ${h.streak} dias` : ''}</div>
                </div>
                <div style="display:flex;align-items:center;gap:6px;flex-shrink:0">
                    <button class="icon-btn" style="background:rgba(255,71,87,0.15);color:var(--accent-pink);width:34px;height:34px;font-size:0.8rem;border:none;border-radius:50%;cursor:pointer" 
                        onclick="event.stopPropagation(); deleteHabitDirect('${h.id}')">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                    <button class="icon-btn" style="${completeBtnStyle};width:34px;height:34px;font-size:0.85rem;border-radius:50%;cursor:pointer;transition:all 0.2s" 
                        onclick="event.stopPropagation(); toggleHabitDirect('${h.id}'); setTimeout(() => filterHabits(document.querySelector('#view-habits .study-chip.active')?.dataset?.filter || 'all'), 200)">
                        <i class="fa-solid ${h.isDone ? 'fa-rotate-left' : 'fa-check'}"></i>
                    </button>
                </div>
            </div>`;
        }).join('');

        // Activate drag & drop reordering
        makeSortable(container, 'habits', 'id');
    };

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
        const defaultDate = (typeof getSelectedDate === 'function' ? getSelectedDate() : new Date().toISOString().split('T')[0]);
        LocalDB.upsert('tasks', { id: Date.now(), name: 'Nova tarefa', title: 'Nova tarefa', priority: 'medium', status: 'todo', created_at: new Date().toISOString(), due_date: defaultDate });
        const tasks = LocalDB.get('tasks');
        const t = tasks[tasks.length - 1];
        openTaskDetail(t.id);
    };

    window.completeCurrentTask = function() {
        if (!currentTaskId) return;
        toggleTaskDirect(currentTaskId);
        closeTaskDetail();
    };

    window.deleteTaskInline = function(taskId, event) {
        if (event) event.stopPropagation();
        if (confirm('Deletar esta tarefa?')) {
            const tasks = LocalDB.get('tasks') || [];
            const idx = tasks.findIndex(t => String(t.id) === String(taskId));
            if (idx > -1) {
                tasks[idx].is_deleted = 1;
                tasks[idx].updated_at = new Date().toISOString();
                LocalDB.set('tasks', tasks);
                if (typeof loadTasks === 'function') loadTasks();
                if (typeof filterTasks === 'function') filterTasks('all');
            }
        }
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

    window.toggleSubtaskInline = function(taskId, subtaskIdx) {
        const tasks = LocalDB.get('tasks');
        const t = tasks.find(x => String(x.id) === String(taskId));
        if (!t) return;
        const subs = Array.isArray(t.subtasks) ? t.subtasks : (Array.isArray(t.subtasks_json) ? t.subtasks_json : []);
        if (!subs[subtaskIdx]) return;
        
        subs[subtaskIdx].done = !subs[subtaskIdx].done;
        t.subtasks = subs;
        t.subtasks_json = subs;
        
        const allDone = subs.length > 0 && subs.every(s => s.done);
        if (allDone && !t.done_at) {
            t.done_at = new Date().toISOString();
            t.status = 'done';
            if (typeof showToast === 'function') showToast('Tarefa concluída automaticamente!');
        } else if (!allDone && t.done_at) {
            t.done_at = null;
            t.status = 'todo';
        }
        
        LocalDB.upsert('tasks', t);
        if (taskKanbanMode) renderTaskKanban();
        else filterTasks(document.querySelector('#view-tasks .study-chip.active')?.dataset?.filter || 'today');
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
        const today = new Date().toISOString().split('T')[0];
        
        if (filter === 'done') {
            tasks = tasks.filter(t => t.done_at);
        } else if (filter === 'today') {
            // Show pending tasks due today or earlier, OR tasks completed today
            tasks = tasks.filter(t => {
                if (t.done_at) {
                    return t.done_at.startsWith(today); // Completed today
                }
                return t.due_date <= today || !t.due_date; // Pending and due today/earlier/no date
            });
        } else if (filter === 'high') {
            tasks = tasks.filter(t => !t.done_at && t.priority === 'high');
        } else if (filter === 'all') {
            // All pending tasks, plus completed tasks if they were completed today
            tasks = tasks.filter(t => {
                if (t.done_at) return t.done_at.startsWith(today);
                return true;
            });
        }
        
        // If calendar date is explicitly selected (and it's not today), filter tightly to that date
        if (NexusCalendar.activeModule === 'tasks' && sel !== today) {
            tasks = (LocalDB.get('tasks') || []).filter(t => !t.is_deleted);
            tasks = tasks.filter(t => t.due_date === sel);
        }
        
        // Sort: Pending first, then completed
        tasks.sort((a, b) => {
            const aDone = !!a.done_at;
            const bDone = !!b.done_at;
            if (aDone === bDone) return 0;
            return aDone ? 1 : -1;
        });
        if (!tasks.length) {
            container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;">Nenhuma tarefa.</div>';
            return;
        }
        container.innerHTML = tasks.map(t => {
            const isDone = !!t.done_at;
            let subtasksHtml = '';
            const subs = Array.isArray(t.subtasks) ? t.subtasks : (Array.isArray(t.subtasks_json) ? t.subtasks_json : []);
            if (subs.length > 0) {
                subtasksHtml = `<div style="margin-top:8px; display:flex; flex-direction:column; gap:6px; padding-left:4px; border-left: 2px solid rgba(255,255,255,0.1); margin-left: 4px;">` +
                    subs.map((s, i) => `
                        <div style="display:flex; align-items:center; gap:8px;" onclick="event.stopPropagation(); window.toggleSubtaskInline('${t.id}', ${i})">
                            <div class="custom-checkbox ${s.done ? 'checked' : ''}" style="width:16px;height:16px;min-width:16px;border:1px solid ${s.done ? 'var(--accent-green)' : 'var(--border-light)'};border-radius:4px;display:flex;align-items:center;justify-content:center;cursor:pointer;background:${s.done ? 'var(--accent-green)' : 'transparent'}">
                                ${s.done ? '<i class="fa-solid fa-check" style="font-size:10px;color:black"></i>' : ''}
                            </div>
                            <span style="font-size:0.8rem; color:${s.done ? 'var(--text-secondary)' : 'white'}; text-decoration:${s.done ? 'line-through' : 'none'}">${escapeHtml(s.name)}</span>
                        </div>
                    `).join('') + `</div>`;
            }

            return `<div class="list-item glass" data-id="${t.id}" onclick="openTaskDetail('${t.id}')" style="display:flex; flex-direction:column; padding-right:8px; padding-top:12px; padding-bottom:12px; transition:all 0.3s ease; opacity:${isDone ? 0.6 : 1};">
                <div style="display:flex; align-items:center; width:100%">
                    <div class="item-main" style="flex:1"><div class="item-title" style="text-decoration:${isDone?'line-through':'none'};color:${isDone?'var(--text-secondary)':'white'}">${escapeHtml(t.name || t.title)}</div></div>
                    <div style="display:flex;gap:4px">
                        <button class="icon-btn" onclick="event.stopPropagation();deleteTaskDirect(event, '${t.id}')" style="width:36px;height:36px;background:rgba(255,0,0,0.1);border-radius:50%;color:var(--accent-pink)"><i class="fa-solid fa-trash"></i></button>
                        <button class="icon-btn" onclick="event.stopPropagation();toggleTaskDirect('${t.id}')" style="width:36px;height:36px;border-radius:50%;${isDone?'background:var(--accent-green);color:white':'background:rgba(0,0,0,0.2);color:var(--text-secondary)'}"><i class="fa-solid ${isDone ? 'fa-rotate-left' : 'fa-check'}"></i></button>
                    </div>
                </div>
                ${subtasksHtml}
            </div>`;
        }).join('');

        // Activate drag & drop reordering
        makeSortable(container, 'tasks', 'id');
    };

    window.completeCurrentHabit = function() {
        if (!currentHabitId) return;
        toggleHabitDirect(currentHabitId, getSelectedDate());
        closeHabitDetail();
    };

    // --- Native reminders ---
    function scheduleNativeReminder(id, title, body, triggerAtMs) {
        if (window.AndroidNative && typeof AndroidNative.scheduleReminder === 'function') {
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
                if (ms > Date.now()) scheduleNativeReminder(rid, t.name || 'Tarefa', t.description || 'Lembrete de tarefa', ms);
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
            scheduleNativeReminder(rid, 'Hora do Habito', h.name, trigger.getTime());
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
        const now = new Date();
        const timeStr = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
        const td = todayISO();
        const logs = LocalDB.get('habit_logs') || [];
        (LocalDB.get('habits') || []).filter(h => h.active === 1 && !h.is_deleted).forEach(habit => {
            const t = habit.alarm_time || habit.target_time;
            if (!t || t.substring(0, 5) !== timeStr) return;
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

    // --- Workout form (Live Tracker) ---
    let editingWorkoutId = null;
    let workoutTimerInterval = null;
    let workoutSeconds = 0;
    let workoutIsRunning = false;
    let workoutIsResting = false;
    let workoutSeries = 0;

    function formatWorkoutTime(sec) {
        const m = Math.floor(sec / 60).toString().padStart(2, '0');
        const s = (sec % 60).toString().padStart(2, '0');
        return `${m}:${s}`;
    }

    function updateWorkoutDisplay() {
        const disp = document.getElementById('workout-stopwatch-display');
        if (disp) disp.textContent = formatWorkoutTime(workoutSeconds);
    }

    window.openWorkoutForm = function(workoutId) {
        editingWorkoutId = workoutId || null;
        workoutSeconds = 0;
        workoutIsRunning = false;
        workoutIsResting = false;
        workoutSeries = 0;
        clearInterval(workoutTimerInterval);
        
        const workouts = LocalDB.get('fitness_workouts') || [];
        const w = workoutId ? workouts.find(x => String(x.id) === String(workoutId)) : null;
        
        document.getElementById('workout-form-title').textContent = w ? 'Editar Treino' : 'Treino Livre';
        document.getElementById('workout-current-ex').value = w ? (w.muscle_group || '') : '';
        document.getElementById('workout-form-notes').value = w ? (w.notes || '') : '';
        document.getElementById('workout-series-count').textContent = w ? (w.duration_minutes || 0) : '0';
        workoutSeries = w ? parseInt(w.duration_minutes || 0) : 0;
        
        if (w && w.calories) {
            workoutSeconds = w.calories; // hack: use calories field for saved seconds
        }
        updateWorkoutDisplay();
        document.getElementById('workout-stopwatch-status').textContent = 'PREPARANDO';
        document.getElementById('workout-stopwatch-status').style.color = 'var(--text-secondary)';
        
        const startBtn = document.getElementById('btn-workout-start');
        if (startBtn) startBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
        
        document.getElementById('workout-form-delete-btn').style.display = w ? 'block' : 'none';
        document.getElementById('workout-form-modal').style.display = 'flex';
    };

    window.closeWorkoutForm = function() {
        clearInterval(workoutTimerInterval);
        document.getElementById('workout-form-modal').style.display = 'none';
    };

    window.openWorkoutBuilder = function() { openWorkoutForm(); };

    window.toggleWorkoutTimer = function() {
        if (workoutIsRunning && !workoutIsResting) {
            // Pause
            workoutIsRunning = false;
            clearInterval(workoutTimerInterval);
            document.getElementById('btn-workout-start').innerHTML = '<i class="fa-solid fa-play"></i>';
            document.getElementById('workout-stopwatch-status').textContent = 'PAUSADO';
            document.getElementById('workout-stopwatch-status').style.color = 'var(--accent-orange)';
        } else {
            // Start
            workoutIsRunning = true;
            workoutIsResting = false;
            clearInterval(workoutTimerInterval);
            workoutTimerInterval = setInterval(() => {
                workoutSeconds++;
                updateWorkoutDisplay();
            }, 1000);
            document.getElementById('btn-workout-start').innerHTML = '<i class="fa-solid fa-pause"></i>';
            document.getElementById('workout-stopwatch-status').textContent = 'EM EXECUÇÃO';
            document.getElementById('workout-stopwatch-status').style.color = 'var(--accent-green)';
        }
    };

    window.restWorkoutTimer = function() {
        workoutIsRunning = true;
        workoutIsResting = true;
        clearInterval(workoutTimerInterval);
        workoutTimerInterval = setInterval(() => {
            workoutSeconds++;
            updateWorkoutDisplay();
        }, 1000);
        document.getElementById('btn-workout-start').innerHTML = '<i class="fa-solid fa-play"></i>';
        document.getElementById('workout-stopwatch-status').textContent = 'DESCANSANDO';
        document.getElementById('workout-stopwatch-status').style.color = 'var(--accent-blue)';
    };

    window.resetWorkoutTimer = function() {
        if (confirm('Zerar o cronômetro?')) {
            workoutSeconds = 0;
            updateWorkoutDisplay();
        }
    };

    window.addWorkoutSet = function() {
        workoutSeries++;
        document.getElementById('workout-series-count').textContent = workoutSeries;
    };

    window.saveWorkoutForm = function() {
        clearInterval(workoutTimerInterval);
        const name = "Treino Livre";
        const currentEx = document.getElementById('workout-current-ex')?.value || '';
        const notes = document.getElementById('workout-form-notes')?.value || '';
        
        const payload = {
            name: currentEx ? `Treino: ${currentEx}` : name,
            muscle_group: currentEx,
            date: todayISO(),
            duration_minutes: workoutSeries, // Save sets in duration_minutes
            calories: workoutSeconds, // Save seconds in calories
            notes: notes
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
        updateFitnessStats();
        const data = (LocalDB.get('fitness_workouts') || []).filter(t => !t.is_deleted)
            .sort((a, b) => (b.date || b.created_at || '').localeCompare(a.date || a.created_at || ''));
        if (!data.length) {
            container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;">Nenhum treino.</div>';
            return;
        }
        container.innerHTML = data.slice(0, 15).map(t => {
            const timeStr = t.calories ? formatWorkoutTime(t.calories) : '00:00';
            const seriesStr = t.duration_minutes || 0;
            return `
            <div class="list-item glass" style="transition:all 0.2s ease">
                <div class="item-main" style="flex:1;min-width:0;cursor:pointer" onclick="openWorkoutForm(${t.id})">
                    <span class="item-title" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(t.name || 'Treino Livre')}</span>
                    <span class="item-subtitle"><i class="fa-solid fa-stopwatch"></i> ${timeStr} · <i class="fa-solid fa-layer-group"></i> ${seriesStr} séries</span>
                </div>
                <button class="icon-btn" style="background:rgba(255,71,87,0.15);color:var(--accent-pink);width:34px;height:34px;font-size:0.8rem;border:none;border-radius:50%;cursor:pointer;flex-shrink:0"
                    onclick="event.stopPropagation(); deleteFitnessWorkout('${t.id}')">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>`;
        }).join('');
    };

    // --- Studies: subjects grid ---
    function loadSubjectsGrid() {
        const grid = document.getElementById('subjects-grid');
        if (!grid) return;
        const notebooks = LocalDB.get('study_notebooks') || [];
        const notes = (LocalDB.get('study_notes') || []).filter(n => !n.is_deleted);
        if (!notebooks.length) {
            grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text-secondary);padding:20px">Sem materias. Crie a primeira!</div>';
            return;
        }
        grid.innerHTML = notebooks.map(nb => {
            const subjectNotes = notes.filter(n => String(n.notebook_id) === String(nb.id));
            const dueCount = getDueFlashcardsForNotebook(nb.id).length;
            const latest = [...subjectNotes].sort((a, b) => (b.updated_at || b.created_at || '').localeCompare(a.updated_at || a.created_at || ''))[0];
            const coverStyle = nb.cover_image ? `background-image:url('${nb.cover_image}')` : 'background:linear-gradient(135deg,#6c5ce7,#a29bfe)';
            return `<div class="subject-card" onclick="openSubjectDetail('${nb.id}')">
                <div class="subject-card-cover" style="${coverStyle}"></div>
                <div class="subject-card-body"><div class="subject-card-name">${nb.icon || ''} ${escapeHtml(nb.name)}</div>
                <div class="subject-card-count">${subjectNotes.length} nota${subjectNotes.length !== 1 ? 's' : ''} · ${dueCount} card${dueCount !== 1 ? 's' : ''} hoje</div>
                <div class="subject-card-latest">${escapeHtml(latest ? latest.title || 'Sem titulo' : 'Sem notas ainda')}</div></div>
            </div>`;
        }).join('');
    }

    window.openSubjectForm = function() {
        document.getElementById('subject-form-modal').style.display = 'flex';
        document.getElementById('subject-form-name').value = '';
        document.getElementById('subject-form-icon').value = '📚';
        document.getElementById('subject-form-cover').value = '';
    };

    window.saveSubjectForm = function() {
        const name = document.getElementById('subject-form-name')?.value?.trim();
        if (!name) return;
        const nb = {
            id: Date.now().toString(),
            name,
            icon: document.getElementById('subject-form-icon')?.value || '📚',
            cover_image: document.getElementById('subject-form-cover')?.value || null,
            created_at: new Date().toISOString()
        };
        const notebooks = LocalDB.get('study_notebooks') || [];
        notebooks.push(nb);
        LocalDB.set('study_notebooks', notebooks);
        document.getElementById('subject-form-modal').style.display = 'none';
        loadStudies();
    };

    window.openNewNotebook = window.openSubjectForm;

    window.openSubjectDetail = function(notebookId) {
        currentNotebookId = notebookId;
        const nb = (LocalDB.get('study_notebooks') || []).find(n => String(n.id) === String(notebookId));
        const view = document.getElementById('subject-detail-view');
        if (!view || !nb) return;
        document.getElementById('subject-detail-title').textContent = (nb.icon || '') + ' ' + nb.name;
        view.style.display = 'block';
        renderSubjectStudySummary(notebookId);
        const notes = (LocalDB.get('study_notes') || []).filter(n => !n.is_deleted && String(n.notebook_id) === String(notebookId));
        const list = document.getElementById('subject-notes-list');
        list.innerHTML = notes.length ? notes.map(n => renderNoteCard(n)).join('') : '<div style="text-align:center;padding:30px;color:var(--text-secondary)">Sem notas</div>';

        // Fullscreen Immersive Mode
        const header = document.querySelector('.app-header');
        const bottomNav = document.querySelector('.bottom-nav');
        if (header) header.style.display = 'none';
        if (bottomNav) bottomNav.style.display = 'none';
    };

    window.closeSubjectDetail = function() {
        document.getElementById('subject-detail-view').style.display = 'none';
        currentNotebookId = null;

        // Restore header and bottom nav
        const header = document.querySelector('.app-header');
        const bottomNav = document.querySelector('.bottom-nav');
        if (header) header.style.display = 'flex';
        if (bottomNav) bottomNav.style.display = 'flex';
    };

    window.openSubjectMenu = function(ev) {
        ev.stopPropagation();
        const popup = document.getElementById('subject-menu-popup');
        if (popup) {
            popup.style.display = 'block';
            popup.style.top = (ev.clientY + 10) + 'px';
            popup.style.left = (ev.clientX - 120) + 'px';
        }
        setTimeout(() => document.addEventListener('click', closeSubjectMenu, { once: true }), 50);
    };

    function closeSubjectMenu() {
        const popup = document.getElementById('subject-menu-popup');
        if (popup) popup.style.display = 'none';
    }

    window.changeSubjectCover = function() {
        const url = prompt('URL da imagem de capa:');
        if (!url || !currentNotebookId) return;
        const notebooks = LocalDB.get('study_notebooks') || [];
        const idx = notebooks.findIndex(n => String(n.id) === String(currentNotebookId));
        if (idx !== -1) { notebooks[idx].cover_image = url; LocalDB.set('study_notebooks', notebooks); loadStudies(); openSubjectDetail(currentNotebookId); }
        closeSubjectMenu();
    };

    window.renameSubject = function() {
        const name = prompt('Novo nome:');
        if (!name || !currentNotebookId) return;
        const notebooks = LocalDB.get('study_notebooks') || [];
        const idx = notebooks.findIndex(n => String(n.id) === String(currentNotebookId));
        if (idx !== -1) { notebooks[idx].name = name.trim(); LocalDB.set('study_notebooks', notebooks); loadStudies(); openSubjectDetail(currentNotebookId); }
        closeSubjectMenu();
    };

    window.deleteSubject = function() {
        if (!currentNotebookId || !confirm('Excluir materia e manter notas sem caderno?')) return;
        const notebooks = LocalDB.get('study_notebooks') || [];
        const idx = notebooks.findIndex(n => String(n.id) === String(currentNotebookId));
        if (idx !== -1) {
            notebooks[idx].is_deleted = true;
            notebooks[idx].updated_at = new Date().toISOString();
            LocalDB.set('study_notebooks', notebooks);
        }
        closeSubjectDetail();
        loadStudies();
        closeSubjectMenu();
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
        const subject = document.getElementById('note-subject')?.value || '';
        const notebookId = document.getElementById('note-notebook')?.value || currentNotebookId || '';
        if (!title && !content) { showInAppNotification('Escreva algo primeiro!', 'warn'); return; }
        const notes = LocalDB.get('study_notes') || [];
        const now = new Date().toISOString();
        if (editingNoteId) {
            const idx = notes.findIndex(n => String(n.id) === String(editingNoteId));
            if (idx !== -1) notes[idx] = { ...notes[idx], title, content, tags, subject, notebook_id: notebookId, updated_at: now };
        } else {
            notes.push({ id: Date.now().toString(), title, content, tags, subject, notebook_id: notebookId, created_at: now, updated_at: now });
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
        const url = document.getElementById('yt-url-input')?.value?.trim();
        if (!url) return;
        const videoId = extractYouTubeId(url);
        if (!videoId) { alert('URL invalida'); return; }
        closeYouTubeModal();
        const editor = document.getElementById('note-content-rich');
        if (!editor) return;
        editor.focus();
        const embedSrc = getYouTubeEmbedSrc(videoId);
        const embedHTML = `<div class="yt-embed-block" contenteditable="false">
            <iframe
                src="${embedSrc}"
                title="YouTube video player"
                loading="lazy"
                referrerpolicy="strict-origin-when-cross-origin"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen></iframe>
        </div><p><br></p>`;
        document.execCommand('insertHTML', false, embedHTML);
        saveNoteDebounced();
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
        renderStudyCockpit();
        renderStudyRecentNotes();
        loadSubjectsGrid();
        if (typeof loadNotebooksGrid === 'function') loadNotebooksGrid();
        if (typeof ensureChartJs === 'function') ensureChartJs().then(() => setTimeout(renderStudyCharts, 100));
    };

    window.openFinanceOverflow = function(ev) {
        ev.stopPropagation();
        showToast('Mais acoes de financas em breve');
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
    scanPhoneStorage();
};

window.openCleanerView = function() {
    navigateTo('view-cleaner');
};

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        const stats = typeof getNativeStorageStatsSync === 'function' ? getNativeStorageStatsSync() : null;
        if (stats && stats.cacheBytes) updateStorageWarningBadge(stats.cacheBytes);
        else if (typeof getLocalStorageFootprint === 'function') updateStorageWarningBadge(getLocalStorageFootprint().total);
    }, 1500);
});

// ================================================================
// ALARMS SYSTEM
// ================================================================
let activeAudioAlarm = null;
let _currentAlarmRingingId = null;

window.loadAlarms = function() {
    const list = document.getElementById('alarms-list');
    if (!list) return;
    const alarms = LocalDB.get('alarms') || [];
    if (alarms.length === 0) {
        list.innerHTML = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;">Nenhum alarme configurado.</div>';
        return;
    }
    alarms.sort((a,b) => a.time.localeCompare(b.time));
    list.innerHTML = alarms.map(a => {
        const daysLabel = ['D','S','T','Q','Q','S','S'].map((d,i) => a.days.includes(i) ? `<span style="color:var(--accent-primary);font-weight:bold">${d}</span>` : `<span style="color:var(--text-secondary)">${d}</span>`).join(' ');
        return `<div class="list-item glass" onclick="openAlarmForm('${a.id}')" style="display:flex;align-items:center;padding:15px;cursor:pointer;">
            <div style="flex:1">
                <div style="font-size:2rem;font-weight:bold;color:${a.enabled?'white':'var(--text-secondary)'}">${a.time}</div>
                <div style="font-size:0.8rem;color:var(--text-secondary)">${escapeHtml(a.name || 'Alarme')} • <span style="font-size:0.75rem">${daysLabel}</span></div>
            </div>
            <label class="switch" onclick="event.stopPropagation()">
                <input type="checkbox" ${a.enabled ? 'checked' : ''} onchange="toggleAlarm('${a.id}', this.checked)">
                <span class="slider round"></span>
            </label>
        </div>`;
    }).join('');
};

window.openAlarmForm = function(id = null) {
    const modal = document.getElementById('alarm-form-modal');
    const timeEl = document.getElementById('alarm-time');
    const nameEl = document.getElementById('alarm-name');
    const btn = document.getElementById('alarm-delete-btn');
    document.querySelectorAll('.day-chip').forEach(b => b.classList.add('active')); // all days active by default
    
    if (id) {
        const a = (LocalDB.get('alarms')||[]).find(x => x.id === id);
        if (a) {
            timeEl.value = a.time;
            nameEl.value = a.name || '';
            document.querySelectorAll('.day-chip').forEach(b => {
                if (a.days.includes(parseInt(b.dataset.day))) b.classList.add('active');
                else b.classList.remove('active');
            });
            btn.style.display = 'block';
            btn.onclick = () => deleteAlarm(id);
            modal.dataset.editId = id;
        }
    } else {
        timeEl.value = '';
        nameEl.value = '';
        btn.style.display = 'none';
        modal.dataset.editId = '';
    }
    
    document.querySelectorAll('.day-chip').forEach(b => {
        b.onclick = () => b.classList.toggle('active');
    });
    
    if (modal) modal.style.display = 'flex';
};

window.closeAlarmForm = function() {
    const modal = document.getElementById('alarm-form-modal');
    if (modal) modal.style.display = 'none';
};

window.saveAlarm = function() {
    const time = document.getElementById('alarm-time').value;
    const name = document.getElementById('alarm-name').value.trim();
    const days = Array.from(document.querySelectorAll('.day-chip.active')).map(b => parseInt(b.dataset.day));
    if (!time) {
        if (typeof showToast === 'function') showToast('Defina a hora do alarme');
        return;
    }
    if (days.length === 0) {
        if (typeof showToast === 'function') showToast('Selecione pelo menos um dia');
        return;
    }
    
    const alarms = LocalDB.get('alarms') || [];
    const editId = document.getElementById('alarm-form-modal').dataset.editId;
    
    if (editId) {
        const a = alarms.find(x => x.id === editId);
        if (a) {
            a.time = time;
            a.name = name;
            a.days = days;
        }
    } else {
        alarms.push({ id: Date.now().toString(), time, name, days, enabled: true, last_triggered: null });
    }
    
    LocalDB.set('alarms', alarms);
    closeAlarmForm();
    loadAlarms();
    if (typeof showToast === 'function') showToast('Alarme salvo');
};

window.deleteAlarm = function(id) {
    if(!confirm('Excluir este alarme?')) return;
    const alarms = LocalDB.get('alarms') || [];
    const idx = alarms.findIndex(a => String(a.id) === String(id));
    if (idx !== -1) {
        alarms[idx].is_deleted = true;
        alarms[idx].updated_at = new Date().toISOString();
        LocalDB.set('alarms', alarms);
    }
    closeAlarmForm();
    loadAlarms();
};

window.toggleAlarm = function(id, state) {
    const alarms = LocalDB.get('alarms') || [];
    const a = alarms.find(x => x.id === id);
    if (a) {
        a.enabled = state;
        LocalDB.set('alarms', alarms);
        loadAlarms();
    }
};

window.checkGeneralAlarms = function() {
    const alarms = LocalDB.get('alarms') || [];
    const now = new Date();
    const currentDay = now.getDay();
    const currentHrs = String(now.getHours()).padStart(2, '0');
    const currentMins = String(now.getMinutes()).padStart(2, '0');
    const currentTime = `${currentHrs}:${currentMins}`;
    const todayISO = now.toISOString().split('T')[0];
    
    alarms.forEach(a => {
        if (a.enabled && a.days.includes(currentDay) && a.time === currentTime) {
            // Ensure we only ring once per minute per day
            if (a.last_triggered !== todayISO + 'T' + currentTime) {
                a.last_triggered = todayISO + 'T' + currentTime;
                LocalDB.upsert('alarms', a);
                triggerAlarmRinging(a);
            }
        }
    });
};

function triggerAlarmRinging(a) {
    _currentAlarmRingingId = a.id;
    const modal = document.getElementById('alarm-ring-modal');
    if (modal) {
        document.getElementById('alarm-ring-time').textContent = a.time;
        document.getElementById('alarm-ring-name').textContent = escapeHtml(a.name || 'Alarme');
        modal.style.display = 'flex';
        
        // Native android trigger
        if (window.AndroidNative && typeof window.AndroidNative.playAlarmSound === 'function') {
            window.AndroidNative.playAlarmSound();
        } else {
            // Web Audio API Fallback
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                activeAudioAlarm = setInterval(() => {
                    const osc = ctx.createOscillator();
                    osc.type = 'square';
                    osc.frequency.setValueAtTime(800, ctx.currentTime);
                    osc.frequency.exponentialRampToValueAtTime(1200, ctx.currentTime + 0.2);
                    osc.connect(ctx.destination);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.5);
                }, 1000);
            } catch(e) {}
        }
    }
}

window.stopAlarmRinging = function() {
    const modal = document.getElementById('alarm-ring-modal');
    if (modal) modal.style.display = 'none';
    if (activeAudioAlarm) {
        clearInterval(activeAudioAlarm);
        activeAudioAlarm = null;
    }
    if (window.AndroidNative && typeof window.AndroidNative.stopAlarmSound === 'function') {
        window.AndroidNative.stopAlarmSound();
    }
    _currentAlarmRingingId = null;
};

setInterval(window.checkGeneralAlarms, 10000);

// ================================================================
// FINANCE GOALS & BUDGET
// ================================================================

window.openFinanceGoalForm = function() {
    document.getElementById('fg-name').value = '';
    document.getElementById('fg-target').value = '';
    document.getElementById('fg-saved').value = '0';
    document.getElementById('finance-goal-modal').style.display = 'flex';
};
window.closeFinanceGoalForm = function() {
    document.getElementById('finance-goal-modal').style.display = 'none';
};
window.saveFinanceGoal = function() {
    const name = document.getElementById('fg-name').value.trim();
    const target = parseFloat(document.getElementById('fg-target').value) || 0;
    const saved = parseFloat(document.getElementById('fg-saved').value) || 0;
    if (!name || target <= 0) { showInAppNotification('Preencha o nome e o valor alvo', 'warn'); return; }
    const goals = LocalDB.get('finance_goals') || [];
    goals.push({ id: Date.now(), name, target, saved, created_at: new Date().toISOString() });
    LocalDB.set('finance_goals', goals);
    closeFinanceGoalForm();
    renderFinanceGoals();
    showInAppNotification('Meta criada!', 'success');
};

window.addToFinanceGoal = function(id, amount) {
    const goals = LocalDB.get('finance_goals') || [];
    const g = goals.find(x => String(x.id) === String(id));
    if (!g) return;
    g.saved = Math.min(g.target, (g.saved || 0) + amount);
    LocalDB.set('finance_goals', goals);
    renderFinanceGoals();
    if (g.saved >= g.target) showInAppNotification(`🎉 Meta "${g.name}" alcançada!`, 'success');
};

window.deleteFinanceGoal = function(id) {
    window.showConfirm('Excluir esta meta?', () => {
        const goals = LocalDB.get('finance_goals') || [];
        const idx = goals.findIndex(x => String(x.id) === String(id));
        if (idx !== -1) {
            goals[idx].is_deleted = true;
            goals[idx].updated_at = new Date().toISOString();
            LocalDB.set('finance_goals', goals);
        }
        renderFinanceGoals();
    });
};

function renderFinanceGoals() {
    const el = document.getElementById('finance-goals-list');
    if (!el) return;
    const goals = (LocalDB.get('finance_goals') || []);
    if (!goals.length) {
        el.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-secondary);font-size:0.85rem">Nenhuma meta ainda. Crie uma!</div>';
        return;
    }
    el.innerHTML = goals.map(g => {
        const pct = Math.min(100, Math.round((g.saved / g.target) * 100));
        const color = pct >= 100 ? 'var(--accent-green)' : pct > 50 ? 'var(--accent-blue)' : 'var(--accent-purple)';
        return `<div style="background:rgba(255,255,255,0.04);border-radius:14px;padding:14px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                <span style="font-weight:700;color:white">${g.name}</span>
                <button onclick="deleteFinanceGoal('${g.id}')" style="background:none;border:none;color:var(--accent-pink);cursor:pointer;font-size:0.85rem"><i class="fa-solid fa-trash"></i></button>
            </div>
            <div style="background:rgba(255,255,255,0.08);border-radius:8px;overflow:hidden;height:8px;margin-bottom:8px">
                <div style="height:100%;width:${pct}%;background:${color};border-radius:8px;transition:width 0.5s ease"></div>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-size:0.8rem;color:var(--text-secondary)">R$${g.saved.toFixed(2)} / R$${g.target.toFixed(2)}</span>
                <span style="font-size:0.8rem;font-weight:700;color:${color}">${pct}%</span>
            </div>
            <div style="display:flex;gap:6px;margin-top:10px">
                ${[50,100,200,500].map(v => `<button onclick="addToFinanceGoal('${g.id}',${v})" style="flex:1;padding:6px 0;border-radius:8px;border:1px solid var(--border-glass);background:rgba(255,255,255,0.05);color:white;cursor:pointer;font-size:0.75rem">+R$${v}</button>`).join('')}
            </div>
        </div>`;
    }).join('');
}

// Budget
window.openBudgetForm = function() {
    document.getElementById('bg-category').value = '';
    document.getElementById('bg-limit').value = '';
    document.getElementById('budget-form-modal').style.display = 'flex';
};
window.closeBudgetForm = function() {
    document.getElementById('budget-form-modal').style.display = 'none';
};
window.saveBudgetLimit = function() {
    const category = document.getElementById('bg-category').value.trim();
    const limit = parseFloat(document.getElementById('bg-limit').value) || 0;
    if (!category || limit <= 0) { showInAppNotification('Preencha a categoria e o limite', 'warn'); return; }
    const budgets = LocalDB.get('finance_budgets') || [];
    const existing = budgets.findIndex(b => b.category.toLowerCase() === category.toLowerCase());
    if (existing !== -1) budgets[existing].limit = limit;
    else budgets.push({ id: Date.now(), category, limit });
    LocalDB.set('finance_budgets', budgets);
    closeBudgetForm();
    renderFinanceBudgets();
    showInAppNotification('Limite salvo!', 'success');
};

window.deleteBudgetLimit = function(id) {
    window.showConfirm('Remover este limite?', () => {
        const budgets = LocalDB.get('finance_budgets') || [];
        const idx = budgets.findIndex(x => String(x.id) === String(id));
        if (idx !== -1) {
            budgets[idx].is_deleted = true;
            budgets[idx].updated_at = new Date().toISOString();
            LocalDB.set('finance_budgets', budgets);
        }
        renderFinanceBudgets();
    });
};

function renderFinanceBudgets() {
    const el = document.getElementById('finance-budgets-list');
    if (!el) return;
    const budgets = LocalDB.get('finance_budgets') || [];
    if (!budgets.length) {
        el.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-secondary);font-size:0.85rem">Nenhum limite definido.</div>';
        return;
    }
    const now = new Date();
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();
    const txs = (LocalDB.get('finance_transactions') || []).filter(t => !t.is_deleted && t.type === 'expense' && t.created_at >= monthStart);

    el.innerHTML = budgets.map(b => {
        const spent = txs.filter(t => (t.category || '').toLowerCase() === b.category.toLowerCase())
                        .reduce((s, t) => s + Number(t.amount), 0);
        const pct = Math.min(100, Math.round((spent / b.limit) * 100));
        const color = pct >= 90 ? 'var(--accent-pink)' : pct > 60 ? '#f97316' : 'var(--accent-green)';
        return `<div style="background:rgba(255,255,255,0.04);border-radius:14px;padding:14px">
            <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                <span style="font-weight:700;color:white">${b.category}</span>
                <button onclick="deleteBudgetLimit('${b.id}')" style="background:none;border:none;color:var(--accent-pink);cursor:pointer;font-size:0.85rem"><i class="fa-solid fa-trash"></i></button>
            </div>
            <div style="background:rgba(255,255,255,0.08);border-radius:8px;overflow:hidden;height:8px;margin-bottom:8px">
                <div style="height:100%;width:${pct}%;background:${color};border-radius:8px;transition:width 0.5s ease"></div>
            </div>
            <div style="display:flex;justify-content:space-between">
                <span style="font-size:0.8rem;color:var(--text-secondary)">R$${spent.toFixed(2)} / R$${b.limit.toFixed(2)}</span>
                <span style="font-size:0.8rem;font-weight:700;color:${color}">${pct}%${pct >= 90 ? ' ⚠️' : ''}</span>
            </div>
        </div>`;
    }).join('');
}

// Hook into finance load
const _origLoadFinances = window.loadFinances;
window.loadFinances = function() {
    if (typeof _origLoadFinances === 'function') _origLoadFinances();
    setTimeout(() => { renderFinanceGoals(); renderFinanceBudgets(); }, 100);
};

window.UnifiedJarvisClient = {
    socket: null,
    state: 'offline',
    deviceId: 'mobile:android',
    sessionId: '',
    url: '',
    heartbeatTimer: null,

    getConfig() {
        const host = (localStorage.getItem('unified_jarvis_host') || '').trim() || '127.0.0.1';
        const port = parseInt(localStorage.getItem('unified_jarvis_port') || '5124', 10) || 5124;
        const rawUrl = (localStorage.getItem('unified_jarvis_ws') || '').trim();
        const url = rawUrl || `ws://${host}:${port}/jarvis/ws`;
        return { host, port, url };
    },

    refreshUrl() {
        this.url = this.getConfig().url;
        return this.url;
    },

    setState(state) {
        this.state = state;
        const node = document.getElementById('unified-jarvis-status');
        if (!node) return;
        node.dataset.state = state;
        const label = node.querySelector('span') || node;
        label.textContent = state === 'online' ? 'Jarvis PC conectado' : 'Jarvis PC offline';
        const hint = document.getElementById('unified-jarvis-settings-hint');
        if (hint) {
            const cfg = this.getConfig();
            hint.textContent = state === 'online'
                ? `Conectado em ${cfg.host}:${cfg.port}.`
                : `Offline. Verifique se o bridge esta ativo em ${cfg.host}:${cfg.port}.`;
        }
    },

    loadNativeDeviceInfo() {
        if (!window.AndroidNative || typeof AndroidNative.getUnifiedDeviceInfo !== 'function') return null;
        try {
            const info = JSON.parse(AndroidNative.getUnifiedDeviceInfo());
            this.deviceId = info.device_id || this.deviceId;
            return info;
        } catch (_) {
            return null;
        }
    },

    connect(forceReconnect) {
        this.refreshUrl();
        if (forceReconnect && this.socket) {
            try { this.socket.close(); } catch (_) {}
            this.socket = null;
        }
        if (this.socket && this.socket.readyState === WebSocket.OPEN) return;
        const nativeDevice = this.loadNativeDeviceInfo();
        try {
            this.socket = new WebSocket(this.url);
        } catch (_) {
            this.setState('offline');
            return;
        }
        this.socket.onopen = () => {
            this.setState('online');
            this.sendEvent('device_register', '*', nativeDevice || {
                device_id: this.deviceId,
                kind: 'mobile',
                name: 'Android',
                capabilities: {
                    voice_input: true,
                    voice_output: true,
                    display: true,
                    camera: true,
                    local_actions: true
                }
            });
            this.startHeartbeat();
        };
        this.socket.onmessage = (message) => this.handleMessage(message.data);
        this.socket.onclose = () => {
            this.stopHeartbeat();
            this.setState('offline');
        };
        this.socket.onerror = () => {
            this.stopHeartbeat();
            this.setState('offline');
        };
    },

    startHeartbeat() {
        this.stopHeartbeat();
        this.sendHeartbeat();
        this.heartbeatTimer = setInterval(() => this.sendHeartbeat(), 25000);
    },

    stopHeartbeat() {
        if (!this.heartbeatTimer) return;
        clearInterval(this.heartbeatTimer);
        this.heartbeatTimer = null;
    },

    sendHeartbeat() {
        return this.sendEvent('device_heartbeat', '*', {
            device_id: this.deviceId
        });
    },

    sendEvent(type, targetDevice, payload) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return false;
        const id = window.crypto && crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
        const event = {
            event_id: id,
            session_id: this.sessionId || 'mobile-session',
            source_device: this.deviceId,
            target_device: targetDevice || '*',
            type,
            payload: payload || {},
            created_at: new Date().toISOString(),
            expires_at: new Date(Date.now() + 60000).toISOString()
        };
        this.socket.send(JSON.stringify(event));
        return true;
    },

    handleMessage(raw) {
        let event;
        try {
            event = JSON.parse(raw);
        } catch (_) {
            return;
        }
        if (event.type === 'session' && event.session) {
            this.sessionId = event.session.session_id || this.sessionId;
            return;
        }
        if (event.type === 'render_update') {
            renderUnifiedJarvisUpdate(event.payload || {});
        }
        if (event.type === 'assistant_delta' && event.payload && event.payload.text) {
            if (event.payload.render !== false) {
                renderUnifiedJarvisUpdate({
                    surface_id: 'assistant-live',
                    op: 'append',
                    block: { type: 'assistant_transcript', text: event.payload.text }
                });
            }
            speakUnifiedJarvisDelta(event.payload.text);
        }
    }
};

function speakUnifiedJarvisDelta(text) {
    if (!text || !jarvisCallActive || typeof speakJarvisResponse !== 'function') return;
    speakJarvisResponse(text);
}

window.loadUnifiedJarvisSettingsUI = function() {
    const cfg = window.UnifiedJarvisClient.getConfig();
    const hostInput = document.getElementById('unified-jarvis-host');
    const portInput = document.getElementById('unified-jarvis-port');
    if (hostInput) hostInput.value = cfg.host;
    if (portInput) portInput.value = String(cfg.port);
    window.UnifiedJarvisClient.refreshUrl();
};

window.saveUnifiedJarvisSettings = function() {
    const host = (document.getElementById('unified-jarvis-host')?.value || '').trim() || '127.0.0.1';
    const port = parseInt(document.getElementById('unified-jarvis-port')?.value || '5124', 10) || 5124;
    localStorage.setItem('unified_jarvis_host', host);
    localStorage.setItem('unified_jarvis_port', String(Math.max(1024, Math.min(65535, port))));
    localStorage.removeItem('unified_jarvis_ws');
    window.UnifiedJarvisClient.refreshUrl();
    showToast('Conexao do Jarvis PC salva.');
};

window.connectUnifiedJarvis = function(forceReconnect) {
    if (forceReconnect) window.saveUnifiedJarvisSettings();
    window.UnifiedJarvisClient.connect(!!forceReconnect);
};

window.sendUnifiedJarvisInterrupt = function(scope) {
    return window.UnifiedJarvisClient.sendEvent('interrupt', '*', {
        scope: scope || 'all',
        reason: 'user_tap'
    });
};

window.sendUnifiedJarvisUtterance = function(userText) {
    const text = (userText || '').trim();
    if (!text) return false;
    return window.UnifiedJarvisClient.sendEvent('user_utterance', 'desktop:local', {
        text,
        input_mode: jarvisCallActive ? 'voice' : 'text'
    });
};

window.startUnifiedJarvisAutoConnect = function() {
    if (window.UnifiedJarvisClient._autoConnectStarted) return;
    window.UnifiedJarvisClient._autoConnectStarted = true;
    const tick = () => {
        if (window.UnifiedJarvisClient.state !== 'online') {
            window.UnifiedJarvisClient.connect();
        }
    };
    setTimeout(tick, 1200);
    setInterval(tick, 12000);
};

function renderUnifiedJarvisUpdate(update) {
    const surface = document.getElementById('unified-renderer-surface');
    if (!surface) return;
    surface.hidden = false;
    if (update.op === 'clear') {
        surface.innerHTML = '';
        surface.hidden = true;
        return;
    }
    const block = update.block || {};
    if (block.type === 'assistant_transcript' || block.type === 'text') {
        const line = document.createElement('p');
        line.className = 'unified-renderer-transcript';
        line.textContent = block.text || '';
        surface.appendChild(line);
        surface.scrollTop = surface.scrollHeight;
    }
}

window.startUnifiedJarvisAutoConnect();

// ================================================================
// MOBILE UI PASS: Studies menu, compact tasks/habits, OCR, finance
// ================================================================

function nexusTodayISO() {
    return new Date().toISOString().split('T')[0];
}

function normalizeSubtasksList(value) {
    if (!Array.isArray(value)) return [];
    return value.map((s) => {
        if (typeof s === 'string') return { name: s, done: false };
        return { name: s.name || s.title || '', done: !!s.done };
    }).filter(s => s.name.trim());
}

function renderCardSubtasks(subtasks, onClick) {
    const subs = normalizeSubtasksList(subtasks);
    if (!subs.length) return '';
    return `<div class="card-subtasks">` + subs.slice(0, 5).map((s, i) => `
        <div class="card-subtask-row" onclick="event.stopPropagation();${onClick}(${i})">
            <span class="mini-check ${s.done ? 'checked' : ''}">${s.done ? '<i class="fa-solid fa-check"></i>' : ''}</span>
            <span style="${s.done ? 'text-decoration:line-through;color:var(--text-secondary)' : ''}">${escapeHtml(s.name)}</span>
        </div>
    `).join('') + `</div>`;
}

function openTextInputSheet(title, label, value, onSave) {
    let sheet = document.getElementById('text-input-sheet');
    if (!sheet) {
        sheet = document.createElement('div');
        sheet.id = 'text-input-sheet';
        sheet.className = 'bottom-sheet';
        sheet.innerHTML = `
            <div class="bottom-sheet-content glass">
                <div class="bottom-sheet-handle"></div>
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                    <h3 id="text-input-title" style="margin:0;font-size:1.05rem"></h3>
                    <button onclick="document.getElementById('text-input-sheet').style.display='none'" class="icon-btn"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <div class="form-field"><label id="text-input-label"></label><input id="text-input-value" type="text"></div>
                <button id="text-input-save" style="width:100%;background:var(--accent-primary);border:none;color:white;padding:13px;border-radius:12px;font-weight:800">Salvar</button>
            </div>`;
        document.body.appendChild(sheet);
    }
    document.getElementById('text-input-title').textContent = title || 'Editar';
    document.getElementById('text-input-label').textContent = label || 'Valor';
    const input = document.getElementById('text-input-value');
    input.value = value || '';
    document.getElementById('text-input-save').onclick = () => {
        const next = input.value.trim();
        sheet.style.display = 'none';
        if (next) onSave(next);
    };
    sheet.style.display = 'flex';
    setTimeout(() => input.focus(), 60);
}

window.openNoteMenu = function(ev, noteId) {
    if (ev) ev.stopPropagation();
    window._currentNoteMenuId = noteId;
    let sheet = document.getElementById('note-action-sheet');
    if (!sheet) {
        sheet = document.createElement('div');
        sheet.id = 'note-action-sheet';
        sheet.className = 'bottom-sheet';
        sheet.innerHTML = `
            <div class="bottom-sheet-content glass">
                <div class="bottom-sheet-handle"></div>
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                    <h3 style="margin:0;font-size:1.05rem">Nota</h3>
                    <button onclick="closeNoteActionSheet()" class="icon-btn"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <div class="sheet-action-grid">
                    <button onclick="openNoteConfigModal('rename')"><i class="fa-solid fa-pen"></i><span>Renomear</span></button>
                    <button onclick="openNoteConfigModal('cover')"><i class="fa-solid fa-image"></i><span>Capa e icone</span></button>
                    <button onclick="openNoteConfigModal('config')"><i class="fa-solid fa-sliders"></i><span>Materia e IA</span></button>
                    <button onclick="deleteNoteFromMenu()" style="color:var(--accent-pink)"><i class="fa-solid fa-trash" style="color:var(--accent-pink)"></i><span>Excluir</span></button>
                </div>
            </div>`;
        document.body.appendChild(sheet);
    }
    sheet.style.display = 'flex';
};

window.closeNoteActionSheet = function() {
    const sheet = document.getElementById('note-action-sheet');
    if (sheet) sheet.style.display = 'none';
};

window.closeNoteMenu = function() {
    window.closeNoteActionSheet();
    const popup = document.getElementById('note-menu-popup');
    if (popup) popup.style.display = 'none';
};

window.openNoteConfigModal = function(action) {
    const noteId = window._currentNoteMenuId;
    if (!noteId) return;
    const notes = LocalDB.get('study_notes') || [];
    const note = notes.find(n => String(n.id) === String(noteId));
    if (!note) return;
    closeNoteActionSheet();
    const sheet = document.getElementById('note-config-sheet');
    if (!sheet) return;
    const notebooks = LocalDB.get('study_notebooks') || [];
    const select = document.getElementById('note-config-notebook');
    select.innerHTML = `<option value="">Sem materia</option>` + notebooks.map(nb =>
        `<option value="${nb.id}" ${String(nb.id) === String(note.notebook_id || '') ? 'selected' : ''}>${nb.icon || ''} ${escapeHtml(nb.name)}</option>`
    ).join('');
    document.getElementById('note-config-title').value = note.title || '';
    document.getElementById('note-config-icon').value = note.icon || '';
    document.getElementById('note-config-cover').value = note.cover_image || note.coverImage || '';
    document.getElementById('note-config-tags').value = note.tags || '';
    document.getElementById('note-config-subject').value = note.subject || '';
    sheet.dataset.action = action || 'config';
    sheet.style.display = 'flex';
    const focusId = action === 'rename' ? 'note-config-title' : action === 'cover' ? 'note-config-icon' : 'note-config-subject';
    setTimeout(() => document.getElementById(focusId)?.focus(), 80);
};

window.closeNoteConfigSheet = function() {
    const sheet = document.getElementById('note-config-sheet');
    if (sheet) sheet.style.display = 'none';
};

window.saveNoteConfigSheet = function() {
    const noteId = window._currentNoteMenuId;
    const notes = LocalDB.get('study_notes') || [];
    const idx = notes.findIndex(n => String(n.id) === String(noteId));
    if (idx === -1) return;
    notes[idx] = {
        ...notes[idx],
        title: document.getElementById('note-config-title')?.value.trim() || notes[idx].title || 'Sem titulo',
        icon: document.getElementById('note-config-icon')?.value.trim() || '',
        cover_image: document.getElementById('note-config-cover')?.value.trim() || '',
        notebook_id: document.getElementById('note-config-notebook')?.value || '',
        tags: document.getElementById('note-config-tags')?.value.trim() || '',
        subject: document.getElementById('note-config-subject')?.value.trim() || '',
        updated_at: new Date().toISOString()
    };
    LocalDB.set('study_notes', notes);
    closeNoteConfigSheet();
    if (window.currentNotebookId) openSubjectDetail(window.currentNotebookId);
    else loadStudies();
    showInAppNotification('Nota atualizada.', 'success');
};

window.deleteNoteFromMenu = function() {
    closeNoteActionSheet();
    deleteNoteFromConfigSheet();
};

window.deleteNoteFromConfigSheet = function() {
    const noteId = window._currentNoteMenuId;
    if (!noteId) return;
    window.showConfirm('Excluir esta nota?', () => {
        const notes = LocalDB.get('study_notes') || [];
        const idx = notes.findIndex(n => String(n.id) === String(noteId));
        if (idx !== -1) {
            notes[idx].is_deleted = true;
            notes[idx].updated_at = new Date().toISOString();
            LocalDB.set('study_notes', notes);
        }
        closeNoteConfigSheet();
        if (window.currentNotebookId) openSubjectDetail(window.currentNotebookId);
        else loadStudies();
    });
};

function notePreviewText(content) {
    const div = document.createElement('div');
    div.innerHTML = content || '';
    return (div.textContent || div.innerText || content || '').replace(/[#*`_>-]/g, '').trim();
}

renderNoteCard = function(n) {
    const tags = (n.tags || '').split('#').filter(t => t.trim()).map(t => `<span class="tag-badge">#${escapeHtml(t.trim())}</span>`).join('');
    const date = n.updated_at ? new Date(n.updated_at).toLocaleDateString('pt-BR', {day:'2-digit',month:'short'}) : '';
    const pin = n.pinned ? '<i class="fa-solid fa-thumbtack" style="color:var(--accent-primary);font-size:0.7rem;margin-right:4px"></i>' : '';
    const icon = n.icon ? `${escapeHtml(n.icon)} ` : '';
    const preview = notePreviewText(n.content || '');
    return `
    <div class="note-card ${n.pinned ? 'pinned' : ''}" style="position:relative">
        <div onclick="openNoteEditor('${n.id}', '${n.notebook_id || ''}')" style="cursor:pointer;flex:1;display:block">
            <div class="note-title" style="padding-right:34px">${icon}${pin}${escapeHtml(n.title || 'Sem titulo')}</div>
            <div class="note-excerpt">${escapeHtml(preview)}</div>
            <div class="note-meta">
                <div class="note-tags">${tags}</div>
                <span style="font-size:0.7rem;color:var(--text-secondary)">${date}</span>
            </div>
        </div>
        <button class="icon-btn" onclick="openNoteMenu(event, '${n.id}')" style="position:absolute;top:8px;right:8px;padding:4px;color:var(--text-secondary);width:30px;height:30px;background:rgba(0,0,0,0.3);border-radius:50%;"><i class="fa-solid fa-ellipsis-vertical"></i></button>
    </div>`;
};

window.filterTasks = function(filter, btn) {
    if (btn) {
        document.querySelectorAll('#view-tasks .study-chip').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }
    if (typeof taskKanbanMode !== 'undefined' && taskKanbanMode) { renderTaskKanban(); return; }
    const container = document.getElementById('tasks-list-view');
    if (!container) return;
    let tasks = (LocalDB.get('tasks') || []).filter(t => !t.is_deleted);
    const sel = typeof getSelectedDate === 'function' ? getSelectedDate() : nexusTodayISO();
    const today = nexusTodayISO();
    if (filter === 'done') tasks = tasks.filter(t => t.done_at);
    else if (filter === 'today') tasks = tasks.filter(t => t.done_at ? t.done_at.startsWith(today) : (t.due_date <= today || !t.due_date));
    else if (filter === 'high') tasks = tasks.filter(t => !t.done_at && t.priority === 'high');
    else if (filter === 'all') tasks = tasks.filter(t => t.done_at ? t.done_at.startsWith(today) : true);
    if (window.NexusCalendar && NexusCalendar.activeModule === 'tasks' && sel !== today) {
        tasks = (LocalDB.get('tasks') || []).filter(t => !t.is_deleted && t.due_date === sel);
    }
    tasks.sort((a,b) => (!!a.done_at === !!b.done_at) ? 0 : (!!a.done_at ? 1 : -1));
    if (!tasks.length) {
        container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;">Nenhuma tarefa.</div>';
        return;
    }
    container.innerHTML = tasks.map(t => {
        const isDone = !!t.done_at;
        const subs = normalizeSubtasksList(t.subtasks || t.subtasks_json);
        const subCount = subs.length ? `<span class="item-subtitle">${subs.filter(s => s.done).length}/${subs.length} subtarefas</span>` : '';
        return `<div class="list-item glass task-card-mobile" data-id="${t.id}" onclick="openTaskDetail('${t.id}')" style="opacity:${isDone ? 0.62 : 1}">
            <div class="task-card-content">
                <div class="task-card-head">
                    <div class="item-main" style="flex:1;min-width:0">
                        <div class="item-title" style="text-decoration:${isDone ? 'line-through' : 'none'};color:${isDone ? 'var(--text-secondary)' : 'white'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(t.name || t.title || 'Tarefa')}</div>
                        ${subCount}
                    </div>
                    <div class="task-actions">
                        <button class="icon-btn" onclick="event.stopPropagation();deleteTaskDirect(event, '${t.id}')" style="width:32px;height:32px;background:rgba(255,0,0,0.1);border-radius:50%;color:var(--accent-pink)"><i class="fa-solid fa-trash"></i></button>
                        <button class="icon-btn" onclick="event.stopPropagation();toggleTaskDirect('${t.id}')" style="width:32px;height:32px;border-radius:50%;${isDone ? 'background:var(--accent-green);color:white' : 'background:rgba(0,0,0,0.2);color:var(--text-secondary)'}"><i class="fa-solid ${isDone ? 'fa-rotate-left' : 'fa-check'}"></i></button>
                    </div>
                </div>
                ${renderCardSubtasks(subs, `window.toggleSubtaskInline.bind(null,'${t.id}')`)}
            </div>
        </div>`;
    }).join('');
    makeSortable(container, 'tasks', 'id');
};

function renderHabitSubtasksEditor(subtasks) {
    const list = document.getElementById('habit-subtasks-list');
    if (!list) return;
    const subs = normalizeSubtasksList(subtasks);
    if (!subs.length) {
        list.innerHTML = '<div style="color:var(--text-secondary);font-size:0.8rem">Nenhuma subtarefa.</div>';
        return;
    }
    list.innerHTML = subs.map((s, i) => `
        <div class="mini-subtask-row">
            <button class="mini-check ${s.done ? 'checked' : ''}" onclick="toggleHabitSubtaskInline(${i})">${s.done ? '<i class="fa-solid fa-check"></i>' : ''}</button>
            <span style="flex:1;${s.done ? 'text-decoration:line-through' : ''}">${escapeHtml(s.name)}</span>
            <button class="icon-btn" onclick="removeHabitSubtaskInline(${i})" style="width:26px;height:26px;color:var(--accent-pink);background:transparent"><i class="fa-solid fa-xmark"></i></button>
        </div>
    `).join('');
}

window.addHabitSubtaskInline = function() {
    if (!currentHabitId) {
        showInAppNotification('Salve o habito antes de adicionar subtarefas.', 'info');
        return;
    }
    openTextInputSheet('Nova subtarefa', 'Nome', '', (name) => {
        const habits = LocalDB.get('habits') || [];
        const h = habits.find(x => String(x.id) === String(currentHabitId));
        if (!h) return;
        h.subtasks = normalizeSubtasksList(h.subtasks || h.subtasks_json);
        h.subtasks.push({ name, done: false });
        h.subtasks_json = h.subtasks;
        LocalDB.set('habits', habits);
        renderHabitSubtasksEditor(h.subtasks);
        filterHabits(document.querySelector('#view-habits .study-chip.active')?.dataset?.filter || 'all');
    });
};

window.toggleHabitSubtaskInline = function(idx) {
    const habits = LocalDB.get('habits') || [];
    const h = habits.find(x => String(x.id) === String(currentHabitId));
    if (!h) return;
    h.subtasks = normalizeSubtasksList(h.subtasks || h.subtasks_json);
    if (!h.subtasks[idx]) return;
    h.subtasks[idx].done = !h.subtasks[idx].done;
    h.subtasks_json = h.subtasks;
    LocalDB.set('habits', habits);
    renderHabitSubtasksEditor(h.subtasks);
    filterHabits(document.querySelector('#view-habits .study-chip.active')?.dataset?.filter || 'all');
};

window.removeHabitSubtaskInline = function(idx) {
    const habits = LocalDB.get('habits') || [];
    const h = habits.find(x => String(x.id) === String(currentHabitId));
    if (!h) return;
    h.subtasks = normalizeSubtasksList(h.subtasks || h.subtasks_json);
    h.subtasks.splice(idx, 1);
    h.subtasks_json = h.subtasks;
    LocalDB.set('habits', habits);
    renderHabitSubtasksEditor(h.subtasks);
    filterHabits(document.querySelector('#view-habits .study-chip.active')?.dataset?.filter || 'all');
};

const _nexusOpenHabitForm = window.openHabitForm;
window.openHabitForm = function(habitId) {
    if (typeof _nexusOpenHabitForm === 'function') _nexusOpenHabitForm(habitId);
    const habits = LocalDB.get('habits') || [];
    const h = habitId ? habits.find(x => String(x.id) === String(habitId)) : null;
    renderHabitSubtasksEditor(h ? (h.subtasks || h.subtasks_json) : []);
};

window.openHabitDetail = function(habitId) {
    window.openHabitForm(habitId);
};

const _nexusSaveHabitForm = window.saveHabitForm;
window.saveHabitForm = function() {
    const habitId = currentHabitId;
    if (typeof _nexusSaveHabitForm === 'function') _nexusSaveHabitForm();
    if (!habitId) return;
    const habits = LocalDB.get('habits') || [];
    const h = habits.find(x => String(x.id) === String(habitId));
    if (h) {
        h.subtasks = normalizeSubtasksList(h.subtasks || h.subtasks_json);
        h.subtasks_json = h.subtasks;
        LocalDB.set('habits', habits);
    }
};

window.filterHabits = function(filter, btn) {
    document.querySelectorAll('#view-habits .study-chip').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    const container = document.getElementById('habits-list');
    if (!container) return;
    const logs = LocalDB.get('habit_logs') || [];
    const today = nexusTodayISO();
    let habits = (LocalDB.get('habits') || []).filter(h => h.active === 1 && !h.is_deleted);
    let enriched = habits.map(h => {
        const isDone = logs.some(l => String(l.habit_id) === String(h.id) && l.date === today && !l.is_deleted);
        let streak = 0;
        for (let i = 0; i < 60; i++) {
            const d = new Date(); d.setDate(d.getDate() - i);
            const ds = d.toISOString().split('T')[0];
            if (logs.some(l => String(l.habit_id) === String(h.id) && l.date === ds && !l.is_deleted)) streak++;
            else if (i > 0) break;
        }
        return { ...h, isDone, streak, subtasks: normalizeSubtasksList(h.subtasks || h.subtasks_json) };
    });
    if (filter === 'done') enriched = enriched.filter(h => h.isDone);
    else if (filter === 'morning') enriched = enriched.filter(h => h.period === 'morning' && !h.isDone);
    else if (filter === 'afternoon') enriched = enriched.filter(h => h.period === 'afternoon' && !h.isDone);
    else if (filter === 'night') enriched = enriched.filter(h => h.period === 'night' && !h.isDone);
    else enriched = enriched.filter(h => !h.isDone);
    if (!enriched.length) {
        container.innerHTML = `<div style="text-align:center;color:var(--text-secondary);margin-top:30px;padding:20px">
            <i class="fa-solid ${filter === 'done' ? 'fa-check-double' : 'fa-list-check'}" style="font-size:2rem;opacity:0.4;margin-bottom:10px;display:block"></i>
            ${filter === 'done' ? 'Nenhum habito concluido hoje!' : 'Nenhum habito nesta categoria.'}
        </div>`;
        return;
    }
    container.innerHTML = enriched.map(h => {
        const periodLabel = h.period === 'morning' ? 'Manha' : h.period === 'afternoon' ? 'Tarde' : h.period === 'night' ? 'Noite' : 'Qualquer horario';
        const doneCount = h.subtasks.filter(s => s.done).length;
        const subLabel = h.subtasks.length ? ` · ${doneCount}/${h.subtasks.length} subtarefas` : '';
        return `<div class="list-item glass habit-card-mobile" data-id="${h.id}" onclick="openHabitDetail('${h.id}')" style="${h.isDone ? 'opacity:0.65' : ''}">
            <div class="habit-card-content">
                <div class="habit-card-head">
                    <div class="item-main" style="flex:1;min-width:0">
                        <div class="item-title" style="${h.isDone ? 'text-decoration:line-through;color:var(--text-secondary)' : ''};white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(h.name)}</div>
                        <div class="item-subtitle">${periodLabel}${h.streak > 0 ? ` · ${h.streak} dias` : ''}${subLabel}</div>
                    </div>
                    <div class="habit-actions">
                        <button class="icon-btn" style="background:rgba(255,71,87,0.15);color:var(--accent-pink);width:32px;height:32px;border:none;border-radius:50%" onclick="event.stopPropagation(); deleteHabitDirect('${h.id}')"><i class="fa-solid fa-trash"></i></button>
                        <button class="icon-btn" style="${h.isDone ? 'background:rgba(0,200,100,0.2);color:var(--accent-green);border:1px solid var(--accent-green)' : 'background:var(--accent-primary);color:white;border:none'};width:32px;height:32px;border-radius:50%" onclick="event.stopPropagation(); toggleHabitDirect('${h.id}'); setTimeout(() => filterHabits(document.querySelector('#view-habits .study-chip.active')?.dataset?.filter || 'all'), 200)"><i class="fa-solid ${h.isDone ? 'fa-rotate-left' : 'fa-check'}"></i></button>
                    </div>
                </div>
                ${renderCardSubtasks(h.subtasks, `window.toggleHabitCardSubtask.bind(null,'${h.id}')`)}
            </div>
        </div>`;
    }).join('');
    makeSortable(container, 'habits', 'id');
};

window.toggleHabitCardSubtask = function(habitId, idx) {
    const habits = LocalDB.get('habits') || [];
    const h = habits.find(x => String(x.id) === String(habitId));
    if (!h) return;
    h.subtasks = normalizeSubtasksList(h.subtasks || h.subtasks_json);
    if (!h.subtasks[idx]) return;
    h.subtasks[idx].done = !h.subtasks[idx].done;
    h.subtasks_json = h.subtasks;
    LocalDB.set('habits', habits);
    filterHabits(document.querySelector('#view-habits .study-chip.active')?.dataset?.filter || 'all');
};

function saveEditorSelection() {
    const editor = document.getElementById('note-content-rich');
    const sel = window.getSelection();
    if (!editor || !sel || !sel.rangeCount) return;
    const range = sel.getRangeAt(0);
    if (editor.contains(range.commonAncestorContainer)) window._noteEditorSavedRange = range.cloneRange();
}

function restoreEditorSelection() {
    const editor = document.getElementById('note-content-rich');
    const range = window._noteEditorSavedRange;
    if (!editor || !range) { editor?.focus(); return false; }
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    editor.focus();
    return true;
}

function insertHtmlIntoNoteEditor(html) {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return false;
    editor.focus();
    let inserted = false;
    try {
        restoreEditorSelection();
        inserted = document.execCommand('insertHTML', false, html);
    } catch (_) {
        inserted = false;
    }
    if (!inserted) {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = html;
        while (wrapper.firstChild) editor.appendChild(wrapper.firstChild);
        inserted = true;
    }
    return inserted;
}

window.triggerOcrCamera = function() {
    const editor = document.getElementById('note-content-rich');
    if (editor) saveEditorSelection();
    const sheet = document.getElementById('ocr-source-sheet');
    if (sheet) sheet.style.display = 'flex';
};

window.closeOcrSourceSheet = function() {
    const sheet = document.getElementById('ocr-source-sheet');
    if (sheet) sheet.style.display = 'none';
};

window.startOcrFromGallery = function() {
    closeOcrSourceSheet();
    const input = document.getElementById('ocr-file-input');
    if (!input) return;
    input.removeAttribute('capture');
    input.value = '';
    input.click();
};

window.startOcrFromCamera = function() {
    closeOcrSourceSheet();
    if (window.AndroidNative && typeof window.AndroidNative.openNativeCamera === 'function') {
        window.AndroidNative.openNativeCamera();
        showToast('Abrindo camera...');
        return;
    }
    const input = document.getElementById('ocr-file-input');
    if (input) {
        input.setAttribute('capture', 'environment');
        input.value = '';
        input.click();
    }
};

window.handleOcrFileSelected = function(event) {
    const file = event?.target?.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => processOcrImageDataUrl(String(reader.result || ''));
    reader.readAsDataURL(file);
};

window.onNativeCameraResult = function(dataUrl) {
    if (!dataUrl) return;
    processOcrImageDataUrl(dataUrl);
};

async function processOcrImageDataUrl(dataUrl) {
    const editor = document.getElementById('note-content-rich');
    if (!editor) { showToast('Abra o editor de notas para inserir o texto.'); return; }
    const status = document.getElementById('ocr-status');
    if (status) status.style.display = 'block';
    try {
        let text = '';
        try {
            text = await runGroqVisionOcr(dataUrl);
        } catch (groqErr) {
            console.warn('[OCR Groq fallback]', groqErr);
            text = await runGeminiVisionOcr(dataUrl);
        }
        if (!text.trim()) throw new Error('Nenhum texto encontrado.');
        const html = '<p>' + escapeHtmlLight(text).replace(/\n/g, '<br>') + '</p>';
        insertHtmlIntoNoteEditor(html);
        if (typeof saveNoteDebounced === 'function') saveNoteDebounced();
        showInAppNotification('Texto transcrito e inserido.', 'success');
    } catch (e) {
        showInAppNotification(e.message || 'Falha ao transcrever imagem.', 'warn');
    } finally {
        if (status) status.style.display = 'none';
    }
}

window.openFinanceOverflow = function(ev) {
    if (ev) ev.stopPropagation();
    let sheet = document.getElementById('finance-actions-sheet');
    if (!sheet) {
        sheet = document.createElement('div');
        sheet.id = 'finance-actions-sheet';
        sheet.className = 'bottom-sheet';
        sheet.innerHTML = `
            <div class="bottom-sheet-content glass">
                <div class="bottom-sheet-handle"></div>
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                    <h3 style="margin:0;font-size:1.05rem">Financas</h3>
                    <button onclick="document.getElementById('finance-actions-sheet').style.display='none'" class="icon-btn"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <div class="sheet-action-grid">
                    <button onclick="openFinanceTransactionForm('expense')"><i class="fa-solid fa-arrow-trend-down"></i><span>Gasto</span></button>
                    <button onclick="openFinanceTransactionForm('income')"><i class="fa-solid fa-arrow-trend-up"></i><span>Ganho</span></button>
                </div>
                <button onclick="showFinanceSyncInfo()" style="width:100%;margin-top:10px;border:1px solid rgba(255,255,255,0.08);background:rgba(255,255,255,0.04);color:var(--text-secondary);padding:12px;border-radius:12px;font:inherit;font-weight:700">
                    <i class="fa-solid fa-building-columns"></i> Bancos / Mercado Pago
                </button>
            </div>`;
        document.body.appendChild(sheet);
    }
    sheet.style.display = 'flex';
};

window.openFinanceTransactionForm = function(type) {
    const actions = document.getElementById('finance-actions-sheet');
    if (actions) actions.style.display = 'none';
    const sheet = document.getElementById('finance-tx-sheet');
    if (!sheet) return;
    const isIncome = type === 'income';
    document.getElementById('finance-tx-title').textContent = isIncome ? 'Registrar ganho' : 'Registrar gasto';
    document.getElementById('finance-tx-type').value = isIncome ? 'income' : 'expense';
    document.getElementById('finance-tx-desc').value = '';
    document.getElementById('finance-tx-amount').value = '';
    document.getElementById('finance-tx-category').value = isIncome ? 'Receita' : 'Geral';
    document.getElementById('finance-tx-date').value = nexusTodayISO();
    sheet.style.display = 'flex';
    setTimeout(() => document.getElementById('finance-tx-desc')?.focus(), 80);
};

window.closeFinanceTransactionForm = function() {
    const sheet = document.getElementById('finance-tx-sheet');
    if (sheet) sheet.style.display = 'none';
};

window.saveFinanceTransactionForm = function() {
    const type = document.getElementById('finance-tx-type')?.value || 'expense';
    const description = document.getElementById('finance-tx-desc')?.value.trim() || (type === 'income' ? 'Ganho' : 'Gasto');
    const amount = Number(document.getElementById('finance-tx-amount')?.value || 0);
    const category = document.getElementById('finance-tx-category')?.value.trim() || (type === 'income' ? 'Receita' : 'Geral');
    const date = document.getElementById('finance-tx-date')?.value || nexusTodayISO();
    if (amount <= 0) { showInAppNotification('Informe um valor maior que zero.', 'warn'); return; }
    LocalDB.upsert('finance_transactions', {
        id: Date.now(),
        type,
        amount,
        description,
        category,
        occurred_at: date + 'T12:00:00.000Z',
        created_at: new Date().toISOString()
    });
    closeFinanceTransactionForm();
    loadFinances();
    if (typeof ensureChartJs === 'function') ensureChartJs().then(() => setTimeout(renderFinanceCharts, 100));
    else if (typeof renderFinanceCharts === 'function') renderFinanceCharts();
    showInAppNotification(type === 'income' ? 'Ganho registrado.' : 'Gasto registrado.', 'success');
};

window.showFinanceSyncInfo = function() {
    const actions = document.getElementById('finance-actions-sheet');
    if (actions) actions.style.display = 'none';
    showInAppNotification('Sync bancario gratis exige Open Finance autorizado/parceiro. Por enquanto use lancamentos manuais.', 'info');
};

async function runGeminiNoteAction(mode, content) {
    const key = typeof getGeminiKey === 'function' ? getGeminiKey() : localStorage.getItem('nexus_gemini_key');
    if (!key) throw new Error('Configure a chave Gemini nas configuracoes.');
    const prompts = {
        summarize_text: 'Resuma o texto abaixo em portugues, com pontos principais, conceitos importantes e uma lista curta do que revisar depois.',
        expand_text: 'Expanda e melhore o texto abaixo em portugues, mantendo a intencao original e organizando em paragrafos claros.',
        translate: 'Traduza o texto abaixo para portugues natural se estiver em outro idioma; se ja estiver em portugues, melhore a clareza sem mudar o sentido.',
        deep_search: 'Analise o tema abaixo como um assistente de estudos. Explique o assunto, liste pontos importantes e sugira perguntas de revisao. Nao invente fontes externas.'
    };
    const instruction = prompts[mode] || 'Responda ao pedido abaixo de forma util e direta em portugues.';
    const data = await callGeminiGenerate([{ text: `${instruction}\n\n${content}` }], key);
    const text = data?.candidates?.[0]?.content?.parts?.map(p => p.text || '').join('\n').trim();
    if (!text) throw new Error('Gemini nao retornou texto.');
    return text;
}

async function callGroqChat(messages, options = {}) {
    const key = typeof getGroqKey === 'function' ? getGroqKey() : localStorage.getItem('nexus_groq_key');
    if (!key) throw new Error('Configure a chave Groq nas configuracoes.');
    const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer ' + key,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            model: options.model || 'llama-3.3-70b-versatile',
            messages,
            temperature: options.temperature ?? 0.2,
            max_completion_tokens: options.max_completion_tokens || 1200,
            stream: false
        })
    });
    if (!res.ok) {
        let detail = '';
        try { detail = await res.text(); } catch (_) {}
        throw new Error('Groq falhou (' + res.status + ')' + (detail ? ': ' + detail.slice(0, 180) : '.'));
    }
    return await res.json();
}

async function runGroqNoteAction(mode, content) {
    const prompts = {
        summarize_text: 'Resuma o texto em portugues, com pontos principais, conceitos importantes e uma lista curta do que revisar depois.',
        expand_text: 'Expanda e melhore o texto em portugues, mantendo a intencao original e organizando em paragrafos claros.',
        translate: 'Traduza o texto para portugues natural se estiver em outro idioma; se ja estiver em portugues, melhore a clareza sem mudar o sentido.',
        deep_search: 'Analise o tema como um assistente de estudos. Explique o assunto, liste pontos importantes e sugira perguntas de revisao. Nao invente fontes externas.',
        summarize_video: 'Explique que resumo de video precisa de transcricao ou backend do YouTube; se houver texto colado, resuma esse texto.'
    };
    const data = await callGroqChat([
        { role: 'system', content: 'Voce e o Jarvis no app Nexus. Seja direto, util e escreva em portugues do Brasil.' },
        { role: 'user', content: `${prompts[mode] || 'Responda de forma util.'}\n\n${content}` }
    ], { model: 'llama-3.3-70b-versatile' });
    const text = data?.choices?.[0]?.message?.content?.trim();
    if (!text) throw new Error('Groq nao retornou texto.');
    return text;
}

async function callGeminiGenerate(parts, key) {
    const apiKey = key || (typeof getGeminiKey === 'function' ? getGeminiKey() : localStorage.getItem('nexus_gemini_key'));
    if (!apiKey) throw new Error('Configure a chave Gemini nas configuracoes.');
    const models = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash-latest', 'gemini-1.5-flash'];
    let lastError = '';
    for (const model of models) {
        try {
            const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(apiKey)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ contents: [{ parts }] })
            });
            if (res.ok) return await res.json();
            lastError = `${model}: ${res.status}`;
            if (![404, 400].includes(res.status)) break;
        } catch (e) {
            lastError = e.message || String(e);
        }
    }
    throw new Error('Gemini falhou (' + lastError + ').');
}

function dataUrlToImage(dataUrl) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error('Imagem invalida.'));
        img.src = dataUrl;
    });
}

async function compressImageDataUrlForApi(dataUrl) {
    const img = await dataUrlToImage(dataUrl);
    const maxSide = 1600;
    const scale = Math.min(1, maxSide / Math.max(img.width || maxSide, img.height || maxSide));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round((img.width || maxSide) * scale));
    canvas.height = Math.max(1, Math.round((img.height || maxSide) * scale));
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.82);
}

async function runGroqVisionOcr(dataUrl) {
    const prepared = await compressImageDataUrlForApi(dataUrl);
    const data = await callGroqChat([
        {
            role: 'user',
            content: [
                {
                    type: 'text',
                    text: 'Transcreva fielmente todo o texto visivel nesta imagem. Preserve quebras de linha, listas, contas e pontuacao. Responda somente com o texto transcrito.'
                },
                {
                    type: 'image_url',
                    image_url: { url: prepared }
                }
            ]
        }
    ], {
        model: 'meta-llama/llama-4-scout-17b-16e-instruct',
        max_completion_tokens: 2400
    });
    const text = data?.choices?.[0]?.message?.content?.trim();
    if (!text) throw new Error('Groq nao retornou texto da imagem.');
    return text;
}

async function runGeminiVisionOcr(dataUrl) {
    const prepared = await compressImageDataUrlForApi(dataUrl);
    const match = prepared.match(/^data:(.*?);base64,(.*)$/);
    if (!match) throw new Error('Imagem invalida.');
    const data = await callGeminiGenerate([
        { text: 'Transcreva fielmente todo o texto visivel nesta imagem. Preserve quebras de linha, listas, contas e pontuacao. Responda somente com o texto transcrito.' },
        { inline_data: { mime_type: match[1] || 'image/jpeg', data: match[2] } }
    ]);
    const text = data?.candidates?.[0]?.content?.parts?.map(p => p.text || '').join('\n').trim();
    if (!text) throw new Error('Gemini nao retornou texto da imagem.');
    return text;
}

window.openJarvisPanel = function(mode) {
    const panel = document.getElementById('jarvis-panel');
    if (!panel) return;
    panel.style.display = 'flex';
    if (mode && typeof setJarvisMode === 'function') setJarvisMode(mode, null);
    if (typeof _jarvisMode !== 'undefined' && _jarvisMode === 'summarize_text') {
        const sel = window.getSelection();
        const prompt = document.getElementById('jarvis-prompt');
        if (prompt && sel && sel.toString().trim()) prompt.value = sel.toString().trim();
    }
    const result = document.getElementById('jarvis-result');
    const loading = document.getElementById('jarvis-loading');
    const input = document.getElementById('jarvis-input-area');
    if (result) result.style.display = 'none';
    if (loading) loading.style.display = 'none';
    if (input) input.style.display = 'block';
};
openJarvisPanel = window.openJarvisPanel;

window.openNoteJarvisAction = function(mode) {
    window.openJarvisPanel(mode || 'summarize_text');
    const editor = document.getElementById('note-content-rich');
    const text = editor ? (editor.innerText || '').trim() : '';
    const prompt = document.getElementById('jarvis-prompt');
    if (prompt && text) prompt.value = text.slice(0, 6000);
};

const _nexusPreviousRunJarvisAction = window.runJarvisAction;
window.runJarvisAction = async function() {
    if (typeof _jarvisMode !== 'undefined' && _jarvisMode === 'generate_flashcards') {
        if (typeof _nexusPreviousRunJarvisAction === 'function') return _nexusPreviousRunJarvisAction();
    }
    const prompt = document.getElementById('jarvis-prompt')?.value?.trim();
    if (!prompt) { showInAppNotification('Insira um texto ou URL.', 'warn'); return; }
    const input = document.getElementById('jarvis-input-area');
    const loading = document.getElementById('jarvis-loading');
    const resultBox = document.getElementById('jarvis-result');
    const resultText = document.getElementById('jarvis-result-text');
    if (input) input.style.display = 'none';
    if (loading) loading.style.display = 'block';
    if (resultBox) resultBox.style.display = 'none';
    try {
        let result = '';
        let apiResponse = null;
        try {
            result = await runGroqNoteAction(_jarvisMode, prompt);
        } catch (groqErr) {
            console.warn('[Jarvis Groq fallback]', groqErr);
            if (_jarvisMode === 'generate_image' || _jarvisMode === 'summarize_video') {
                result = _jarvisMode === 'summarize_video'
                    ? await runGeminiNoteAction('summarize_text', prompt)
                    : 'Geracao de imagem ainda precisa do backend configurado.';
            } else {
                result = await runGeminiNoteAction(_jarvisMode, prompt);
            }
        }
        _jarvisLastResult = result;
        _jarvisLastApiResponse = apiResponse;
        if (loading) loading.style.display = 'none';
        if (resultBox) resultBox.style.display = 'block';
        if (resultText) {
            resultText.innerHTML = _jarvisMode === 'generate_image' && apiResponse?.image_url
                ? `<img src="${apiResponse.image_url}" style="max-width:100%;border-radius:10px">`
                : escapeHtmlLight(result).replace(/\n/g, '<br>');
        }
    } catch (e) {
        if (loading) loading.style.display = 'none';
        showInAppNotification(e.message || 'Erro ao processar com Jarvis.', 'warn');
    } finally {
        if (input) input.style.display = 'block';
    }
};
runJarvisAction = window.runJarvisAction;

// ================================================================
// NOTE AGENT: research, inspect notes, draft changes, apply/undo
// ================================================================

function plainTextFromHtml(html) {
    const div = document.createElement('div');
    div.innerHTML = html || '';
    return (div.innerText || div.textContent || '').replace(/\s+\n/g, '\n').trim();
}

function generateLocalNoteSummary(note) {
    const text = plainTextFromHtml(note?.content || '');
    const sentences = text.split(/(?<=[.!?])\s+/).filter(Boolean);
    const summary = (sentences.slice(0, 3).join(' ') || text).slice(0, 520);
    const words = text.toLowerCase()
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9\s]/g, ' ')
        .split(/\s+/)
        .filter(w => w.length > 4 && !['sobre','porque','quando','muito','tambem','entao','como','para','com','uma','este','esta','esse','essa'].includes(w));
    const counts = {};
    words.forEach(w => counts[w] = (counts[w] || 0) + 1);
    const keywords = Object.entries(counts).sort((a,b) => b[1] - a[1]).slice(0, 8).map(([w]) => w);
    const outline = Array.from((note?.content || '').matchAll(/<h[1-3][^>]*>(.*?)<\/h[1-3]>/gi))
        .map(m => plainTextFromHtml(m[1]).slice(0, 80))
        .filter(Boolean)
        .slice(0, 8);
    return { summary, keywords, outline };
}

function refreshNoteSummaryFields(note) {
    if (!note) return note;
    const meta = generateLocalNoteSummary(note);
    note.summary = meta.summary;
    note.ai_summary = meta.summary;
    note.keywords = meta.keywords;
    note.outline = meta.outline;
    note.summary_updated_at = new Date().toISOString();
    return note;
}

const _noteAgentSaveNote = window.saveNote;
window.saveNote = function() {
    const beforeId = editingNoteId ? String(editingNoteId) : null;
    if (typeof _noteAgentSaveNote === 'function') _noteAgentSaveNote();
    const notes = LocalDB.get('study_notes') || [];
    let saved = beforeId ? notes.find(n => String(n.id) === beforeId) : null;
    if (!saved) {
        saved = notes.filter(n => !n.is_deleted).sort((a,b) => (b.updated_at || b.created_at || '').localeCompare(a.updated_at || a.created_at || ''))[0];
    }
    if (saved) {
        refreshNoteSummaryFields(saved);
        LocalDB.set('study_notes', notes);
    }
};
saveNote = window.saveNote;

function getStudyAgentContext() {
    const notebooks = (LocalDB.get('study_notebooks') || []).filter(n => !n.is_deleted);
    const notes = (LocalDB.get('study_notes') || []).filter(n => !n.is_deleted).map(n => {
        const nb = notebooks.find(x => String(x.id) === String(n.notebook_id));
        const meta = n.summary || n.ai_summary ? null : generateLocalNoteSummary(n);
        return {
            id: String(n.id),
            title: n.title || 'Sem titulo',
            notebook_id: n.notebook_id || '',
            notebook: nb ? nb.name : '',
            tags: n.tags || '',
            subject: n.subject || '',
            summary: n.summary || n.ai_summary || meta?.summary || plainTextFromHtml(n.content || '').slice(0, 360),
            keywords: n.keywords || meta?.keywords || [],
            outline: n.outline || meta?.outline || [],
            updated_at: n.updated_at || n.created_at || ''
        };
    });
    return { notebooks, notes };
}

function extractJsonObject(text) {
    const raw = String(text || '').trim();
    try { return JSON.parse(raw); } catch (_) {}
    const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
    if (fenced) {
        try { return JSON.parse(fenced[1]); } catch (_) {}
    }
    const start = raw.indexOf('{');
    const end = raw.lastIndexOf('}');
    if (start !== -1 && end > start) {
        try { return JSON.parse(raw.slice(start, end + 1)); } catch (_) {}
    }
    throw new Error('Jarvis nao retornou um plano estruturado.');
}

async function groqNoteAgentResearch(userRequest) {
    try {
        const data = await callGroqChat([
            {
                role: 'system',
                content: 'Voce pesquisa para um app de estudos. Use conhecimento e, se disponivel no modelo, ferramentas de busca. Responda em portugues com fatos, estrutura, fontes/links uteis e sugestoes de imagem/video quando fizer sentido.'
            },
            { role: 'user', content: userRequest }
        ], {
            model: 'groq/compound',
            temperature: 0.2,
            max_completion_tokens: 1800
        });
        return data?.choices?.[0]?.message?.content?.trim() || '';
    } catch (e) {
        console.warn('[Note Agent research fallback]', e);
        return runGroqNoteAction('deep_search', userRequest);
    }
}

function cleanAgentSearchQuery(text) {
    return String(text || '')
        .replace(/\b(crie|criar|adicione|adicionar|nota|pesquise|pesquisar|sobre|completa|curta|estrutura|estudo|existente|nova)\b/gi, ' ')
        .replace(/[^\p{L}\p{N}\s-]/gu, ' ')
        .replace(/\s+/g, ' ')
        .trim()
        .slice(0, 90);
}

async function fetchWikipediaAsset(query) {
    const q = encodeURIComponent(query || '');
    if (!q) return null;
    const urls = [
        `https://pt.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch=${q}&gsrlimit=1&prop=extracts|pageimages|info&exintro=1&explaintext=1&piprop=thumbnail|original&pithumbsize=900&inprop=url&format=json&origin=*`,
        `https://en.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch=${q}&gsrlimit=1&prop=extracts|pageimages|info&exintro=1&explaintext=1&piprop=thumbnail|original&pithumbsize=900&inprop=url&format=json&origin=*`
    ];
    for (const url of urls) {
        try {
            const res = await fetch(url);
            if (!res.ok) continue;
            const data = await res.json();
            const page = Object.values(data?.query?.pages || {})[0];
            if (!page) continue;
            return {
                title: page.title || query,
                extract: (page.extract || '').slice(0, 1200),
                page_url: page.fullurl || '',
                image_url: page.original?.source || page.thumbnail?.source || '',
                image_source: page.fullurl || 'Wikipedia'
            };
        } catch (e) {
            console.warn('[Wikipedia asset search]', e);
        }
    }
    return null;
}

async function findOpenStudyAssets(userRequest, plan) {
    const query = cleanAgentSearchQuery(plan?.title || userRequest);
    const wiki = await fetchWikipediaAsset(query);
    const images = [];
    const references = [];
    if (wiki) {
        if (wiki.image_url) {
            images.push({
                url: wiki.image_url,
                alt: wiki.title,
                caption: `Imagem: ${wiki.title}`,
                source: wiki.image_source
            });
        }
        if (wiki.page_url || wiki.extract) {
            references.push({
                title: wiki.title,
                url: wiki.page_url,
                excerpt: wiki.extract
            });
        }
    }
    return { query, images, references };
}

async function groqNoteAgentPlan(userRequest, context, research) {
    const currentNote = editingNoteId ? (LocalDB.get('study_notes') || []).find(n => String(n.id) === String(editingNoteId)) : null;
    const plannerPrompt = {
        request: userRequest,
        current_note_id: currentNote ? String(currentNote.id) : null,
        notes_index: context.notes.slice(0, 80),
        subjects: context.notebooks.map(n => ({ id: String(n.id), name: n.name, icon: n.icon || '' })),
        research: research.slice(0, 8000)
    };
    const data = await callGroqChat([
        {
            role: 'system',
            content: `Voce e um agente editor de notas do Nexus. Escolha se deve criar nota nova ou atualizar uma existente.
Use titulos, materias e resumos para escolher. Se houver nota existente claramente relacionada, prefira atualizar. Se nao houver, crie uma nova.
Responda SOMENTE JSON valido neste formato:
{"action":"create|update","target_note_id":null,"title":"...","notebook_id":null,"reason":"..."}`
        },
        { role: 'user', content: JSON.stringify(plannerPrompt) }
    ], {
        model: 'llama-3.3-70b-versatile',
        temperature: 0.1,
        max_completion_tokens: 700
    });
    const plan = extractJsonObject(data?.choices?.[0]?.message?.content || '');
    if (plan.action !== 'update' && plan.action !== 'create') plan.action = 'create';
    return plan;
}

function normalizeAgentHtml(html) {
    const template = document.createElement('template');
    template.innerHTML = html || '';
    template.content.querySelectorAll('script,style,object,embed').forEach(el => el.remove());
    template.content.querySelectorAll('*').forEach(el => {
        [...el.attributes].forEach(attr => {
            const name = attr.name.toLowerCase();
            const value = attr.value || '';
            if (name.startsWith('on')) el.removeAttribute(attr.name);
            if ((name === 'src' || name === 'href') && /^javascript:/i.test(value)) el.removeAttribute(attr.name);
        });
        if (el.tagName === 'IFRAME') {
            const src = el.getAttribute('src') || '';
            if (!/youtube(-nocookie)?\.com\/embed\//i.test(src)) el.remove();
        }
        if (el.tagName === 'IMG') {
            el.setAttribute('loading', 'lazy');
            el.style.maxWidth = '100%';
            el.style.borderRadius = '10px';
        }
    });
    return template.innerHTML.trim();
}

function buildYoutubeEmbedHtml(url) {
    const id = typeof extractYouTubeId === 'function' ? extractYouTubeId(url || '') : null;
    if (!id || typeof getYouTubeEmbedSrc !== 'function') return '';
    return `<div class="yt-embed-block" contenteditable="false"><iframe src="${getYouTubeEmbedSrc(id)}" title="YouTube video player" loading="lazy" referrerpolicy="strict-origin-when-cross-origin" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div><p><br></p>`;
}

async function groqNoteAgentDraft(userRequest, plan, research, assets = { images: [], references: [] }) {
    const notes = LocalDB.get('study_notes') || [];
    const target = plan.target_note_id ? notes.find(n => String(n.id) === String(plan.target_note_id)) : null;
    const targetText = target ? {
        id: String(target.id),
        title: target.title,
        content_html: (target.content || '').slice(0, 18000),
        summary: target.summary || target.ai_summary || ''
    } : null;
    const data = await callGroqChat([
        {
            role: 'system',
            content: `Voce escreve notas ricas em HTML para um editor mobile. Gere conteudo completo, organizado e estudavel.
Use apenas tags simples: h1,h2,h3,p,ul,ol,li,strong,em,blockquote,hr,figure,figcaption,img,a.
Nao invente URL de imagem. Se houver available_images, pode inserir no maximo 2 imagens com <figure><img src="URL" alt="..."><figcaption>Fonte: ...</figcaption></figure>.
Se nao houver URL confiavel, escreva [imagem sugerida: consulta] quando a imagem realmente ajudaria.
Para YouTube, inclua URLs em "youtube_urls" quando relevantes.
Responda SOMENTE JSON valido:
{"action":"create|update","target_note_id":null,"title":"...","notebook_id":null,"html":"...","reason":"...","youtube_urls":[]}`
        },
        {
            role: 'user',
            content: JSON.stringify({
                request: userRequest,
                plan,
                target_note: targetText,
                research: research.slice(0, 10000),
                available_images: assets.images || [],
                available_references: assets.references || []
            })
        }
    ], {
        model: 'llama-3.3-70b-versatile',
        temperature: 0.25,
        max_completion_tokens: 3600
    });
    const draft = extractJsonObject(data?.choices?.[0]?.message?.content || '');
    draft.action = draft.action || plan.action || 'create';
    draft.target_note_id = draft.target_note_id || plan.target_note_id || null;
    draft.title = draft.title || plan.title || 'Nota sem titulo';
    draft.notebook_id = draft.notebook_id || plan.notebook_id || target?.notebook_id || currentNotebookId || '';
    let html = normalizeAgentHtml(draft.html || '');
    (draft.youtube_urls || []).slice(0, 2).forEach(url => {
        const embed = buildYoutubeEmbedHtml(url);
        if (embed && !html.includes(url)) html += embed;
    });
    if (!html) throw new Error('Jarvis nao gerou conteudo para a nota.');
    draft.html = html;
    draft.reason = draft.reason || plan.reason || '';
    return draft;
}

function showNoteAgentDraft(draft) {
    window._noteAgentDraft = draft;
    const resultBox = document.getElementById('jarvis-result');
    const resultText = document.getElementById('jarvis-result-text');
    if (!resultBox || !resultText) return;
    const notes = LocalDB.get('study_notes') || [];
    const notebooks = LocalDB.get('study_notebooks') || [];
    const target = draft.action === 'update' && draft.target_note_id ? notes.find(n => String(n.id) === String(draft.target_note_id)) : null;
    const notebook = draft.notebook_id ? notebooks.find(n => String(n.id) === String(draft.notebook_id)) : null;
    const targetText = target ? `Atualizar: ${escapeHtml(target.title || 'Sem titulo')}` : 'Criar nova nota';
    const imgCount = (draft.html.match(/<img\b/gi) || []).length;
    resultBox.style.display = 'block';
    resultText.innerHTML = `
        <div style="display:flex;flex-direction:column;gap:10px">
            <div><strong>${targetText}</strong></div>
            <div style="display:flex;gap:6px;flex-wrap:wrap">
                <span style="font-size:0.72rem;padding:4px 8px;border-radius:999px;background:rgba(108,92,231,0.16);color:#b7adff">${escapeHtml(draft.title || 'Sem titulo')}</span>
                ${notebook ? `<span style="font-size:0.72rem;padding:4px 8px;border-radius:999px;background:rgba(0,206,201,0.12);color:var(--accent-blue)">${escapeHtml(notebook.name)}</span>` : ''}
                ${imgCount ? `<span style="font-size:0.72rem;padding:4px 8px;border-radius:999px;background:rgba(0,184,148,0.12);color:var(--accent-green)">${imgCount} imagem(ns)</span>` : ''}
            </div>
            <div style="color:var(--text-secondary);font-size:0.85rem">${escapeHtml(draft.reason || 'Rascunho preparado.')}</div>
            <div style="max-height:220px;overflow:auto;border:1px solid var(--border-glass);border-radius:10px;padding:10px;background:rgba(255,255,255,0.04)">${draft.html}</div>
            <div style="display:flex;gap:8px">
                <button onclick="applyNoteAgentDraft()" style="flex:1;background:var(--accent-green);border:none;color:white;padding:11px;border-radius:10px;font-weight:800">Aplicar</button>
                <button onclick="discardNoteAgentDraft()" style="flex:1;background:rgba(255,255,255,0.08);border:1px solid var(--border-glass);color:white;padding:11px;border-radius:10px;font-weight:800">Descartar</button>
            </div>
        </div>`;
}

window.applyNoteAgentDraft = function() {
    const draft = window._noteAgentDraft;
    if (!draft) return;
    const notes = LocalDB.get('study_notes') || [];
    const now = new Date().toISOString();
    if (draft.action === 'update' && draft.target_note_id) {
        const idx = notes.findIndex(n => String(n.id) === String(draft.target_note_id));
        if (idx !== -1) {
            window._noteAgentUndo = { type: 'update', note: { ...notes[idx] } };
            notes[idx] = refreshNoteSummaryFields({
                ...notes[idx],
                title: draft.title || notes[idx].title,
                content: draft.html,
                notebook_id: draft.notebook_id || notes[idx].notebook_id || '',
                updated_at: now
            });
            LocalDB.set('study_notes', notes);
            openNoteEditor(notes[idx].id, notes[idx].notebook_id || null);
        }
    } else {
        const note = refreshNoteSummaryFields({
            id: Date.now().toString(),
            title: draft.title || 'Nova nota',
            content: draft.html,
            notebook_id: draft.notebook_id || currentNotebookId || '',
            tags: '#jarvis',
            subject: draft.title || '',
            created_at: now,
            updated_at: now
        });
        notes.push(note);
        window._noteAgentUndo = { type: 'create', note_id: String(note.id) };
        LocalDB.set('study_notes', notes);
        openNoteEditor(note.id, note.notebook_id || null);
    }
    window._noteAgentDraft = null;
    const resultText = document.getElementById('jarvis-result-text');
    if (resultText) {
        resultText.innerHTML = `<div style="display:flex;flex-direction:column;gap:10px">
            <strong>Alteracao aplicada.</strong>
            <button onclick="undoNoteAgentChange()" style="background:rgba(255,255,255,0.08);border:1px solid var(--border-glass);color:white;padding:11px;border-radius:10px;font-weight:800">Desfazer alteracao</button>
        </div>`;
    }
    if (typeof loadStudies === 'function') loadStudies();
};

window.undoNoteAgentChange = function() {
    const undo = window._noteAgentUndo;
    if (!undo) return;
    const notes = LocalDB.get('study_notes') || [];
    if (undo.type === 'update' && undo.note) {
        const idx = notes.findIndex(n => String(n.id) === String(undo.note.id));
        if (idx !== -1) notes[idx] = undo.note;
        else notes.push(undo.note);
        LocalDB.set('study_notes', notes);
        openNoteEditor(undo.note.id, undo.note.notebook_id || null);
    } else if (undo.type === 'create' && undo.note_id) {
        LocalDB.set('study_notes', notes.filter(n => String(n.id) !== String(undo.note_id)));
        closeNoteEditor();
        loadStudies();
    }
    window._noteAgentUndo = null;
    showInAppNotification('Alteracao desfeita.', 'info');
};

window.discardNoteAgentDraft = function() {
    window._noteAgentDraft = null;
    const result = document.getElementById('jarvis-result');
    if (result) result.style.display = 'none';
};

async function runNoteAgentFromPanel() {
    const prompt = document.getElementById('jarvis-prompt')?.value?.trim();
    if (!prompt) { showInAppNotification('Descreva o que o Jarvis deve pesquisar/escrever.', 'warn'); return; }
    const input = document.getElementById('jarvis-input-area');
    const loading = document.getElementById('jarvis-loading');
    const result = document.getElementById('jarvis-result');
    if (input) input.style.display = 'none';
    if (loading) loading.style.display = 'block';
    if (result) result.style.display = 'none';
    try {
        const context = getStudyAgentContext();
        const research = await groqNoteAgentResearch(prompt);
        const plan = await groqNoteAgentPlan(prompt, context, research);
        const assets = await findOpenStudyAssets(prompt, plan);
        const enrichedResearch = [
            research,
            assets.references?.length ? '\n\nReferencias abertas encontradas:\n' + assets.references.map(r => `- ${r.title}: ${r.url}\n${r.excerpt || ''}`).join('\n') : ''
        ].join('');
        const draft = await groqNoteAgentDraft(prompt, plan, enrichedResearch, assets);
        if (loading) loading.style.display = 'none';
        showNoteAgentDraft(draft);
    } catch (e) {
        if (loading) loading.style.display = 'none';
        showInAppNotification(e.message || 'Falha no agente de notas.', 'warn');
    } finally {
        if (input) input.style.display = 'block';
    }
}

function ensureNoteAgentTab() {
    const tabs = document.querySelector('#jarvis-panel .jarvis-tab')?.parentElement;
    if (!tabs || document.getElementById('jarvis-note-agent-tab')) return;
    const btn = document.createElement('button');
    btn.id = 'jarvis-note-agent-tab';
    btn.className = 'jarvis-tab';
    btn.innerHTML = '<i class="fa-solid fa-file-pen"></i> Agente';
    btn.onclick = function() { setJarvisMode('note_agent', this); };
    tabs.appendChild(btn);
}

const _noteAgentSetJarvisMode = window.setJarvisMode || setJarvisMode;
window.setJarvisMode = function(mode, btn) {
    if (typeof _noteAgentSetJarvisMode === 'function' && mode !== 'note_agent') {
        _noteAgentSetJarvisMode(mode, btn);
        return;
    }
    _jarvisMode = mode || 'note_agent';
    window._noteAgentDraft = null;
    document.querySelectorAll('.jarvis-tab').forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');
    const prompt = document.getElementById('jarvis-prompt');
    if (prompt) {
        prompt.placeholder = 'Ex: pesquise raiz quadrada e crie/atualize uma nota completa com exemplos, imagens sugeridas e videos relevantes...';
        prompt.value = '';
    }
    const result = document.getElementById('jarvis-result');
    if (result) result.style.display = 'none';
};
setJarvisMode = window.setJarvisMode;

const _noteAgentOpenJarvisPanel = window.openJarvisPanel;
window.openJarvisPanel = function(mode) {
    ensureNoteAgentTab();
    if (typeof _noteAgentOpenJarvisPanel === 'function') _noteAgentOpenJarvisPanel(mode);
    ensureNoteAgentTab();
};
openJarvisPanel = window.openJarvisPanel;

const _noteAgentRunJarvisAction = window.runJarvisAction;
window.runJarvisAction = async function() {
    if (typeof _jarvisMode !== 'undefined' && _jarvisMode === 'note_agent') {
        return runNoteAgentFromPanel();
    }
    if (typeof _noteAgentRunJarvisAction === 'function') return _noteAgentRunJarvisAction();
};
runJarvisAction = window.runJarvisAction;

document.addEventListener('DOMContentLoaded', ensureNoteAgentTab);

// ================================================================
// VISION BOARD
// ================================================================

window.openVisionBoard = function() {
    const modal = document.getElementById('vision-board-modal');
    if (modal) { modal.style.display = 'flex'; renderVisionBoard(); }
};
window.closeVisionBoard = function() {
    const modal = document.getElementById('vision-board-modal');
    if (modal) modal.style.display = 'none';
};

window.addVisionImage = function(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(e) {
        const images = LocalDB.get('vision_board') || [];
        images.push({ id: Date.now(), src: e.target.result, label: '', added_at: new Date().toISOString() });
        LocalDB.set('vision_board', images);
        renderVisionBoard();
    };
    reader.readAsDataURL(file);
    event.target.value = '';
};

window.deleteVisionImage = function(id) {
    window.showConfirm('Remover esta imagem do Vision Board?', () => {
        const images = LocalDB.get('vision_board') || [];
        const idx = images.findIndex(x => String(x.id) === String(id));
        if (idx !== -1) {
            images[idx].is_deleted = true;
            images[idx].updated_at = new Date().toISOString();
            LocalDB.set('vision_board', images);
        }
        renderVisionBoard();
    });
};

function renderVisionBoard() {
    const grid = document.getElementById('vision-board-grid');
    if (!grid) return;
    const images = LocalDB.get('vision_board') || [];
    if (!images.length) {
        grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px 20px;color:var(--text-secondary)"><i class="fa-solid fa-images" style="font-size:2.5rem;opacity:0.3;display:block;margin-bottom:12px"></i>Adicione imagens que representam seus sonhos!</div>';
        return;
    }
    grid.innerHTML = images.map(img => `
        <div style="position:relative;border-radius:16px;overflow:hidden;aspect-ratio:1;background:#111">
            <img src="${img.src}" style="width:100%;height:100%;object-fit:cover;display:block">
            <button onclick="deleteVisionImage('${img.id}')" style="position:absolute;top:6px;right:6px;background:rgba(0,0,0,0.6);border:none;color:white;width:28px;height:28px;border-radius:50%;cursor:pointer;font-size:0.8rem;display:flex;align-items:center;justify-content:center"><i class="fa-solid fa-trash"></i></button>
        </div>`).join('');
}
