/** Nexus Mobile — nexus-routines.js */
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
