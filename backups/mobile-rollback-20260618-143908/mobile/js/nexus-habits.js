/** Nexus Mobile — nexus-habits.js */
// Heatmap + loadHabits delegando para nexus-forms.js (filterHabits / toggleHabitDirect)

window.loadHabits = function() {
    const heatmapContainer = document.getElementById('habit-heatmap-container');
    const habits = LocalDB.get('habits').filter(h => h.active !== 0 && !h.is_deleted);
    const logs = LocalDB.get('habit_logs') || [];

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

    if (typeof window.filterHabits === 'function') {
        const chip = document.querySelector('#view-habits .study-chip.active') || document.querySelector('#view-habits .study-chip[data-filter="all"]');
        window.filterHabits(chip?.dataset?.filter || 'all', chip || null);
    }
};

window.closeHabitDetail = window.closeHabitDetail || function() {
    const modal = document.getElementById('habit-detail-modal');
    if (modal) modal.style.display = 'none';
};
