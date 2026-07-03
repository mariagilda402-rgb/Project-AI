// ----------------------------------------------------
// UI Logic
// ----------------------------------------------------
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        closeTransientMobileSurfaces();
        
        document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');
        
        const targetId = item.getAttribute('data-target');
        const targetView = document.getElementById(targetId);
        if (!targetView) {
            console.warn("Missing mobile view:", targetId);
            return;
        }
        document.querySelectorAll('.view').forEach(view => view.classList.remove('active-view'));
        targetView.classList.add('active-view');
        
        if(targetId === 'view-habits' && typeof loadHabits === 'function') loadHabits();
        if(targetId === 'view-finance' && typeof loadFinances === 'function') loadFinances();
        if(targetId === 'view-tasks' && typeof loadTasks === 'function') loadTasks();
        if(targetId === 'view-videos' && typeof loadVideos === 'function') loadVideos();
        if(targetId === 'view-shop' && typeof loadShop === 'function') loadShop();
        if(targetId === 'view-iot' && typeof discoverIoT === 'function') discoverIoT();
        if(targetId === 'view-studies' && typeof loadStudies === 'function') loadStudies();
        if(targetId === 'view-goals' && typeof loadGoals === 'function') loadGoals();
        if(targetId === 'view-fitness' && typeof loadFitness === 'function') loadFitness();
        if(targetId === 'view-routines' && typeof loadRoutines === 'function') loadRoutines();
        if(targetId === 'view-journal' && typeof loadJournal === 'function') loadJournal();
        if(targetId === 'view-cleaner' && typeof loadCleaner === 'function') loadCleaner();
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
    if (window.AndroidNative && typeof window.AndroidNative.showNotification === 'function') {
        window.AndroidNative.showNotification(title, body);
        return;
    }
    if (!("Notification" in window) || !navigator.serviceWorker) return;
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
