import re

with open('mobile/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

chat_ui = '''
            <!-- Chat Interface -->
            <div id="home-chat-container" class="glass" style="margin-top: 20px; padding: 15px; border-radius: 16px; display: flex; flex-direction: column; gap: 10px; height: 350px;">
                <h3 style="margin: 0; font-size: 1.1rem; color: var(--accent-blue);"><i class="fa-solid fa-comments"></i> Jarvis Chat</h3>
                
                <div id="chat-history" style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; padding-right: 5px;">
                    <div class="chat-message jarvis-msg" style="align-self: flex-start; background: rgba(0, 206, 201, 0.15); border: 1px solid var(--accent-blue); padding: 10px 15px; border-radius: 12px; border-bottom-left-radius: 2px; max-width: 85%;">
                        <p style="margin: 0; font-size: 0.95rem; color: white;">Olá! Como posso ajudar você hoje?</p>
                    </div>
                </div>
                
                <div style="display: flex; gap: 10px;">
                    <input type="text" id="chat-input" placeholder="Digite uma mensagem..." style="flex: 1; padding: 12px; border-radius: 12px; background: rgba(0,0,0,0.5); color: white; border: 1px solid var(--border-glass); font-size: 1rem;">
                    <button onclick="sendChatMessage()" style="background: linear-gradient(135deg, var(--accent-purple), var(--accent-blue)); color: white; border: none; padding: 0 20px; border-radius: 12px; display: flex; align-items: center; justify-content: center;"><i class="fa-solid fa-paper-plane"></i></button>
                </div>
            </div>
'''

if 'id="home-chat-container"' not in c:
    # Append after the actions-scroll
    actions_end = re.search(r'<div class="actions-scroll".*?</div>', c, re.DOTALL)
    if actions_end:
        c = c[:actions_end.end()] + chat_ui + c[actions_end.end():]
        with open('mobile/index.html', 'w', encoding='utf-8') as f:
            f.write(c)
