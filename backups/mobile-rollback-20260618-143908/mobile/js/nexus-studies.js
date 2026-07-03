/** Nexus Mobile — nexus-studies.js */
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
    loadSubjectsGrid();
    const list = document.getElementById('studies-list');
    if (list) renderStudyNotesList('all', null);
}
window.loadStudies = loadStudies;

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
    loadSubjectsGrid();
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
    const notebooks = (LocalDB.get('study_notebooks') || []).filter(n => !n.is_deleted);
    if (!notebooks.length) {
        grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text-secondary);padding:20px">Sem matérias. Toque em + para criar.</div>';
        return;
    }
    grid.innerHTML = notebooks.map(nb => renderSubjectFolderCard(nb)).join('');
}
window.loadSubjectsGrid = loadSubjectsGrid;

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
