// Offline-First Data Operations
// ----------------------------------------------------

function syncUserStatsToNexusUser() {
    const stats = LocalDB.get('user_stats') || { xp: 0, points: 0, level: 1 };
    const user = LocalDB.getSingle('nexus_user', 1) || { id: 1, name: 'Comandante' };
    user.xp = stats.xp || 0;
    user.points = stats.points || 0;
    user.level = stats.level || 1;
    LocalDB.upsert('nexus_user', user);
}

function loadUserStats() {
    syncUserStatsToNexusUser();
    const stats = LocalDB.get('user_stats') || { xp: 0, level: 1, points: 0 };
    const user = LocalDB.getSingle('nexus_user', 1) || { name: 'Comandante' };
    setTextIfPresent('user-level', stats.level);
    setTextIfPresent('user-name', user.name || 'Comandante');
    setTextIfPresent('val-xp', stats.xp);
    setTextIfPresent('val-points', stats.points);
}

function loadVideos() {
    const container = document.getElementById('videos-list');
    if (!container) return;
    const data = LocalDB.get('nexus_videos').filter(v => !v.is_deleted);
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhum vídeo salvo offline.</div>';
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
    if (typeof filterHabits === 'function') {
        const active = document.querySelector('#view-habits .study-chip.active');
        filterHabits(active?.dataset?.filter || 'all', active || null);
        return;
    }
    const container = document.getElementById('habits-list');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;">Nenhum hábito cadastrado.</div>';
}

window.toggleHabit = function(id) {
    toggleHabitDirect(id);
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
    if (task) {
        task.done_at = new Date().toISOString();
        task.status = 'done';
        task.completed = 1;
        LocalDB.upsert('tasks', task);
        awardXP(task.points_reward || 10, 'Tarefa concluida');
        loadTasks();
        backgroundSync();
    }
};

function loadFinances() {
    const container = document.getElementById('finance-list');
    const data = LocalDB.get('finance_transactions').filter(t => !t.is_deleted).sort((a,b) => (b.occurred_at || b.created_at || '').localeCompare(a.occurred_at || a.created_at || ''));
    
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Sem transações.</div>';
    data.slice(0, 15).forEach(t => {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        el.innerHTML = `<div class="item-main"><span class="item-title">${t.description || 'Transação'}</span><span class="item-subtitle" style="color:${t.type==='income'?'#00b894':'#fd79a8'}">${t.type==='income'?'+':'-'} $${t.amount}</span></div>`;
        container.appendChild(el);
    });
}

// ----------------------------------------------------
// ----------------------------------------------------
// New Offline Modules
// ----------------------------------------------------

function loadShop() {
    const container = document.getElementById('shop-list');
    if (!container) return;
    ensureDefaultRewards();
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
        container.innerHTML = '<div style="text-align:center; color:var(--text-secondary); margin-top:20px; padding:20px;"><i class="fa-solid fa-store" style="font-size:2rem;opacity:0.4;margin-bottom:10px;display:block"></i>Nenhuma recompensa ainda.<br><button onclick="ensureDefaultRewards();loadShop()" style="margin-top:12px;background:var(--accent-primary);border:none;color:white;padding:10px 18px;border-radius:8px;cursor:pointer;font-family:inherit">Carregar recompensas padrão</button></div>';
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
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px; padding:20px;"><i class="fa-solid fa-bullseye" style="font-size:2rem;opacity:0.4;margin-bottom:10px;display:block"></i>Sem metas ativas.<br><button onclick="promptAddGoal()" style="margin-top:12px;background:var(--accent-primary);border:none;color:white;padding:10px 18px;border-radius:8px;cursor:pointer;font-family:inherit">Criar primeira meta</button></div>';
    data.forEach(t => {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        el.innerHTML = `<div class="item-main"><span class="item-title">${t.name}</span><span class="item-subtitle">Progresso: ${t.progress || 0}%</span></div>
            <button class="item-action" style="width:auto;padding:0 12px" onclick="updateGoalProgress(${t.id})">+10%</button>`;
        container.appendChild(el);
    });
}

window.promptAddGoal = function() {
    const name = prompt('Nome da meta:');
    if (!name || !name.trim()) return;
    LocalDB.upsert('nexus_goals', {
        id: Date.now(),
        name: name.trim(),
        progress: 0,
        status: 'active'
    });
    loadGoals();
    showToast('Meta criada!');
};

window.updateGoalProgress = function(id) {
    const goals = LocalDB.get('nexus_goals');
    const goal = goals.find(g => g.id === id);
    if (!goal) return;
    goal.progress = Math.min(100, (goal.progress || 0) + 10);
    if (goal.progress >= 100) goal.status = 'achieved';
    LocalDB.upsert('nexus_goals', goal);
    loadGoals();
    showToast('Progresso atualizado!');
};

function updateFitnessStats() {
    const workouts = LocalDB.get('fitness_workouts').filter(t => !t.is_deleted);
    const now = new Date();
    const weekAgo = new Date(now);
    weekAgo.setDate(weekAgo.getDate() - 7);
    const weekCount = workouts.filter(w => {
        const d = new Date(w.date || w.created_at || 0);
        return d >= weekAgo;
    }).length;

    const dates = [...new Set(workouts.map(w => (w.date || w.created_at || '').split('T')[0]).filter(Boolean))].sort().reverse();
    let streak = 0;
    const today = now.toISOString().split('T')[0];
    for (let i = 0; i < 60; i++) {
        const d = new Date(now);
        d.setDate(d.getDate() - i);
        const ds = d.toISOString().split('T')[0];
        if (dates.includes(ds)) streak++;
        else if (i > 0) break;
    }
    if (!dates.includes(today) && streak === 0 && dates.length) {
        const last = dates[0];
        const diff = Math.floor((now - new Date(last)) / 86400000);
        if (diff === 1) streak = 1;
    }

    setTextIfPresent('fit-week-count', weekCount);
    setTextIfPresent('fit-streak', streak);
    setTextIfPresent('fit-total', workouts.length);
}

function loadFitness() {
    const container = document.getElementById('fitness-list');
    if (!container) return;
    updateFitnessStats();
    const data = LocalDB.get('fitness_workouts').filter(t => !t.is_deleted)
        .sort((a, b) => (b.date || b.created_at || '').localeCompare(a.date || a.created_at || ''));
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhum treino registrado.</div>';
    data.slice(0, 10).forEach(t => {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        const title = t.name || t.type || 'Treino';
        const sub = t.muscle_group || t.notes || '';
        const meta = t.duration_minutes ? `${t.duration_minutes} min` : (t.date || '').split('T')[0];
        el.innerHTML = `<div class="item-main"><span class="item-title">${escapeHtml(title)}</span><span class="item-subtitle">${escapeHtml(sub || meta)}</span></div>`;
        container.appendChild(el);
    });
}

window.loadVideos = window.loadVideos || loadVideos;
window.loadTasks = window.loadTasks || loadTasks;
window.loadFinances = window.loadFinances || loadFinances;
window.loadFinance = window.loadFinance || loadFinances;
window.loadShop = window.loadShop || loadShop;
window.loadStudies = window.loadStudies || loadStudies;
window.loadGoals = window.loadGoals || loadGoals;
window.loadFitness = window.loadFitness || loadFitness;

window.ensureDefaultRewards = function() {
    const rewards = LocalDB.get('nexus_rewards').filter(r => !r.is_deleted);
    if (rewards.length > 0) return;
    const now = new Date().toISOString();
    LocalDB.set('nexus_rewards', [
        { id: 1, name: 'Pausa Café', cost: 50, description: '15 min de descanso merecido', created_at: now, updated_at: now, sync_status: 'pending' },
        { id: 2, name: 'Episódio Série', cost: 100, description: 'Assistir um episódio favorito', created_at: now, updated_at: now, sync_status: 'pending' },
        { id: 3, name: 'Jantar Especial', cost: 200, description: 'Comida favorita no fim de semana', created_at: now, updated_at: now, sync_status: 'pending' }
    ]);
};

window.discoverIoT = async function() {
    const container = document.getElementById('iot-list');
    if (!container) return;
    const offlineMsg = '<div style="text-align:center;color:var(--text-secondary);margin-top:20px;padding:20px"><i class="fa-solid fa-house-signal" style="font-size:2rem;opacity:0.4;margin-bottom:10px;display:block"></i>Casa IoT requer o Nexus desktop na mesma rede.<br>Use o app desktop para controlar lâmpadas e sensores.</div>';
    if (!navigator.onLine || window.location.protocol === 'file:') {
        container.innerHTML = offlineMsg;
        return;
    }
    container.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-circle-notch fa-spin"></i> Buscando...</div>';
    try {
        const res = await fetch('/api/nexus/iot/discover');
        const data = await res.json();
        if (data && data.devices) {
            container.innerHTML = data.devices.length ? '' : offlineMsg;
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
        } else {
            container.innerHTML = offlineMsg;
        }
    } catch (e) {
        container.innerHTML = offlineMsg;
    }
};

window.promptAddHabit = function() {
    const modal = document.getElementById('create-modal');
    const typeSel = document.getElementById('create-type');
    if (modal && typeSel) {
        typeSel.value = 'habit';
        document.getElementById('habit-options').style.display = 'flex';
        openCreateModal();
        return;
    }
    const name = prompt('Nome do hábito:');
    if (!name || !name.trim()) return;
    LocalDB.upsert('habits', { id: Date.now(), name: name.trim(), active: 1, current_streak: 0, period: 'all' });
    loadHabits();
    backgroundSync();
    showToast('Hábito criado!');
};

window.promptAddTask = function() {
    const modal = document.getElementById('create-modal');
    const typeSel = document.getElementById('create-type');
    if (modal && typeSel) {
        typeSel.value = 'task';
        document.getElementById('habit-options').style.display = 'none';
        openCreateModal();
        return;
    }
    const title = prompt('Título da tarefa:');
    if (!title || !title.trim()) return;
    LocalDB.upsert('tasks', { id: Date.now(), title: title.trim(), name: title.trim(), points_reward: 10 });
    loadTasks();
    backgroundSync();
    showToast('Tarefa criada!');
};

function appendChatBubble(role, text, loading) {
    const hist = document.getElementById('chat-history');
    if (!hist) return null;
    const div = document.createElement('div');
    div.className = 'chat-message ' + (role === 'user' ? 'user-msg' : 'jarvis-msg');
    div.style.cssText = role === 'user'
        ? 'align-self:flex-end;background:rgba(139,92,246,0.25);border:1px solid var(--accent-purple);padding:10px 15px;border-radius:12px;border-bottom-right-radius:2px;max-width:85%'
        : 'align-self:flex-start;background:rgba(0,206,201,0.15);border:1px solid var(--accent-blue);padding:10px 15px;border-radius:12px;border-bottom-left-radius:2px;max-width:85%';
    div.innerHTML = '<p style="margin:0;font-size:0.95rem;color:white">' + (loading ? '<i class="fa-solid fa-circle-notch fa-spin"></i> ' : '') + escapeHtml(text) + '</p>';
    hist.appendChild(div);
    hist.scrollTop = hist.scrollHeight;
    return div;
}

function tryLocalJarvisCommand(text) {
    const t = text.toLowerCase().trim();
    if (/^(oi|olá|ola|hey|jarvis)/.test(t)) {
        return 'Olá! Posso criar hábitos, tarefas, registrar treinos ou ajudar nos estudos. O que precisa?';
    }
    const habitMatch = t.match(/(?:criar|adicionar|novo)\s+h[aá]bito\s+(.+)/i) || t.match(/h[aá]bito:\s*(.+)/i);
    if (habitMatch) {
        const name = habitMatch[1].trim();
        LocalDB.upsert('habits', { id: Date.now(), name, active: 1, current_streak: 0, period: 'all' });
        loadHabits();
        backgroundSync();
        return `Hábito "${name}" criado. Boa sorte mantendo a consistência!`;
    }
    const taskMatch = t.match(/(?:criar|adicionar|nova)\s+tarefa\s+(.+)/i) || t.match(/tarefa:\s*(.+)/i);
    if (taskMatch) {
        const title = taskMatch[1].trim();
        LocalDB.upsert('tasks', { id: Date.now(), title, name: title, points_reward: 10 });
        loadTasks();
        backgroundSync();
        return `Tarefa "${title}" adicionada à sua lista.`;
    }
    if (/quantos\s+cards|srs|flashcard/.test(t)) {
        const cards = LocalDB.get('flashcards').filter(c => !c.is_deleted);
        const due = cards.filter(c => !c.next_review || c.next_review <= new Date().toISOString()).length;
        return `Você tem ${due} flashcards para revisar hoje (${cards.length} no total).`;
    }
    if (/briefing|resumo\s+do\s+dia|hoje/.test(t)) {
        const habits = LocalDB.get('habits').filter(h => h.active === 1 && !h.is_deleted);
        const today = new Date().toISOString().split('T')[0];
        const done = LocalDB.get('habit_logs').filter(l => l.date === today).length;
        const tasks = LocalDB.get('tasks').filter(x => !x.done_at && !x.is_deleted).length;
        return `Hoje: ${done}/${habits.length} hábitos feitos, ${tasks} tarefas pendentes. Foco no ENEM — revise seus cards SRS!`;
    }
    return null;
}

async function pollCommandResult(cmdId, timeoutMs) {
    const supabaseClient = window.nexusSupabase;
    if (!supabaseClient) return null;
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        const { data } = await supabaseClient.from('nexus_commands').select('status,result').eq('id', cmdId).maybeSingle();
        if (data?.status === 'completed' && data.result) {
            try {
                const parsed = JSON.parse(data.result);
                return parsed.reply || parsed.message || data.result;
            } catch (_) {
                return data.result;
            }
        }
        if (data?.status === 'error') return 'Erro ao processar no desktop. Tente novamente.';
        await new Promise(r => setTimeout(r, 2000));
    }
    return null;
}

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
                    backgroundSync();
                    return;
                }
            }
        } catch (e) {
            console.warn('Chat queue error:', e);
        }
    }

    const fallback = 'Jarvis offline. Comandos locais: "criar hábito X", "criar tarefa Y", "quantos cards". Com o PC ligado, processo ações completas.';
    if (pending) pending.querySelector('p').textContent = fallback;
};

window.requestMorningBriefing = function() {
    const input = document.getElementById('chat-input');
    if (input) input.value = 'briefing do dia';
    sendChatMessage();
};

window.navigateTo = function(viewId) {
    const nav = document.querySelector(`.nav-item[data-target="${viewId}"]`);
    if (nav) nav.click();
};

function loadTodayDashboard() {
    const now = new Date();
    const today = now.toISOString().split('T')[0];
    const dateLabel = document.getElementById('hoje-date-label');
    if (dateLabel) {
        dateLabel.textContent = now.toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'short' });
    }

    const habits = LocalDB.get('habits').filter(h => h.active === 1 && !h.is_deleted);
    const logs = LocalDB.get('habit_logs');
    const doneToday = logs.filter(l => l.date === today).length;
    const tasks = LocalDB.get('tasks').filter(t => !t.done_at && !t.is_deleted);
    const cards = LocalDB.get('flashcards').filter(c => !c.is_deleted);
    const dueCards = cards.filter(c => {
        const nr = c.next_review || c.nextReviewDate;
        return !nr || nr <= now.toISOString();
    }).length;

    const brief = document.getElementById('hoje-briefing-text');
    if (brief) {
        brief.textContent = `${doneToday}/${habits.length} hábitos feitos · ${tasks.length} tarefas · ${dueCards} cards SRS para revisar.`;
    }

    const list = document.getElementById('hoje-habits-checklist');
    if (list) {
        const morning = habits.filter(h => !h.period || h.period === 'all' || h.period === 'morning').slice(0, 5);
        if (!morning.length) {
            list.innerHTML = '<div style="font-size:0.85rem;color:var(--text-secondary)">Nenhum hábito. Toque em + Hábito para começar.</div>';
        } else {
            list.innerHTML = morning.map(h => {
                const done = logs.some(l => String(l.habit_id) === String(h.id) && l.date === today);
                return `<div class="list-item glass" style="padding:10px 12px;display:flex;justify-content:space-between;align-items:center">
                    <span style="font-size:0.9rem">${escapeHtml(h.name)}</span>
                    <button class="icon-btn ${done ? 'done' : ''}" style="width:28px;height:28px" onclick="toggleHabitDirect('${h.id}');loadTodayDashboard()">
                        <i class="fa-solid fa-check"></i>
                    </button>
                </div>`;
            }).join('');
        }
    }
}

window.toggleIoT = function(ip, turnOn) {
    showToast('IoT disponível apenas com Nexus desktop na mesma rede.');
};

