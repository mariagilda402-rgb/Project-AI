/** Nexus Mobile — nexus-journal.js */
// ================================================================
// JOURNAL / MOOD MODULE
// ================================================================

const MOOD_EMOJIS = ['', '\u{1F613}', '\u{1F615}', '\u{1F610}', '\u{1F604}', '\u{1F929}'];
const MOOD_LABELS = ['', 'P\u00e9ssimo', 'Ruim', 'Neutro', 'Bom', '\u00d3timo'];
const MOOD_COLORS = ['', '#ef4444', '#f97316', '#6b7280', '#10b981', '#8b5cf6'];

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

window.deleteJournalEntry = function() {
    const date = editingJournalId;
    if (!date) return;
    if (!confirm('Excluir entrada do diário para esta data?')) return;
    const entries = LocalDB.get('journal_entries').filter(e => e.date !== date);
    LocalDB.set('journal_entries', entries);
    closeJournalEntry();
    loadJournal();
    showInAppNotification('Entrada removida.', 'success');
    if (typeof backgroundSync === 'function') backgroundSync();
};
