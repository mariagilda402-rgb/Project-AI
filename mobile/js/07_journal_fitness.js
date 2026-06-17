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
