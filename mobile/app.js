window.onerror = function(msg, url, line, col, error) {
    alert("ERRO JS: " + msg + " na linha " + line);
    return false;
};

// Supabase Configuration
const supabaseUrl = 'https://oxwpwfhjyiiwdhcggtlt.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im94d3B3ZmhqeWlpd2RoY2dndGx0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExMzA3NjAsImV4cCI6MjA5NjcwNjc2MH0.mIOis8ugOlubw2P6Z8_TuNeLukvltsXAlPb-ttaaOpY';
var nexusDb = null;
if (window.supabase) {
    nexusDb = window.supabase.createClient(supabaseUrl, supabaseKey);
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
        return rows.find(function(r) { return r.id === id; });
    }
    static upsert(table, record) {
        const rows = this.get(table);
        const idx = rows.findIndex(function(r) { return r.id === record.id; });
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
function backgroundSync() { return; 
    if (!navigator.onLine || !supabase) return;
    try {
        const tables = ['nexus_user', 'habits', 'tasks', 'finance_transactions', 'nexus_rewards', 'study_notes', 'nexus_goals', 'fitness_workouts'];
        let lastSync = localStorage.getItem('nexus_last_sync') || '1970-01-01T00:00:00Z';
        let newSyncTime = lastSync;

        for (let table of tables) {
            // Pull
            // await sync
            if (remoteData && remoteData.length > 0) {
                remoteData.forEach(function(remoteRow) {
                    const localRow = LocalDB.getSingle(table, remoteRow.id);
                    if (!localRow || remoteRow.updated_at > (localRow.updated_at || '')) {
                        const rows = LocalDB.get(table);
                        const idx = rows.findIndex(function(r) { return r.id === remoteRow.id; });
                        if (idx > -1) Object.assign(rows[idx], remoteRow);
                        else rows.push(remoteRow);
                        LocalDB.set(table, rows);
                        if (remoteRow.updated_at > newSyncTime) newSyncTime = remoteRow.updated_at;
                    }
                });
            }

            // Push
            const localData = LocalDB.get(table).filter(function(r) { return (r.updated_at || '') > lastSync; });
            for (let localRow of localData) {
                // Remove UI-only fields if necessary
                var cleanRow = Object.assign({}, localRow);
                // await upsert
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
document.querySelectorAll('.nav-item').forEach(function(item) {
    item.addEventListener('click', function(e) {
        e.preventDefault();
        
        document.querySelectorAll('.nav-item').forEach(function(nav) { nav.classList.remove('active'); });
        item.classList.add('active');
        
        const targetId = item.getAttribute('data-target');
        document.querySelectorAll('.view').forEach(function(view) { view.classList.remove('active-view'); });
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
function requestNotificationPermission() {
    if (!("Notification" in window)) return;
    if (Notification.permission === "granted") return;
    
    if (Notification.permission !== "denied") {
        Notification.requestPermission();
    }
}

function sendLocalNotification(title, body) {
    // Use native bridge if available (WebView Android)
    if (window.AndroidNative && window.AndroidNative.showNotification) {
        window.AndroidNative.showNotification(title, body);
        return;
    }
    // Fallback: Web Notification API (only works in browser, not file:// WebView)
    if (typeof Notification !== 'undefined' && Notification.permission === "granted") {
        try {
            navigator.serviceWorker.ready.then(function(registration) {
                registration.showNotification(title, {
                    body: body,
                    icon: 'https://cdn-icons-png.flaticon.com/512/8244/8244509.png',
                    vibrate: [200, 100, 200]
                });
            });
        } catch(e) { console.log('SW notification not available:', e); }
    } else {
        // Last resort: in-app banner
        showInAppNotification(title + ': ' + body);
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
    data.forEach(function(v) {
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
    const data = LocalDB.get('habits').filter(function(h) { return h.active === 1 && !h.is_deleted; });
    
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhum hÃ¡bito cadastrado.</div>';
    data.forEach(function(habit) {
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
    const data = LocalDB.get('tasks').filter(function(t) { return !t.done_at && !t.is_deleted; });
    
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Sem tarefas ativas!</div>';
    data.forEach(function(t) {
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
    const data = LocalDB.get('finance_transactions').filter(function(t) { return !t.is_deleted; }).sort(function(a,b) { return (b.occurred_at || b.created_at || '').localeCompare(a.occurred_at || a.created_at || ''); });
    
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Sem transaÃ§Ãµes.</div>';
    data.slice(0, 15).forEach(function(t) {
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
    const data = LocalDB.get('nexus_rewards').filter(function(r) { return !r.is_deleted; });
    if(data.length) {
        container.innerHTML = '';
        data.forEach(function(item) {
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
    const data = LocalDB.get('study_notes').filter(function(t) { return !t.is_deleted; });
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhuma nota de estudo.</div>';
    data.forEach(function(t) {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        el.innerHTML = `<div class="item-main"><span class="item-title">${t.title}</span><span class="item-subtitle">${t.subject || 'Geral'}</span></div>`;
        container.appendChild(el);
    });
}

function loadGoals() {
    const container = document.getElementById('goals-list');
    if(!container) return;
    const data = LocalDB.get('nexus_goals').filter(function(t) { return !t.is_deleted && t.status !== 'achieved'; });
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Sem metas ativas.</div>';
    data.forEach(function(t) {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        el.innerHTML = `<div class="item-main"><span class="item-title">${t.name}</span><span class="item-subtitle">Progresso: ${t.progress || 0}%</span></div>`;
        container.appendChild(el);
    });
}

function loadFitness() {
    const container = document.getElementById('fitness-list');
    if(!container) return;
    const data = LocalDB.get('fitness_workouts').filter(function(t) { return !t.is_deleted; });
    container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhum treino registrado.</div>';
    data.slice(0,10).forEach(function(t) {
        const el = document.createElement('div');
        el.className = 'list-item glass';
        el.innerHTML = `<div class="item-main"><span class="item-title">${t.type}</span><span class="item-subtitle">${t.duration_minutes || 0} min | ${t.calories_burned || 0} kcal</span></div>`;
        container.appendChild(el);
    });
}

window.promptAddGoal = function() {
    const name = prompt("Nome da Meta:");
    if (!name) return;
    const goal = {
        id: Date.now(),
        name: name,
        progress: 0,
        status: 'active',
        created_at: new Date().toISOString()
    };
    LocalDB.upsert('nexus_goals', goal);
    loadGoals();
    backgroundSync();
};

window.promptAddWorkout = function() {
    const type = prompt("Tipo de Treino (ex: Musculação, Corrida):");
    if (!type) return;
    const min = parseInt(prompt("Duração (minutos):", "30")) || 30;
    const workout = {
        id: Date.now(),
        type: type,
        duration_minutes: min,
        calories_burned: min * 8, // estimate
        created_at: new Date().toISOString()
    };
    LocalDB.upsert('fitness_workouts', workout);
    loadFitness();
    backgroundSync();
};

window.discoverIoT = function() {
    if (!nexusDb) return;
    const container = document.getElementById('iot-list');
    if(container) container.innerHTML = '<div class="loading-spinner"><div style="grid-column: span 2; text-align: center;"><i class="fa-solid fa-circle-notch fa-spin"></i> Buscando na rede da sua casa...</div></div>';
    
    // Command the PC to discover devices
    nexusDb.from('nexus_commands').insert([{
        command: 'DISCOVER_IOT',
        source: 'mobile_iot',
        status: 'pending'
    }]).then(function() {
        // Poll for result
        var attempts = 0;
        var poll = setInterval(function() {
            attempts++;
            if (attempts > 10) { 
                clearInterval(poll); 
                if(container) container.innerHTML = '<div style="grid-column: span 2; text-align:center; color:red; margin-top:20px;">Timeout ao buscar dispositivos.</div>';
                return; 
            }
            nexusDb.from('nexus_commands')
                .select('result, status')
                .eq('source', 'mobile_iot')
                .eq('status', 'completed')
                .order('created_at', { ascending: false })
                .limit(1)
                .then(function(res) {
                    if (res.data && res.data.length > 0 && res.data[0].result) {
                        clearInterval(poll);
                        try {
                            const data = JSON.parse(res.data[0].result);
                            if(container) {
                                container.innerHTML = data.length ? '' : '<div style="grid-column: span 2; text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhum dispositivo encontrado.</div>';
                                data.forEach(function(dev) {
                                    const el = document.createElement('div');
                                    el.className = 'glass';
                                    el.style.cssText = 'padding: 15px; border-radius: 16px; text-align: center; border: 1px solid ' + (dev.status === 'LIGADO' ? 'var(--accent-blue)' : 'var(--border-glass)') + ';';
                                    el.innerHTML = `
                                        <i class="fa-solid fa-lightbulb fa-2x" style="color: ${dev.status === 'LIGADO' ? 'var(--accent-blue)' : 'var(--text-secondary)'}; margin-bottom: 10px;"></i>
                                        <p style="margin: 0; font-weight: bold; color: white;">${dev.name}</p>
                                        <p style="margin: 0; font-size: 0.8rem; color: ${dev.status === 'LIGADO' ? 'var(--accent-green)' : 'var(--text-secondary)'};">${dev.status}</p>
                                        <button onclick="toggleIoT('${dev.ip}', ${dev.status === 'LIGADO' ? 'false' : 'true'})" style="margin-top: 10px; background: ${dev.status === 'LIGADO' ? 'var(--accent-pink)' : 'var(--accent-green)'}; color: white; border: none; padding: 5px 15px; border-radius: 8px;">${dev.status === 'LIGADO' ? 'Desligar' : 'Ligar'}</button>
                                    `;
                                    container.appendChild(el);
                                });
                            }
                        } catch(e) {
                            if(container) container.innerHTML = '<div style="grid-column: span 2; text-align:center; color:red; margin-top:20px;">Erro parseando dispositivos.</div>';
                        }
                    }
                });
        }, 3000);
    });
};

window.toggleIoT = function(ip, turnOn) {
    if (!nexusDb) return;
    const stateStr = turnOn ? 'ON' : 'OFF';
    nexusDb.from('nexus_commands').insert([{
        command: 'TOGGLE_IOT:' + ip + ':' + stateStr,
        source: 'mobile_iot_toggle',
        status: 'pending'
    }]).then(function() {
        alert("Enviado comando para " + (turnOn ? "ligar" : "desligar") + " o dispositivo.");
        setTimeout(discoverIoT, 2000); // refresh list
    });
};

// ----------------------------------------------------
// Realtime Subscription
// ----------------------------------------------------
function setupRealtime() {
    if (!supabase) return;
    nexusDb.channel('custom-all-channel')
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'nexus_user' },
      function(payload) {
          backgroundSync();
      }
    ).on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'tasks' },
      function(payload) { backgroundSync(); }
    ).on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'habits' },
      function(payload) { backgroundSync(); }
    )
    .subscribe();
}

// App Initialization
document.addEventListener('DOMContentLoaded', function() {
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
window.openSettingsModal = function() {
    document.getElementById('settings-modal').classList.add('show');
};

window.closeSettingsModal = function() {
    document.getElementById('settings-modal').classList.remove('show');
};

window.toggleModule = function(moduleId) {
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
    
    modules.forEach(function(mod) {
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
document.addEventListener('DOMContentLoaded', function() {
    applyUiPrefs();
});

// ----------------------------------------------------
// Quick Add Logic (FAB)
// ----------------------------------------------------
window.openCreateModal = function() {
    document.getElementById('create-title').value = '';
    document.getElementById('create-desc').value = '';
    document.getElementById('create-time').value = '08:00';
    document.getElementById('create-modal').classList.add('show');
};

window.closeCreateModal = function() {
    document.getElementById('create-modal').classList.remove('show');
};

document.getElementById('create-type').addEventListener('change', function(e) {
    const opts = document.getElementById('habit-options');
    opts.style.display = e.target.value === 'habit' ? 'flex' : 'none';
});

window.saveQuickAdd = function() {
    var type = document.getElementById('create-type').value;
    var title = document.getElementById('create-title').value.trim();
    if (!title) {
        alert('O t\u00edtulo \u00e9 obrigat\u00f3rio.');
        return;
    }

    if (type === 'task') {
        var newTask = {
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
        var time = document.getElementById('create-time').value;
        var desc = document.getElementById('create-desc').value;
        var icon = document.getElementById('create-icon') ? document.getElementById('create-icon').value : 'fa-fire';
        var freq = document.getElementById('create-freq') ? document.getElementById('create-freq').value : 'daily';
        var xp = document.getElementById('create-xp') ? parseInt(document.getElementById('create-xp').value) || 50 : 50;
        
        var newHabit = {
            id: Date.now(),
            name: title,
            description: desc,
            icon: icon,
            frequency: freq,
            active: 1,
            target_time: time,
            current_streak: 0,
            xp_reward: xp,
            created_at: new Date().toISOString()
        };
        LocalDB.upsert('habits', newHabit);
        loadHabits();
        sendLocalNotification('H\u00e1bito Criado', 'Seu novo h\u00e1bito foi salvo offline.');
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

window.startPomodoro = function() {
    if (pomoActive) return;
    pomoActive = true;
    
    // Play a tiny beep to acknowledge start
    playBeep(400, 100);
    
    pomoInterval = setInterval(function() {
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

window.pausePomodoro = function() {
    pomoActive = false;
    clearInterval(pomoInterval);
};

window.resetPomodoro = function() {
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
        setTimeout(function() { oscillator.stop(); }, duration);
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
    
    const activeHabits = LocalDB.get('habits').filter(function(h) { return h.active === 1 && !h.is_deleted; });
    activeHabits.forEach(function(habit) {
        if (habit.target_time && habit.target_time.substring(0, 5) === timeStr) {
            // Verifica se j foi feito hoje (simplificado, precisaria de uma checkagem real nos logs)
            sendLocalNotification('Hora do Hábito!', habit.name);
            playBeep(600, 300);
            setTimeout(function() { playBeep(600, 300); }, 500);
        }
    });
}

// Add alarm checker to main loop
setInterval(checkHabitAlarms, 30000); // checks every 30 seconds




window.startNexusAI = function() {
    var cmd = prompt("Qual o seu comando para o Nexus (Gemini)?");
    if(cmd) {
        nexusDb.from('nexus_commands').insert([
            { command: cmd, source: 'mobile', status: 'pending' }
        ]).then(function(res) {
            if(res.error) {
                alert("Erro ao enviar comando: " + res.error.message);
            } else {
                alert("Comando enviado para o PC com sucesso!");
            }
        });
    }
};


window.processVideoInsights = function() {
    var url = document.getElementById('video-url').value.trim();
    var promptTxt = document.getElementById('video-prompt').value.trim();
    
    if(!url) {
        alert("Por favor, cole um link do YouTube válido.");
        return;
    }
    
    var fullCommand = "VIDEO_INSIGHT: " + url + " | PROMPT: " + promptTxt;
    
    document.getElementById('video-processing-status').style.display = 'block';
    
    nexusDb.from('nexus_commands').insert([
        { command: fullCommand, source: 'mobile_video', status: 'pending' }
    ]).then(function(res) {
        if(res.error) {
            alert("Erro ao enviar para o PC: " + res.error.message);
            document.getElementById('video-processing-status').style.display = 'none';
        } else {
            // Success
            setTimeout(function() {
                alert("O Jarvis (PC) recebeu o link e está processando o vídeo! Verifique as Anotações depois.");
                document.getElementById('video-url').value = '';
                document.getElementById('video-prompt').value = '';
                document.getElementById('video-processing-status').style.display = 'none';
            }, 1000);
        }
    });
};


window.openNoteEditor = function(noteId = null) {
    document.getElementById('study-main-view').style.display = 'none';
    document.getElementById('note-editor-view').style.display = 'flex';
    document.getElementById('ai-diff-panel').style.display = 'none';
    
    if (noteId) {
        // Load existing note logic here
        // var note = LocalDB.get('study_notes', noteId);
    } else {
        document.getElementById('note-title').value = '';
        document.getElementById('note-subject').value = '';
        document.getElementById('note-content').value = '';
        window.currentNoteId = null;
    }
};

window.closeNoteEditor = function() {
    document.getElementById('note-editor-view').style.display = 'none';
    document.getElementById('study-main-view').style.display = 'block';
};

window.saveNote = function() {
    var title = document.getElementById('note-title').value.trim();
    var subject = document.getElementById('note-subject').value.trim();
    var content = document.getElementById('note-content').value.trim();
    
    if(!title || !content) {
        alert("Título e conteúdo são obrigatórios.");
        return;
    }
    
    var newNote = {
        id: window.currentNoteId || Date.now(),
        subject: title,  // In the DB it's called subject
        general_subject: subject, // new field
        content: content,
        created_at: new Date().toISOString()
    };
    
    LocalDB.upsert('study_notes', newNote);
    
    // If subject is empty, we send a command to Jarvis to auto-summarize it
    if(!subject) {
        nexusDb.from('nexus_commands').insert([
            { command: "AUTO_SUMMARIZE_NOTE: " + newNote.id, source: 'mobile_study', status: 'pending' }
        ]).then(function() {});
    }
    
    alert("Nota salva!");
    closeNoteEditor();
    loadNotes(); // Assuming this exists or will exist
    backgroundSync();
};

window.acceptAiDiff = function() {
    // Logic to accept the AI suggestion
    document.getElementById('ai-diff-panel').style.display = 'none';
    alert("Alteração do Jarvis aplicada!");
};

window.rejectAiDiff = function() {
    // Logic to reject the AI suggestion
    document.getElementById('ai-diff-panel').style.display = 'none';
    // Revert to original content
};


window.syncNexusMemory = function() {
    if(!navigator.onLine) return; // Only sync when online
    
    nexusDb.from('nexus_memory_sync').select('*').then(function(res) {
        if(!res.error && res.data) {
            var memory = {};
            res.data.forEach(function(row) {
                memory[row.key_name] = row.data_json;
            });
            LocalDB.upsert('nexus_memory', { id: 'jarvis_brain', data: memory });
            console.log("Memórias do PC sincronizadas com sucesso!");
        }
    });
};

// Auto-sync memory every 5 minutes if online
setInterval(syncNexusMemory, 300000);
// Trigger once on load
setTimeout(syncNexusMemory, 5000);


window.sendChatMessage = function() {
    var input = document.getElementById('chat-input');
    var msg = input.value.trim();
    if(!msg) return;
    
    // Add user message to UI
    var history = document.getElementById('chat-history');
    var userBubble = document.createElement('div');
    userBubble.className = 'chat-message user-msg';
    userBubble.style.cssText = 'align-self: flex-end; background: rgba(108, 92, 231, 0.4); border: 1px solid var(--accent-purple); padding: 10px 15px; border-radius: 12px; border-bottom-right-radius: 2px; max-width: 85%;';
    userBubble.innerHTML = '<p style="margin: 0; font-size: 0.95rem; color: white;">' + msg + '</p>';
    history.appendChild(userBubble);
    
    input.value = '';
    history.scrollTop = history.scrollHeight;
    
    // Send to nexus_commands
    nexusDb.from('nexus_commands').insert([
        { command: "CHAT: " + msg, source: 'mobile_chat', status: 'pending' }
    ]).then(function() {});
};


window.callTimerInterval = null;
window.callSeconds = 0;

window.toggleJarvisCall = function() {
    var banner = document.getElementById('jarvis-call-banner');
    if (banner.style.display === 'none' || banner.style.display === '') {
        // Start Call
        banner.style.display = 'flex';
        window.callSeconds = 0;
        document.getElementById('jarvis-call-timer').innerText = '00:00';
        window.callTimerInterval = setInterval(function() {
            window.callSeconds++;
            var m = Math.floor(window.callSeconds / 60).toString().padStart(2, '0');
            var s = (window.callSeconds % 60).toString().padStart(2, '0');
            document.getElementById('jarvis-call-timer').innerText = m + ':' + s;
        }, 1000);
        
        // Notify Native Android
        if(window.AndroidNative) {
            window.AndroidNative.startJarvisCall();
        } else {
            console.log("Mocking Jarvis Call (No Native Bridge)");
        }
    } else {
        endJarvisCall();
    }
};

window.endJarvisCall = function() {
    var banner = document.getElementById('jarvis-call-banner');
    banner.style.display = 'none';
    clearInterval(window.callTimerInterval);
    if(window.AndroidNative) {
        window.AndroidNative.stopJarvisCall();
    }
};

window.requestJarvisVision = function() {
    if(window.AndroidNative) {
        window.AndroidNative.captureScreenAndClipboard();
        alert("Jarvis está processando sua tela e área de transferência...");
    } else {
        alert("Visão nativa não disponível neste dispositivo.");
    }
};

// Called by Native Android to insert speech into chat
window.receiveJarvisSpeech = function(text) {
    var history = document.getElementById('chat-history');
    if(history) {
        var bubble = document.createElement('div');
        bubble.className = 'chat-message jarvis-msg';
        bubble.style.cssText = 'align-self: flex-start; background: rgba(0, 206, 201, 0.15); border: 1px solid var(--accent-blue); padding: 10px 15px; border-radius: 12px; border-bottom-left-radius: 2px; max-width: 85%;';
        bubble.innerHTML = '<p style="margin: 0; font-size: 0.95rem; color: white;">' + text + '</p>';
        history.appendChild(bubble);
        history.scrollTop = history.scrollHeight;
    }
};


window.receiveNativeVision = function(data) {
    // Send to nexus_commands for processing
    nexusDb.from('nexus_commands').insert([
        { command: "VISION_CLIPBOARD: " + data, source: 'mobile_vision', status: 'pending' }
    ]).then(function() {
        alert("Dados da tela/clipboard enviados pro Jarvis analisar!");
    });
};

// ====================================================
// PHASE 11: OCR via Camera (Gemini Vision)
// ====================================================
window.triggerOcrCamera = function() {
    if (window.AndroidNative && window.AndroidNative.openNativeCamera) {
        window.AndroidNative.openNativeCamera();
    } else {
        // Fallback: HTML file input with camera capture
        document.getElementById('ocr-file-input').click();
    }
};

// Called by native Java after camera capture
window.receiveCameraImage = function(base64jpeg) {
    var status = document.getElementById('ocr-status');
    if (status) { status.style.display = 'block'; }

    // Send OCR command to Supabase → PC will process with Gemini Vision
    if (nexusDb) {
        nexusDb.from('nexus_commands').insert([{
            command: 'IMAGE_TRANSCRIPT:' + base64jpeg,
            source: 'mobile_ocr',
            status: 'pending'
        }]).then(function() {
            if (status) {
                status.innerHTML = '<i class="fa-solid fa-check"></i> Enviado! O Jarvis irá transcrever e inserir o texto aqui em breve.';
                setTimeout(function() { status.style.display = 'none'; }, 4000);
            }
            // Poll for result every 5s for up to 60s
            var attempts = 0;
            var poll = setInterval(function() {
                attempts++;
                if (attempts > 12) { clearInterval(poll); return; }
                nexusDb.from('nexus_commands')
                    .select('result, status')
                    .eq('source', 'mobile_ocr')
                    .eq('status', 'completed')
                    .order('created_at', { ascending: false })
                    .limit(1)
                    .then(function(res) {
                        if (res.data && res.data.length > 0 && res.data[0].result) {
                            clearInterval(poll);
                            var textarea = document.getElementById('note-content');
                            if (textarea) {
                                textarea.value = (textarea.value ? textarea.value + '\n\n' : '') + res.data[0].result;
                            }
                        }
                    });
            }, 5000);
        });
    }
};

// Fallback: file input handler
window.handleOcrFileSelected = function(event) {
    var file = event.target.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function(e) {
        var base64 = e.target.result.split(',')[1];
        window.receiveCameraImage(base64);
    };
    reader.readAsDataURL(file);
};

// PC returns transcription result and calls this
window.receiveOcrTranscription = function(text) {
    var textarea = document.getElementById('note-content');
    if (textarea) {
        textarea.value = (textarea.value ? textarea.value + '\n\n' : '') + text;
    }
    var status = document.getElementById('ocr-status');
    if (status) { status.style.display = 'none'; }
};

// ====================================================
// PHASE 11: Flashcards Tinder-Style
// ====================================================
window._flashcards = [];
window._fcIndex = 0;
window._fcFlipped = false;

window.showFlashcards = function() {
    // Navigate to studies first
    document.querySelectorAll('.view').forEach(function(v) { v.classList.remove('active-view'); });
    var sv = document.getElementById('view-studies');
    if (sv) sv.classList.add('active-view');

    var fc = document.getElementById('flashcard-view');
    if (fc) {
        fc.style.display = 'flex';
        fc.style.flexDirection = 'column';
    }

    // Load from Supabase or LocalDB
    var cards = LocalDB.get('flashcards');
    if (cards.length === 0) {
        // Demo cards if none exist
        cards = [
            { id: 1, question: 'O que é fotossíntese?', answer: 'Processo pelo qual plantas convertem luz solar em energia química (glicose).', next_review: null, ease: 2.5 },
            { id: 2, question: 'O que é Machine Learning?', answer: 'Subcampo da IA onde sistemas aprendem com dados sem serem explicitamente programados.', next_review: null, ease: 2.5 }
        ];
        LocalDB.set('flashcards', cards);
    }

    // Filter due cards
    var now = new Date().toISOString();
    var due = cards.filter(function(c) { return !c.next_review || c.next_review <= now; });
    if (due.length === 0) due = cards; // show all if none due

    window._flashcards = due;
    window._fcIndex = 0;
    window._fcFlipped = false;
    window.renderFlashcard();
};

window.renderFlashcard = function() {
    var total = window._flashcards.length;
    var idx = window._fcIndex;
    var counter = document.getElementById('fc-counter');
    if (counter) counter.textContent = (idx + 1) + '/' + total;

    var card = window._flashcards[idx];
    if (!card) {
        document.getElementById('fc-front').textContent = '🎉 Todas as cartas revisadas!';
        document.getElementById('fc-back').style.display = 'none';
        return;
    }

    document.getElementById('fc-front').textContent = card.question;
    var back = document.getElementById('fc-back');
    back.textContent = card.answer;
    back.style.display = 'none';
    window._fcFlipped = false;
};

window.flipFlashcard = function() {
    if (window._fcFlipped) return;
    window._fcFlipped = true;
    var back = document.getElementById('fc-back');
    if (back) back.style.display = 'block';
    var card = document.getElementById('flashcard-card');
    if (card) {
        card.style.background = 'rgba(0,206,201,0.1)';
        card.style.borderColor = 'var(--accent-blue)';
    }
};

window.answerFlashcard = function(correct) {
    if (!window._fcFlipped) {
        alert('Toque na carta primeiro para ver a resposta!');
        return;
    }
    var card = window._flashcards[window._fcIndex];
    if (card) {
        // Spaced repetition: SM-2 simplified
        var ease = card.ease || 2.5;
        var interval = correct ? Math.round(ease * (card.interval || 1)) : 1;
        ease = Math.max(1.3, ease + (correct ? 0.1 : -0.2));
        var nextDate = new Date(Date.now() + interval * 86400000).toISOString();
        card.ease = ease;
        card.interval = interval;
        card.next_review = nextDate;
        LocalDB.upsert('flashcards', card);
    }

    // Reset card style
    var cardEl = document.getElementById('flashcard-card');
    if (cardEl) { cardEl.style.background = ''; cardEl.style.borderColor = 'var(--accent-purple)'; }

    window._fcIndex++;
    if (window._fcIndex >= window._flashcards.length) {
        document.getElementById('fc-front').textContent = '🎉 Sessão concluída! +50 XP';
        document.getElementById('fc-back').style.display = 'none';
    } else {
        window.renderFlashcard();
    }
};

window.closeFlashcards = function() {
    var fc = document.getElementById('flashcard-view');
    if (fc) fc.style.display = 'none';
};

// ====================================================
// PHASE 12: Journal (Diário) - Text & Voice
// ====================================================
var _journalRecognition = null;

window.openJournal = function() {
    // Make studies view active
    document.querySelectorAll('.view').forEach(function(v) { v.classList.remove('active-view'); });
    var sv = document.getElementById('view-studies');
    if (sv) sv.classList.add('active-view');

    var jv = document.getElementById('journal-view');
    if (jv) {
        jv.style.display = 'flex';
        jv.style.flexDirection = 'column';
    }
    var dateEl = document.getElementById('journal-date');
    if (dateEl) {
        dateEl.textContent = new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' });
    }
    // Load today's entry if exists
    var today = new Date().toISOString().split('T')[0];
    var entries = LocalDB.get('journal_entries');
    var todayEntry = entries.find(function(e) { return e.date === today; });
    var ta = document.getElementById('journal-content');
    if (ta) ta.value = todayEntry ? (todayEntry.content || '') : '';
};

window.closeJournal = function() {
    var jv = document.getElementById('journal-view');
    if (jv) jv.style.display = 'none';
    if (_journalRecognition) { try { _journalRecognition.stop(); } catch(e) {} }
};

window.startJournalDictation = function() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert('Reconhecimento de voz não suportado neste navegador/WebView.');
        return;
    }
    var btn = document.getElementById('journal-mic-btn');
    var status = document.getElementById('journal-mic-status');

    if (_journalRecognition && _journalRecognition.active) {
        _journalRecognition.stop();
        return;
    }

    _journalRecognition = new SpeechRecognition();
    _journalRecognition.lang = 'pt-BR';
    _journalRecognition.continuous = true;
    _journalRecognition.interimResults = true;
    _journalRecognition.active = true;

    if (btn) btn.style.background = 'linear-gradient(135deg, var(--accent-pink), var(--accent-purple))';
    if (status) status.textContent = '🔴 Gravando... Fale agora';

    var finalTranscript = '';
    _journalRecognition.onresult = function(event) {
        var interim = '';
        for (var i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript + ' ';
            } else {
                interim += event.results[i][0].transcript;
            }
        }
        var ta = document.getElementById('journal-content');
        if (ta) ta.value = finalTranscript + interim;
    };

    _journalRecognition.onend = function() {
        _journalRecognition.active = false;
        if (btn) btn.style.background = 'linear-gradient(135deg,var(--accent-purple),var(--accent-pink))';
        if (status) status.textContent = 'Gravação encerrada. Salve sua entrada!';
    };

    _journalRecognition.start();
};

window.saveJournalEntry = function() {
    var content = (document.getElementById('journal-content') || {}).value;
    if (!content || !content.trim()) { alert('Escreva ou dite algo primeiro!'); return; }

    var today = new Date().toISOString().split('T')[0];
    var entry = {
        id: today,
        date: today,
        content: content,
        device_source: 'mobile', // CONTEXT: from mobile
        updated_at: new Date().toISOString()
    };
    LocalDB.upsert('journal_entries', entry);

    // Queue AI summarization on PC
    if (nexusDb) {
        nexusDb.from('nexus_commands').insert([{
            command: 'SUMMARIZE_JOURNAL:' + today,
            source: 'mobile_journal',
            status: 'pending',
            context: JSON.stringify({ device: 'mobile', date: today })
        }]).then(function() {});
    }

    alert('📖 Entrada do Diário salva! O Jarvis irá analisá-la no PC.');
    window.closeJournal();
};

// ====================================================
// PHASE 12: Device Context Injection
// ====================================================
// Inject device context into every nexus_command
var _originalNexusInsert = null;
function injectDeviceContext() {
    if (!nexusDb) return;
    var deviceCtx = JSON.stringify({
        device: 'mobile',
        user_agent: navigator.userAgent,
        timestamp: new Date().toISOString(),
        location: 'Nexus Mobile App'
    });
    // Store in localStorage so PC can read it from commands
    localStorage.setItem('nexus_device_context', deviceCtx);
}
injectDeviceContext();

// ====================================================
// PHASE 12: Remote Clipboard Control
// ====================================================
// To copy to the PHONE's clipboard
window.copyToLocalClipboard = function(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function() {
            console.log('Copied to mobile clipboard:', text.substring(0, 50));
        }).catch(function() {
            // Fallback
            var ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed'; ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
        });
    }
};

// To copy to the PC clipboard (sends command via Supabase)
window.copyToPcClipboard = function(text) {
    if (nexusDb) {
        nexusDb.from('nexus_commands').insert([{
            command: 'COPY_TO_PC_CLIPBOARD: ' + text,
            source: 'mobile_clipboard',
            status: 'pending'
        }]).then(function() {
            console.log('PC clipboard command sent.');
        });
    }
};

// ====================================================
// PHASE 13: PC → Mobile Push Notifications
// ====================================================
// Poll Supabase every 20s (when active) or 60s (when hidden) for commands directed at mobile
setInterval(function() {
    if (!nexusDb || !navigator.onLine) return;
    if (document.hidden) return; // Save battery when screen is off / app in background
    nexusDb.from('nexus_commands')
        .select('*')
        .eq('status', 'pending')
        .eq('source', 'pc_notification')
        .limit(5)
        .then(function(res) {
            if (!res.data || res.data.length === 0) return;
            res.data.forEach(function(cmd) {
                // Mark as delivered
                nexusDb.from('nexus_commands').update({ status: 'delivered' }).eq('id', cmd.id).then(function() {});

                var msg = cmd.command || 'Nova mensagem do Jarvis';

                // Show in-app notification
                showInAppNotification(msg);

                // Native Android notification
                if (window.AndroidNative && window.AndroidNative.showNotification) {
                    window.AndroidNative.showNotification('Jarvis', msg);
                }

                // Also show in chat
                window.receiveJarvisSpeech(msg);
            });
        });
}, 20000);

function showInAppNotification(msg) {
    var notif = document.createElement('div');
    notif.style.cssText = 'position:fixed; top:60px; left:50%; transform:translateX(-50%); background:rgba(108,92,231,0.95); color:white; padding:12px 20px; border-radius:12px; z-index:9999; max-width:90%; text-align:center; font-size:0.9rem; box-shadow:0 4px 20px rgba(0,0,0,0.4); animation: slideDown 0.3s ease;';
    notif.innerHTML = '<i class="fa-solid fa-robot"></i> ' + msg;
    document.body.appendChild(notif);
    setTimeout(function() {
        notif.style.opacity = '0';
        notif.style.transition = 'opacity 0.5s';
        setTimeout(function() { notif.remove(); }, 500);
    }, 5000);
}

// ====================================================
// PHASE 14: Geofencing & GPS Context
// ====================================================
(function initGeoFencing() {
    if (!navigator.geolocation) return;
    
    var lastLat = null;
    var lastLon = null;
    var MIN_DISTANCE_METERS = 200; // Only report if moved more than 200m

    function distanceMeters(lat1, lon1, lat2, lon2) {
        var R = 6371000;
        var dLat = (lat2 - lat1) * Math.PI / 180;
        var dLon = (lon2 - lon1) * Math.PI / 180;
        var a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    }

    function checkAndReport() {
        if (document.hidden) return; // Don't use GPS when screen is off
        navigator.geolocation.getCurrentPosition(function(pos) {
            var lat = pos.coords.latitude;
            var lon = pos.coords.longitude;

            // Only send update if location changed significantly
            if (lastLat !== null && distanceMeters(lastLat, lastLon, lat, lon) < MIN_DISTANCE_METERS) {
                return;
            }
            lastLat = lat;
            lastLon = lon;

            var geoData = {
                lat: lat,
                lon: lon,
                accuracy: pos.coords.accuracy,
                timestamp: new Date().toISOString(),
                device: 'mobile'
            };
            localStorage.setItem('nexus_last_location', JSON.stringify(geoData));

            if (nexusDb) {
                nexusDb.from('nexus_commands').insert([{
                    command: 'GPS_UPDATE: ' + JSON.stringify(geoData),
                    source: 'mobile_geo',
                    status: 'pending'
                }]).then(function() {});
            }
        }, function(err) {
            console.log('Geo not available:', err.message);
        }, { timeout: 10000, maximumAge: 300000 });
    }

    // Check every 5 minutes
    setInterval(checkAndReport, 300000);
})();

// Kick off geo on startup too (after 3s delay to not overwhelm init)
setTimeout(function() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(function(pos) {
        localStorage.setItem('nexus_last_location', JSON.stringify({
            lat: pos.coords.latitude, lon: pos.coords.longitude,
            timestamp: new Date().toISOString(), device: 'mobile'
        }));
    }, function() {}, { timeout: 10000 });
}, 3000);


