import re

with open('mobile/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

old_studies = re.search(r'<div id="view-studies" class="view">.*?</div>\s*</div>', c, re.DOTALL)
if old_studies:
    new_studies = '''<div id="view-studies" class="view">
            <h2 class="page-title">MindPalace (Estudos)</h2>
            
            <div id="study-main-view">
                <div class="actions-scroll" style="margin-bottom: 15px;">
                    <button class="action-bubble" onclick="openNoteEditor()"><i class="fa-solid fa-plus"></i><br>Nova Nota</button>
                    <button class="action-bubble"><i class="fa-solid fa-brain"></i><br>Revisar</button>
                </div>
                <div class="list-container" id="studies-list">
                    <div class="loading-spinner"><i class="fa-solid fa-circle-notch fa-spin"></i> Carregando...</div>
                </div>
            </div>

            <!-- Note Editor (Hidden by default) -->
            <div id="note-editor-view" class="glass" style="display: none; padding: 20px; flex-direction: column; gap: 15px; height: calc(100vh - 120px); position: absolute; top: 0; left: 0; width: 100%; z-index: 10;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <button onclick="closeNoteEditor()" style="background: none; border: none; color: white; font-size: 1.5rem;"><i class="fa-solid fa-arrow-left"></i></button>
                    <h3 style="margin: 0;">Editor de Notas</h3>
                    <button onclick="saveNote()" style="background: var(--accent-green); border: none; color: white; padding: 8px 15px; border-radius: 8px; font-weight: bold;"><i class="fa-solid fa-save"></i> Salvar</button>
                </div>
                
                <input type="text" id="note-title" placeholder="Título da Nota" style="padding: 12px; border-radius: 8px; background: rgba(0,0,0,0.4); color: white; border: 1px solid var(--border-glass); font-size: 1.2rem; font-weight: bold;">
                <input type="text" id="note-subject" placeholder="Assunto Geral (Visível para IA)" style="padding: 10px; border-radius: 8px; background: rgba(0,0,0,0.2); color: var(--accent-purple); border: 1px dashed var(--accent-purple); font-size: 0.9rem;">
                
                <textarea id="note-content" placeholder="Escreva suas anotações aqui..." style="flex: 1; padding: 15px; border-radius: 8px; background: rgba(0,0,0,0.4); color: white; border: 1px solid var(--border-glass); font-size: 1rem; resize: none;"></textarea>
                
                <!-- AI Diff Review Panel (Hidden by default) -->
                <div id="ai-diff-panel" style="display: none; flex-direction: column; gap: 10px; padding: 15px; border: 1px solid var(--accent-blue); background: rgba(0, 206, 201, 0.1); border-radius: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: var(--accent-blue); font-weight: bold;"><i class="fa-solid fa-robot"></i> Jarvis sugeriu uma alteração!</span>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button onclick="acceptAiDiff()" style="flex: 1; background: var(--accent-green); color: white; border: none; padding: 10px; border-radius: 8px;"><i class="fa-solid fa-check"></i> Aceitar</button>
                        <button onclick="rejectAiDiff()" style="flex: 1; background: var(--accent-pink); color: white; border: none; padding: 10px; border-radius: 8px;"><i class="fa-solid fa-xmark"></i> Recusar</button>
                    </div>
                </div>
            </div>
        </div>'''
    c = c[:old_studies.start()] + new_studies + c[old_studies.end():]

with open('mobile/index.html', 'w', encoding='utf-8') as f:
    f.write(c)
