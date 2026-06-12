import re

with open('mobile/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

vision_js = '''
window.receiveNativeVision = function(data) {
    // Send to nexus_commands for processing
    nexusDb.from('nexus_commands').insert([
        { command: "VISION_CLIPBOARD: " + data, source: 'mobile_vision', status: 'pending' }
    ]).then(function() {
        alert("Dados da tela/clipboard enviados pro Jarvis analisar!");
    });
};
'''

if 'window.receiveNativeVision' not in c:
    c += '\n' + vision_js
    with open('mobile/app.js', 'w', encoding='utf-8') as f:
        f.write(c)
