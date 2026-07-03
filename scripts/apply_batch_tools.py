import re

with open('mobile/app.js', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update jarvisTools to the single batch tool
new_tools = """const jarvisTools = [
    {
        type: 'function',
        function: {
            name: 'execute_nexus_commands',
            description: 'Executa múltiplos comandos do sistema de uma só vez (Criar Hábito, Tarefa, Diário, etc).',
            parameters: {
                type: 'object',
                properties: {
                    commands: {
                        type: 'array',
                        description: 'Lista de ações para executar em lote',
                        items: {
                            type: 'object',
                            properties: {
                                action: { 
                                    type: 'string', 
                                    enum: ['create_habit', 'create_task', 'create_flashcard', 'create_diary_entry', 'get_flashcards_status', 'get_daily_briefing', 'analyze_habit_patterns', 'read_recent_diaries'] 
                                },
                                payload: { 
                                    type: 'object', 
                                    description: 'Parâmetros da ação (ex: name, title, front, back, content, limit)' 
                                }
                            },
                            required: ['action']
                        }
                    }
                },
                required: ['commands']
            }
        }
    }
];"""

code = re.sub(r'const jarvisTools = \[.*?\];', new_tools, code, flags=re.DOTALL)

# 2. Rewrite handleJarvisToolCalls to process the batch commands
new_handler = """function handleJarvisToolCalls(toolCalls) {
    const results = [];
    for (const tc of toolCalls) {
        if (tc.type === 'function' && tc.function.name === 'execute_nexus_commands') {
            const args = tc.function.arguments ? JSON.parse(tc.function.arguments) : {};
            const commands = args.commands || [];
            let resultStrs = [];
            
            for(let cmd of commands) {
                const action = cmd.action;
                const payload = cmd.payload || {};
                try {
                    if (action === 'create_habit') {
                        LocalDB.upsert('habits', { id: Date.now() + Math.random(), name: payload.name, active: 1, current_streak: 0, period: 'all' });
                        if (typeof loadHabits === 'function') loadHabits();
                        resultStrs.push(`Hábito "${payload.name}" criado.`);
                    } else if (action === 'create_task') {
                        LocalDB.upsert('tasks', { id: Date.now() + Math.random(), title: payload.title, name: payload.title, points_reward: 10 });
                        if (typeof loadTasks === 'function') loadTasks();
                        resultStrs.push(`Tarefa "${payload.title}" criada.`);
                    } else if (action === 'create_flashcard') {
                        LocalDB.upsert('flashcards', { id: Date.now() + Math.random(), front: payload.front, back: payload.back });
                        resultStrs.push(`Flashcard criado (Frente: ${payload.front}).`);
                    } else if (action === 'create_diary_entry') {
                        LocalDB.upsert('diaries', { id: Date.now() + Math.random(), content: payload.content, date: new Date().toISOString() });
                        resultStrs.push(`Entrada no diário registrada.`);
                    } else if (action === 'get_flashcards_status') {
                        const cards = LocalDB.get('flashcards').filter(c => !c.is_deleted);
                        const due = cards.filter(c => !c.next_review || c.next_review <= new Date().toISOString()).length;
                        resultStrs.push(`Flashcards: ${due} pendentes hoje.`);
                    } else if (action === 'get_daily_briefing') {
                        const habits = LocalDB.get('habits').filter(h => h.active === 1 && !h.is_deleted);
                        const today = new Date().toISOString().split('T')[0];
                        const done = LocalDB.get('habit_logs').filter(l => l.date === today).length;
                        const tasks = LocalDB.get('tasks').filter(x => !x.done_at && !x.is_deleted).length;
                        resultStrs.push(`Resumo: ${done}/${habits.length} hábitos, ${tasks} tarefas pendentes.`);
                    } else if (action === 'analyze_habit_patterns') {
                        const habits = LocalDB.get('habits').filter(h => !h.is_deleted);
                        const logs = LocalDB.get('habit_logs');
                        let report = "Relatório de Hábitos:\\n";
                        for(let h of habits) {
                            const hLogs = logs.filter(l => l.habit_id === h.id);
                            report += `- ${h.name}: ${hLogs.length}x total. Streak: ${h.current_streak}.\\n`;
                        }
                        resultStrs.push(report);
                    } else if (action === 'read_recent_diaries') {
                        const limit = payload.limit || 3;
                        const diaries = LocalDB.get('diaries').filter(d => !d.is_deleted).sort((a,b) => b.id - a.id).slice(0, limit);
                        if (diaries.length === 0) resultStrs.push("Nenhum diário recente.");
                        else resultStrs.push("Diários:\\n" + diaries.map(d => `[${new Date(d.id).toLocaleDateString()}] ${d.content}`).join("\\n"));
                    } else {
                        resultStrs.push(`Ação '${action}' desconhecida.`);
                    }
                } catch(e) {
                    resultStrs.push(`Erro na ação '${action}': ${e.message}`);
                }
            }
            if (typeof backgroundSync === 'function') backgroundSync();
            results.push({ role: 'tool', content: resultStrs.join('\\n'), tool_call_id: tc.id });
        } else {
            // Other fallback tool call
            results.push({ role: 'tool', content: "Ação não encontrada ou ferramenta inválida.", tool_call_id: tc.id });
        }
    }
    return results;
}"""

# Replace handleJarvisToolCalls block
# Because it might be slightly modified, we use regex to replace from 'function handleJarvisToolCalls' to the end of its body.
# We match from 'function handleJarvisToolCalls(toolCalls) {' up to its matching closing brace (before runMemoryExtractorInBackground).
code = re.sub(r'function handleJarvisToolCalls\(toolCalls\) \{.*?\}\n    return results;\n\}', new_handler, code, flags=re.DOTALL)

# 3. Update getSystemPrompt to explicitly forbid XML and force `execute_nexus_commands`
new_prompt_code = """function getSystemPrompt() {
    let mem = LocalDB.get('jarvis_structured_memory');
    let facts = "";
    if (Array.isArray(mem) && mem.length > 0) {
        facts = "\\n\\nMEMÓRIA (Fatos Conhecidos):\\n- " + mem.join("\\n- ");
    }
    return "Você é o Jarvis, psicólogo e conselheiro no Nexus Mobile. Para interagir com o app, use EXCLUSIVAMENTE o tool call 'execute_nexus_commands' com um array JSON válido de ações. NÃO USE TAGS XML NUNCA. Seja amigo e motivador." + facts;
}"""

code = re.sub(r'function getSystemPrompt\(\) \{.*?\n\}', new_prompt_code, code, flags=re.DOTALL)

with open('mobile/app.js', 'w', encoding='utf-8') as f:
    f.write(code)

print("Batch tool updates applied successfully.")
