import re

with open('mobile/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

banner_ui = '''
    <!-- Jarvis Call Banner (Hidden by default) -->
    <div id="jarvis-call-banner" style="display: none; position: fixed; top: 0; left: 0; width: 100%; background: rgba(0, 206, 201, 0.9); color: white; padding: 10px; z-index: 1000; display: none; align-items: center; justify-content: space-between; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);">
        <div style="display: flex; align-items: center; gap: 10px;">
            <i class="fa-solid fa-phone-volume fa-shake"></i>
            <div>
                <strong style="display: block; font-size: 0.9rem;">Em Ligação com Jarvis</strong>
                <span id="jarvis-call-timer" style="font-size: 0.8rem;">00:00</span>
            </div>
        </div>
        <div style="display: flex; gap: 15px;">
            <button onclick="requestJarvisVision()" style="background: none; border: none; color: white; font-size: 1.2rem;"><i class="fa-solid fa-eye"></i></button>
            <button onclick="endJarvisCall()" style="background: var(--accent-pink); border: none; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold;"><i class="fa-solid fa-phone-slash"></i></button>
        </div>
    </div>
'''

if 'id="jarvis-call-banner"' not in c:
    c = c.replace('<body>', '<body>\n' + banner_ui)
    
    # Change the existing FAB onclick
    c = c.replace('onclick="startNexusAI()"', 'onclick="toggleJarvisCall()"')
    
    with open('mobile/index.html', 'w', encoding='utf-8') as f:
        f.write(c)
