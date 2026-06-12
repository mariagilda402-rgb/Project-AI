import re

with open('mobile/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

c = re.sub(r'V[^\w<>]*deos', 'Vídeos', c)

old_videos = re.search(r'<div id="view-videos" class="view">.*?</div>\s*</div>', c, re.DOTALL)
if old_videos:
    new_videos = '''<div id="view-videos" class="view">
            <h2 class="page-title">Insights de Vídeos (Jarvis AI)</h2>
            <div class="glass" style="padding: 20px; margin-bottom: 20px; border-radius: 16px; display: flex; flex-direction: column; gap: 15px;">
                <p style="color: var(--text-secondary); font-size: 0.9rem;">Cole um link do YouTube e peça para o Jarvis extrair os insights e integrá-los aos seus Estudos.</p>
                
                <input type="url" id="video-url" placeholder="https://youtube.com/watch?v=..." style="padding: 14px; border-radius: 12px; background: rgba(0,0,0,0.4); color: white; border: 1px solid var(--border-glass); width: 100%; font-size: 1rem;">
                
                <textarea id="video-prompt" rows="3" placeholder="Ex: Pegue todos os insights desse vídeo e crie anotações nos estudos..." style="padding: 14px; border-radius: 12px; background: rgba(0,0,0,0.4); color: white; border: 1px solid var(--border-glass); width: 100%; font-size: 1rem; resize: vertical;"></textarea>
                
                <button onclick="processVideoInsights()" style="background: linear-gradient(135deg, var(--accent-purple), var(--accent-blue)); color: white; padding: 14px; border: none; border-radius: 12px; font-weight: bold; font-size: 1.1rem; display: flex; align-items: center; justify-content: center; gap: 10px; box-shadow: 0 4px 15px rgba(108, 92, 231, 0.4);">
                    <i class="fa-solid fa-wand-magic-sparkles"></i> Analisar Vídeo
                </button>
            </div>
            
            <div id="video-processing-status" style="display: none; text-align: center; color: var(--accent-blue); padding: 20px;">
                <i class="fa-solid fa-circle-notch fa-spin fa-2x"></i>
                <p style="margin-top: 10px;">Jarvis está processando... (Acompanhe no PC)</p>
            </div>
        </div>'''
    c = c[:old_videos.start()] + new_videos + c[old_videos.end():]

with open('mobile/index.html', 'w', encoding='utf-8') as f:
    f.write(c)
