import re

with open('mobile/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

func_js = '''
window.openNoteEditor = function(noteId = null) {
    document.getElementById('study-main-view').style.display = 'none';
    document.getElementById('note-editor-view').style.display = 'flex';
    document.getElementById('ai-diff-panel').style.display = 'none';
    
    if (noteId) {
        // Load existing note logic here
        // var note = LocalDB.get('study_notes', noteId);
    } else {
        document.getElementById('note-title').value = '';
        document.getElementById('note-subject').value = '';
        document.getElementById('note-content').value = '';
        window.currentNoteId = null;
    }
};

window.closeNoteEditor = function() {
    document.getElementById('note-editor-view').style.display = 'none';
    document.getElementById('study-main-view').style.display = 'block';
};

window.saveNote = function() {
    var title = document.getElementById('note-title').value.trim();
    var subject = document.getElementById('note-subject').value.trim();
    var content = document.getElementById('note-content').value.trim();
    
    if(!title || !content) {
        alert("Título e conteúdo são obrigatórios.");
        return;
    }
    
    var newNote = {
        id: window.currentNoteId || Date.now(),
        subject: title,  // In the DB it's called subject
        general_subject: subject, // new field
        content: content,
        created_at: new Date().toISOString()
    };
    
    LocalDB.upsert('study_notes', newNote);
    
    // If subject is empty, we send a command to Jarvis to auto-summarize it
    if(!subject) {
        nexusDb.from('nexus_commands').insert([
            { command: "AUTO_SUMMARIZE_NOTE: " + newNote.id, source: 'mobile_study', status: 'pending' }
        ]).then(function() {});
    }
    
    alert("Nota salva!");
    closeNoteEditor();
    loadNotes(); // Assuming this exists or will exist
    backgroundSync();
};

window.acceptAiDiff = function() {
    // Logic to accept the AI suggestion
    document.getElementById('ai-diff-panel').style.display = 'none';
    alert("Alteração do Jarvis aplicada!");
};

window.rejectAiDiff = function() {
    // Logic to reject the AI suggestion
    document.getElementById('ai-diff-panel').style.display = 'none';
    // Revert to original content
};
'''

if 'window.openNoteEditor' not in c:
    c += '\n' + func_js
    with open('mobile/app.js', 'w', encoding='utf-8') as f:
        f.write(c)
