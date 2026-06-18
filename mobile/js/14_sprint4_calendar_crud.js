// SPRINT 4 — NexusCalendar, CRUD forms, reminders, studies redesign
// ================================================================

(function() {
    const MONTH_NAMES = ['Janeiro','Fevereiro','Marco','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
    const todayISO = () => new Date().toISOString().split('T')[0];

    function getDailyBudget() {
        const el = document.getElementById('nexus_daily_budget');
        const fromEl = el && el.value ? parseFloat(el.value) : null;
        if (fromEl && fromEl > 0) return fromEl;
        const stored = parseFloat(localStorage.getItem('nexus_daily_budget') || '0');
        return stored > 0 ? stored : 100;
    }

    window.saveDailyBudget = function(val) {
        localStorage.setItem('nexus_daily_budget', String(val || 100));
        const el = document.getElementById('nexus_daily_budget');
        if (el) el.value = val;
    };

    function habitScheduledOnDay(habit, dateISO) {
        const dow = new Date(dateISO + 'T12:00:00').getDay();
        const days = habit.days_of_week || [1,2,3,4,5];
        if (Array.isArray(days) && days.length) return days.map(Number).includes(dow);
        return true;
    }

    function ratioColor(ratio, hasData) {
        if (!hasData) return 'hm-gray';
        if (ratio >= 1) return 'hm-green';
        if (ratio >= 0.5) return 'hm-orange';
        if (ratio > 0) return 'hm-orange';
        return 'hm-red';
    }

    function getFitnessPlanDays() {
        try {
            const parsed = JSON.parse(localStorage.getItem('nexus_fitness_plan_days') || '[1,2,3,4,5]');
            return Array.isArray(parsed) ? parsed.map(Number) : [1,2,3,4,5];
        } catch (e) { return [1,2,3,4,5]; }
    }

    window.NexusCalendar = {
        selectedDateISO: todayISO(),
        currentYear: new Date().getFullYear(),
        currentMonth: new Date().getMonth() + 1,
        activeModule: 'habits',
        onSelectCallback: null,
        _monthCache: null,

        getSelectedDate() { return this.selectedDateISO; },

        open(opts) {
            opts = opts || {};
            this.activeModule = opts.module || 'habits';
            this.onSelectCallback = opts.onSelect || null;
            const modal = document.getElementById('nexus-calendar-modal');
            if (modal) modal.style.display = 'flex';
            this.render();
        },

        close() {
            const modal = document.getElementById('nexus-calendar-modal');
            if (modal) modal.style.display = 'none';
        },

        changeMonth(delta) {
            this.currentMonth += delta;
            if (this.currentMonth < 1) { this.currentMonth = 12; this.currentYear--; }
            else if (this.currentMonth > 12) { this.currentMonth = 1; this.currentYear++; }
            this.render();
        },

        goToday() {
            this.currentYear = new Date().getFullYear();
            this.currentMonth = new Date().getMonth() + 1;
            this.selectDay(todayISO());
        },

        selectDay(dateISO) {
            this.selectedDateISO = dateISO;
            this.close();
            this.updateDateLabels();
            if (typeof this.onSelectCallback === 'function') this.onSelectCallback(dateISO);
        },

        updateDateLabels() {
            const d = new Date(this.selectedDateISO + 'T12:00:00');
            const label = this.selectedDateISO === todayISO() ? 'Hoje' : d.toLocaleDateString('pt-BR', { day: 'numeric', month: 'short' });
            ['habits-date-label','tasks-date-label','finance-date-label','fitness-date-label'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.textContent = label;
            });
        },

        buildMonthSummary(module, year, month) {
            const daysInMonth = new Date(year, month, 0).getDate();
            const summary = {};
            for (let d = 1; d <= daysInMonth; d++) {
                const dateISO = `${year}-${String(month).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
                summary[dateISO] = { color: 'hm-gray', ratio: 0, hasData: false };
            }

            if (module === 'habits') {
                const habits = (LocalDB.get('habits') || []).filter(h => h.active === 1 && !h.is_deleted);
                const logs = LocalDB.get('habit_logs') || [];
                const logsByDate = {};
                logs.forEach(l => {
                    if (!l.date || l.is_deleted) return;
                    if (!logsByDate[l.date]) logsByDate[l.date] = new Set();
                    logsByDate[l.date].add(String(l.habit_id));
                });
                Object.keys(summary).forEach(dateISO => {
                    const scheduled = habits.filter(h => habitScheduledOnDay(h, dateISO));
                    if (!scheduled.length) { summary[dateISO].color = 'hm-gray'; return; }
                    const done = scheduled.filter(h => logsByDate[dateISO] && logsByDate[dateISO].has(String(h.id))).length;
                    const ratio = done / scheduled.length;
                    summary[dateISO] = { ratio, hasData: true, color: ratioColor(ratio, true) };
                });
            } else if (module === 'tasks') {
                const tasks = (LocalDB.get('tasks') || []).filter(t => !t.is_deleted && t.due_date);
                Object.keys(summary).forEach(dateISO => {
                    const due = tasks.filter(t => t.due_date === dateISO);
                    if (!due.length) return;
                    const done = due.filter(t => t.done_at || t.status === 'done').length;
                    const ratio = done / due.length;
                    summary[dateISO] = { ratio, hasData: true, color: ratioColor(ratio, true) };
                });
            } else if (module === 'finance') {
                const budget = getDailyBudget();
                const tx = (LocalDB.get('finance_transactions') || []).filter(t => !t.is_deleted && t.type === 'expense');
                Object.keys(summary).forEach(dateISO => {
                    const spent = tx.filter(t => (t.occurred_at || t.date || t.created_at || '').split('T')[0] === dateISO)
                        .reduce((s, t) => s + Math.abs(Number(t.amount) || 0), 0);
                    if (spent <= 0) return;
                    const ratio = budget > 0 ? spent / budget : 1;
                    let color = 'hm-green';
                    if (ratio >= 1) color = 'hm-red';
                    else if (ratio >= 0.5) color = 'hm-orange';
                    summary[dateISO] = { ratio, hasData: true, color };
                });
            } else if (module === 'fitness') {
                const planDays = getFitnessPlanDays();
                const workouts = (LocalDB.get('fitness_workouts') || []).filter(w => !w.is_deleted);
                const workoutDates = new Set(workouts.map(w => (w.date || w.created_at || '').split('T')[0]).filter(Boolean));
                Object.keys(summary).forEach(dateISO => {
                    const dow = new Date(dateISO + 'T12:00:00').getDay();
                    const planned = planDays.includes(dow);
                    const logged = workoutDates.has(dateISO);
                    if (!planned && !logged) return;
                    if (planned && logged) summary[dateISO] = { ratio: 1, hasData: true, color: 'hm-green' };
                    else if (planned && !logged) summary[dateISO] = { ratio: 0, hasData: true, color: 'hm-red' };
                    else summary[dateISO] = { ratio: 0, hasData: true, color: 'hm-gray' };
                });
            }
            return summary;
        },

        render() {
            const grid = document.getElementById('nexus-cal-grid');
            const label = document.getElementById('nexus-cal-month-label');
            if (!grid) return;
            if (label) label.textContent = `${MONTH_NAMES[this.currentMonth - 1]} ${this.currentYear}`;
            this._monthCache = this.buildMonthSummary(this.activeModule, this.currentYear, this.currentMonth);
            grid.innerHTML = '';
            const firstDay = new Date(this.currentYear, this.currentMonth - 1, 1).getDay();
            const daysInMonth = new Date(this.currentYear, this.currentMonth, 0).getDate();
            for (let i = 0; i < firstDay; i++) {
                const empty = document.createElement('div');
                grid.appendChild(empty);
            }
            for (let d = 1; d <= daysInMonth; d++) {
                const dateISO = `${this.currentYear}-${String(this.currentMonth).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
                const dayData = this._monthCache[dateISO] || { color: 'hm-gray' };
                const box = document.createElement('button');
                box.type = 'button';
                box.className = 'nexus-cal-day ' + dayData.color + (dateISO === this.selectedDateISO ? ' active-day' : '');
                box.textContent = d;
                box.onclick = () => this.selectDay(dateISO);
                grid.appendChild(box);
            }
        }
    };

    // --- Habit fixes ---
    function getSelectedDate() {
        return (window.NexusCalendar && NexusCalendar.getSelectedDate()) || todayISO();
    }

    window.toggleHabitDirect = function(habitId, dateISO) {
        const targetDate = dateISO || getSelectedDate();
        const logs = LocalDB.getAll('habit_logs');
        const idx = logs.findIndex(l => String(l.habit_id) === String(habitId) && l.date === targetDate && !l.is_deleted);
        if (idx !== -1) {
            logs.splice(idx, 1);
            LocalDB.set('habit_logs', logs);
        } else {
            const entry = { id: Date.now(), habit_id: habitId, date: targetDate, completed_date: targetDate };
            LocalDB.upsert('habit_logs', entry);
            awardXP(5, 'Habito concluido');
        }
        if (typeof filterHabits === 'function') filterHabits(document.querySelector('#view-habits .study-chip.active')?.dataset?.filter || 'all');
        loadXPPanel();
        backgroundSync();
    };

    window.openHabitForm = function(habitId) {
        currentHabitId = habitId || null;
        const modal = document.getElementById('habit-detail-modal');
        const habits = LocalDB.get('habits') || [];
        const h = habitId ? habits.find(x => String(x.id) === String(habitId)) : null;
        document.getElementById('habit-form-title').textContent = h ? 'Editar Habito' : 'Novo Habito';
        document.getElementById('habit-form-name').value = h ? h.name : '';
        document.getElementById('habit-form-desc').value = h ? (h.description || '') : '';
        document.getElementById('habit-form-xp').value = h ? (h.xp_reward || 50) : 50;
        document.getElementById('habit-form-period').value = h ? (h.period || 'all') : 'morning';
        const reminder = h ? (h.alarm_time || h.target_time || '') : '';
        document.getElementById('habit-alarm-time').value = reminder ? reminder.substring(0, 5) : '';
        const days = h && h.days_of_week ? h.days_of_week.map(Number) : [1,2,3,4,5];
        document.querySelectorAll('#habit-form-dow .dow-btn').forEach(btn => {
            btn.classList.toggle('selected', days.includes(Number(btn.dataset.d)));
        });
        if (h) openHabitDetailStats(h);
        if (modal) modal.style.display = 'flex';
    };

    window.openHabitDetail = function(habitId) { openHabitForm(habitId); };

    function openHabitDetailStats(h) {
        const logs = LocalDB.get('habit_logs') || [];
        const sel = getSelectedDate();
        let streak = 0;
        const now = new Date();
        for (let i = 0; i < 60; i++) {
            const d = new Date(now); d.setDate(d.getDate() - i);
            const ds = d.toISOString().split('T')[0];
            if (logs.some(l => String(l.habit_id) === String(h.id) && l.date === ds)) streak++;
            else if (i > 0) break;
        }
        const total = logs.filter(l => String(l.habit_id) === String(h.id)).length;
        const isDone = logs.some(l => String(l.habit_id) === String(h.id) && l.date === sel);
        if (document.getElementById('habit-detail-streak')) document.getElementById('habit-detail-streak').textContent = streak;
        if (document.getElementById('habit-detail-total')) document.getElementById('habit-detail-total').textContent = total;
        const btn = document.getElementById('habit-detail-complete-btn');
        if (btn) {
            btn.innerHTML = isDone ? '<i class="fa-solid fa-xmark"></i> Desmarcar' : '<i class="fa-solid fa-check"></i> Feito';
        }
    }

    window.saveHabitForm = function() {
        const name = document.getElementById('habit-form-name')?.value?.trim();
        if (!name) { showToast('Nome obrigatorio'); return; }
        const days = [];
        document.querySelectorAll('#habit-form-dow .dow-btn.selected').forEach(b => days.push(Number(b.dataset.d)));
        const time = document.getElementById('habit-alarm-time')?.value || '';
        const payload = {
            name,
            description: document.getElementById('habit-form-desc')?.value || '',
            xp_reward: parseInt(document.getElementById('habit-form-xp')?.value || '50', 10),
            period: document.getElementById('habit-form-period')?.value || 'all',
            days_of_week: days.length ? days : [1,2,3,4,5],
            alarm_time: time,
            target_time: time,
            active: 1
        };
        if (currentHabitId) {
            const habits = LocalDB.get('habits');
            const idx = habits.findIndex(h => String(h.id) === String(currentHabitId));
            if (idx !== -1) { habits[idx] = { ...habits[idx], ...payload }; LocalDB.set('habits', habits); }
        } else {
            LocalDB.upsert('habits', { id: Date.now(), ...payload, created_at: new Date().toISOString() });
        }
        syncHabitReminders();
        closeHabitDetail();
        loadHabits();
        backgroundSync();
        showToast('Habito salvo!');
    };

    document.querySelectorAll('#habit-form-dow .dow-btn').forEach(btn => {
        btn.addEventListener('click', () => btn.classList.toggle('selected'));
    });

    window.saveHabitAlarm = function() {
        if (!currentHabitId) return;
        const time = document.getElementById('habit-alarm-time')?.value || '';
        const habits = LocalDB.get('habits');
        const idx = habits.findIndex(h => String(h.id) === String(currentHabitId));
        if (idx !== -1) {
            habits[idx].alarm_time = time;
            habits[idx].target_time = time;
            LocalDB.set('habits', habits);
            syncHabitReminders();
        }
    };

    window.filterHabits = function(filter, btn) {
        document.querySelectorAll('#view-habits .study-chip').forEach(b => b.classList.remove('active'));
        if (btn) btn.classList.add('active');
        const container = document.getElementById('habits-list');
        if (!container) return;
        let habits = (LocalDB.get('habits') || []).filter(h => h.active === 1 && !h.is_deleted);
        if (filter === 'morning') habits = habits.filter(h => h.period === 'morning');
        else if (filter === 'afternoon') habits = habits.filter(h => h.period === 'afternoon');
        else if (filter === 'night') habits = habits.filter(h => h.period === 'night');
        const logs = LocalDB.get('habit_logs') || [];
        const sel = getSelectedDate();
        if (!habits.length) {
            container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;">Nenhum habito nesta categoria.</div>';
            return;
        }
        container.innerHTML = habits.map(h => {
            const isDone = logs.some(l => String(l.habit_id) === String(h.id) && l.date === sel);
            return `<div class="list-item glass ${isDone ? 'done' : ''}" style="cursor:pointer" onclick="openHabitDetail('${h.id}')">
                <div class="item-main"><div class="item-title">${escapeHtml(h.name)}</div>
                <div class="item-subtitle">${sel === todayISO() ? 'Hoje' : sel}</div></div>
                <button class="icon-btn ${isDone ? 'done' : ''}" onclick="event.stopPropagation();toggleHabitDirect('${h.id}')"><i class="fa-solid ${isDone ? 'fa-check' : 'fa-plus'}"></i></button>
            </div>`;
        }).join('');
    };

    function renderHabitChartsFixed() {
        if (typeof Chart === 'undefined') return;
        if (typeof initChartDefaults === 'function') initChartDefaults();
        const habits = (LocalDB.get('habits') || []).filter(h => h.active === 1 && !h.is_deleted);
        const logs = LocalDB.get('habit_logs') || [];
        const labels = [], percentages = [];
        for (let i = 13; i >= 0; i--) {
            const d = new Date(); d.setDate(d.getDate() - i);
            const iso = d.toISOString().split('T')[0];
            labels.push(d.getDate() + '/' + (d.getMonth()+1));
            const scheduled = habits.filter(h => habitScheduledOnDay(h, iso));
            if (!scheduled.length) { percentages.push(0); continue; }
            const done = scheduled.filter(h => logs.some(l => String(l.habit_id) === String(h.id) && l.date === iso)).length;
            percentages.push(Math.round((done / scheduled.length) * 100));
        }
        if (typeof safeDestroyChart === 'function') safeDestroyChart('habits-line-chart');
        const ctx = document.getElementById('habits-line-chart');
        if (ctx && typeof Chart !== 'undefined') {
            window._chartInstances = window._chartInstances || {};
            window._chartInstances['habits-line-chart'] = new Chart(ctx, {
                type: 'line',
                data: { labels, datasets: [{ label: 'Aderencia (%)', data: percentages, borderColor: '#a78bfa', backgroundColor: 'rgba(167,139,250,0.1)', fill: true, tension: 0.4 }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100 } } }
            });
        }
    }
    window.renderHabitCharts = renderHabitChartsFixed;

    // --- Task enhancements ---
    window.openTaskForm = function() {
        LocalDB.upsert('tasks', { id: Date.now(), name: 'Nova tarefa', title: 'Nova tarefa', priority: 'medium', status: 'todo', created_at: new Date().toISOString() });
        const tasks = LocalDB.get('tasks');
        const t = tasks[tasks.length - 1];
        openTaskDetail(t.id);
    };

    window.completeCurrentTask = function() {
        if (!currentTaskId) return;
        toggleTaskDirect(currentTaskId);
        closeTaskDetail();
    };

    window.addSubtaskInline = function() {
        const modal = document.getElementById('subtask-inline-modal');
        if (modal) { modal.style.display = 'flex'; document.getElementById('subtask-inline-name').value = ''; }
    };

    window.confirmSubtaskInline = function() {
        const name = document.getElementById('subtask-inline-name')?.value?.trim();
        if (!name || !currentTaskId) return;
        const tasks = LocalDB.get('tasks');
        const t = tasks.find(x => String(x.id) === String(currentTaskId));
        if (t) {
            if (!t.subtasks) t.subtasks = [];
            t.subtasks.push({ name, done: false });
            if (t.subtasks_json) t.subtasks_json = t.subtasks;
            LocalDB.set('tasks', tasks);
            renderSubtasks(t.subtasks);
        }
        document.getElementById('subtask-inline-modal').style.display = 'none';
    };

    window.addSubtask = window.addSubtaskInline;

    const _saveTaskDetailOrig = window.saveTaskDetail;
    window.saveTaskDetail = function() {
        if (!currentTaskId) return;
        const tasks = LocalDB.get('tasks');
        const t = tasks.find(x => String(x.id) === String(currentTaskId));
        if (!t) return;
        t.name = document.getElementById('task-detail-name')?.value || t.name;
        t.title = t.name;
        t.priority = document.getElementById('task-detail-priority')?.value || 'medium';
        t.status = document.getElementById('task-detail-status')?.value || 'todo';
        t.due_date = document.getElementById('task-detail-due')?.value || null;
        t.description = document.getElementById('task-detail-description')?.value || '';
        t.notify_enabled = document.getElementById('task-detail-notify-enabled')?.checked ? 1 : 0;
        const notifyAt = document.getElementById('task-detail-notify-at')?.value;
        t.notify_at = notifyAt ? new Date(notifyAt).toISOString() : null;
        t.subtasks_json = t.subtasks || [];
        LocalDB.set('tasks', tasks);
        syncTaskReminders();
        if (typeof _saveTaskDetailOrig === 'function') _saveTaskDetailOrig();
    };

    const _openTaskDetailOrig = window.openTaskDetail;
    window.openTaskDetail = function(taskId) {
        currentTaskId = taskId;
        const tasks = LocalDB.get('tasks');
        const t = tasks.find(x => String(x.id) === String(taskId));
        if (!t) return;
        const modal = document.getElementById('task-detail-modal');
        document.getElementById('task-detail-name').value = t.name || t.title || '';
        document.getElementById('task-detail-description').value = t.description || '';
        document.getElementById('task-detail-priority').value = t.priority || 'medium';
        document.getElementById('task-detail-status').value = t.status || (t.done_at ? 'done' : 'todo');
        document.getElementById('task-detail-due').value = t.due_date || '';
        document.getElementById('task-detail-notify-enabled').checked = !!t.notify_enabled;
        if (t.notify_at) {
            const nd = new Date(t.notify_at);
            document.getElementById('task-detail-notify-at').value = nd.toISOString().slice(0, 16);
        }
        const subs = t.subtasks || t.subtasks_json || [];
        t.subtasks = Array.isArray(subs) ? subs : [];
        renderSubtasks(t.subtasks);
        if (modal) modal.style.display = 'flex';
    };

    window.filterTasks = function(filter, btn) {
        if (btn) {
            document.querySelectorAll('#view-tasks .study-chip').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        }
        if (taskKanbanMode) { renderTaskKanban(); return; }
        const container = document.getElementById('tasks-list-view');
        if (!container) return;
        let tasks = (LocalDB.get('tasks') || []).filter(t => !t.is_deleted);
        const sel = getSelectedDate();
        if (filter === 'done') tasks = tasks.filter(t => t.done_at);
        else tasks = tasks.filter(t => !t.done_at);
        if (filter === 'today') tasks = tasks.filter(t => t.due_date === sel || t.due_date === todayISO());
        if (filter === 'high') tasks = tasks.filter(t => t.priority === 'high');
        if (NexusCalendar.activeModule === 'tasks' && sel !== todayISO()) {
            tasks = tasks.filter(t => t.due_date === sel);
        }
        if (!tasks.length) {
            container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;">Nenhuma tarefa.</div>';
            return;
        }
        container.innerHTML = tasks.map(t => {
            const isDone = !!t.done_at;
            return `<div class="list-item glass" onclick="openTaskDetail('${t.id}')">
                <div class="item-main"><div class="item-title" style="text-decoration:${isDone?'line-through':'none'}">${escapeHtml(t.name || t.title)}</div></div>
                <button class="icon-btn" onclick="event.stopPropagation();toggleTaskDirect('${t.id}')"><i class="fa-solid fa-check"></i></button>
            </div>`;
        }).join('');
    };

    window.completeCurrentHabit = function() {
        if (!currentHabitId) return;
        toggleHabitDirect(currentHabitId, getSelectedDate());
        closeHabitDetail();
    };

    // --- Native reminders ---
    function scheduleNativeReminder(id, title, body, triggerAtMs) {
        if (window.AndroidNative && typeof AndroidNative.scheduleReminder === 'function') {
            AndroidNative.scheduleReminder(id, title, body, triggerAtMs);
        }
    }

    function cancelNativeReminder(id) {
        if (window.AndroidNative && typeof AndroidNative.cancelReminder === 'function') {
            AndroidNative.cancelReminder(id);
        }
    }

    window.syncTaskReminders = function() {
        const tasks = (LocalDB.get('tasks') || []).filter(t => !t.is_deleted);
        tasks.forEach(t => {
            const rid = parseInt(String(t.id).replace(/\D/g,'').slice(-7) || '0', 10) || Math.abs(Number(t.id) % 100000);
            if (t.notify_enabled && t.notify_at && !t.done_at) {
                const ms = new Date(t.notify_at).getTime();
                if (ms > Date.now()) scheduleNativeReminder(rid, t.name || 'Tarefa', t.description || 'Lembrete de tarefa', ms);
                else cancelNativeReminder(rid);
            } else cancelNativeReminder(rid);
        });
    };

    window.syncHabitReminders = function() {
        const habits = (LocalDB.get('habits') || []).filter(h => h.active === 1 && !h.is_deleted);
        const logs = LocalDB.get('habit_logs') || [];
        const td = todayISO();
        habits.forEach(h => {
            const time = h.alarm_time || h.target_time;
            if (!time) return;
            const rid = 200000 + (parseInt(String(h.id).replace(/\D/g,'').slice(-5) || '0', 10) % 50000);
            const doneToday = logs.some(l => String(l.habit_id) === String(h.id) && l.date === td);
            if (doneToday) { cancelNativeReminder(rid); return; }
            const [hh, mm] = time.substring(0, 5).split(':').map(Number);
            const trigger = new Date();
            trigger.setHours(hh, mm, 0, 0);
            if (trigger.getTime() <= Date.now()) trigger.setDate(trigger.getDate() + 1);
            scheduleNativeReminder(rid, 'Hora do Habito', h.name, trigger.getTime());
        });
    };

    const _pendingReminders = [];
    window.checkPendingReminders = function() {
        const now = Date.now();
        const tasks = (LocalDB.get('tasks') || []).filter(t => t.notify_enabled && t.notify_at && !t.done_at && !t.is_deleted);
        tasks.forEach(t => {
            const ms = new Date(t.notify_at).getTime();
            const key = 'task-' + t.id;
            if (ms <= now && ms > now - 60000 && !_pendingReminders.includes(key)) {
                _pendingReminders.push(key);
                sendLocalNotification(t.name || 'Tarefa', t.description || 'Lembrete');
            }
        });
    };

    function checkHabitAlarmsFixed() {
        const now = new Date();
        const timeStr = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
        const td = todayISO();
        const logs = LocalDB.get('habit_logs') || [];
        (LocalDB.get('habits') || []).filter(h => h.active === 1 && !h.is_deleted).forEach(habit => {
            const t = habit.alarm_time || habit.target_time;
            if (!t || t.substring(0, 5) !== timeStr) return;
            if (logs.some(l => String(l.habit_id) === String(habit.id) && l.date === td)) return;
            sendLocalNotification('Hora do Habito!', habit.name);
            playBeep(600, 300);
        });
        checkPendingReminders();
    }
    window.checkHabitAlarms = checkHabitAlarmsFixed;

    // --- saveQuickAdd fix ---
    window.saveQuickAdd = function() {
        const type = document.getElementById('create-type').value;
        const title = document.getElementById('create-title').value.trim();
        if (!title) { alert('O titulo e obrigatorio.'); return; }
        if (type === 'task') {
            LocalDB.upsert('tasks', {
                id: Date.now(),
                name: title,
                title: title,
                priority: 'medium',
                status: 'todo',
                points_reward: 10,
                created_at: new Date().toISOString()
            });
            loadTasks();
        } else {
            const time = document.getElementById('create-time')?.value || '';
            const desc = document.getElementById('create-desc')?.value || '';
            const freq = document.getElementById('create-freq')?.value || 'daily';
            const icon = document.getElementById('create-icon')?.value || 'fa-fire';
            const xp = parseInt(document.getElementById('create-xp')?.value || '50', 10);
            let days = [1,2,3,4,5];
            if (freq === 'weekdays') days = [1,2,3,4,5];
            else if (freq === 'weekends') days = [0,6];
            else days = [0,1,2,3,4,5,6];
            LocalDB.upsert('habits', {
                id: Date.now(),
                name: title,
                description: desc,
                active: 1,
                target_time: time,
                alarm_time: time,
                icon,
                xp_reward: xp,
                days_of_week: days,
                period: 'morning',
                created_at: new Date().toISOString()
            });
            loadHabits();
            syncHabitReminders();
        }
        closeCreateModal();
        backgroundSync();
    };

    // --- Goals form ---
    let editingGoalId = null;
    window.openGoalForm = function(goalId) {
        editingGoalId = goalId || null;
        const goals = LocalDB.get('nexus_goals') || [];
        const g = goalId ? goals.find(x => String(x.id) === String(goalId)) : null;
        document.getElementById('goal-form-title').textContent = g ? 'Editar Meta' : 'Nova Meta';
        document.getElementById('goal-form-name').value = g ? g.name : '';
        document.getElementById('goal-form-description').value = g ? (g.description || '') : '';
        document.getElementById('goal-form-target-date').value = g ? (g.target_date || '') : '';
        document.getElementById('goal-form-progress').value = g ? (g.progress || 0) : 0;
        document.getElementById('goal-form-progress-label').textContent = g ? (g.progress || 0) : 0;
        document.getElementById('goal-form-status').value = g ? (g.status || 'active') : 'active';
        document.getElementById('goal-form-delete-btn').style.display = g ? 'block' : 'none';
        document.getElementById('goal-form-modal').style.display = 'flex';
    };

    window.saveGoalForm = function() {
        const name = document.getElementById('goal-form-name')?.value?.trim();
        if (!name) return;
        const payload = {
            name,
            description: document.getElementById('goal-form-description')?.value || '',
            target_date: document.getElementById('goal-form-target-date')?.value || null,
            progress: parseInt(document.getElementById('goal-form-progress')?.value || '0', 10),
            status: document.getElementById('goal-form-status')?.value || 'active'
        };
        if (payload.progress >= 100) payload.status = 'achieved';
        if (editingGoalId) {
            const goals = LocalDB.get('nexus_goals');
            const idx = goals.findIndex(g => String(g.id) === String(editingGoalId));
            if (idx !== -1) { goals[idx] = { ...goals[idx], ...payload }; LocalDB.set('nexus_goals', goals); }
        } else {
            LocalDB.upsert('nexus_goals', { id: Date.now(), ...payload });
        }
        document.getElementById('goal-form-modal').style.display = 'none';
        editingGoalId = null;
        loadGoals();
    };

    window.deleteGoalForm = function() {
        if (!editingGoalId) return;
        const goals = LocalDB.get('nexus_goals');
        const idx = goals.findIndex(g => String(g.id) === String(editingGoalId));
        if (idx !== -1) { goals[idx].is_deleted = true; LocalDB.set('nexus_goals', goals); }
        document.getElementById('goal-form-modal').style.display = 'none';
        editingGoalId = null;
        loadGoals();
    };

    window.promptAddGoal = function() { openGoalForm(); };

    window.loadGoals = function() {
        const container = document.getElementById('goals-list');
        if (!container) return;
        const all = (LocalDB.get('nexus_goals') || []).filter(t => !t.is_deleted);
        const active = all.filter(t => t.status !== 'achieved');
        const archived = all.filter(t => t.status === 'achieved');
        container.innerHTML = active.length ? active.map(t => `
            <div class="list-item glass" onclick="openGoalForm(${t.id})" style="cursor:pointer">
                <div class="item-main"><span class="item-title">${escapeHtml(t.name)}</span>
                <span class="item-subtitle">${t.progress || 0}% · ${t.description || ''}</span></div>
            </div>`).join('') : '<div style="text-align:center;color:var(--text-secondary);padding:20px">Sem metas ativas.<button onclick="openGoalForm()" style="margin-top:12px;background:var(--accent-primary);border:none;color:white;padding:10px 18px;border-radius:8px">Criar meta</button></div>';
        const archSec = document.getElementById('goals-archived-section');
        const archList = document.getElementById('goals-archived-list');
        if (archived.length && archSec && archList) {
            archSec.style.display = 'block';
            archList.innerHTML = archived.map(t => `<div class="list-item glass" onclick="openGoalForm(${t.id})" style="opacity:0.7;cursor:pointer"><div class="item-main"><span class="item-title">${escapeHtml(t.name)}</span></div></div>`).join('');
        } else if (archSec) archSec.style.display = 'none';
    };

    // --- Workout form ---
    let editingWorkoutId = null;
    window.openWorkoutForm = function(workoutId) {
        editingWorkoutId = workoutId || null;
        const workouts = LocalDB.get('fitness_workouts') || [];
        const w = workoutId ? workouts.find(x => String(x.id) === String(workoutId)) : null;
        document.getElementById('workout-form-title').textContent = w ? 'Editar Treino' : 'Novo Treino';
        document.getElementById('workout-form-name').value = w ? (w.name || '') : '';
        document.getElementById('workout-form-muscle').value = w ? (w.muscle_group || '') : '';
        document.getElementById('workout-form-date').value = w ? (w.date || todayISO()) : todayISO();
        document.getElementById('workout-form-duration').value = w ? (w.duration_minutes || '') : '';
        document.getElementById('workout-form-calories').value = w ? (w.calories || '') : '';
        document.getElementById('workout-form-notes').value = w ? (w.notes || '') : '';
        renderWorkoutExercises(w ? (w.exercises || []) : []);
        document.getElementById('workout-form-delete-btn').style.display = w ? 'block' : 'none';
        document.getElementById('workout-form-modal').style.display = 'flex';
    };

    window.openWorkoutBuilder = function() { openWorkoutForm(); };

    function renderWorkoutExercises(exs) {
        const list = document.getElementById('workout-exercises-list');
        if (!list) return;
        window._workoutExercises = exs || [];
        list.innerHTML = window._workoutExercises.map((e, i) => `
            <div style="display:flex;gap:8px;align-items:center;background:rgba(255,255,255,0.04);padding:8px;border-radius:8px">
                <span style="flex:1;font-size:0.85rem">${escapeHtml(e.name || e)}</span>
                <button onclick="removeWorkoutExercise(${i})" style="background:none;border:none;color:var(--text-secondary)"><i class="fa-solid fa-xmark"></i></button>
            </div>`).join('');
    }

    window.addWorkoutExercise = function() {
        const name = prompt('Nome do exercicio:');
        if (!name) return;
        window._workoutExercises = window._workoutExercises || [];
        window._workoutExercises.push({ name: name.trim() });
        renderWorkoutExercises(window._workoutExercises);
    };

    window.removeWorkoutExercise = function(i) {
        window._workoutExercises.splice(i, 1);
        renderWorkoutExercises(window._workoutExercises);
    };

    window.saveWorkoutForm = function() {
        const name = document.getElementById('workout-form-name')?.value?.trim();
        if (!name) return;
        const payload = {
            name,
            muscle_group: document.getElementById('workout-form-muscle')?.value || '',
            date: document.getElementById('workout-form-date')?.value || todayISO(),
            duration_minutes: parseInt(document.getElementById('workout-form-duration')?.value || '0', 10) || null,
            calories: parseInt(document.getElementById('workout-form-calories')?.value || '0', 10) || null,
            notes: document.getElementById('workout-form-notes')?.value || '',
            exercises: window._workoutExercises || []
        };
        if (editingWorkoutId) {
            const workouts = LocalDB.get('fitness_workouts');
            const idx = workouts.findIndex(w => String(w.id) === String(editingWorkoutId));
            if (idx !== -1) { workouts[idx] = { ...workouts[idx], ...payload }; LocalDB.set('fitness_workouts', workouts); }
        } else {
            LocalDB.upsert('fitness_workouts', { id: Date.now(), ...payload, created_at: new Date().toISOString() });
            awardXP(25, 'Treino registrado');
        }
        document.getElementById('workout-form-modal').style.display = 'none';
        editingWorkoutId = null;
        loadFitness();
    };

    window.deleteWorkoutForm = function() {
        if (!editingWorkoutId) return;
        const workouts = LocalDB.get('fitness_workouts');
        const idx = workouts.findIndex(w => String(w.id) === String(editingWorkoutId));
        if (idx !== -1) { workouts[idx].is_deleted = true; LocalDB.set('fitness_workouts', workouts); }
        document.getElementById('workout-form-modal').style.display = 'none';
        editingWorkoutId = null;
        loadFitness();
    };

    window.loadFitness = function() {
        const container = document.getElementById('fitness-list');
        if (!container) return;
        updateFitnessStats();
        const data = (LocalDB.get('fitness_workouts') || []).filter(t => !t.is_deleted)
            .sort((a, b) => (b.date || b.created_at || '').localeCompare(a.date || a.created_at || ''));
        container.innerHTML = data.length ? data.slice(0, 15).map(t => `
            <div class="list-item glass" onclick="openWorkoutForm(${t.id})" style="cursor:pointer">
                <div class="item-main"><span class="item-title">${escapeHtml(t.name || 'Treino')}</span>
                <span class="item-subtitle">${escapeHtml(t.muscle_group || '')} · ${t.duration_minutes || ''} min</span></div>
            </div>`).join('') : '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;">Nenhum treino.</div>';
    };

    // --- Studies: subjects grid ---
    function loadSubjectsGrid() {
        const grid = document.getElementById('subjects-grid');
        if (!grid) return;
        const notebooks = LocalDB.get('study_notebooks') || [];
        const notes = (LocalDB.get('study_notes') || []).filter(n => !n.is_deleted);
        if (!notebooks.length) {
            grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text-secondary);padding:20px">Sem materias. Crie a primeira!</div>';
            return;
        }
        grid.innerHTML = notebooks.map(nb => {
            const count = notes.filter(n => String(n.notebook_id) === String(nb.id)).length;
            const coverStyle = nb.cover_image ? `background-image:url('${nb.cover_image}')` : 'background:linear-gradient(135deg,#6c5ce7,#a29bfe)';
            return `<div class="subject-card" onclick="openSubjectDetail('${nb.id}')">
                <div class="subject-card-cover" style="${coverStyle}"></div>
                <div class="subject-card-body"><div class="subject-card-name">${nb.icon || ''} ${escapeHtml(nb.name)}</div>
                <div class="subject-card-count">${count} nota${count !== 1 ? 's' : ''}</div></div>
            </div>`;
        }).join('');
    }

    window.openSubjectForm = function() {
        document.getElementById('subject-form-modal').style.display = 'flex';
        document.getElementById('subject-form-name').value = '';
        document.getElementById('subject-form-icon').value = '📚';
        document.getElementById('subject-form-cover').value = '';
    };

    window.saveSubjectForm = function() {
        const name = document.getElementById('subject-form-name')?.value?.trim();
        if (!name) return;
        const nb = {
            id: Date.now().toString(),
            name,
            icon: document.getElementById('subject-form-icon')?.value || '📚',
            cover_image: document.getElementById('subject-form-cover')?.value || null,
            created_at: new Date().toISOString()
        };
        const notebooks = LocalDB.get('study_notebooks') || [];
        notebooks.push(nb);
        LocalDB.set('study_notebooks', notebooks);
        document.getElementById('subject-form-modal').style.display = 'none';
        loadStudies();
    };

    window.openNewNotebook = window.openSubjectForm;

    window.openSubjectDetail = function(notebookId) {
        currentNotebookId = notebookId;
        const nb = (LocalDB.get('study_notebooks') || []).find(n => String(n.id) === String(notebookId));
        const view = document.getElementById('subject-detail-view');
        if (!view || !nb) return;
        document.getElementById('subject-detail-title').textContent = (nb.icon || '') + ' ' + nb.name;
        view.style.display = 'block';
        const notes = (LocalDB.get('study_notes') || []).filter(n => !n.is_deleted && String(n.notebook_id) === String(notebookId));
        const list = document.getElementById('subject-notes-list');
        list.innerHTML = notes.length ? notes.map(n => renderNoteCard(n)).join('') : '<div style="text-align:center;padding:30px;color:var(--text-secondary)">Sem notas</div>';
    };

    window.closeSubjectDetail = function() {
        document.getElementById('subject-detail-view').style.display = 'none';
        currentNotebookId = null;
    };

    window.openSubjectMenu = function(ev) {
        ev.stopPropagation();
        const popup = document.getElementById('subject-menu-popup');
        if (popup) {
            popup.style.display = 'block';
            popup.style.top = (ev.clientY + 10) + 'px';
            popup.style.left = (ev.clientX - 120) + 'px';
        }
        setTimeout(() => document.addEventListener('click', closeSubjectMenu, { once: true }), 50);
    };

    function closeSubjectMenu() {
        const popup = document.getElementById('subject-menu-popup');
        if (popup) popup.style.display = 'none';
    }

    window.changeSubjectCover = function() {
        const url = prompt('URL da imagem de capa:');
        if (!url || !currentNotebookId) return;
        const notebooks = LocalDB.get('study_notebooks') || [];
        const idx = notebooks.findIndex(n => String(n.id) === String(currentNotebookId));
        if (idx !== -1) { notebooks[idx].cover_image = url; LocalDB.set('study_notebooks', notebooks); loadStudies(); openSubjectDetail(currentNotebookId); }
        closeSubjectMenu();
    };

    window.renameSubject = function() {
        const name = prompt('Novo nome:');
        if (!name || !currentNotebookId) return;
        const notebooks = LocalDB.get('study_notebooks') || [];
        const idx = notebooks.findIndex(n => String(n.id) === String(currentNotebookId));
        if (idx !== -1) { notebooks[idx].name = name.trim(); LocalDB.set('study_notebooks', notebooks); loadStudies(); openSubjectDetail(currentNotebookId); }
        closeSubjectMenu();
    };

    window.deleteSubject = function() {
        if (!currentNotebookId || !confirm('Excluir materia e manter notas sem caderno?')) return;
        const notebooks = LocalDB.get('study_notebooks') || [];
        const filtered = notebooks.filter(n => String(n.id) !== String(currentNotebookId));
        LocalDB.set('study_notebooks', filtered);
        closeSubjectDetail();
        loadStudies();
        closeSubjectMenu();
    };

    function extractNoteTitleFromEditor() {
        const editor = document.getElementById('note-content-rich');
        if (!editor) return 'Sem titulo';
        const h1 = editor.querySelector('h1');
        if (h1 && h1.textContent.trim()) return h1.textContent.trim();
        const text = (editor.innerText || '').trim().split('\n').find(l => l.trim());
        return text ? text.substring(0, 80) : 'Sem titulo';
    }

    window.saveNote = function() {
        const editor = document.getElementById('note-content-rich');
        const hidden = document.getElementById('note-content');
        if (editor && hidden) hidden.value = editor.innerHTML;
        const title = extractNoteTitleFromEditor();
        const content = hidden ? hidden.value : '';
        const tags = document.getElementById('note-tags')?.value || '';
        const subject = document.getElementById('note-subject')?.value || '';
        const notebookId = document.getElementById('note-notebook')?.value || currentNotebookId || '';
        if (!title && !content) { showInAppNotification('Escreva algo primeiro!', 'warn'); return; }
        const notes = LocalDB.get('study_notes') || [];
        const now = new Date().toISOString();
        if (editingNoteId) {
            const idx = notes.findIndex(n => String(n.id) === String(editingNoteId));
            if (idx !== -1) notes[idx] = { ...notes[idx], title, content, tags, subject, notebook_id: notebookId, updated_at: now };
        } else {
            notes.push({ id: Date.now().toString(), title, content, tags, subject, notebook_id: notebookId, created_at: now, updated_at: now });
            awardXP(15, 'Nova nota');
        }
        LocalDB.set('study_notes', notes);
        if (window._tempCoverImage || window._tempIcon) {
            const saved = editingNoteId ? notes.find(n => String(n.id) === String(editingNoteId)) : notes[notes.length - 1];
            if (saved) {
                if (window._tempCoverImage) { saved.cover_image = window._tempCoverImage; window._tempCoverImage = null; }
                if (window._tempIcon) { saved.icon = window._tempIcon; window._tempIcon = null; }
                LocalDB.set('study_notes', notes);
            }
        }
        closeNoteEditor();
        loadStudies();
        showInAppNotification('Nota salva!', 'success');
    };

    window.insertYouTubeEmbed = function() {
        const url = document.getElementById('yt-url-input')?.value?.trim();
        if (!url) return;
        const videoId = extractYouTubeId(url);
        if (!videoId) { alert('URL invalida'); return; }
        closeYouTubeModal();
        const editor = document.getElementById('note-content-rich');
        if (!editor) return;
        editor.focus();
        const embedSrc = getYouTubeEmbedSrc(videoId);
        const embedHTML = `<div class="yt-embed-block" contenteditable="false">
            <iframe
                src="${embedSrc}"
                title="YouTube video player"
                loading="lazy"
                referrerpolicy="strict-origin-when-cross-origin"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen></iframe>
        </div><p><br></p>`;
        document.execCommand('insertHTML', false, embedHTML);
        saveNoteDebounced();
    };

    window.filterNoteLinkList = function(query) {
        const container = document.getElementById('note-link-list');
        if (!container) return;
        const notes = LocalDB.getAll('study_notes') || [];
        const filtered = query ? notes.filter(n => (n.title || '').toLowerCase().includes(query.toLowerCase())) : notes;
        container.innerHTML = filtered.length ? filtered.map(note => `
            <div class="slash-item" onclick="openNoteById('${note.id}')"><span class="slash-icon">📎</span><div><b>${escapeHtml(note.title || 'Sem titulo')}</b></div></div>`).join('') : '<div style="padding:20px;text-align:center;color:var(--text-secondary)">Nenhuma nota</div>';
    };

    window.openNoteById = function(id) {
        const notes = LocalDB.getAll('study_notes') || [];
        const note = notes.find(n => String(n.id) === String(id));
        if (note) openNoteEditor(note.id, note.notebook_id || null);
    };

    function renderBacklinksFixed(noteId) {
        const panel = document.getElementById('backlinks-panel');
        const list = document.getElementById('backlinks-list');
        if (!panel || !list || !noteId) { if (panel) panel.style.display = 'none'; return; }
        const notes = LocalDB.getAll('study_notes') || [];
        const backlinks = notes.filter(n => String(n.id) !== String(noteId) && n.content && n.content.includes(String(noteId)));
        if (!backlinks.length) { panel.style.display = 'none'; return; }
        panel.style.display = 'block';
        list.innerHTML = backlinks.map(bl => `<div style="padding:10px;background:rgba(255,255,255,0.05);border-radius:8px;cursor:pointer" onclick="openNoteById('${bl.id}')">${escapeHtml(bl.title || 'Nota')}</div>`).join('');
    }
    window.renderBacklinks = renderBacklinksFixed;

    window.toggleToolbarOverflow = function(ev) {
        ev.stopPropagation();
        const menu = document.getElementById('rt-overflow-menu');
        if (menu) menu.style.display = menu.style.display === 'none' ? 'flex' : 'none';
    };

    const _loadStudiesOrig = window.loadStudies;
    window.loadStudies = function() {
        if (typeof _loadStudiesOrig === 'function') _loadStudiesOrig();
        loadSubjectsGrid();
        if (typeof loadNotebooksGrid === 'function') loadNotebooksGrid();
        if (typeof ensureChartJs === 'function') ensureChartJs().then(() => setTimeout(renderStudyCharts, 100));
    };

    window.openFinanceOverflow = function(ev) {
        ev.stopPropagation();
        showToast('Mais acoes de financas em breve');
    };

    // Boot: sync reminders + load budget
    document.addEventListener('DOMContentLoaded', () => {
        const budgetEl = document.getElementById('nexus_daily_budget');
        const stored = localStorage.getItem('nexus_daily_budget');
        if (budgetEl && stored) budgetEl.value = stored;
        syncTaskReminders();
        syncHabitReminders();
        NexusCalendar.updateDateLabels();
    });

    setInterval(checkPendingReminders, 30000);

})();

// ================================================================
