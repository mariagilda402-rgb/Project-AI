/** Nexus Mobile — nexus-gamification.js */
// ================================================================
// XP & GAMIFICATION SYSTEM
// ================================================================

function awardXP(amount, reason) {
    const stats = (typeof getUserStats === 'function' ? getUserStats() : null) || { xp: 0, points: 0, level: 1, xp_today: 0, last_xp_date: '' };
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
    syncUserStatsToNexusUser();
    
    // XP log
    const xpLog = LocalDB.get('xp_log') || [];
    xpLog.unshift({ amount, reason, date: new Date().toISOString() });
    if (xpLog.length > 200) xpLog.pop();
    LocalDB.set('xp_log', xpLog);
    
    if (leveledUp) {
        showInAppNotification('LEVEL UP! Voce chegou ao nivel ' + newLevel + '!', 'success');
        if (window.NexusAudio) window.NexusAudio.play('complete');
        if (navigator.vibrate) navigator.vibrate([100, 50, 100, 50, 200]);
    } else if (window.NexusAudio) {
        window.NexusAudio.play('progress');
    }
    
    loadXPPanel();
    loadTodayDashboard();
    console.info('[XP] +' + amount + ' XP: ' + reason + ' (total: ' + stats.xp + ')');
}

function loadXPPanel() {
    const stats = (typeof getUserStats === 'function' ? getUserStats() : null) || { xp: 0, points: 0, level: 1, xp_today: 0 };
    const xpVal = Number(stats.xp) || 0;
    const ptsVal = Number(stats.points) || 0;
    const xpForCurrentLevel = (stats.level - 1) * 500;
    const xpProgress = stats.xp - xpForCurrentLevel;
    const xpForNextLevel = 500;
    const pct = Math.min(100, Math.floor((xpProgress / xpForNextLevel) * 100));
    
    const xpEl = document.getElementById('stat-xp');
    const ptsEl = document.getElementById('stat-points');
    const barEl = document.getElementById('xp-progress-bar');
    const lvlEl = document.getElementById('xp-level-label');
    const streakBadge = document.getElementById('xp-streak-badge');
    
    if (xpEl) xpEl.textContent = xpVal.toLocaleString('pt-BR');
    if (ptsEl) ptsEl.textContent = ptsVal.toLocaleString('pt-BR');
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
