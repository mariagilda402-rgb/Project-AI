// ----------------------------------------------------
// Compatibility exports & runtime contract guards
// ----------------------------------------------------
// Keep this module last. It makes legacy inline HTML handlers explicit on
// window and provides small safe fallbacks for optional editor/native actions.

window.refreshViewContent = window.refreshViewContent || function(viewId) {
    switch (viewId) {
        case 'view-home':
            if (typeof loadTodayDashboard === 'function') loadTodayDashboard();
            if (typeof loadUserStats === 'function') loadUserStats();
            break;
        case 'view-habits': if (window.loadHabits) window.loadHabits(); break;
        case 'view-tasks': if (window.loadTasks) window.loadTasks(); break;
        case 'view-finance':
            if (window.loadFinance) window.loadFinance();
            else if (window.loadFinances) window.loadFinances();
            break;
        case 'view-studies': if (window.loadStudies) window.loadStudies(); break;
        case 'view-goals': if (window.loadGoals) window.loadGoals(); break;
        case 'view-fitness': if (window.loadFitness) window.loadFitness(); break;
        case 'view-journal': if (window.loadJournal) window.loadJournal(); break;
        case 'view-routines': if (window.loadRoutines) window.loadRoutines(); break;
        case 'view-videos': if (window.loadVideos) window.loadVideos(); break;
        case 'view-shop': if (window.loadShop) window.loadShop(); break;
        case 'view-iot': if (window.discoverIoT) window.discoverIoT(); break;
        case 'view-settings': break;
        case 'view-cleaner': if (window.loadCleaner) window.loadCleaner(); break;
        default: break;
    }
};

(function exposeLegacyHandlers() {
    const names = [
        'openYouTubeModal', 'closeYouTubeModal', 'insertYouTubeEmbed',
        'openSlashMenu', 'closeSlashMenu', 'openJarvisPanel', 'closeJarvisPanel',
        'richCmd', 'saveNote', 'openNoteEditor', 'closeNoteEditor',
        'openQuiz', 'startQuiz', 'startJournalDictation', 'openWorkoutForm'
    ];
    names.forEach((name) => {
        try {
            if (typeof window[name] !== 'function' && typeof eval(name) === 'function') {
                window[name] = eval(name);
            }
        } catch (_) {}
    });
})();

window.acceptAiDiff = window.acceptAiDiff || function() {
    const preview = document.getElementById('ai-diff-preview');
    const editor = document.getElementById('rich-editor');
    const panel = document.getElementById('ai-diff-panel');
    if (preview && editor) editor.innerHTML = preview.innerHTML || preview.textContent || '';
    if (panel) panel.style.display = 'none';
    if (typeof showToast === 'function') showToast('Sugestão aplicada.');
};

window.rejectAiDiff = window.rejectAiDiff || function() {
    const panel = document.getElementById('ai-diff-panel');
    if (panel) panel.style.display = 'none';
    if (typeof showToast === 'function') showToast('Sugestão descartada.');
};

window.handleOcrFileSelected = window.handleOcrFileSelected || function(event) {
    const file = event && event.target && event.target.files && event.target.files[0];
    if (!file) return;
    if (window.AndroidNative && typeof window.AndroidNative.processOcrImage === 'function') {
        window.AndroidNative.processOcrImage(file.name || 'ocr-image');
    } else if (typeof showToast === 'function') {
        showToast('OCR nativo indisponível neste ambiente.');
    }
};

window.forceOTAUpdate = window.forceOTAUpdate || function() {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.getRegistrations().then((regs) => regs.forEach((reg) => reg.update && reg.update()));
    }
    if (typeof showToast === 'function') showToast('Verificando atualização da interface...');
    setTimeout(() => window.location.reload(), 500);
};

window.updateNativeApk = window.updateNativeApk || function() {
    if (window.AndroidNative && typeof window.AndroidNative.updateNativeApk === 'function') {
        window.AndroidNative.updateNativeApk();
    } else if (typeof showToast === 'function') {
        showToast('Atualização nativa indisponível neste ambiente.');
    }
};

// Explicit aliases kept as literal window.* assignments so contract tests and
// WebView inline handlers can detect these public entry points reliably.
try { window.openYouTubeModal = window.openYouTubeModal || openYouTubeModal; } catch (_) {}
try { window.closeYouTubeModal = window.closeYouTubeModal || closeYouTubeModal; } catch (_) {}
try { window.insertYouTubeEmbed = window.insertYouTubeEmbed || insertYouTubeEmbed; } catch (_) {}
try { window.openSlashMenu = window.openSlashMenu || openSlashMenu; } catch (_) {}
try { window.closeSlashMenu = window.closeSlashMenu || closeSlashMenu; } catch (_) {}
try { window.openJarvisPanel = window.openJarvisPanel || openJarvisPanel; } catch (_) {}
try { window.openNoteEditor = window.openNoteEditor || openNoteEditor; } catch (_) {}
try { window.saveNote = window.saveNote || saveNote; } catch (_) {}
try { window.openQuiz = window.openQuiz || openQuiz; } catch (_) {}
try { window.startQuiz = window.startQuiz || startQuiz; } catch (_) {}
try { window.startJournalDictation = window.startJournalDictation || startJournalDictation; } catch (_) {}
try { window.openWorkoutForm = window.openWorkoutForm || openWorkoutForm; } catch (_) {}
