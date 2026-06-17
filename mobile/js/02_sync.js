// ----------------------------------------------------
// Sync Engine (unified offline-first)
// ----------------------------------------------------
const SYNC_TABLES = [
    'nexus_user', 'habits', 'habit_logs', 'tasks', 'finance_transactions',
    'nexus_rewards', 'study_notes', 'study_notebooks', 'flashcards', 'nexus_goals',
    'fitness_workouts', 'nexus_videos', 'routines', 'journal_entries',
    'pomo_sessions', 'reading_books', 'reading_sessions', 'quiz_attempts'
];
let syncInProgress = false;

function updateSyncIndicator(status, detail) {
    const textEl = document.getElementById('sync-status-text');
    const chip = document.getElementById('sync-status-chip');
    if (!textEl) return;
    const labels = {
        offline: 'Offline',
        syncing: 'Sincronizando...',
        synced: detail || 'Sincronizado',
        error: 'Erro de sync',
        conflicts: detail || 'Conflitos'
    };
    textEl.textContent = labels[status] || detail || 'Offline';
    if (chip) {
        chip.style.color = status === 'synced' ? 'var(--accent-green)'
            : status === 'syncing' ? 'var(--accent-blue)'
            : status === 'error' ? '#ff4757'
            : 'var(--text-secondary)';
    }
}

function mergeRemoteRow(table, remoteRow, localRows) {
    const idx = localRows.findIndex(r => String(r.id) === String(remoteRow.id));
    const localRow = idx > -1 ? localRows[idx] : null;
    if (remoteRow.is_deleted) {
        if (idx > -1) localRows.splice(idx, 1);
        return localRows;
    }
    const remoteTs = remoteRow.updated_at || '';
    const localTs = localRow?.updated_at || '';
    if (!localRow) {
        localRows.push({ ...remoteRow, sync_status: 'synced' });
    } else if (remoteTs > localTs) {
        if (localRow.sync_status === 'pending' && localTs >= remoteTs) {
            return localRows;
        }
        localRows[idx] = { ...localRow, ...remoteRow, sync_status: 'synced' };
    }
    return localRows;
}

async function syncData() {
    if (syncInProgress) return;
    const supabaseClient = window.nexusSupabase;
    if (!navigator.onLine || !supabaseClient) {
        updateSyncIndicator('offline');
        return;
    }
    syncInProgress = true;
    updateSyncIndicator('syncing');
    try {
        let lastSync = localStorage.getItem('nexus_last_sync') || '1970-01-01T00:00:00Z';
        let newSyncTime = lastSync;
        let conflictCount = 0;

        for (const table of SYNC_TABLES) {
            const { data: remoteData } = await supabaseClient
                .from(table).select('*').gt('updated_at', lastSync).order('updated_at', { ascending: true });
            if (remoteData?.length) {
                let localRows = LocalDB.get(table);
                remoteData.forEach(remoteRow => {
                    const before = localRows.length;
                    localRows = mergeRemoteRow(table, remoteRow, localRows);
                    if (remoteRow.updated_at > newSyncTime) newSyncTime = remoteRow.updated_at;
                });
                LocalDB.set(table, localRows);
            }

            let localRows = LocalDB.get(table);
            const toPush = localRows.filter(r =>
                (r.sync_status === 'pending' || (r.updated_at || '') > lastSync) && !r.is_deleted
            );
            for (const localRow of toPush) {
                const cleanRow = { ...localRow };
                delete cleanRow.sync_status;
                if (currentUser?.id) cleanRow.user_id = currentUser.id;
                if (cleanRow.id && typeof cleanRow.id === 'string' && isNaN(Number(cleanRow.id))) {
                    delete cleanRow.id;
                }
                const { error: pushErr } = await supabaseClient.from(table).upsert(cleanRow);
                if (!pushErr) {
                    const idx = localRows.findIndex(r => String(r.id) === String(localRow.id) || r.client_id === localRow.client_id);
                    if (idx > -1) {
                        localRows[idx].sync_status = 'synced';
                        if (localRow.updated_at > newSyncTime) newSyncTime = localRow.updated_at;
                    }
                } else {
                    console.error('Push error', table, pushErr);
                }
            }
            LocalDB.set(table, localRows);

            const tombstones = localRows.filter(r => r.is_deleted && r.sync_status === 'pending');
            for (const row of tombstones) {
                const cleanRow = { ...row, is_deleted: 1 };
                delete cleanRow.sync_status;
                const { error } = await supabaseClient.from(table).upsert(cleanRow);
                if (!error) row.sync_status = 'synced';
            }
            if (tombstones.length) LocalDB.set(table, localRows);
        }

        const conflicts = JSON.parse(localStorage.getItem('nexus_sync_conflicts') || '[]');
        conflictCount = conflicts.length;
        localStorage.setItem('nexus_last_sync', newSyncTime);
        const timeLabel = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
        updateSyncIndicator(conflictCount ? 'conflicts' : 'synced', conflictCount ? `${conflictCount} conflito(s)` : `Sync ${timeLabel}`);

        const activeView = document.querySelector('.active-view');
        if (activeView) {
            if (activeView.id === 'view-habits') loadHabits();
            if (activeView.id === 'view-finance') loadFinances();
            if (activeView.id === 'view-tasks') loadTasks();
            if (activeView.id === 'view-videos') loadVideos();
            if (activeView.id === 'view-shop') loadShop();
        }
        loadUserStats();
    } catch (e) {
        console.error('Sync error:', e);
        updateSyncIndicator('error');
    } finally {
        syncInProgress = false;
    }
}

async function backgroundSync() {
    return syncData();
}

window.syncData = syncData;
window.backgroundSync = backgroundSync;

