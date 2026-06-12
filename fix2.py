import re

with open('mobile/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Fix ANY weird characters in the whole file
c = re.sub(r'H[^\w<>]*bito', 'Hábito', c)
c = re.sub(r'H[^\w<>]*bitos', 'Hábitos', c)
c = re.sub(r'Anota[^\w<>]*es', 'Anotações', c)
c = re.sub(r'A[^\w<>]*es R[^\w<>]*pidas', 'Ações Rápidas', c)
c = re.sub(r'Finan[^\w<>]*as', 'Finanças', c)
c = re.sub(r'V[^\w<>]*deos', 'Vídeos', c)
c = re.sub(r'In[^\w<>]*cio', 'Início', c)
c = re.sub(r'Experi[^\w<>]*ncia', 'Experiência', c)
c = re.sub(r'M[^\w<>]*dulos', 'Módulos', c)
c = re.sub(r'T[^\w<>]*tulo', 'Título', c)
c = re.sub(r'Conclu[^\w<>]*do', 'Concluído', c)
c = re.sub(r'Configura[^\w<>]*es', 'Configurações', c)

# Fix missing onclicks
c = re.sub(r'<button class="action-bubble"><i class="fa-solid fa-plus"></i><br>Hábito</button>', '<button class="action-bubble" onclick="openCreateModal()"><i class="fa-solid fa-plus"></i><br>Hábito</button>', c)
c = re.sub(r'<button class="action-bubble"><i class="fa-solid fa-wallet"></i><br>Despesa</button>', '<button class="action-bubble" onclick="document.querySelector(\'.nav-item[data-target=\\\'view-finance\\\']\').click();"><i class="fa-solid fa-wallet"></i><br>Despesa</button>', c)
c = re.sub(r'<button class="action-bubble"><i class="fa-solid fa-pen"></i><br>Nota</button>', '<button class="action-bubble" onclick="document.querySelector(\'.nav-item[data-target=\\\'view-studies\\\']\').click();"><i class="fa-solid fa-pen"></i><br>Nota</button>', c)
c = re.sub(r'<button class="action-bubble"><i class="fa-solid fa-brain"></i><br>Flashcard</button>', '<button class="action-bubble" onclick="document.querySelector(\'.nav-item[data-target=\\\'view-studies\\\']\').click();"><i class="fa-solid fa-brain"></i><br>Flashcard</button>', c)

old_modal = re.search(r'<div class="modal-content glass">\s*<div class="modal-header">\s*<h2 class="modal-title">Novo Registro</h2>.*?<button onclick="saveQuickAdd\(\)".*?</button>\s*</div>\s*</div>', c, re.DOTALL)
if old_modal:
    new_modal = '''<div class="modal-content glass">
            <div class="modal-header">
                <h2 class="modal-title">Novo Registro</h2>
                <button class="close-btn" onclick="closeCreateModal()"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="modal-body" style="display: flex; flex-direction: column; gap: 15px;">
                <select id="create-type" style="padding: 12px; border-radius: 8px; background: rgba(0,0,0,0.5); color: white; border: 1px solid var(--border-glass);">
                    <option value="task">📝 Nova Tarefa</option>
                    <option value="habit">🔥 Novo Hábito</option>
                </select>
                <input type="text" id="create-title" placeholder="Nome / Título" style="padding: 12px; border-radius: 8px; background: rgba(0,0,0,0.5); color: white; border: 1px solid var(--border-glass);">
                
                <div id="habit-options" style="display: none; flex-direction: column; gap: 15px;">
                    <div style="display:flex; gap:10px;">
                        <input type="time" id="create-time" style="flex:1; padding: 12px; border-radius: 8px; background: rgba(0,0,0,0.5); color: white; border: 1px solid var(--border-glass);">
                        <select id="create-icon" style="flex:1; padding: 12px; border-radius: 8px; background: rgba(0,0,0,0.5); color: white; border: 1px solid var(--border-glass);">
                            <option value="fa-fire">🔥 Fogo</option>
                            <option value="fa-dumbbell">💪 Peso</option>
                            <option value="fa-book">📚 Livro</option>
                            <option value="fa-droplet">💧 Água</option>
                            <option value="fa-heart">❤️ Coração</option>
                        </select>
                    </div>
                    <select id="create-freq" style="padding: 12px; border-radius: 8px; background: rgba(0,0,0,0.5); color: white; border: 1px solid var(--border-glass);">
                        <option value="daily">Todos os Dias</option>
                        <option value="weekdays">Dias de Semana</option>
                        <option value="weekends">Finais de Semana</option>
                    </select>
                    <input type="number" id="create-xp" placeholder="Recompensa de XP (ex: 50)" style="padding: 12px; border-radius: 8px; background: rgba(0,0,0,0.5); color: white; border: 1px solid var(--border-glass);">
                    <input type="text" id="create-desc" placeholder="Descrição (opcional)" style="padding: 12px; border-radius: 8px; background: rgba(0,0,0,0.5); color: white; border: 1px solid var(--border-glass);">
                </div>

                <button onclick="saveQuickAdd()" style="background: linear-gradient(135deg, var(--accent-purple), var(--accent-blue)); color: white; padding: 14px; border: none; border-radius: 12px; font-weight: 800; font-size: 1.1rem; margin-top: 10px; box-shadow: 0 0 15px rgba(108,92,231,0.5);">SALVAR</button>
            </div>
        </div>'''
    c = c[:old_modal.start()] + new_modal + c[old_modal.end():]

with open('mobile/index.html', 'w', encoding='utf-8') as f:
    f.write(c)
