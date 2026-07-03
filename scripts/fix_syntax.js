const fs = require('fs');
let c = fs.readFileSync('mobile/app.js', 'utf8');

c = c.replace(/"Relatório de Hábitos:\n"/g, '"Relatório de Hábitos:\\n"');
c = c.replace(/\.current_streak\}\.\n`/g, '.current_streak}.\\n`');
c = c.replace(/"Diários:\n"/g, '"Diários:\\n"');
c = c.replace(/\.join\("\n"\)/g, '.join("\\n")');
c = c.replace(/\.join\('\n'\)/g, '.join("\\n")');
c = c.replace(/facts = "\n\nMEMÓRIA \(Fatos Conhecidos\):\n- "/g, 'facts = "\\n\\nMEMÓRIA (Fatos Conhecidos):\\n- "');
c = c.replace(/\.join\("\n- "\)/g, '.join("\\n- ")');

fs.writeFileSync('mobile/app.js', c);
console.log('Fixed syntax literals');
