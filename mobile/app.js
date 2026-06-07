// Supabase Configuration
const supabaseUrl = 'https://hlzkuqbnuabcmnooszrl.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhsemt1cWJudWFiY21ub29zenJsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk5MDc0NDksImV4cCI6MjA5NTQ4MzQ0OX0.MUcIs1NdagOJQJZRkrkdgqVP2rtTUzJk2qvu9JY5a5U';
const supabase = window.supabase.createClient(supabaseUrl, supabaseKey);

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
// Fetch Data & Realtime Sync
// ----------------------------------------------------

async function loadUserStats() {
    try {
        const { data, error } = await supabase.from('nexus_user').select('xp, level, points').eq('id', 1).single();
        if (data) {
            document.getElementById('user-level').innerText = data.level;
            document.getElementById('val-xp').innerText = data.xp;
            document.getElementById('val-points').innerText = data.points;
        }
    } catch (err) { console.error(err); }
}

async function loadVideos() {
    const container = document.getElementById('videos-list');
    const { data, error } = await supabase.from('nexus_videos').select('*').order('created_at', { ascending: false });
    
    if (data) {
        container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhum vídeo adicionado.</div>';
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
}

async function loadHabits() {
    const container = document.getElementById('habits-list');
    const { data, error } = await supabase.from('habits').select('*').eq('active', 1).order('id', { ascending: true });
    
    if(data) {
        container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Nenhum hábito cadastrado.</div>';
        data.forEach(habit => {
            const el = document.createElement('div');
            el.className = 'list-item glass';
            el.innerHTML = `
                <div class="item-main">
                    <span class="item-title">${habit.name}</span>
                    <span class="item-subtitle">Streak: 🔥 ${habit.current_streak}</span>
                </div>
                <button class="item-action" onclick="toggleHabit(${habit.id}, this)">
                    <i class="fa-solid fa-check"></i>
                </button>
            `;
            container.appendChild(el);
        });
    }
}

window.toggleHabit = async (id, btn) => {
    btn.classList.toggle('done');
    if (navigator.vibrate) navigator.vibrate(50);
    
    if (btn.classList.contains('done')) {
        sendLocalNotification('Hábito Concluído!', 'Você ganhou pontos de experiência!');
        // Aqui enviaria o update para o Supabase
        await loadUserStats(); // reload stats
    }
};

async function loadTasks() {
    const container = document.getElementById('tasks-list');
    const { data, error } = await supabase.from('tasks').select('*').eq('completed', 0);
    
    if (data) {
        container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Sem tarefas ativas!</div>';
        data.forEach(t => {
            const el = document.createElement('div');
            el.className = 'list-item glass';
            el.innerHTML = `<div class="item-main"><span class="item-title">${t.title}</span><span class="item-subtitle">+${t.points_reward} XP</span></div>`;
            container.appendChild(el);
        });
    }
}

async function loadFinances() {
    const container = document.getElementById('finance-list');
    const { data, error } = await supabase.from('finance_transactions').select('*').order('created_at', { ascending: false }).limit(10);
    
    if (data) {
        container.innerHTML = data.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Sem transações.</div>';
        data.forEach(t => {
            const el = document.createElement('div');
            el.className = 'list-item glass';
            el.innerHTML = `<div class="item-main"><span class="item-title">${t.description || 'Transação'}</span><span class="item-subtitle" style="color:${t.type==='income'?'#00b894':'#fd79a8'}">${t.type==='income'?'+':'-'} $${t.amount}</span></div>`;
            container.appendChild(el);
        });
    }
}

// ----------------------------------------------------
// Shop & IoT (Local Network API)
// ----------------------------------------------------

async function loadShop() {
    const container = document.getElementById('shop-list');
    try {
        const res = await fetch('/api/nexus/shop');
        const data = await res.json();
        if (data && data.items) {
            container.innerHTML = data.items.length ? '' : '<div style="text-align:center; color:var(--text-secondary); margin-top:20px;">Loja vazia.</div>';
            data.items.forEach(item => {
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
        }
    } catch (e) {
        container.innerHTML = '<div style="text-align:center; color:red; margin-top:20px;">Erro ao carregar loja (Conecte na mesma rede do PC).</div>';
    }
}

window.buyItem = async (id, name, cost) => {
    if (!confirm(`Deseja resgatar ${name} por ${cost} pontos?`)) return;
    try {
        const res = await fetch('/api/nexus/shop/buy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_id: id })
        });
        const out = await res.json();
        if (out.ok) {
            alert('Compra efetuada com sucesso!');
            loadUserStats(); // Update pts
        } else {
            alert(out.message || 'Erro ao comprar item.');
        }
    } catch (e) {
        alert('Erro de conexão com o servidor local.');
    }
};

window.discoverIoT = async () => {
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

window.toggleIoT = async (ip, turn_on) => {
    try {
        const res = await fetch('/api/nexus/iot/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: turn_on ? 'turn_on' : 'turn_off', target_ip: ip })
        });
        const out = await res.json();
        if (out.ok) {
            alert(out.result || 'Comando enviado.');
            discoverIoT();
        } else {
            alert('Erro: ' + out.error);
        }
    } catch (e) {
        alert('Erro de conexão com o servidor local.');
    }
};

// ----------------------------------------------------
// Realtime Subscription
// ----------------------------------------------------
function setupRealtime() {
    supabase.channel('custom-all-channel')
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'nexus_user' },
      (payload) => {
        console.log('Nexus User Update received!', payload);
        if (payload.new && payload.new.id === 1) {
            document.getElementById('user-level').innerText = payload.new.level;
            document.getElementById('val-xp').innerText = payload.new.xp;
            document.getElementById('val-points').innerText = payload.new.points;
            sendLocalNotification('XP Atualizado', `Você agora tem ${payload.new.xp} XP!`);
        }
      }
    )
    .subscribe();
}

// App Initialization
document.addEventListener('DOMContentLoaded', () => {
    loadUserStats();
    setTimeout(requestNotificationPermission, 2000);
    setupRealtime();
});
