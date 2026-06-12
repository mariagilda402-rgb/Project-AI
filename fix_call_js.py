import re

with open('mobile/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

call_js = '''
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
'''

if 'window.toggleJarvisCall' not in c:
    c += '\n' + call_js
    with open('mobile/app.js', 'w', encoding='utf-8') as f:
        f.write(c)
