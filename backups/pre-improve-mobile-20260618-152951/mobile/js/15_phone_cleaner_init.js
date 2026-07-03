// PHONE CLEANER MODULE — native bridge + local heuristics
// ================================================================

function formatBytes(bytes) {
    const n = Number(bytes) || 0;
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
    if (n < 1024 * 1024 * 1024) return (n / (1024 * 1024)).toFixed(1) + ' MB';
    return (n / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

function parseNativeJson(raw) {
    if (!raw) return null;
    try {
        return typeof raw === 'string' ? JSON.parse(raw) : raw;
    } catch (_) {
        return null;
    }
}

function getLocalStorageFootprint() {
    let total = 0;
    const large = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        const val = localStorage.getItem(key) || '';
        const size = (key.length + val.length) * 2;
        total += size;
        if (size > 50000) large.push({ key, size });
    }
    large.sort((a, b) => b.size - a.size);
    return { total, large: large.slice(0, 5) };
}

function findOrphanedHabitLogs() {
    const habits = (LocalDB.get('habits') || []).filter(h => !h.is_deleted);
    const habitIds = new Set(habits.map(h => String(h.id)));
    const logs = LocalDB.get('habit_logs') || [];
    return logs.filter(l => !habitIds.has(String(l.habit_id)));
}

function findStaleSyncData() {
    const conflicts = JSON.parse(localStorage.getItem('nexus_sync_conflicts') || '[]');
    const lastSync = localStorage.getItem('nexus_last_sync');
    const stale = [];
    if (conflicts.length > 10) stale.push({ type: 'sync_conflicts', count: conflicts.length });
    if (lastSync) {
        const age = Date.now() - new Date(lastSync).getTime();
        if (age > 30 * 24 * 60 * 60 * 1000) stale.push({ type: 'old_sync_marker', ageDays: Math.floor(age / 86400000) });
    }
    return stale;
}

function scanJsStorageCategories() {
    const ls = getLocalStorageFootprint();
    const orphans = findOrphanedHabitLogs();
    const stale = findStaleSyncData();
    const categories = [];

    categories.push({
        id: 'localStorage',
        name: 'Dados locais (localStorage)',
        bytes: ls.total,
        desc: ls.large.length ? ls.large.length + ' entradas grandes' : 'Dados do app offline',
        cleanable: false
    });

    if (orphans.length) {
        categories.push({
            id: 'orphan_logs',
            name: 'Logs de habitos orfaos',
            bytes: orphans.length * 120,
            desc: orphans.length + ' registros sem habito',
            cleanable: true,
            count: orphans.length
        });
    }

    if (stale.length) {
        categories.push({
            id: 'stale_sync',
            name: 'Dados de sync antigos',
            bytes: stale.reduce((s, x) => s + (x.count || 1) * 200, 0),
            desc: 'Conflitos ou metadados desatualizados',
            cleanable: true
        });
    }

    const nativeStats = getNativeStorageStatsSync();
    if (nativeStats) {
        if (nativeStats.cacheBytes > 0) {
            categories.push({
                id: 'native_cache',
                name: 'Cache nativo (Android)',
                bytes: nativeStats.cacheBytes,
                desc: 'Cache WebView e arquivos temporarios',
                cleanable: true
            });
        }
        if (nativeStats.tempBytes > 0) {
            categories.push({
                id: 'native_temp',
                name: 'Arquivos temporarios',
                bytes: nativeStats.tempBytes,
                desc: 'Pasta temp do app',
                cleanable: true
            });
        }
        if (nativeStats.bundleBytes > 1024 * 1024) {
            categories.push({
                id: 'web_bundle',
                name: 'Bundle web baixado',
                bytes: nativeStats.bundleBytes,
                desc: 'Atualizacao OTA da interface (limpeza profunda)',
                cleanable: true,
                deepOnly: true
            });
        }
    }

    return categories;
}

function getNativeStorageStatsSync() {
    if (!window.AndroidNative || typeof AndroidNative.getStorageStats !== 'function') return null;
    try {
        return parseNativeJson(AndroidNative.getStorageStats());
    } catch (_) {
        return null;
    }
}

function getNativeDiagnosticsSync() {
    if (!window.AndroidNative || typeof AndroidNative.getDeviceDiagnostics !== 'function') return null;
    try {
        return parseNativeJson(AndroidNative.getDeviceDiagnostics());
    } catch (_) {
        return null;
    }
}

function renderCleanerCategories(categories) {
    const container = document.getElementById('cleaner-scan-results');
    if (!container) return;
    if (!categories.length) {
        container.innerHTML = '<div class="glass" style="padding:14px;border-radius:12px;text-align:center;color:var(--text-secondary);font-size:0.85rem">Nada para limpar. Toque em Escanear.</div>';
        return;
    }
    container.innerHTML = categories.map(c => `
        <div class="cleaner-cat-item">
            <div>
                <div class="cleaner-cat-name">${escapeHtml(c.name)}</div>
                <div class="cleaner-cat-desc">${escapeHtml(c.desc || '')}</div>
            </div>
            <span class="cleaner-cat-size">${formatBytes(c.bytes)}</span>
        </div>`).join('');
}

function renderCleanerTips(categories, diag) {
    const list = document.getElementById('cleaner-tips-list');
    if (!list) return;
    const tips = [
        'Feche apps em segundo plano para liberar RAM.',
        'Mantenha pelo menos 10% de armazenamento livre para o Android funcionar bem.',
        'Desative animacoes pesadas em Configuracoes > Experiencia se o app estiver lento.'
    ];
    if (diag && diag.lowMemory) tips.unshift('Memoria baixa detectada — use Limpeza Rapida agora.');
    if (diag && diag.batteryPercent != null && diag.batteryPercent < 20) {
        tips.push('Bateria abaixo de 20% — ative economia de energia nas configuracoes do Android.');
    }
    const bigCache = categories.find(c => c.id === 'native_cache' && c.bytes > 50 * 1024 * 1024);
    if (bigCache) tips.unshift('Cache acima de 50 MB — recomendamos Limpeza Rapida.');
    list.innerHTML = tips.map(t => `<div class="cleaner-tip"><i class="fa-solid fa-circle-info" style="margin-right:6px;color:var(--accent-blue)"></i>${escapeHtml(t)}</div>`).join('');
}

function updateStorageWarningBadge(cacheBytes) {
    const badge = document.getElementById('storage-warning-badge');
    const hint = document.getElementById('settings-storage-hint');
    const threshold = 30 * 1024 * 1024;
    const show = cacheBytes > threshold;
    if (badge) badge.style.display = show ? 'block' : 'none';
    if (hint) hint.textContent = 'Cache: ' + formatBytes(cacheBytes || 0) + (show ? ' — considere limpar' : '');
}

function setCleanerProgress(pct, label) {
    const wrap = document.getElementById('cleaner-progress');
    const bar = document.getElementById('cleaner-progress-bar');
    const lbl = document.getElementById('cleaner-progress-label');
    if (wrap) wrap.style.display = pct >= 0 ? 'block' : 'none';
    if (bar) bar.style.width = Math.min(100, Math.max(0, pct)) + '%';
    if (lbl && label) lbl.textContent = label;
}

function showCleanerResults(text) {
    const box = document.getElementById('cleaner-results');
    const txt = document.getElementById('cleaner-results-text');
    if (box) box.style.display = 'block';
    if (txt) txt.textContent = text;
}

function cleanJsCategories(deep) {
    let freed = 0;
    const details = [];

    const orphans = findOrphanedHabitLogs();
    if (orphans.length) {
        const valid = (LocalDB.get('habit_logs') || []).filter(l => {
            const habits = (LocalDB.get('habits') || []).filter(h => !h.is_deleted);
            return habits.some(h => String(h.id) === String(l.habit_id));
        });
        freed += orphans.length * 120;
        LocalDB.set('habit_logs', valid);
        details.push(orphans.length + ' logs orfaos removidos');
    }

    const conflicts = JSON.parse(localStorage.getItem('nexus_sync_conflicts') || '[]');
    if (deep && conflicts.length > 20) {
        localStorage.setItem('nexus_sync_conflicts', JSON.stringify(conflicts.slice(-5)));
        freed += (conflicts.length - 5) * 200;
        details.push('Conflitos de sync antigos limpos');
    }

    if (deep) {
        const ls = getLocalStorageFootprint();
        ls.large.forEach(entry => {
            if (entry.key.startsWith('nexus_chart_') || entry.key.startsWith('nexus_temp_')) {
                const before = (entry.key.length + (localStorage.getItem(entry.key) || '').length) * 2;
                localStorage.removeItem(entry.key);
                freed += before;
                details.push('Cache ' + entry.key);
            }
        });
    }

    return { freed, details };
}

function runNativeClean(mode) {
    if (!window.AndroidNative || typeof AndroidNative.runNativeClean !== 'function') {
        let freed = 0;
        if (typeof AndroidNative.clearAppCache === 'function') freed += Number(AndroidNative.clearAppCache()) || 0;
        if (typeof AndroidNative.clearTempFiles === 'function') freed += Number(AndroidNative.clearTempFiles()) || 0;
        return { totalFreed: freed, cacheFreed: freed, tempFreed: 0, mode };
    }
    return parseNativeJson(AndroidNative.runNativeClean(mode)) || { totalFreed: 0 };
}

window.scanPhoneStorage = async function() {
    setCleanerProgress(10, 'Escaneando armazenamento...');
    const stats = getNativeStorageStatsSync();
    const diag = getNativeDiagnosticsSync();
    const categories = scanJsStorageCategories();

    if (stats && !stats.error) {
        const usedEl = document.getElementById('cleaner-storage-used');
        const freeEl = document.getElementById('cleaner-storage-free');
        const cacheEl = document.getElementById('cleaner-cache-size');
        const bar = document.getElementById('cleaner-storage-bar');
        if (usedEl) usedEl.textContent = formatBytes(stats.usedBytes);
        if (freeEl) freeEl.textContent = formatBytes(stats.freeBytes) + ' livres';
        if (cacheEl) cacheEl.textContent = formatBytes(stats.cacheBytes);
        if (bar && stats.totalBytes) bar.style.width = Math.round((stats.usedBytes / stats.totalBytes) * 100) + '%';
        updateStorageWarningBadge(stats.cacheBytes);
    } else {
        const ls = getLocalStorageFootprint();
        const usedEl = document.getElementById('cleaner-storage-used');
        const cacheEl = document.getElementById('cleaner-cache-size');
        if (usedEl) usedEl.textContent = formatBytes(ls.total);
        if (cacheEl) cacheEl.textContent = formatBytes(ls.total);
        updateStorageWarningBadge(ls.total);
    }

    if (diag && !diag.error) {
        const ramEl = document.getElementById('cleaner-ram-info');
        const procEl = document.getElementById('cleaner-process-count');
        if (ramEl && diag.availRamBytes) {
            ramEl.textContent = formatBytes(diag.availRamBytes) + ' livre';
        }
        if (procEl) procEl.textContent = String(diag.runningProcesses || '—');
    }

    renderCleanerCategories(categories);
    renderCleanerTips(categories, diag);
    setCleanerProgress(-1, '');
    window._cleanerLastScan = { stats, diag, categories, at: Date.now() };
};

window.runQuickClean = async function() {
    setCleanerProgress(15, 'Limpando cache...');
    const native = runNativeClean('quick');
    setCleanerProgress(55, 'Removendo dados orfaos...');
    const js = cleanJsCategories(false);
    setCleanerProgress(90, 'Finalizando...');
    const totalFreed = (native.totalFreed || 0) + js.freed;
    const parts = [];
    if (native.totalFreed) parts.push(formatBytes(native.totalFreed) + ' cache nativo');
    if (js.freed) parts.push(formatBytes(js.freed) + ' dados locais');
    if (js.details.length) parts.push(js.details.join(', '));
    showCleanerResults(totalFreed > 0
        ? 'Liberados ' + formatBytes(totalFreed) + (parts.length ? ' (' + parts.join(' · ') + ')' : '')
        : 'Nada significativo para limpar agora.');
    setCleanerProgress(100, 'Concluido!');
    setTimeout(() => setCleanerProgress(-1, ''), 1200);
    showToast('Limpeza rapida: ' + formatBytes(totalFreed) + ' liberados');
    await scanPhoneStorage();
};

window.runDeepClean = async function() {
    if (!confirm('Limpeza profunda remove cache, temporarios, logs orfaos e metadados antigos. Continuar?')) return;
    setCleanerProgress(10, 'Limpeza profunda em andamento...');
    const native = runNativeClean('deep');
    setCleanerProgress(50, 'Limpando dados locais...');
    const js = cleanJsCategories(true);
    setCleanerProgress(85, 'Otimizando...');
    const totalFreed = (native.totalFreed || 0) + js.freed;
    showCleanerResults('Limpeza profunda concluida. Liberados ' + formatBytes(totalFreed) + '.');
    setCleanerProgress(100, 'Concluido!');
    setTimeout(() => setCleanerProgress(-1, ''), 1500);
    showToast('Limpeza profunda: ' + formatBytes(totalFreed) + ' liberados');
    await scanPhoneStorage();
};

window.getCleanerSuggestions = function() {
    const scan = window._cleanerLastScan;
    if (!scan) return ['Execute um escaneamento primeiro.'];
    const suggestions = [];
    scan.categories.filter(c => c.cleanable).forEach(c => {
        suggestions.push('Limpar ' + c.name + ' (' + formatBytes(c.bytes) + ')');
    });
    if (!suggestions.length) suggestions.push('Armazenamento em bom estado.');
    return suggestions;
};

window.requestCleanerAiAdvice = async function() {
    const adviceEl = document.getElementById('cleaner-ai-advice');
    const scan = window._cleanerLastScan || {};
    const localTips = getCleanerSuggestions();

    if (!isWifiConnected()) {
        if (adviceEl) {
            adviceEl.style.display = 'block';
            adviceEl.textContent = 'Offline — sugestoes locais: ' + localTips.join(' · ');
        }
        return;
    }

    if (adviceEl) {
        adviceEl.style.display = 'block';
        adviceEl.textContent = 'Analisando...';
    }

    const report = {
        storage: scan.stats,
        diagnostics: scan.diag,
        categories: (scan.categories || []).map(c => ({ name: c.name, size: formatBytes(c.bytes), cleanable: c.cleanable })),
        localSuggestions: localTips
    };

    if (window.nexusSupabase && typeof sendChatMessage === 'function') {
        const prompt = document.getElementById('chat-input');
        if (prompt) {
            prompt.value = 'Analise este relatorio de armazenamento do Nexus Mobile e sugira o que limpar (resposta curta em portugues): ' + JSON.stringify(report);
            sendChatMessage();
            if (adviceEl) adviceEl.textContent = 'Pedido enviado ao Jarvis Chat — veja a resposta na tela inicial.';
            return;
        }
    }

    if (adviceEl) {
        adviceEl.textContent = localTips.join(' · ');
    }
};

window.loadCleaner = function() {
    scanPhoneStorage();
};

window.openCleanerView = function() {
    navigateTo('view-cleaner');
};

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        const stats = getNativeStorageStatsSync();
        if (stats && stats.cacheBytes) updateStorageWarningBadge(stats.cacheBytes);
        else updateStorageWarningBadge(getLocalStorageFootprint().total);
    }, 1500);
});
