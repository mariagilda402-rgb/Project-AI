window.onerror = function(msg, url, line, col, error) {
    alert("ERRO JS: " + msg + " na linha " + line);
    return false;
};

// Supabase Configuration
const supabaseUrl = 'https://oxwpwfhjyiiwdhcggtlt.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im94d3B3ZmhqeWlpd2RoY2dndGx0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExMzA3NjAsImV4cCI6MjA5NjcwNjc2MH0.mIOis8ugOlubw2P6Z8_TuNeLukvltsXAlPb-ttaaOpY';
let supabase = null;
if (window.supabase) {
    supabase = window.supabase.createClient(supabaseUrl, supabaseKey);
} else {
    console.warn("Supabase client not loaded. Running in full offline mode.");
}

// ----------------------------------------------------
// Offline-First Database (LocalStorage)
// ----------------------------------------------------
class LocalDB {
    static get(table) {
        try {
            const data = JSON.parse(localStorage.getItem(`nexus_${table}`) || '[]');
            return Array.isArray(data) ? data : [];
        } catch(e) {
            return [];
        }
    }
    static set(table, data) {
        localStorage.setItem(`nexus_${table}`, JSON.stringify(data));
    }
    static getSingle(table, id) {
        const rows = this.get(table);
        return rows.find(r => r.id === id);
    }
    static upsert(table, record) {
        const rows = this.get(table);
        const idx = rows.findIndex(r => r.id === record.id);
        record.updated_at = new Date().toISOString();
        if (idx > -1) {
            rows[idx] = { ...rows[idx], ...record };
        } else {
            if (!record.id) record.id = Date.now(); // pseudo-id for new local records
            rows.push(record);
        }
        this.set(table, rows);
        return record;
    }
}

// ----------------------------------------------------
// Sync Engine
// ----------------------------------------------------
async function backgroundSync() {
    if (!navigator.onLine || !supabase) return;
    try {
        const tables = ['nexus_user', 'habits', 'tasks', 'finance_transactions', 'nexus_rewards', 'study_notes', 'nexus_goals', 'fitness_workouts'];
        let lastSync = localStorage.getItem('nexus_last_sync') || '1970-01-01T00:00:00Z';
        let newSyncTime = lastSync;

        for (let table of tables) {
            // Pull
            const { data: remoteData, error } = await supabase.from(table).select('*').gt('updated_at', lastSync).order('updated_at', { ascending: true });
            if (remoteData && remoteData.length > 0) {
                remoteData.forEach(remoteRow => {
                    const localRow = LocalDB.getSingle(table, remoteRow.id);
                    if (!localRow || remoteRow.updated_at > (localRow.updated_at || '')) {
                        const rows = LocalDB.get(table);
                        const idx = rows.findIndex(r => r.id === remoteRow.id);
                        if (idx > -1) Object.assign(rows[idx], remoteRow);
                        else rows.push(remoteRow);
                        LocalDB.set(table, rows);
                        if (remoteRow.updated_at > newSyncTime) newSyncTime = remoteRow.updated_at;
                    }
                });
            }

            // Push
            const localData = LocalDB.get(table).filter(r => (r.updated_at || '') > lastSync);
            for (let localRow of localData) {
                // Remove UI-only fields if necessary
                const cleanRow = Object.assign({}, localRow);
                const { error: pushErr } = await supabase.from(table).upsert(cleanRow);
                if (!pushErr) {
                    if (localRow.updated_at > newSyncTime) newSyncTime = localRow.updated_at;
                }
            }
        }
        localStorage.setItem('nexus_last_sync', newSyncTime);
        
        // Refresh UI if necessary
        const activeView = document.querySelector('.active-view');
        if(activeView) {
            if(activeView.id === 'view-habits') loadHabits();
            if(activeView.id === 'view-finance') loadFinances();
            if(activeView.id === 'view-tasks') loadTasks();
        }
        loadUserStats();
    } catch (e) {
        console.error("Sync error:", e);
    }
}

// ----------------------------------------------------
// UI Logic
// ----------------------------------------------------
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        
        document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');
        
        const targetId = item.getAttribute('data-target');
        document.querySelectorAll('.view').forEach(view => view.classList.remove('active-view'));
        document.getElementById(targetId).classList.add('active-view');
        
        if(targetId === 'view-habits') loadHabits();
        if(targetId === 'view-finance') loadFinances();
        if(targetId === 'view-tasks') loadTasks();
        if(targetId === 'view-videos') loadVideos();
        if(targetId === 'view-shop') loadShop();
        if(targetId === 'view-iot') discoverIoT();
        if(targetId === 'view-studies') loadStudies();
        if(targetId === 'view-goals') loadGoals();
        if(targetId === 'view-fitness') loadFitness();
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

function loadUserStats() {
    const user = LocalDB.getSingle('nexus_user', 1) || { xp: 0, level: 1, points: 0 };
    document.getElementById('user-level').innerText = user.level;
    document.getElementById('val-xp').innerText = user.xp;
    document.getElementById('val-points').innerText = user.points;
}

function loadVideos() {
    const container = document.getElementById('videos-list');
    const data = LocalDB.get('nexus_videos');
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhum vÃ­deo salvo offline.</div>';
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
    const container = document.getElementById('habits-list');
    const data = LocalDB.get('habits').filter(h => h.active === 1 && !h.is_deleted);
    
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhum hÃ¡bito cadastrado.</div>';
    data.forEach(habit => {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        const isDone = false; // Need a better way to store daily completions offline
        el.innerHTML = `
            <div class="item-main">
                <span class="item-title">${habit.name}</span>
                <span class="item-subtitle">Streak: ðŸ”¥ ${habit.current_streak}</span>
            </div>
            <button class="item-action ${isDone ? 'done' : ''}" onclick="toggleHabit(${habit.id}, this)">
                <i class="fa-solid fa-check"></i>
            </button>
        `;
        container.appendChild(el);
    });
}

window.toggleHabit = function(id, btn) {
    btn.classList.toggle('done');
    if (navigator.vibrate) navigator.vibrate(50);
    
    if (btn.classList.contains('done')) {
        sendLocalNotification('HÃ¡bito ConcluÃ­do!', 'VocÃª ganhou pontos de experiÃªncia!');
        
        // Update user stats offline
        const user = LocalDB.getSingle('nexus_user', 1) || { id: 1, xp: 0, points: 0, level: 1 };
        user.xp += 25;
        user.points += 25;
        user.level = 1 + Math.floor(user.xp / 1000);
        LocalDB.upsert('nexus_user', user);
        
        loadUserStats();
        backgroundSync(); // trigger sync
    }
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
    if(task) {
        task.done_at = new Date().toISOString();
        LocalDB.upsert('tasks', task);
        
        const user = LocalDB.getSingle('nexus_user', 1);
        if(user) {
            user.xp += task.points_reward || 10;
            user.points += task.points_reward || 10;
            user.level = 1 + Math.floor(user.xp / 1000);
            LocalDB.upsert('nexus_user', user);
            loadUserStats();
        }
        loadTasks();
        backgroundSync();
    }
};

function loadFinances() {
    const container = document.getElementById('finance-list');
    const data = LocalDB.get('finance_transactions').filter(t => !t.is_deleted).sort((a,b) => (b.occurred_at || b.created_at || '').localeCompare(a.occurred_at || a.created_at || ''));
    
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Sem transaÃ§Ãµes.</div>';
    data.slice(0, 15).forEach(t => {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        el.innerHTML = `<div class="item-main"><span class="item-title">${t.description || 'TransaÃ§Ã£o'}</span><span class="item-subtitle" style="color:${t.type==='income'?'#00b894':'#fd79a8'}">${t.type==='income'?'+':'-'} $${t.amount}</span></div>`;
        container.appendChild(el);
    });
}

// ----------------------------------------------------
// ----------------------------------------------------
// New Offline Modules
// ----------------------------------------------------

function loadShop() {
    const container = document.getElementById('shop-list');
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
        container.innerHTML = '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhuma recompensa offline. Sincronize para puxar itens.</div>';
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
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Sem metas ativas.</div>';
    data.forEach(t => {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        el.innerHTML = `<div class="item-main"><span class="item-title">${t.name}</span><span class="item-subtitle">Progresso: ${t.progress || 0}%</span></div>`;
        container.appendChild(el);
    });
}

function loadFitness() {
    const container = document.getElementById('fitness-list');
    if(!container) return;
    const data = LocalDB.get('fitness_workouts').filter(t => !t.is_deleted);
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhum treino registrado.</div>';
    data.slice(0,10).forEach(t => {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        el.innerHTML = `<div class="item-main"><span class="item-title">${t.type}</span><span class="item-subtitle">${t.duration_minutes || 0} min | ${t.calories_burned || 0} kcal</span></div>`;
        container.appendChild(el);
    });
}

window.discoverIoT = async function() {
    const container = document.getElementById('iot-list');
    container.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-circle-notch fa-spin"></i> Buscando...</div>';
    try {
        const res = await fetch('/api/nexus/iot/discover');
        const data = await res.json();
        if (data && data.devices) {
            container.innerHTML = data.devices.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhum dispositivo encontrado.</div>';
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
        }
    } catch (e) {
        container.innerHTML = '<div style="text-align:center; color:red; margin-top:20px;">Erro ao buscar dispositivos.</div>';
    }
};

// ----------------------------------------------------
// Realtime Subscription
// ----------------------------------------------------
function setupRealtime() {
    if (!supabase) return;
    supabase.channel('custom-all-channel')
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
    const cards = LocalDB.get('flashcards');
    const pomoLog = LocalDB.get('pomo_sessions') || [];
    
    const todayStr = new Date().toDateString();
    const todayPomos = pomoLog.filter(p => new Date(p.date).toDateString() === todayStr).length;
    
    // Study streak
    let streak = 0;
    const now = new Date();
    for (let i = 0; i < 60; i++) {
        const d = new Date(now);
        d.setDate(d.getDate() - i);
        const ds = d.toDateString();
        const hadStudy = notes.some(n => n.created_at && new Date(n.created_at).toDateString() === ds) ||
                         pomoLog.some(p => new Date(p.date).toDateString() === ds);
        if (hadStudy) streak++;
        else if (i > 0) break;
    }
    
    const sv = document.getElementById('study-streak-val');
    const pv = document.getElementById('study-pomo-val');
    const nv = document.getElementById('study-notes-val');
    const cv = document.getElementById('study-cards-val');
    if (sv) sv.textContent = streak;
    if (pv) pv.textContent = todayPomos;
    if (nv) nv.textContent = notes.length;
    if (cv) cv.textContent = cards.length;
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
        id: Date.now().toString(),
        name: name.trim(),
        muscle_group: muscleGroup,
        exercises: [],
        date: new Date().toISOString(),
        created_at: new Date().toISOString()
    };
    const workouts = LocalDB.get('fitness_workouts');
    workouts.push(workout);
    LocalDB.set('fitness_workouts', workouts);
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
    diet_meals: [], body_measures: [], xp_log: [], user_stats: null
};
const _origGet = LocalDB.get;
LocalDB.get = function(key) {
    const val = _origGet.call(this, key);
    if (val === null || val === undefined) return _newDefaults[key] !== undefined ? (_newDefaults[key] === null ? null : JSON.parse(JSON.stringify(_newDefaults[key]))) : val;
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
    const logs = LocalDB.get('habit_logs');
    const today = new Date().toISOString().split('T')[0];
    const idx = logs.findIndex(l => l.habit_id === habitId && l.date === today);
    if (idx !== -1) {
        logs.splice(idx, 1);
    } else {
        logs.push({ id: Date.now().toString(), habit_id: habitId, date: today });
        awardXP(5, 'Habito concluido');
    }
    LocalDB.set('habit_logs', logs);
    filterHabits(document.querySelector('#view-habits .study-chip.active')?.dataset?.filter || 'all');
    loadXPPanel();
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
    const idx = habits.findIndex(h => h.id === currentHabitId);
    if (idx !== -1) {
        habits[idx].alarm_time = time;
        LocalDB.set('habits', habits);
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
    const idx = habits.findIndex(h => h.id === currentHabitId);
    if (idx !== -1) {
        habits[idx].is_deleted = true;
        LocalDB.set('habits', habits);
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
            const completedCount = logs.filter(l => l.date === dateStr && habits.some(h => h.id === l.habit_id)).length;
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
    const tasks = LocalDB.get('tasks');
    const t = tasks.find(x => x.id === currentTaskId);
    if (t) {
        t.is_deleted = true;
        LocalDB.set('tasks', tasks);
        closeTaskDetail();
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
    } else {
        document.body.classList.remove('theme-amoled');
        LocalDB.set('amoled_enabled', false);
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
    // Initial UI load from LocalStorage
    loadUserStats();
    loadHabits();
    
    // Background tasks
    setTimeout(requestNotificationPermission, 2000);
    setTimeout(backgroundSync, 1000); // Initial sync on boot
    setupRealtime();
    
    // Poll sync every minute if online
    setInterval(backgroundSync, 60000);
});

// ----------------------------------------------------
// UI Preferences & Module Toggling
// ----------------------------------------------------
window.openSettingsModal = () => {
    document.getElementById('settings-modal').classList.add('show');
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
    const modules = ['habits', 'finance', 'tasks', 'videos', 'shop', 'iot', 'studies', 'goals', 'fitness'];
    
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
    const embedHTML = `<div class="yt-embed-block" contenteditable="false">
        <iframe src="https://www.youtube.com/embed/${videoId}?rel=0" allowfullscreen loading="lazy"></iframe>
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

function openJarvisPanel(mode) {
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
            // Backend offline — use simulated responses for demo
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
    if (pomoActive) return;
    pomoActive = true;
    
    // Play a tiny beep to acknowledge start
    playBeep(400, 100);
    
    pomoInterval = setInterval(() => {
        if (pomoTimeLeft > 0) {
            pomoTimeLeft--;
            document.getElementById('pomodoro-timer').innerText = formatPomoTime(pomoTimeLeft);
        } else {
            // Finished!
            clearInterval(pomoInterval);
            pomoActive = false;
            
            // Reward XP
            const user = LocalDB.getSingle('nexus_user', 1) || { id: 1, xp: 0, points: 0, level: 1 };
            user.xp += 50;
            user.points += 50;
            user.level = 1 + Math.floor(user.xp / 1000);
            LocalDB.upsert('nexus_user', user);
            
            loadUserStats();
            backgroundSync();
            
            sendLocalNotification('Foco Concluído!', 'Você ganhou +50 XP por 25 minutos de estudo.');
            playBeep(800, 500); // Toca alarme final
            
            pomoTimeLeft = 25 * 60; // reset
            document.getElementById('pomodoro-timer').innerText = formatPomoTime(pomoTimeLeft);
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
    _pomoTimeLeft = 5 * 60; // 5 min break
    initPomodoroUI();
    document.getElementById('pomo-mode-label').textContent = 'DESCANSO';
    
    // Save history
    let ph = LocalDB.getAll('pomodoros') || [];
    ph.push({ date: new Date().toISOString(), duration: 25 });
    LocalDB.saveAll('pomodoros', ph);
    
    // Reward XP
    if (typeof addXP === 'function') addXP(50);
    showToast('🍅 Pomodoro concluído! +50 XP');
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
    const cards = LocalDB.getAll('flashcards') || [];
    cards.push({
        id: 'fc_' + Date.now() + Math.floor(Math.random()*1000),
        noteId: noteId,
        front: front,
        back: back,
        interval: 0,
        repetition: 0,
        efactor: 2.5,
        nextReviewDate: new Date().toISOString()
    });
    LocalDB.saveAll('flashcards', cards);
}

function getDueFlashcards() {
    const cards = LocalDB.getAll('flashcards') || [];
    const now = new Date().toISOString();
    return cards.filter(c => c.nextReviewDate <= now);
}

window.showFlashcards = function() {
    initFlashcardsDB();
    _flashcardQueue = getDueFlashcards();
    
    // Add some dummy cards if empty for demo
    if (LocalDB.getAll('flashcards').length === 0) {
        createFlashcard('O que é o algoritmo SM-2?', 'É um algoritmo de Repetição Espaçada usado pelo Anki para otimizar a memorização.');
        createFlashcard('Qual a capital do Brasil?', 'Brasília');
        _flashcardQueue = getDueFlashcards();
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
    
    // Update DB
    const allCards = LocalDB.getAll('flashcards') || [];
    const idx = allCards.findIndex(c => c.id === card.id);
    if (idx !== -1) {
        allCards[idx] = card;
        LocalDB.saveAll('flashcards', allCards);
    }
    
    // Animate and next
    const cardDiv = document.getElementById('flashcard-card');
    cardDiv.style.transform = isCorrect ? 'translateX(50px) rotate(5deg) opacity(0)' : 'translateX(-50px) rotate(-5deg) opacity(0)';
    
    setTimeout(() => {
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
        if (Notification.permission === 'granted') {
            new Notification('Nexus Studies', { body: `Você tem ${due.length} flashcards para revisar hoje!` });
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initFlashcardsDB();
    insertGenerateFlashcardsButton();
    
    // Request notification permission if not asked
    if (Notification.permission === 'default') {
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

let _chartInstances = {};

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
    if (_chartInstances[id]) {
        _chartInstances[id].destroy();
        _chartInstances[id] = null;
    }
}

// ─── Finance Charts ──────────────────────────────────────────────

function renderFinanceCharts() {
    if (typeof Chart === 'undefined') return;
    initChartDefaults();
    
    const transactions = LocalDB.getAll('transactions') || [];
    
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
    
    const pomos = LocalDB.getAll('pomodoros') || [];
    // Currently, flashcards don't log history per day, so we'll just track pomodoros for the chart
    
    const days = 7;
    const labels = [];
    const pomoData = [];
    
    for (let i = days - 1; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        const iso = d.toISOString().split('T')[0];
        
        const dayName = d.toLocaleDateString('pt-BR', { weekday: 'short' });
        labels.push(dayName);
        
        const count = pomos.filter(p => p.date.startsWith(iso)).length;
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
    setTimeout(renderFinanceCharts, 100);
};

const _origLoadHabitsForCharts = window.loadHabits;
window.loadHabits = function() {
    if (typeof _origLoadHabitsForCharts === 'function') _origLoadHabitsForCharts();
    setTimeout(renderHabitCharts, 100);
};

const _origLoadStudiesForCharts = window.loadStudies;
window.loadStudies = function() {
    if (typeof _origLoadStudiesForCharts === 'function') _origLoadStudiesForCharts();
    setTimeout(renderStudyCharts, 100);
};


// ================================================================
// MULTI-USER AUTH & SETTINGS
// ================================================================

let currentUser = null;

// Listen for auth changes
if (supabase) {
    supabase.auth.onAuthStateChange((event, session) => {
        currentUser = session ? session.user : null;
        updateSettingsUI();
        if (event === 'SIGNED_IN') {
            forceSyncData();
        }
    });
    
    // Initial check
    supabase.auth.getSession().then(({ data: { session } }) => {
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

async function loginWithGoogle() {
    if (!supabase) {
        alert("Servidor indisponível (Offline).");
        return;
    }
    const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: window.location.origin + window.location.pathname }
    });
    if (error) {
        alert("Erro no login: " + error.message);
    }
}

async function logoutGoogle() {
    if (!supabase) return;
    const { error } = await supabase.auth.signOut();
    if (!error) {
        currentUser = null;
        updateSettingsUI();
        showToast("Você saiu da conta.");
    }
}

// Intercept pushChangesToSupabase to inject user_id
const _origPushChanges = window.pushChangesToSupabase;
window.pushChangesToSupabase = async function() {
    if (!supabase || !navigator.onLine || !currentUser) return; // Only push if logged in
    
    try {
        const syncTables = ['habits', 'tasks', 'finance_transactions', 'study_notes', 'nexus_user', 'nexus_videos', 'nexus_rewards', 'nexus_goals', 'fitness_workouts'];
        for (let table of syncTables) {
            const data = LocalDB.getAll(table) || [];
            const toPush = data.filter(d => !d.sync_status || d.sync_status === 'pending');
            if (toPush.length > 0) {
                // Attach user_id for RLS
                const cleanData = toPush.map(row => {
                    let cleanRow = { ...row, user_id: currentUser.id };
                    delete cleanRow.sync_status;
                    if (cleanRow.id && typeof cleanRow.id === 'string') delete cleanRow.id;
                    return cleanRow;
                });
                const { error } = await supabase.from(table).upsert(cleanData);
                if (!error) {
                    data.forEach(d => { if (toPush.find(t => t === d)) d.sync_status = 'synced'; });
                    LocalDB.saveAll(table, data);
                } else {
                    console.error("Push error:", error);
                }
            }
        }
        LocalDB.saveAll('last_push', new Date().toISOString());
    } catch (e) {
        console.error("Sync error:", e);
    }
};

function forceSyncData() {
    showToast("Sincronizando com a Nuvem...");
    if (typeof syncData === 'function') {
        syncData().then(() => {
            showToast("Sincronização Concluída!");
        });
    }
}

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
