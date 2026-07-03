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
    if (typeof startPomodoro === 'function' && document.getElementById('pomo-time')) {
        startPomodoro();
        return;
    }
    if (pomoActive) return;
    pomoActive = true;
    playBeep(400, 100);
    pomoInterval = setInterval(() => {
        if (pomoTimeLeft > 0) {
            pomoTimeLeft--;
            const el = document.getElementById('pomodoro-timer');
            if (el) el.innerText = formatPomoTime(pomoTimeLeft);
        } else {
            clearInterval(pomoInterval);
            pomoActive = false;
            LocalDB.upsert('pomo_sessions', {
                id: Date.now(),
                type: 'focus',
                duration_minutes: 25,
                session_date: new Date().toISOString().split('T')[0]
            });
            awardXP(20, 'Sessao Pomodoro completa');
            sendLocalNotification('Foco Concluido!', 'Voce ganhou +20 XP por 25 minutos de estudo.');
            playBeep(800, 500);
            pomoTimeLeft = 25 * 60;
            const el = document.getElementById('pomodoro-timer');
            if (el) el.innerText = formatPomoTime(pomoTimeLeft);
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
