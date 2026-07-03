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

window.deleteCurrentHabit = function() {
    if (!currentHabitId) return;
    if (!confirm('Deseja realmente excluir este habito? O historico sera perdido.')) return;
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
