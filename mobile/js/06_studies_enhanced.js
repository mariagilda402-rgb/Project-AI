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

function renderNoteCard(n) {
    const tags = (n.tags||'').split('#').filter(t => t.trim()).map(t => `<span class="tag-badge">#${t.trim()}</span>`).join('');
    const date = n.updated_at ? new Date(n.updated_at).toLocaleDateString('pt-BR', {day:'2-digit',month:'short'}) : '';
    const pin = n.pinned ? '<i class="fa-solid fa-thumbtack" style="color:var(--accent-primary);font-size:0.7rem;margin-right:4px"></i>' : '';
    return `
    <div class="note-card ${n.pinned?'pinned':''}" onclick="openNoteEditor('${n.id}', '${n.notebook_id||''}')">
        <div class="note-title">${pin}${escapeHtml(n.title||'Sem titulo')}</div>
        <div class="note-excerpt">${escapeHtml((n.content||'').replace(/[#*`_>-]/g,'').trim())}</div>
        <div class="note-meta">
            <div class="note-tags">${tags}</div>
            <span style="font-size:0.7rem;color:var(--text-secondary)">${date}</span>
        </div>
    </div>`;
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
        if (navigator.vibrate) navigator.vibrate([100, 50, 100, 50, 200]);
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
