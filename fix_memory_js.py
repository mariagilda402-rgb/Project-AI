import re

with open('mobile/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

func_js = '''
window.syncNexusMemory = function() {
    if(!navigator.onLine) return; // Only sync when online
    
    nexusDb.from('nexus_memory_sync').select('*').then(function(res) {
        if(!res.error && res.data) {
            var memory = {};
            res.data.forEach(function(row) {
                memory[row.key_name] = row.data_json;
            });
            LocalDB.upsert('nexus_memory', { id: 'jarvis_brain', data: memory });
            console.log("Memórias do PC sincronizadas com sucesso!");
        }
    });
};

// Auto-sync memory every 5 minutes if online
setInterval(syncNexusMemory, 300000);
// Trigger once on load
setTimeout(syncNexusMemory, 5000);
'''

if 'window.syncNexusMemory' not in c:
    c += '\n' + func_js
    with open('mobile/app.js', 'w', encoding='utf-8') as f:
        f.write(c)
