// ----------------------------------------------------
// Jarvis cloud bridge + browser speech fallback
// ----------------------------------------------------
// This module makes the restored mobile baseline honest about Jarvis:
// 1) Gemini responses come from Supabase Edge Functions when available.
// 2) TTS uses the jarvis-tts Edge Function when it returns audio.
// 3) If cloud TTS is unavailable, browser speechSynthesis is used explicitly.

async function getSupabaseAccessToken() {
    if (!window.nexusSupabase?.auth?.getSession) return null;
    try {
        const { data } = await window.nexusSupabase.auth.getSession();
        return data?.session?.access_token || null;
    } catch (_) {
        return null;
    }
}

async function invokeJarvisFunction(name, payload) {
    if (!window.nexusSupabase?.functions?.invoke) {
        throw new Error('Supabase Functions indisponível.');
    }
    const { data, error } = await window.nexusSupabase.functions.invoke(name, {
        body: payload,
    });
    if (error) throw error;
    return data || {};
}

function buildJarvisContext() {
    const today = new Date().toISOString().split('T')[0];
    const habits = LocalDB.get('habits').filter(h => h.active === 1 && !h.is_deleted);
    const habitLogs = LocalDB.get('habit_logs').filter(l => (l.date || l.completed_at || '').startsWith(today));
    const tasks = LocalDB.get('tasks').filter(t => !t.done_at && !t.is_deleted);
    const flashcards = LocalDB.get('flashcards').filter(c => !c.is_deleted);
    const dueFlashcards = flashcards.filter(c => !c.next_review || c.next_review <= new Date().toISOString());
    const user = LocalDB.getSingle('nexus_user', 1) || LocalDB.get('user_stats') || {};
    return {
        today,
        user: {
            level: user.level || 1,
            xp: user.xp || 0,
            points: user.points || 0,
        },
        stats: {
            habits_total: habits.length,
            habits_done_today: habitLogs.length,
            tasks_pending: tasks.length,
            flashcards_total: flashcards.length,
            flashcards_due: dueFlashcards.length,
        },
        recent_tasks: tasks.slice(0, 8).map(t => ({ title: t.title || t.name || '', priority: t.priority || 'normal' })),
        recent_habits: habits.slice(0, 8).map(h => ({ name: h.name || '', streak: h.current_streak || 0 })),
    };
}

window.buildJarvisContext = window.buildJarvisContext || buildJarvisContext;

window.callJarvisChat = window.callJarvisChat || async function(message, history) {
    const data = await invokeJarvisFunction('jarvis-chat', {
        message,
        history: history || [],
        source: 'mobile',
        context: buildJarvisContext(),
    });
    if (data.error) throw new Error(data.error);
    return data.reply || data.message || '';
};

window.speakJarvisText = window.speakJarvisText || async function(text) {
    const clean = String(text || '').trim();
    if (!clean) return false;

    try {
        const data = await invokeJarvisFunction('jarvis-tts', {
            text: clean,
            voice: localStorage.getItem('nexus_jarvis_voice') || 'Kore',
        });
        if (data?.audio_base64) {
            const audio = new Audio(`data:${data.mime || 'audio/wav'};base64,${data.audio_base64}`);
            await audio.play();
            return true;
        }
    } catch (e) {
        console.warn('Jarvis cloud TTS unavailable, using speechSynthesis fallback:', e);
    }

    if ('speechSynthesis' in window && 'SpeechSynthesisUtterance' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(clean);
        utterance.lang = 'pt-BR';
        utterance.rate = 1;
        utterance.pitch = 1;
        window.speechSynthesis.speak(utterance);
        return true;
    }
    return false;
};

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

    if (!isWifiConnected()) {
        if (pending) pending.querySelector('p').textContent = 'Sem Wi-Fi. Comandos locais: "criar hábito X", "criar tarefa Y", "quantos cards", "briefing".';
        return;
    }

    const history = [];
    document.querySelectorAll('#chat-history .chat-message').forEach(el => {
        const role = el.classList.contains('user-msg') ? 'user' : 'assistant';
        const content = el.querySelector('p')?.textContent?.trim();
        if (content && content !== 'Processando...') history.push({ role, content });
    });

    try {
        const reply = await window.callJarvisChat(text, history.slice(-8));
        if (reply) {
            if (pending) pending.querySelector('p').textContent = reply;
            await window.speakJarvisText(reply);
            backgroundSync();
            return;
        }
    } catch (e) {
        console.warn('Jarvis Edge chat failed, falling back to desktop command queue:', e);
    }

    if (window.nexusSupabase && isNetworkOnline()) {
        try {
            const { data, error } = await window.nexusSupabase.from('nexus_commands').insert({
                command: 'MOBILE_CHAT: ' + text,
                source: 'mobile',
                status: 'pending'
            }).select('id').single();
            if (!error && data?.id) {
                const reply = await pollCommandResult(data.id, 25000);
                if (reply) {
                    if (pending) pending.querySelector('p').textContent = reply;
                    await window.speakJarvisText(reply);
                    backgroundSync();
                    return;
                }
            }
        } catch (e) {
            console.warn('Chat queue error:', e);
        }
    }

    if (pending) pending.querySelector('p').textContent = 'Jarvis indisponível. Verifique login Google, Wi-Fi, Supabase Functions e GEMINI_API_KEY.';
};

window.runJarvisAction = async function() {
    const prompt = document.getElementById('jarvis-prompt')?.value?.trim();
    if (!prompt) {
        alert('Por favor, insira um texto ou URL.');
        return;
    }
    if (!requireWifiForJarvis('IA nas notas')) return;

    document.getElementById('jarvis-input-area').style.display = 'none';
    document.getElementById('jarvis-loading').style.display = 'block';
    document.getElementById('jarvis-result').style.display = 'none';

    try {
        const payload = { action: _jarvisMode, content: prompt };
        if (_jarvisMode === 'summarize_video') payload.youtube_url = prompt;
        const data = await invokeJarvisFunction('jarvis-note-action', payload);
        const result = data.result || data.text || data.reply || JSON.stringify(data);
        _jarvisLastResult = result;
        _jarvisLastApiResponse = data;
        document.getElementById('jarvis-result-text').innerHTML =
            _jarvisMode === 'generate_image' && data?.image_url
                ? `<img src="${data.image_url}" style="max-width:100%;border-radius:10px">`
                : escapeHtmlLight(result).replace(/\n/g, '<br>');
    } catch (e) {
        _jarvisLastResult = '';
        _jarvisLastApiResponse = null;
        document.getElementById('jarvis-result-text').textContent =
            'Jarvis indisponível. Confirme Supabase Functions, login e GEMINI_API_KEY. Erro: ' + (e.message || e);
    } finally {
        document.getElementById('jarvis-loading').style.display = 'none';
        document.getElementById('jarvis-result').style.display = 'block';
        document.getElementById('jarvis-input-area').style.display = 'block';
    }
};
