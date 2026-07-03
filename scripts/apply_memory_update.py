import re

with open('mobile/app.js', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update jarvisTools
new_tools = """const jarvisTools = [
    { type: 'function', function: { name: 'create_habit', description: 'Cria um novo hábito.', parameters: { type: 'object', properties: { name: { type: 'string', description: 'O nome do hábito' } }, required: ['name'] } } },
    { type: 'function', function: { name: 'create_task', description: 'Cria uma nova tarefa.', parameters: { type: 'object', properties: { title: { type: 'string', description: 'O título da tarefa' } }, required: ['title'] } } },
    { type: 'function', function: { name: 'get_flashcards_status', description: 'Verifica flashcards pendentes.', parameters: { type: 'object', properties: {} } } },
    { type: 'function', function: { name: 'get_daily_briefing', description: 'Pega resumo de hoje.', parameters: { type: 'object', properties: {} } } },
    { type: 'function', function: { name: 'analyze_habit_patterns', description: 'Analisa o histórico profundo de hábitos (miss rates, streaks). Use para detectar vícios ou padrões do usuário.', parameters: { type: 'object', properties: {} } } },
    { type: 'function', function: { name: 'read_recent_diaries', description: 'Lê os últimos relatos do diário do usuário para entender seu estado emocional e contexto de vida.', parameters: { type: 'object', properties: { limit: { type: 'number', description: 'Número máximo de entradas para ler (padrão 3)' } } } } }
];"""

code = re.sub(r'const jarvisTools = \[.*?\];', new_tools, code, flags=re.DOTALL)

# 2. Update handleJarvisToolCalls
new_handler_addition = """                } else if (funcName === 'analyze_habit_patterns') {
                    const habits = LocalDB.get('habits').filter(h => !h.is_deleted);
                    const logs = LocalDB.get('habit_logs');
                    let report = "Relatório de Hábitos:\\n";
                    for(let h of habits) {
                        const hLogs = logs.filter(l => l.habit_id === h.id);
                        report += `- ${h.name}: ${hLogs.length} execuções no total. Streak atual: ${h.current_streak}.\\n`;
                    }
                    resultStr = report || "Nenhum hábito rastreado ainda.";
                } else if (funcName === 'read_recent_diaries') {
                    const limit = args.limit || 3;
                    const diaries = LocalDB.get('diaries').filter(d => !d.is_deleted).sort((a,b) => b.id - a.id).slice(0, limit);
                    if (diaries.length === 0) resultStr = "Nenhum diário encontrado.";
                    else {
                        resultStr = "Últimos relatos:\\n" + diaries.map(d => `[Data: ${new Date(d.id).toLocaleDateString()}] ${d.content}`).join("\\n\\n");
                    }"""

code = code.replace("                } else {", new_handler_addition + "\n                } else {")

# 3. Memory Extraction Function
memory_extractor = """
async function runMemoryExtractorInBackground(userText, assistantText) {
    const groqKey = getGroqKey();
    if(!groqKey) return;
    
    try {
        const url = 'https://api.groq.com/openai/v1/chat/completions';
        const msgs = [{
            role: "system",
            content: "Extraia fatos novos e cruciais sobre a vida, vícios, metas, rotinas, traumas ou preferências do usuário baseados na última troca de mensagens. Retorne SOMENTE um JSON no formato: {'novos_fatos': ['fato 1', 'fato 2']}. Se não houver nada relevante, retorne {'novos_fatos': []}."
        }, {
            role: "user",
            content: `User: ${userText}\\nJarvis: ${assistantText}`
        }];
        
        fetch(url, {
            method: 'POST',
            headers: { 'Authorization': "Bearer " + groqKey, 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: 'llama-3.3-70b-versatile',
                messages: msgs,
                response_format: { type: "json_object" },
                temperature: 0.1
            })
        }).then(res => res.json()).then(data => {
            const result = JSON.parse(data.choices[0].message.content);
            if(result.novos_fatos && result.novos_fatos.length > 0) {
                let mem = LocalDB.get('jarvis_structured_memory');
                if(!Array.isArray(mem)) mem = [];
                mem.push(...result.novos_fatos);
                // Keep only last 30 facts to avoid context bloat
                if(mem.length > 30) mem = mem.slice(mem.length - 30);
                LocalDB.upsert('jarvis_structured_memory', mem, true);
                console.log("Memory Extractor: added facts", result.novos_fatos);
            }
        }).catch(e => console.error("Memory extractor error:", e));
    } catch(e) {}
}

function getSystemPrompt() {
    let mem = LocalDB.get('jarvis_structured_memory');
    let facts = "";
    if (Array.isArray(mem) && mem.length > 0) {
        facts = "\\n\\nO QUE VOCÊ SABE SOBRE O USUÁRIO (Memória Estruturada):\\n- " + mem.join("\\n- ");
    }
    return "Você é o Jarvis, um amigo próximo, mentor de produtividade e conselheiro psicológico, operando no app Nexus Mobile. Sua missão é apoiar emocionalmente o usuário, detectar padrões de vícios, ajudar a criar rotinas saudáveis e dar conselhos táticos baseados em frameworks de produtividade. Leia os diários ou histórico de hábitos quando necessário para entender a fundo o problema dele. Seja empático, conciso e use as ferramentas proativamente para agir na vida dele." + facts;
}
"""

# Insert memory_extractor before window.sendChatMessage
code = code.replace("window.sendChatMessage = async function() {", memory_extractor + "\nwindow.sendChatMessage = async function() {")

# 4. Modify System Prompts
sys_prompt_repl = "if (jarvisTextContext.length === 0 || jarvisTextContext[0].role !== 'system') { jarvisTextContext = [{role: 'system', content: getSystemPrompt()}]; }\n    jarvisTextContext[0].content = getSystemPrompt();"

# We need to replace the static context setup.
# Old: let jarvisTextContext = [ {role: 'system', content: '...'} ];
code = re.sub(r"let jarvisTextContext = \[\s*\{role: 'system', content: '.*?'\}\s*\];", "let jarvisTextContext = [];", code, flags=re.DOTALL)

# Insert system prompt injection into sendChatMessage right before `jarvisTextContext.push({role: 'user', content: text});`
code = code.replace("jarvisTextContext.push({role: 'user', content: text});", sys_prompt_repl + "\n    jarvisTextContext.push({role: 'user', content: text});")

# Insert system prompt injection into queryGeminiAndSpeak
q_repl_old = "if (jarvisContext.length === 0 || jarvisContext[0].role !== 'system') {\n        jarvisContext = [\n            {role: 'system', content: 'Você é o Jarvis no Nexus Mobile. Responda de forma curta e amigável para TTS. Use ferramentas se o usuário pedir para criar hábitos ou tarefas.'},\n            ...jarvisContext\n        ];\n    }"
q_repl_new = "if (jarvisContext.length === 0 || jarvisContext[0].role !== 'system') { jarvisContext = [{role: 'system', content: getSystemPrompt()}, ...jarvisContext]; } else { jarvisContext[0].content = getSystemPrompt(); }"
code = code.replace(q_repl_old, q_repl_new)

# 5. Background call to extractor
# In sendChatMessage:
bg_call1 = "runMemoryExtractorInBackground(text, replyText);"
code = code.replace("const replyText = replyMsg.content || 'Ação executada com sucesso.';", "const replyText = replyMsg.content || 'Ação executada com sucesso.';\n        " + bg_call1)

# In queryGeminiAndSpeak:
bg_call2 = "runMemoryExtractorInBackground(userText, replyText);"
code = code.replace("const replyText = replyMsg.content || 'Ação concluída.';", "const replyText = replyMsg.content || 'Ação concluída.';\n        " + bg_call2)

with open('mobile/app.js', 'w', encoding='utf-8') as f:
    f.write(code)

print("Applied memory system updates.")
