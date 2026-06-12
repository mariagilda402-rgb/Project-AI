import re

with open('mobile/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

chat_js = '''
window.sendChatMessage = function() {
    var input = document.getElementById('chat-input');
    var msg = input.value.trim();
    if(!msg) return;
    
    // Add user message to UI
    var history = document.getElementById('chat-history');
    var userBubble = document.createElement('div');
    userBubble.className = 'chat-message user-msg';
    userBubble.style.cssText = 'align-self: flex-end; background: rgba(108, 92, 231, 0.4); border: 1px solid var(--accent-purple); padding: 10px 15px; border-radius: 12px; border-bottom-right-radius: 2px; max-width: 85%;';
    userBubble.innerHTML = '<p style="margin: 0; font-size: 0.95rem; color: white;">' + msg + '</p>';
    history.appendChild(userBubble);
    
    input.value = '';
    history.scrollTop = history.scrollHeight;
    
    // Send to nexus_commands
    nexusDb.from('nexus_commands').insert([
        { command: "CHAT: " + msg, source: 'mobile_chat', status: 'pending' }
    ]).then(function() {});
};
'''

if 'window.sendChatMessage' not in c:
    c += '\n' + chat_js
    with open('mobile/app.js', 'w', encoding='utf-8') as f:
        f.write(c)
