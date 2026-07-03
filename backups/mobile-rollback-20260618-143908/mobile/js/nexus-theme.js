/** Nexus Mobile — nexus-theme.js */
// ================================================================
// AMOLED THEME (Phase 8)
// ================================================================

window.toggleAmoled = function() {
    const cb = document.getElementById('toggle-amoled');
    if (cb && cb.checked) {
        document.body.classList.add('theme-amoled');
        LocalDB.set('amoled_enabled', true);
        localStorage.setItem('nexus_amoled', '1');
    } else {
        document.body.classList.remove('theme-amoled');
        LocalDB.set('amoled_enabled', false);
        localStorage.removeItem('nexus_amoled');
    }
};

// Hook into initTheme to apply AMOLED on boot
const _origInitTheme = window.initTheme;
window.initTheme = function() {
    if (_origInitTheme) _origInitTheme();
    if (LocalDB.get('amoled_enabled')) {
        document.body.classList.add('theme-amoled');
        const cb = document.getElementById('toggle-amoled');
        if (cb) cb.checked = true;
    }
};


document.addEventListener('DOMContentLoaded', () => {
    if (typeof ensureDefaultRewards === 'function') ensureDefaultRewards();
    initAppPreferences();
    loadUserStats();
    loadHabits();
    loadTodayDashboard();
    if (typeof ensureModuleNavVisible === 'function') ensureModuleNavVisible();
    applyUiPrefs();
    bindMobileNavItems();
    updateJarvisFabState();
    updateNetworkSettingsUI();
    updateSyncIndicator('offline');
    if (window.NexusAudio && typeof window.NexusAudio.initSettingsUI === 'function') window.NexusAudio.initSettingsUI();

    setTimeout(requestNotificationPermission, 2000);
    setTimeout(backgroundSync, 1000);
    setupRealtime();
    startSyncInterval();

    setTimeout(() => {
        const active = document.querySelector('.view.active-view');
        if (active && typeof refreshViewContent === 'function') refreshViewContent(active.id);
    }, 100);
});

// ----------------------------------------------------
// UI Preferences & Module Toggling
// ----------------------------------------------------
window.openSettingsView = function() {
    if (typeof closeSettingsModal === 'function') closeSettingsModal();
    if (typeof activateMobileView === 'function') {
        activateMobileView('view-settings', null);
    } else {
        document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
        document.querySelectorAll('.view').forEach(view => view.classList.remove('active-view'));
        const view = document.getElementById('view-settings');
        if (view) view.classList.add('active-view');
    }
    updateNetworkSettingsUI();
    initAppPreferences();
    if (typeof updateSettingsUI === 'function') updateSettingsUI();
    const authEl = document.getElementById('btn-login-google');
    if (authEl) authEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
};

window.openSettingsAccount = function(ev) {
    if (ev) {
        ev.preventDefault();
        ev.stopPropagation();
    }
    if (typeof closeSettingsModal === 'function') closeSettingsModal();
    requestAnimationFrame(() => {
        if (typeof activateMobileView === 'function') {
            activateMobileView('view-settings', null);
        } else {
            openSettingsView();
            return;
        }
        const main = document.getElementById('main-content');
        if (main) main.scrollTop = 0;
        setTimeout(() => {
            const authEl = document.getElementById('btn-login-google');
            if (authEl) authEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 120);
    });
};

window.openSettingsModal = () => {
    const modal = document.getElementById('settings-modal');
    if (modal) modal.classList.add('show');
};

window.closeSettingsModal = () => {
    document.getElementById('settings-modal').classList.remove('show');
};

window.toggleModule = (moduleId) => {
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
    const modules = ['habits', 'finance', 'tasks', 'videos', 'shop', 'iot', 'studies', 'goals', 'fitness', 'journal', 'routines', 'alarms', 'cleaner'];
    
    modules.forEach(mod => {
        const isEnabled = prefs[mod] !== false;
        const cb = document.getElementById('toggle-' + mod);
        if (cb) cb.checked = isEnabled;
        const navItem = document.querySelector(`.nav-item[data-target="view-${mod}"]`);
        if (navItem) {
            navItem.style.display = isEnabled ? 'flex' : 'none';
        }
    });
    if (typeof applyModuleOrderAndVisibility === 'function') applyModuleOrderAndVisibility();
}

// Call applyUiPrefs on boot
