/**
 * Nexus Mobile Phase 15 — Jarvis voz, alarmes, módulos, chat/call history
 */
(function () {
    'use strict';

    const DEFAULT_MODULE_ORDER = [
        'habits', 'finance', 'routines', 'tasks', 'videos', 'shop', 'studies',
        'goals', 'fitness', 'iot', 'journal', 'alarms', 'cleaner'
    ];

    const MODULE_LABELS = {
        habits: 'Hábitos', finance: 'Finanças', routines: 'Rotinas', tasks: 'Tarefas',
        videos: 'Vídeos', shop: 'Loja', studies: 'Estudos', goals: 'Metas',
        fitness: 'Treino', iot: 'Casa', journal: 'Diário', alarms: 'Alarmes', cleaner: 'Limpar'
    };

    let jarvisCurrentSessionId = null;
    let jarvisCallTurns = [];
    let jarvisSpeechRec = null;
    let jarvisMicMuted = false;
    let jarvisProcessingVoice = false;
    let jarvisVizAnimId = null;
    let jarvisAudioCtx = null;
    let jarvisMicAnalyser = null;
    let jarvisMicStream = null;
    let jarvisTtsAudio = null;
    let jarvisCallOverlayMinimized = false;
    let jarvisCallDebugVisible = false;
    let jarvisVizLastFrame = 0;
    let editingAlarmId = null;
    const _scheduledNativeIds = new Set();

    window.toggleAlarmDayChip = function (btn) {
        if (!btn) return;
        btn.classList.toggle('active');
    };

    window.toggleAlarmDaysRow = function () {
        const mode = document.getElementById('alarm-repeat-input')?.value;
        const row = document.getElementById('alarm-days-row');
        if (row) row.style.display = mode === 'custom' ? 'block' : 'none';
    };

    function getAlarmDaysFromForm() {
        const mode = document.getElementById('alarm-repeat-input')?.value || 'daily';
        if (mode === 'once') return [];
        if (mode === 'daily') return [0, 1, 2, 3, 4, 5, 6];
        if (mode === 'weekdays') return [1, 2, 3, 4, 5];
        const chips = document.querySelectorAll('#alarm-days-chips .alarm-day-chip.active');
        const days = Array.from(chips).map(c => parseInt(c.dataset.day, 10)).filter(n => !Number.isNaN(n));
        return days.length ? days : [0, 1, 2, 3, 4, 5, 6];
    }

    function setAlarmDaysOnForm(days, repeatMode) {
        const modeEl = document.getElementById('alarm-repeat-input');
        if (modeEl) modeEl.value = repeatMode || 'daily';
        toggleAlarmDaysRow();
        document.querySelectorAll('#alarm-days-chips .alarm-day-chip').forEach(c => {
            c.classList.toggle('active', Array.isArray(days) && days.includes(parseInt(c.dataset.day, 10)));
        });
    }

    function inferRepeatMode(days, onceOnly) {
        if (onceOnly) return 'once';
        if (!days || !days.length) return 'daily';
        const d = days.slice().sort((a, b) => a - b).join(',');
        if (d === '0,1,2,3,4,5,6') return 'daily';
        if (d === '1,2,3,4,5') return 'weekdays';
        return 'custom';
    }

    function scheduleNativeAlarm(id, title, body, triggerAtMs, isAlarm, snoozeMin, maxSnooze) {
        if (!window.AndroidNative) return;
        if (typeof AndroidNative.scheduleAlarm === 'function') {
            AndroidNative.scheduleAlarm(id, title, body, triggerAtMs, !!isAlarm, snoozeMin || 5, maxSnooze != null ? maxSnooze : 3);
        } else if (typeof AndroidNative.scheduleReminder === 'function') {
            AndroidNative.scheduleReminder(id, title, body, triggerAtMs);
        }
        _scheduledNativeIds.add(id);
    }

    function cancelAllNativeAlarms() {
        _scheduledNativeIds.forEach(id => {
            if (window.AndroidNative && typeof AndroidNative.cancelReminder === 'function') {
                AndroidNative.cancelReminder(id);
            }
        });
        _scheduledNativeIds.clear();
    }

    function getJarvisTtsProvider() {
        const prefs = JSON.parse(localStorage.getItem('nexus_ui_prefs') || '{}');
        return prefs.jarvis_tts_provider || 'web_speech';
    }

    function getJarvisTtsRate() {
        const prefs = JSON.parse(localStorage.getItem('nexus_ui_prefs') || '{}');
        return prefs.jarvis_tts_rate || 1;
    }

    function getUserSettingsRow() {
        const uid = window.currentUser?.id;
        if (!uid) return null;
        return LocalDB.get('nexus_user_settings').find(r => String(r.user_id) === String(uid)) || null;
    }

    window.saveUserSettingsJson = function (patch) {
        const uid = window.currentUser?.id;
        const prefs = JSON.parse(localStorage.getItem('nexus_ui_prefs') || '{}');
        Object.assign(prefs, patch);
        localStorage.setItem('nexus_ui_prefs', JSON.stringify(prefs));
        if (uid) {
            LocalDB.upsert('nexus_user_settings', {
                id: uid,
                user_id: uid,
                settings_json: prefs,
                updated_at: new Date().toISOString()
            });
            if (typeof backgroundSync === 'function') backgroundSync();
        }
    };

    window.setJarvisTtsProvider = function (provider) {
        saveUserSettingsJson({ jarvis_tts_provider: provider });
    };

    window.setJarvisTtsRate = function (rate) {
        saveUserSettingsJson({ jarvis_tts_rate: parseFloat(rate) || 1 });
    };

    window.buildJarvisContext = function () {
        const today = new Date().toISOString().split('T')[0];
        const habits = LocalDB.get('habits').filter(h => h.active === 1 && !h.is_deleted);
        const logs = LocalDB.get('habit_logs');
        const doneToday = logs.filter(l => l.date === today || l.completed_date === today).length;
        const tasks = LocalDB.get('tasks').filter(t => !t.done_at && !t.is_deleted);
        const goals = LocalDB.get('nexus_goals').filter(g => !g.is_deleted).slice(0, 5)
            .map(g => ({ name: g.name, progress: g.progress || 0 }));
        const schedule = buildAlarmSchedule();
        const next = schedule[0];
        const user = LocalDB.getSingle('nexus_user', 1) || {};
        return {
            habits_today: doneToday,
            habits_total: habits.length,
            pending_tasks: tasks.length,
            next_alarm: next ? next.timeLabel + ' (' + next.title + ')' : '',
            goals,
            user_name: user.name || 'Comandante'
        };
    };

    window.callJarvisChat = async function (text, history) {
        const supabaseClient = window.nexusSupabase;
        if (!supabaseClient || !isNetworkOnline()) return null;
        const context = buildJarvisContext();
        try {
            const { data, error } = await supabaseClient.functions.invoke('jarvis-chat', {
                body: { message: text, source: 'mobile', context, history: history || [] }
            });
            if (!error && data?.reply) return data.reply;
        } catch (e) {
            console.warn('jarvis-chat:', e);
        }
        try {
            const { data, error } = await supabaseClient.from('nexus_commands').insert({
                command: 'MOBILE_CHAT: ' + text,
                source: 'mobile',
                status: 'pending'
            }).select('id').single();
            if (!error && data?.id && typeof pollCommandResult === 'function') {
                return await pollCommandResult(data.id, 25000);
            }
        } catch (e) {
            console.warn('Chat queue:', e);
        }
        return null;
    };

    function persistChatMessage(role, content) {
        if (!content?.trim()) return;
        LocalDB.upsert('jarvis_chat_messages', {
            id: Date.now() + Math.floor(Math.random() * 1000),
            role,
            content: content.trim(),
            source: 'mobile'
        });
        if (typeof backgroundSync === 'function') backgroundSync();
    }

    window.loadJarvisPersistentHistory = function () {
        const hist = document.getElementById('jarvis-persistent-chat');
        if (!hist) return;
        const msgs = LocalDB.get('jarvis_chat_messages')
            .filter(m => !m.is_deleted)
            .sort((a, b) => (a.created_at || '').localeCompare(b.created_at || ''))
            .slice(-120);
        hist.innerHTML = msgs.length ? '' : '<div style="color:var(--text-secondary);font-size:0.85rem;padding:8px">Nenhuma mensagem salva ainda.</div>';
        msgs.forEach(m => {
            const el = document.createElement('div');
            el.className = 'chat-message ' + (m.role === 'user' ? 'user-msg' : 'jarvis-msg');
            el.style.cssText = m.role === 'user'
                ? 'align-self:flex-end;background:rgba(108,92,231,0.2);border:1px solid var(--accent-purple);padding:10px 15px;border-radius:12px;border-bottom-right-radius:2px;max-width:85%'
                : 'align-self:flex-start;background:rgba(0,206,201,0.15);border:1px solid var(--accent-blue);padding:10px 15px;border-radius:12px;border-bottom-left-radius:2px;max-width:85%';
            el.innerHTML = '<p style="margin:0;font-size:0.95rem;color:white">' + escapeHtml(m.content) + '</p>';
            hist.appendChild(el);
        });
        hist.scrollTop = hist.scrollHeight;
    };

    window.sendPersistentJarvisMessage = async function () {
        const input = document.getElementById('jarvis-persistent-input');
        const text = input?.value?.trim();
        if (!text) return;
        const hist = document.getElementById('jarvis-persistent-chat');
        if (hist) {
            const userEl = document.createElement('div');
            userEl.className = 'chat-message user-msg';
            userEl.style.cssText = 'align-self:flex-end;background:rgba(108,92,231,0.2);border:1px solid var(--accent-purple);padding:10px 15px;border-radius:12px;border-bottom-right-radius:2px;max-width:85%';
            userEl.innerHTML = '<p style="margin:0;font-size:0.95rem;color:white">' + escapeHtml(text) + '</p>';
            hist.appendChild(userEl);
        }
        persistChatMessage('user', text);
        if (input) input.value = '';
        const pending = document.createElement('div');
        pending.className = 'chat-message jarvis-msg';
        pending.style.cssText = 'align-self:flex-start;background:rgba(0,206,201,0.15);border:1px solid var(--accent-blue);padding:10px 15px;border-radius:12px;border-bottom-left-radius:2px;max-width:85%';
        pending.innerHTML = '<p style="margin:0;font-size:0.95rem;color:white">Processando...</p>';
        if (hist) hist.appendChild(pending);

        const history = LocalDB.get('jarvis_chat_messages').filter(m => !m.is_deleted).slice(-8)
            .map(m => ({ role: m.role, content: m.content }));
        const reply = await callJarvisChat(text, history);
        const finalReply = reply || 'Jarvis indisponível. Verifique login e conexão.';
        if (pending) pending.querySelector('p').textContent = finalReply;
        persistChatMessage('assistant', finalReply);
        if (hist) hist.scrollTop = hist.scrollHeight;
        if (typeof backgroundSync === 'function') backgroundSync();
    };

    function resetHomeChat() {
        const hist = document.getElementById('chat-history');
        if (!hist) return;
        hist.innerHTML = `<div class="chat-message jarvis-msg" style="align-self:flex-start;background:rgba(0,206,201,0.15);border:1px solid var(--accent-blue);padding:10px 15px;border-radius:12px;border-bottom-left-radius:2px;max-width:85%">
            <p style="margin:0;font-size:0.95rem;color:white">Olá! Como posso ajudar você hoje?</p></div>`;
    }

    function setJarvisCallDebug(top, bottom) {
        const topEl = document.getElementById('jarvis-call-debug-top');
        const botEl = document.getElementById('jarvis-call-debug-bottom');
        if (topEl && top != null) topEl.textContent = top;
        if (botEl && bottom != null) botEl.textContent = bottom;
    }

    function setJarvisUserCaption(text) {
        const el = document.getElementById('jarvis-call-user-caption');
        if (!el) return;
        const t = String(text || '').trim();
        el.textContent = t ? 'Você: ' + t : '';
        el.style.display = t ? 'block' : 'none';
    }

    function setJarvisAssistantCaption(text) {
        const el = document.getElementById('jarvis-call-assistant-caption');
        if (!el) return;
        const t = String(text || '').trim();
        el.textContent = t ? 'Jarvis: ' + t : '';
        el.style.display = t ? 'block' : 'none';
    }

    window.toggleJarvisCallDebug = function () {
        jarvisCallDebugVisible = !jarvisCallDebugVisible;
        const topEl = document.getElementById('jarvis-call-debug-top');
        const botEl = document.getElementById('jarvis-call-debug-bottom');
        if (topEl) topEl.style.display = jarvisCallDebugVisible ? 'block' : 'none';
        if (botEl) botEl.style.display = jarvisCallDebugVisible ? 'block' : 'none';
    };

    window.minimizeJarvisCallOverlay = function () {
        jarvisCallOverlayMinimized = true;
        const overlay = document.getElementById('jarvis-call-overlay');
        const banner = document.getElementById('jarvis-call-banner');
        if (overlay) overlay.style.display = 'none';
        if (banner) banner.style.display = 'flex';
        cancelAnimationFrame(jarvisVizAnimId);
        setJarvisCallDebug('Overlay minimizada — navegue pelo app', 'Chamada ativa em segundo plano');
    };

    window.expandJarvisCallOverlay = function () {
        if (!window.jarvisCallActive) return;
        jarvisCallOverlayMinimized = false;
        const overlay = document.getElementById('jarvis-call-overlay');
        const banner = document.getElementById('jarvis-call-banner');
        if (overlay) overlay.style.display = 'flex';
        if (banner) banner.style.display = 'none';
        startJarvisVizLoop('listening');
    };

    function setJarvisCallState(state) {
        const overlay = document.getElementById('jarvis-call-overlay');
        if (overlay) overlay.dataset.state = state || 'idle';
        const label = document.getElementById('jarvis-call-state-label');
        const map = { listening: 'Ouvindo...', thinking: 'Pensando...', speaking: 'Falando...', idle: 'Em ligação' };
        if (label) label.textContent = map[state] || map.idle;
    }

    function initJarvisVisualizerBars() {
        const wrap = document.getElementById('jarvis-viz-bars');
        if (!wrap || wrap.childElementCount) return;
        for (let i = 0; i < 10; i++) {
            const bar = document.createElement('div');
            bar.className = 'jarvis-viz-bar';
            wrap.appendChild(bar);
        }
    }

    function animateJarvisBars(level) {
        document.querySelectorAll('.jarvis-viz-bar').forEach((bar, i) => {
            const wave = 0.35 + Math.sin(Date.now() / 220 + i * 0.45) * 0.25;
            bar.style.height = (12 + Math.max(0.08, Math.min(1, level || 0.15)) * wave * 48) + 'px';
        });
    }

    function startJarvisVizLoop(mode) {
        if (jarvisCallOverlayMinimized) return;
        cancelAnimationFrame(jarvisVizAnimId);
        const tick = (ts) => {
            if (ts - jarvisVizLastFrame < 33) {
                if (window.jarvisCallActive && !jarvisCallOverlayMinimized) jarvisVizAnimId = requestAnimationFrame(tick);
                return;
            }
            jarvisVizLastFrame = ts;
            let level = 0.12;
            if (mode === 'speaking' && jarvisTtsAudio && !jarvisTtsAudio.paused) level = 0.55 + Math.random() * 0.35;
            else if (mode === 'listening' && jarvisMicAnalyser) {
                const data = new Uint8Array(jarvisMicAnalyser.frequencyBinCount);
                jarvisMicAnalyser.getByteFrequencyData(data);
                let sum = 0;
                for (let i = 0; i < data.length; i++) sum += data[i];
                level = (sum / data.length / 255) * 1.2;
            } else if (mode === 'thinking') level = 0.18 + Math.sin(Date.now() / 280) * 0.08;
            animateJarvisBars(level);
            if (window.jarvisCallActive && !jarvisCallOverlayMinimized) jarvisVizAnimId = requestAnimationFrame(tick);
        };
        jarvisVizAnimId = requestAnimationFrame(tick);
    }

    async function startJarvisMicAnalyser() {
        if (!navigator.mediaDevices?.getUserMedia) return;
        try {
            jarvisMicStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
            jarvisAudioCtx = jarvisAudioCtx || new (window.AudioContext || window.webkitAudioContext)();
            const src = jarvisAudioCtx.createMediaStreamSource(jarvisMicStream);
            jarvisMicAnalyser = jarvisAudioCtx.createAnalyser();
            jarvisMicAnalyser.fftSize = 256;
            src.connect(jarvisMicAnalyser);
        } catch (e) {
            console.warn('Mic analyser:', e);
        }
    }

    function stopJarvisMicAnalyser() {
        if (jarvisMicStream) {
            jarvisMicStream.getTracks().forEach(t => t.stop());
            jarvisMicStream = null;
        }
        jarvisMicAnalyser = null;
    }

    async function speakJarvis(text, onEnd) {
        const clean = String(text || '').trim();
        if (!clean) { if (onEnd) onEnd(); return; }
        setJarvisCallState('speaking');
        setJarvisCallDebug('TTS: iniciando', clean.slice(0, 120));
        setJarvisAssistantCaption(clean);
        if (!jarvisCallOverlayMinimized) startJarvisVizLoop('speaking');

        const tryEdgeTts = async () => {
            if (!window.nexusSupabase || !isNetworkOnline()) return false;
            try {
                const { data, error } = await window.nexusSupabase.functions.invoke('jarvis-tts', {
                    body: { text: clean.slice(0, 4000) }
                });
                if (!error && data && data.audio_base64 && !data.fallback) {
                    setJarvisCallDebug('TTS: nuvem OK', clean.slice(0, 120));
                    jarvisTtsAudio = new Audio('data:' + (data.mime || 'audio/wav') + ';base64,' + data.audio_base64);
                    jarvisTtsAudio.onended = () => { jarvisTtsAudio = null; if (onEnd) onEnd(); };
                    jarvisTtsAudio.onerror = () => { jarvisTtsAudio = null; if (onEnd) onEnd(); };
                    await jarvisTtsAudio.play();
                    return true;
                }
                setJarvisCallDebug('TTS: nuvem indisponível', error?.message || 'fallback');
            } catch (e) {
                console.warn('jarvis-tts:', e);
                setJarvisCallDebug('TTS: erro nuvem', String(e.message || e));
            }
            return false;
        };

        const tryNativeTts = () => new Promise((resolve) => {
            if (!window.AndroidNative || typeof AndroidNative.speakText !== 'function') {
                resolve(false);
                return;
            }
            let done = false;
            const finish = (ok) => {
                if (done) return;
                done = true;
                window.__onJarvisTtsEnd = null;
                resolve(ok);
            };
            window.__onJarvisTtsEnd = () => finish(true);
            try {
                const rate = getJarvisTtsRate();
                if (typeof AndroidNative.speakTextWithRate === 'function') {
                    AndroidNative.speakTextWithRate(clean, rate);
                } else {
                    AndroidNative.speakText(clean);
                }
                setJarvisCallDebug('TTS: Android nativo', clean.slice(0, 120));
                setTimeout(() => finish(true), Math.min(45000, Math.max(3000, clean.length * 90)));
            } catch (e) {
                console.warn('native TTS:', e);
                setJarvisCallDebug('TTS: erro nativo', String(e.message || e));
                finish(false);
            }
        });

        const useGeminiSetting = getJarvisTtsProvider() === 'gemini';
        const webViewNeedsCloud = window.AndroidNative || !('speechSynthesis' in window);
        if (useGeminiSetting || webViewNeedsCloud) {
            const ok = await tryEdgeTts();
            if (ok) return;
        }
        if (window.AndroidNative && typeof AndroidNative.speakText === 'function') {
            const nativeOk = await tryNativeTts();
            if (nativeOk) { if (onEnd) onEnd(); return; }
        }
        speakJarvisWeb(clean, onEnd);
    }

    function speakJarvisWeb(text, onEnd) {
        // AndroidNative TTS fallback for WebView (no speechSynthesis)
        if (!('speechSynthesis' in window)) {
            try {
                if (window.AndroidNative && typeof AndroidNative.speakText === 'function') {
                    setJarvisCallDebug('TTS: Android native TTS', text.slice(0, 120));
                    AndroidNative.speakText(text, 'pt-BR');
                    setTimeout(() => { if (onEnd) onEnd(); }, Math.max(1500, text.length * 55));
                    return;
                }
            } catch(e) {}
            setJarvisCallDebug('TTS: sem speechSynthesis', text.slice(0, 120));
            if (onEnd) onEnd();
            return;
        }
        try { speechSynthesis.cancel(); } catch(e) {}
        const u = new SpeechSynthesisUtterance(text);
        u.lang = 'pt-BR';
        u.rate = getJarvisTtsRate();
        u.onstart = () => setJarvisCallDebug('TTS: voz sistema', text.slice(0, 120));
        u.onend = () => { if (onEnd) onEnd(); };
        u.onerror = (ev) => { setJarvisCallDebug('TTS: erro voz', ev.error || 'unknown'); if (onEnd) onEnd(); };
        speechSynthesis.speak(u);
    }

    function saveCallTurn(role, content) {
        if (!content?.trim()) return;
        jarvisCallTurns.push({ role, content: content.trim(), at: new Date().toISOString() });
        if (jarvisCurrentSessionId) {
            LocalDB.upsert('jarvis_call_turns', {
                id: Date.now() + Math.floor(Math.random() * 1000),
                session_id: jarvisCurrentSessionId,
                role,
                content: content.trim(),
                created_at: new Date().toISOString()
            });
        }
    }

    function startCallSession() {
        jarvisCurrentSessionId = Date.now();
        jarvisCallTurns = [];
        LocalDB.upsert('jarvis_call_sessions', {
            id: jarvisCurrentSessionId,
            started_at: new Date().toISOString(),
            source: 'mobile'
        });
        if (typeof backgroundSync === 'function') backgroundSync();
    }

    function endCallSession() {
        if (!jarvisCurrentSessionId) return;
        const started = window.jarvisCallStartedAt || Date.now();
        const duration = Math.floor((Date.now() - started) / 1000);
        const firstUser = jarvisCallTurns.find(t => t.role === 'user');
        LocalDB.upsert('jarvis_call_sessions', {
            id: jarvisCurrentSessionId,
            started_at: new Date(started).toISOString(),
            ended_at: new Date().toISOString(),
            duration_sec: duration,
            summary: firstUser ? firstUser.content.slice(0, 120) : 'Ligação Jarvis',
            source: 'mobile'
        });
        jarvisCurrentSessionId = null;
        jarvisCallTurns = [];
        if (typeof backgroundSync === 'function') backgroundSync();
        loadJarvisCallHistory();
    }

    function stopJarvisSpeechRecognition() {
        try {
            if (jarvisSpeechRec) {
                jarvisSpeechRec.onend = null;
                jarvisSpeechRec.stop();
            }
        } catch (_) {}
        jarvisSpeechRec = null;
    }

    function startJarvisSpeechRecognition() {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR || jarvisMicMuted || !window.jarvisCallActive) return;
        stopJarvisSpeechRecognition();
        jarvisSpeechRec = new SR();
        jarvisSpeechRec.lang = 'pt-BR';
        jarvisSpeechRec.continuous = false;
        jarvisSpeechRec.interimResults = false;

        jarvisSpeechRec.onresult = async (ev) => {
            const text = ev.results?.[0]?.[0]?.transcript?.trim();
            if (!text || jarvisProcessingVoice) return;
            jarvisProcessingVoice = true;
            setJarvisCallState('thinking');
            setJarvisCallDebug('STT: ' + text, 'Chamando Jarvis...');
            setJarvisUserCaption(text);
            setJarvisAssistantCaption('');
            stopJarvisMicAnalyser();
            if (!jarvisCallOverlayMinimized) startJarvisVizLoop('thinking');
            saveCallTurn('user', text);

            const history = jarvisCallTurns.slice(-8).map(t => ({ role: t.role, content: t.content }));
            const reply = await callJarvisChat(text, history);
            const finalReply = reply || 'Não consegui processar agora. Verifique Wi-Fi e login Google.';
            setJarvisCallDebug('Resposta recebida', finalReply.slice(0, 160));
            setJarvisAssistantCaption(finalReply);
            saveCallTurn('assistant', finalReply);

            speakJarvis(finalReply, () => {
                jarvisProcessingVoice = false;
                if (window.jarvisCallActive && !jarvisMicMuted) {
                    startJarvisMicAnalyser().then(() => {
                        if (window.jarvisCallActive && !jarvisMicMuted) startJarvisSpeechRecognition();
                    });
                }
            });
        };

        jarvisSpeechRec.onerror = (ev) => {
            if (ev.error === 'no-speech' && window.jarvisCallActive && !jarvisMicMuted) {
                setTimeout(startJarvisSpeechRecognition, 400);
            }
        };

        jarvisSpeechRec.onend = () => {
            if (window.jarvisCallActive && !jarvisMicMuted && !jarvisProcessingVoice) {
                setTimeout(startJarvisSpeechRecognition, 300);
            }
        };

        try {
            setJarvisCallState('listening');
            startJarvisVizLoop('listening');
            jarvisSpeechRec.start();
        } catch (e) {
            console.warn('STT start:', e);
        }
    }

    window.toggleJarvisCallMic = function () {
        jarvisMicMuted = !jarvisMicMuted;
        const btn = document.getElementById('jarvis-call-mute-btn');
        if (btn) {
            btn.innerHTML = jarvisMicMuted
                ? '<i class="fa-solid fa-microphone-slash"></i>'
                : '<i class="fa-solid fa-microphone"></i>';
        }
        if (jarvisMicMuted) stopJarvisSpeechRecognition();
        else if (window.jarvisCallActive) startJarvisSpeechRecognition();
    };

    window.toggleJarvisCall = async function () {
        if (window.jarvisCallActive) {
            window.endJarvisCall();
            return;
        }
        if (!requireWifiForJarvis('ligação')) return;
        if (!window.nexusSupabase) {
            showToast('Entre com Google nas configurações para usar o Jarvis.');
            return;
        }
        window.jarvisCallActive = true;
        jarvisCallOverlayMinimized = false;
        jarvisMicMuted = false;
        window.jarvisCallStartedAt = Date.now();
        initJarvisVisualizerBars();
        startCallSession();

        const overlay = document.getElementById('jarvis-call-overlay');
        const banner = document.getElementById('jarvis-call-banner');
        const fab = document.getElementById('nexus-ai-fab');
        if (overlay) overlay.style.display = 'flex';
        if (banner) banner.style.display = 'none';
        setJarvisCallDebug('Ligação iniciada', isWifiConnected() ? 'Wi-Fi OK' : 'Sem Wi-Fi');
        if (fab) fab.classList.add('active');
        if (typeof updateJarvisCallTimer === 'function') updateJarvisCallTimer();
        window.jarvisCallTimerId = setInterval(updateJarvisCallTimer, 1000);

        if (window.AndroidNative && typeof window.AndroidNative.startJarvisCall === 'function') {
            window.AndroidNative.startJarvisCall();
        }

        await startJarvisMicAnalyser();
        speakJarvis('Olá! Jarvis na linha. Pode falar.', () => {
            if (window.jarvisCallActive) startJarvisSpeechRecognition();
        });
    };

    window.endJarvisCall = function () {
        window.jarvisCallActive = false;
        jarvisCallOverlayMinimized = false;
        jarvisProcessingVoice = false;
        if (window.speechSynthesis) speechSynthesis.cancel();
        if (jarvisTtsAudio) { jarvisTtsAudio.pause(); jarvisTtsAudio = null; }
        stopJarvisSpeechRecognition();
        stopJarvisMicAnalyser();
        cancelAnimationFrame(jarvisVizAnimId);
        endCallSession();

        window.jarvisCallStartedAt = 0;
        clearInterval(window.jarvisCallTimerId);
        window.jarvisCallTimerId = null;

        const overlay = document.getElementById('jarvis-call-overlay');
        const banner = document.getElementById('jarvis-call-banner');
        const fab = document.getElementById('nexus-ai-fab');
        const timer = document.getElementById('jarvis-call-timer');
        if (overlay) overlay.style.display = 'none';
        if (banner) banner.style.display = 'none';
        if (fab) fab.classList.remove('active');
        if (timer) timer.textContent = '00:00';
        setJarvisUserCaption('');
        setJarvisAssistantCaption('');

        if (window.AndroidNative && typeof window.AndroidNative.stopJarvisCall === 'function') {
            window.AndroidNative.stopJarvisCall();
        }
    };

    window.loadJarvisCallHistory = function () {
        const list = document.getElementById('jarvis-calls-list');
        if (!list) return;
        const sessions = LocalDB.get('jarvis_call_sessions')
            .filter(s => !s.is_deleted && s.ended_at)
            .sort((a, b) => (b.started_at || '').localeCompare(a.started_at || ''));
        if (!sessions.length) {
            list.innerHTML = '<div style="text-align:center;color:var(--text-secondary);padding:24px">Nenhuma ligação registrada.</div>';
            return;
        }
        list.innerHTML = sessions.map(s => {
            const d = new Date(s.started_at);
            const dur = s.duration_sec ? Math.floor(s.duration_sec / 60) + ' min' : '—';
            return '<div class="list-item glass" style="padding:14px;margin-bottom:10px" onclick="openJarvisCallDetail(' + s.id + ')">' +
                '<div class="item-title">' + escapeHtml(s.summary || 'Ligação Jarvis') + '</div>' +
                '<div style="font-size:0.8rem;color:var(--text-secondary);margin-top:4px">' +
                d.toLocaleString('pt-BR') + ' · ' + dur + '</div></div>';
        }).join('');
    };

    window.openJarvisCallDetail = function (sessionId) {
        const modal = document.getElementById('jarvis-call-detail-modal');
        const body = document.getElementById('jarvis-call-detail-body');
        if (!modal || !body) return;
        const turns = LocalDB.get('jarvis_call_turns')
            .filter(t => String(t.session_id) === String(sessionId) && !t.is_deleted)
            .sort((a, b) => (a.created_at || '').localeCompare(b.created_at || ''));
        body.innerHTML = turns.map(t =>
            '<div class="chat-message ' + (t.role === 'user' ? 'user-msg' : 'jarvis-msg') + '" style="margin-bottom:8px;padding:10px;border-radius:10px">' +
            escapeHtml(t.content) + '</div>'
        ).join('') || '<p style="color:var(--text-secondary)">Sem transcrição.</p>';
        modal.style.display = 'flex';
    };

    window.closeJarvisCallDetail = function () {
        const modal = document.getElementById('jarvis-call-detail-modal');
        if (modal) modal.style.display = 'none';
    };

    window.deleteJarvisCallSession = function (sessionId) {
        LocalDB.deleteRow('jarvis_call_sessions', sessionId);
        LocalDB.get('jarvis_call_turns').filter(t => String(t.session_id) === String(sessionId))
            .forEach(t => LocalDB.deleteRow('jarvis_call_turns', t.id));
        closeJarvisCallDetail();
        loadJarvisCallHistory();
        if (typeof backgroundSync === 'function') backgroundSync();
    };

    function parseDaysOfWeek(raw, fallback) {
        if (Array.isArray(raw)) return raw;
        try { return JSON.parse(raw); } catch (_) { return fallback; }
    }

    function habitScheduledOnDay(habit, dayIndex) {
        const days = parseDaysOfWeek(habit.days_of_week, [1, 2, 3, 4, 5]);
        return days.includes(dayIndex);
    }

    function nextTriggerForTime(timeStr, daysOfWeek) {
        const [hh, mm] = timeStr.substring(0, 5).split(':').map(Number);
        if (Number.isNaN(hh) || Number.isNaN(mm)) return null;
        const now = new Date();
        for (let offset = 0; offset < 8; offset++) {
            const d = new Date(now);
            d.setDate(d.getDate() + offset);
            const dow = d.getDay();
            if (!daysOfWeek.includes(dow)) continue;
            d.setHours(hh, mm, 0, 0);
            if (d.getTime() > now.getTime()) {
                return { triggerAtMs: d.getTime(), label: d.toLocaleString('pt-BR', { weekday: 'short', hour: '2-digit', minute: '2-digit' }) };
            }
        }
        return null;
    }

    window.buildAlarmSchedule = function () {
        const items = [];
        const habits = LocalDB.get('habits').filter(h => h.active === 1 && !h.is_deleted);
        habits.forEach(h => {
            const time = h.alarm_time || h.target_time;
            if (!time) return;
            const days = parseDaysOfWeek(h.days_of_week, [0, 1, 2, 3, 4, 5, 6]);
            const next = nextTriggerForTime(time, days);
            if (!next) return;
            items.push({
                key: 'habit-' + h.id,
                sourceType: 'habit',
                sourceId: h.id,
                title: h.name,
                body: 'Lembrete de hábito',
                time: time.substring(0, 5),
                timeLabel: next.label,
                triggerAtMs: next.triggerAtMs,
                nativeId: 200000 + (Math.abs(Number(h.id)) % 50000)
            });
        });

        const tasks = LocalDB.get('tasks').filter(t => !t.is_deleted && t.notify_enabled && t.notify_at && !t.done_at);
        tasks.forEach(t => {
            const ms = new Date(t.notify_at).getTime();
            if (ms <= Date.now()) return;
            items.push({
                key: 'task-' + t.id,
                sourceType: 'task',
                sourceId: t.id,
                title: t.name || t.title || 'Tarefa',
                body: t.description || 'Lembrete de tarefa',
                time: new Date(t.notify_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
                timeLabel: new Date(t.notify_at).toLocaleString('pt-BR'),
                triggerAtMs: ms,
                nativeId: parseInt(String(t.id).replace(/\D/g, '').slice(-7) || '0', 10) || Math.abs(Number(t.id) % 100000)
            });
        });

        LocalDB.get('nexus_alarms').filter(a => !a.is_deleted && a.enabled !== 0).forEach(a => {
            const onceOnly = a.once_only === 1 || a.repeat_mode === 'once';
            const days = onceOnly ? [new Date().getDay()] : parseDaysOfWeek(a.days_of_week, [0, 1, 2, 3, 4, 5, 6]);
            const next = nextTriggerForTime(a.alarm_time, days);
            if (!next) return;
            items.push({
                key: 'alarm-' + a.id,
                sourceType: 'standalone',
                sourceId: a.id,
                title: a.title,
                body: a.body || 'Alarme',
                time: a.alarm_time.substring(0, 5),
                timeLabel: next.label + (onceOnly ? ' · uma vez' : ''),
                triggerAtMs: next.triggerAtMs,
                nativeId: Math.abs(Number(a.id)) % 900000 + 300000,
                snoozeMinutes: a.snooze_minutes || 5,
                maxSnooze: a.max_snooze != null ? a.max_snooze : 3,
                isAlarm: true
            });
        });

        return items.sort((a, b) => a.triggerAtMs - b.triggerAtMs);
    };

    window.loadAlarms = function () {
        const list = document.getElementById('alarms-list');
        if (!list) return;
        const items = buildAlarmSchedule();
        if (!items.length) {
            list.innerHTML = '<div style="text-align:center;color:var(--text-secondary);padding:24px">Nenhum alarme agendado.</div>';
            return;
        }
        list.innerHTML = items.map(it => {
            const badge = it.sourceType === 'habit' ? 'Hábito' : it.sourceType === 'task' ? 'Tarefa' : 'Alarme';
            return '<div class="list-item glass" style="padding:14px;margin-bottom:10px;display:flex;align-items:center;gap:10px">' +
                '<div style="flex:1"><div class="item-title">' + escapeHtml(it.title) + '</div>' +
                '<div style="font-size:0.8rem;color:var(--text-secondary)">' + escapeHtml(it.timeLabel) + ' · ' + badge + '</div></div>' +
                '<button class="icon-btn" onclick="openAlarmForm(' + (it.sourceType === 'standalone' ? it.sourceId : 'null') + ')" aria-label="Editar"><i class="fa-solid fa-pen"></i></button>' +
                '<button class="icon-btn" onclick="deleteAlarmItem(\'' + it.sourceType + '\',' + it.sourceId + ')" aria-label="Excluir"><i class="fa-solid fa-trash"></i></button></div>';
        }).join('');
    };

    window.deleteAlarmItem = function (sourceType, sourceId) {
        if (sourceType === 'habit') {
            LocalDB.patchRow('habits', sourceId, { alarm_time: null, target_time: null });
            if (typeof loadHabits === 'function') loadHabits();
        } else if (sourceType === 'task') {
            LocalDB.patchRow('tasks', sourceId, { notify_enabled: 0, notify_at: null });
            if (typeof loadTasks === 'function') loadTasks();
        } else {
            LocalDB.deleteRow('nexus_alarms', sourceId);
        }
        rescheduleAllAlarms();
        loadAlarms();
        if (typeof backgroundSync === 'function') backgroundSync();
    };

    window.openAlarmForm = function (alarmId) {
        editingAlarmId = alarmId || null;
        const modal = document.getElementById('alarm-form-modal');
        const a = alarmId ? LocalDB.getSingle('nexus_alarms', alarmId) : null;
        document.getElementById('alarm-form-title').textContent = a ? 'Editar alarme' : 'Novo alarme';
        document.getElementById('alarm-title-input').value = a?.title || '';
        document.getElementById('alarm-body-input').value = a?.body || '';
        document.getElementById('alarm-time-input').value = a?.alarm_time?.substring(0, 5) || '07:00';
        document.getElementById('alarm-snooze-input').value = a?.snooze_minutes || 5;
        document.getElementById('alarm-max-snooze-input').value = a?.max_snooze != null ? a.max_snooze : 3;
        const days = parseDaysOfWeek(a?.days_of_week, [0, 1, 2, 3, 4, 5, 6]);
        setAlarmDaysOnForm(days, inferRepeatMode(days, a?.once_only === 1 || a?.repeat_mode === 'once'));
        if (modal) modal.style.display = 'flex';
    };

    window.closeAlarmForm = function () {
        editingAlarmId = null;
        const modal = document.getElementById('alarm-form-modal');
        if (modal) modal.style.display = 'none';
    };

    window.saveAlarmForm = function () {
        const title = document.getElementById('alarm-title-input').value.trim();
        const body = document.getElementById('alarm-body-input').value.trim();
        const time = document.getElementById('alarm-time-input').value;
        const repeatMode = document.getElementById('alarm-repeat-input')?.value || 'daily';
        const snoozeMinutes = parseInt(document.getElementById('alarm-snooze-input')?.value, 10) || 5;
        const maxSnooze = parseInt(document.getElementById('alarm-max-snooze-input')?.value, 10);
        const days = getAlarmDaysFromForm();
        if (!title || !time) { showToast('Título e horário são obrigatórios.'); return; }
        LocalDB.upsert('nexus_alarms', {
            id: editingAlarmId || Date.now(),
            title,
            body,
            alarm_time: time,
            days_of_week: repeatMode === 'once' ? [new Date().getDay()] : days,
            repeat_mode: repeatMode,
            once_only: repeatMode === 'once' ? 1 : 0,
            snooze_minutes: snoozeMinutes,
            max_snooze: Number.isNaN(maxSnooze) ? 3 : maxSnooze,
            enabled: 1,
            source_type: 'standalone'
        });
        closeAlarmForm();
        rescheduleAllAlarms();
        loadAlarms();
        if (typeof backgroundSync === 'function') backgroundSync();
        showToast('Alarme salvo e agendado.');
    };

    window.rescheduleAllAlarms = function () {
        cancelAllNativeAlarms();
        if (typeof syncHabitReminders === 'function') syncHabitReminders();
        if (typeof syncTaskReminders === 'function') syncTaskReminders();
        buildAlarmSchedule().forEach(it => {
            scheduleNativeAlarm(
                it.nativeId,
                it.title,
                it.body,
                it.triggerAtMs,
                it.isAlarm || it.sourceType === 'standalone',
                it.snoozeMinutes || 5,
                it.maxSnooze != null ? it.maxSnooze : 3
            );
        });
    };

    function getModuleOrder() {
        const prefs = JSON.parse(localStorage.getItem('nexus_ui_prefs') || '{}');
        const order = prefs.moduleOrder;
        if (Array.isArray(order) && order.length) return order;
        return DEFAULT_MODULE_ORDER.slice();
    }

    function reorderDomList(container, selector, order, attr) {
        if (!container) return;
        const items = Array.from(container.querySelectorAll(selector));
        order.forEach(key => {
            const el = items.find(n => n.getAttribute(attr) === 'view-' + key);
            if (el) container.appendChild(el);
        });
    }

    window.applyModuleOrderAndVisibility = function () {
        const prefs = JSON.parse(localStorage.getItem('nexus_ui_prefs') || '{}');
        const order = getModuleOrder();
        const nav = document.querySelector('.bottom-nav');
        reorderDomList(nav, '.nav-item', order, 'data-target');

        order.forEach(mod => {
            const isEnabled = prefs[mod] !== false;
            const cb = document.getElementById('toggle-' + mod);
            if (cb) cb.checked = isEnabled;
            const navItem = document.querySelector('.nav-item[data-target="view-' + mod + '"]');
            if (navItem) navItem.style.display = isEnabled ? 'flex' : 'none';
        });

        const settingsList = document.getElementById('module-settings-list');
        if (settingsList) {
            order.forEach(mod => {
                const row = settingsList.querySelector('[data-module="' + mod + '"]');
                if (row) settingsList.appendChild(row);
            });
        }
    };

    window.initModuleDragSort = function () {
        const list = document.getElementById('module-settings-list');
        if (!list || list.dataset.sortInit) return;
        list.dataset.sortInit = '1';
        let dragRow = null;
        let placeholder = null;
        let startY = 0;
        let rowRect = null;

        const saveOrder = () => {
            const order = Array.from(list.querySelectorAll('.module-sort-row')).map(r => r.dataset.module);
            const prefs = JSON.parse(localStorage.getItem('nexus_ui_prefs') || '{}');
            prefs.moduleOrder = order;
            localStorage.setItem('nexus_ui_prefs', JSON.stringify(prefs));
            saveUserSettingsJson({ moduleOrder: order });
            applyModuleOrderAndVisibility();
        };

        const clearDrag = () => {
            if (dragRow) {
                dragRow.classList.remove('dragging');
                dragRow.style.transform = '';
                dragRow.style.position = '';
                dragRow.style.width = '';
                dragRow.style.zIndex = '';
                dragRow.style.top = '';
                dragRow.style.left = '';
            }
            if (placeholder?.parentNode) placeholder.parentNode.removeChild(placeholder);
            dragRow = null;
            placeholder = null;
        };

        list.querySelectorAll('.module-sort-row').forEach(row => {
            const handle = row.querySelector('.module-drag-handle');
            if (!handle) return;
            row.querySelectorAll('span:not(.module-drag-handle)').forEach(label => {
                label.style.userSelect = 'none';
                label.style.webkitUserSelect = 'none';
            });

            const onMove = (clientY) => {
                if (!dragRow || !placeholder) return;
                const dy = clientY - startY;
                dragRow.style.transform = `translateY(${dy}px)`;
                const rows = Array.from(list.querySelectorAll('.module-sort-row')).filter(r => r !== dragRow);
                let inserted = false;
                for (const over of rows) {
                    const rect = over.getBoundingClientRect();
                    const mid = rect.top + rect.height / 2;
                    if (clientY < mid) {
                        list.insertBefore(placeholder, over);
                        inserted = true;
                        break;
                    }
                }
                if (!inserted) list.appendChild(placeholder);
            };

            const onStart = (e) => {
                e.preventDefault();
                dragRow = row;
                rowRect = row.getBoundingClientRect();
                startY = e.touches ? e.touches[0].clientY : e.clientY;
                placeholder = document.createElement('div');
                placeholder.className = 'module-sort-placeholder';
                placeholder.style.height = rowRect.height + 'px';
                list.insertBefore(placeholder, row);
                row.classList.add('dragging');
                row.style.position = 'relative';
                row.style.zIndex = '10';
                row.style.width = rowRect.width + 'px';
            };

            const onEnd = () => {
                if (!dragRow || !placeholder) return;
                list.insertBefore(dragRow, placeholder);
                clearDrag();
                saveOrder();
            };

            handle.addEventListener('touchstart', onStart, { passive: false });
            handle.addEventListener('touchmove', (e) => {
                if (!dragRow) return;
                e.preventDefault();
                onMove(e.touches[0].clientY);
            }, { passive: false });
            handle.addEventListener('touchend', onEnd);
            handle.addEventListener('mousedown', onStart);
            document.addEventListener('mousemove', (e) => { if (dragRow) onMove(e.clientY); });
            document.addEventListener('mouseup', onEnd);
        });
    };

    const _toggleModule = window.toggleModule;
    window.toggleModule = function (moduleId) {
        if (typeof _toggleModule === 'function') _toggleModule(moduleId);
        else {
            const isChecked = document.getElementById('toggle-' + moduleId).checked;
            const prefs = JSON.parse(localStorage.getItem('nexus_ui_prefs') || '{}');
            prefs[moduleId] = isChecked;
            localStorage.setItem('nexus_ui_prefs', JSON.stringify(prefs));
        }
        applyModuleOrderAndVisibility();
    };

    window.syncHabitRemindersP15 = function () {
        if (typeof notificationsEnabled === 'function' && !notificationsEnabled()) return;
        const habits = LocalDB.get('habits').filter(h => h.active === 1 && !h.is_deleted);
        const logs = LocalDB.get('habit_logs') || [];
        const td = new Date().toISOString().split('T')[0];
        const dow = new Date().getDay();
        habits.forEach(h => {
            const time = h.alarm_time || h.target_time;
            const rid = 200000 + (Math.abs(Number(h.id)) % 50000);
            if (!time || !habitScheduledOnDay(h, dow)) {
                if (window.AndroidNative) AndroidNative.cancelReminder(rid);
                return;
            }
            const doneToday = logs.some(l => String(l.habit_id) === String(h.id) && (l.date === td || l.completed_date === td));
            if (doneToday) {
                if (window.AndroidNative) AndroidNative.cancelReminder(rid);
                return;
            }
            const days = parseDaysOfWeek(h.days_of_week, [0, 1, 2, 3, 4, 5, 6]);
            const next = nextTriggerForTime(time, days);
            if (next && window.AndroidNative && typeof AndroidNative.scheduleReminder === 'function') {
                AndroidNative.scheduleReminder(rid, 'Hora do Hábito', h.name, next.triggerAtMs);
            }
        });
    };

    if (typeof window.syncHabitReminders === 'function') {
        window.syncHabitReminders = syncHabitRemindersP15;
    }

    document.addEventListener('DOMContentLoaded', () => {
        resetHomeChat();
        loadJarvisPersistentHistory();
        loadJarvisCallHistory();
        loadAlarms();
        applyModuleOrderAndVisibility();
        initModuleDragSort();
        if (typeof updateJarvisFabState === 'function') updateJarvisFabState();

        const ttsSel = document.getElementById('cfg-jarvis-tts');
        if (ttsSel) {
            ttsSel.value = getJarvisTtsProvider();
            ttsSel.onchange = () => setJarvisTtsProvider(ttsSel.value);
        }
        const ttsRate = document.getElementById('cfg-jarvis-tts-rate');
        if (ttsRate) {
            ttsRate.value = getJarvisTtsRate();
            ttsRate.onchange = () => setJarvisTtsRate(ttsRate.value);
        }

        if (window.nexusSupabase && typeof backgroundSync === 'function') {
            setTimeout(backgroundSync, 1500);
        }
        setTimeout(rescheduleAllAlarms, 2000);
    });
})();
