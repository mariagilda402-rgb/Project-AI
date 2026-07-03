/** Nexus Mobile — nexus-tasks.js */
// Kanban helpers — CRUD principal em nexus-forms.js

let taskKanbanMode = false;
window.taskKanbanMode = false;

window.toggleTaskKanban = function() {
    taskKanbanMode = !taskKanbanMode;
    window.taskKanbanMode = taskKanbanMode;
    const list = document.getElementById('tasks-list-view');
    const kanban = document.getElementById('tasks-kanban-view');
    const filters = document.querySelector('#view-tasks .habit-filters-scroll');
    if (list) list.style.display = taskKanbanMode ? 'none' : 'flex';
    if (kanban) kanban.style.display = taskKanbanMode ? 'flex' : 'none';
    if (filters) filters.style.display = taskKanbanMode ? 'none' : 'flex';
    if (taskKanbanMode) renderTaskKanban();
    else if (typeof window.filterTasks === 'function') {
        window.filterTasks(document.querySelector('#view-tasks .study-chip.active')?.dataset?.filter || 'all');
    }
};

function renderTaskKanban() {
    const tasks = LocalDB.get('tasks').filter(t => !t.is_deleted);
    const todo = tasks.filter(t => !t.done_at && t.status !== 'doing');
    const doing = tasks.filter(t => !t.done_at && t.status === 'doing');
    const done = tasks.filter(t => t.done_at);

    const renderCard = (t) => {
        const prioColor = t.priority === 'high' ? 'var(--accent-pink)' : t.priority === 'medium' ? '#f59e0b' : 'var(--text-secondary)';
        return `
        <div class="glass" style="padding:12px;border-radius:12px;cursor:pointer;border-left:3px solid ${prioColor}" onclick="openTaskDetail('${t.id}')">
            <div style="font-size:0.9rem;font-weight:600;margin-bottom:6px">${escapeHtml(t.name || t.title || 'Tarefa')}</div>
            ${t.due_date ? `<div style="font-size:0.7rem;color:var(--text-secondary)"><i class="fa-regular fa-clock"></i> ${new Date(t.due_date).toLocaleDateString('pt-BR')}</div>` : ''}
        </div>`;
    };

    const elTodo = document.getElementById('kanban-todo');
    const elDoing = document.getElementById('kanban-doing');
    const elDone = document.getElementById('kanban-done');

    if (elTodo) elTodo.innerHTML = todo.map(renderCard).join('') || '<div style="color:var(--text-secondary);font-size:0.8rem;text-align:center;padding:20px;border:1px dashed var(--border-glass);border-radius:8px">Vazio</div>';
    if (elDoing) elDoing.innerHTML = doing.map(renderCard).join('') || '<div style="color:var(--text-secondary);font-size:0.8rem;text-align:center;padding:20px;border:1px dashed var(--border-glass);border-radius:8px">Arraste tarefas para cá</div>';
    if (elDone) elDone.innerHTML = done.map(renderCard).join('') || '<div style="color:var(--text-secondary);font-size:0.8rem;text-align:center;padding:20px;border:1px dashed var(--border-glass);border-radius:8px">Vazio</div>';
}

window.renderTaskKanban = renderTaskKanban;

window.loadTasks = function() {
    if (taskKanbanMode) renderTaskKanban();
    else if (typeof window.filterTasks === 'function') {
        window.filterTasks('all', document.querySelector('#view-tasks .study-chip[data-filter="all"]'));
    }
};
