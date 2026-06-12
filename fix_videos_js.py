import re

with open('mobile/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

func_js = '''
window.processVideoInsights = function() {
    var url = document.getElementById('video-url').value.trim();
    var promptTxt = document.getElementById('video-prompt').value.trim();
    
    if(!url) {
        alert("Por favor, cole um link do YouTube válido.");
        return;
    }
    
    var fullCommand = "VIDEO_INSIGHT: " + url + " | PROMPT: " + promptTxt;
    
    document.getElementById('video-processing-status').style.display = 'block';
    
    nexusDb.from('nexus_commands').insert([
        { command: fullCommand, source: 'mobile_video', status: 'pending' }
    ]).then(function(res) {
        if(res.error) {
            alert("Erro ao enviar para o PC: " + res.error.message);
            document.getElementById('video-processing-status').style.display = 'none';
        } else {
            // Success
            setTimeout(function() {
                alert("O Jarvis (PC) recebeu o link e está processando o vídeo! Verifique as Anotações depois.");
                document.getElementById('video-url').value = '';
                document.getElementById('video-prompt').value = '';
                document.getElementById('video-processing-status').style.display = 'none';
            }, 1000);
        }
    });
};
'''

if 'window.processVideoInsights' not in c:
    c += '\n' + func_js
    with open('mobile/app.js', 'w', encoding='utf-8') as f:
        f.write(c)
