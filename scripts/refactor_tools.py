import re

with open('mobile/app.js', 'r', encoding='utf-8') as f:
    code = f.read()

tools_code = """
const jarvisTools = [
    { type: 'function', function: { name: 'create_habit', description: 'Cria um novo hábito para o usuário acompanhar diariamente.', parameters: { type: 'object', properties: { name: { type: 'string', description: 'O nome do hábito' } }, required: ['name'] } } },
    { type: 'function', function: { name: 'create_task', description: 'Cria uma nova tarefa pendente para o usuário.', parameters: { type: 'object', properties: { title: { type: 'string', description: 'O título da tarefa' } }, required: ['title'] } } },
    { type: 'function', function: { name: 'get_flashcards_status', description: 'Verifica quantos flashcards estão pendentes para revisão.', parameters: { type: 'object', properties: {} } } },
    { type: 'function', function: { name: 'get_daily_briefing', description: 'Pega o resumo de hoje.', parameters: { type: 'object', properties: {} } } }
];

function handleJarvisToolCalls(toolCalls) {
    const results = [];
    for (const tc of toolCalls) {
        if (tc.type === 'function') {
            const funcName = tc.function.name;
            const args = tc.function.arguments ? JSON.parse(tc.function.arguments) : {};
            let resultStr = '';
            try {
                if (funcName === 'create_habit') {
                    LocalDB.upsert('habits', { id: Date.now(), name: args.name, active: 1, current_streak: 0, period: 'all' });
                    if (typeof loadHabits === 'function') loadHabits();
                    if (typeof backgroundSync === 'function') backgroundSync();
                    resultStr = 'Hábito "' + args.name + '" criado com sucesso.';
                } else if (funcName === 'create_task') {
                    LocalDB.upsert('tasks', { id: Date.now(), title: args.title, name: args.title, points_reward: 10 });
                    if (typeof loadTasks === 'function') loadTasks();
                    if (typeof backgroundSync === 'function') backgroundSync();
                    resultStr = 'Tarefa "' + args.title + '" criada.';
                } else if (funcName === 'get_flashcards_status') {
                    const cards = LocalDB.get('flashcards').filter(c => !c.is_deleted);
                    const due = cards.filter(c => !c.next_review || c.next_review <= new Date().toISOString()).length;
                    resultStr = 'Há ' + due + ' flashcards pendentes.';
                } else if (funcName === 'get_daily_briefing') {
                    const habits = LocalDB.get('habits').filter(h => h.active === 1 && !h.is_deleted);
                    const today = new Date().toISOString().split('T')[0];
                    const done = LocalDB.get('habit_logs').filter(l => l.date === today).length;
                    const tasks = LocalDB.get('tasks').filter(x => !x.done_at && !x.is_deleted).length;
                    resultStr = 'Hábitos hoje: ' + done + '/' + habits.length + '. Tarefas: ' + tasks + ' pendentes.';
                } else {
                    resultStr = 'Ação não encontrada.';
                }
            } catch(e) { resultStr = 'Erro: ' + e.message; }
            results.push({ role: 'tool', content: resultStr, tool_call_id: tc.id });
        }
    }
    return results;
}

let jarvisTextContext = [
    {role: 'system', content: 'Você é o Jarvis, assistente integrado ao app Nexus Mobile. Você DEVE usar suas ferramentas (tools) sempre que o usuário pedir para criar um hábito, tarefa, ou checar o status de algo. Ao usar uma ferramenta e obter sucesso, dê uma resposta bem amigável confirmando a ação.'}
];

window.sendChatMessage = async function() {
    const input = document.getElementById('chat-input');
    const text = input?.value?.trim();
    if (!text) return;
    appendChatBubble('user', text);
    input.value = '';
    const pending = appendChatBubble('jarvis', 'Processando...', true);

    const groqKey = getGroqKey();
    const url = 'https://api.groq.com/openai/v1/chat/completions';
    
    jarvisTextContext.push({role: 'user', content: text});
    if (jarvisTextContext.length > 30) jarvisTextContext = [jarvisTextContext[0], ...jarvisTextContext.slice(-29)];
    
    async function makeCall(msgs) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Authorization': "Bearer " + groqKey, 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: 'llama-3.3-70b-versatile',
                messages: msgs,
                tools: jarvisTools,
                tool_choice: 'auto',
                max_tokens: 300
            })
        });
        if (!res.ok) throw new Error(await res.text());
        return await res.json();
    }

    try {
        let data = await makeCall(jarvisTextContext);
        let replyMsg = data.choices[0].message;
        
        jarvisTextContext.push(replyMsg);
        
        if (replyMsg.tool_calls) {
            const toolResults = handleJarvisToolCalls(replyMsg.tool_calls);
            toolResults.forEach(tr => jarvisTextContext.push(tr));
            data = await makeCall(jarvisTextContext);
            replyMsg = data.choices[0].message;
            jarvisTextContext.push(replyMsg);
        }
        
        const replyText = replyMsg.content || 'Ação executada com sucesso.';
        if (pending) pending.querySelector('p').innerHTML = escapeHtml(replyText).replace(/\\n/g, '<br>');
    } catch (e) {
        console.error(e);
        if (pending) pending.querySelector('p').innerHTML = 'Erro: ' + e.message;
    }
};
"""

code = re.sub(r'function tryLocalJarvisCommand\(text\).*?window\.requestMorningBriefing = function\(\) {', tools_code + '\n\nwindow.requestMorningBriefing = function() {', code, flags=re.DOTALL)

query_code = """async function queryGeminiAndSpeak(userText) {
    if (!userText.trim()) return;
    const groqKey = getGroqKey();
    const url = 'https://api.groq.com/openai/v1/chat/completions';
    
    if (jarvisContext.length === 0 || jarvisContext[0].role !== 'system') {
        jarvisContext = [
            {role: 'system', content: 'Você é o Jarvis no Nexus Mobile. Responda de forma curta e amigável para TTS. Use ferramentas se o usuário pedir para criar hábitos ou tarefas.'},
            ...jarvisContext
        ];
    }
    jarvisContext.push({role: 'user', content: userText});
    
    async function makeCall(msgs) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Authorization': "Bearer " + groqKey, 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: 'llama-3.3-70b-versatile',
                messages: msgs,
                tools: jarvisTools,
                tool_choice: 'auto',
                max_tokens: 200,
                temperature: 0.7
            })
        });
        if (!res.ok) throw new Error(await res.text());
        return await res.json();
    }

    try {
        let data = await makeCall(jarvisContext);
        let replyMsg = data.choices[0].message;
        
        jarvisContext.push(replyMsg);
        
        if (replyMsg.tool_calls) {
            const toolResults = handleJarvisToolCalls(replyMsg.tool_calls);
            toolResults.forEach(tr => jarvisContext.push(tr));
            data = await makeCall(jarvisContext);
            replyMsg = data.choices[0].message;
            jarvisContext.push(replyMsg);
        }
        
        const replyText = replyMsg.content || 'Ação concluída.';
        speakJarvisResponse(replyText);
    } catch (e) {
        setJarvisStatus('Falha ao contactar o cérebro.');
        console.error(e);
        setTimeout(startJarvisRecording, 2000);
    }
}"""

code = re.sub(r'async function queryGeminiAndSpeak\(userText\).*?function speakJarvisResponse\(text\) {', query_code + '\n\nfunction speakJarvisResponse(text) {', code, flags=re.DOTALL)

with open('mobile/app.js', 'w', encoding='utf-8') as f:
    f.write(code)

print('app.js updated successfully.')
