import os
import json
import requests

groq_key = os.environ.get('GROQ_API_KEY') or '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'

tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_nexus_commands",
            "description": "Executa múltiplos comandos do sistema de uma só vez (Criar Hábito, Tarefa, Diário, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "commands": {
                        "type": "array",
                        "description": "Lista de ações para executar em lote",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": { 
                                    "type": "string", 
                                    "enum": ["create_habit", "create_task", "create_flashcard", "create_diary_entry", "get_flashcards_status", "get_daily_briefing", "analyze_habit_patterns", "read_recent_diaries"] 
                                },
                                "payload": { 
                                    "type": "object", 
                                    "description": "Parâmetros da ação (ex: name, title, front, back, content, limit)" 
                                }
                            },
                            "required": ["action"]
                        }
                    }
                },
                "required": ["commands"]
            }
        }
    }
]

messages = [
    {
        "role": "system",
        "content": "Você é o Jarvis, psicólogo e conselheiro no Nexus Mobile. Para interagir com o app, use EXCLUSIVAMENTE o tool call 'execute_nexus_commands' com um array JSON válido de ações. NÃO USE TAGS XML NUNCA. Seja amigo e motivador."
    },
    {
        "role": "user",
        "content": "Jarvis, crie um hábito chamado 'Acordar às 5' e uma tarefa 'Ler 10 páginas'."
    }
]

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {groq_key}",
    "Content-Type": "application/json"
}

def make_call(msgs):
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": msgs,
        "tools": tools,
        "tool_choice": "auto",
        "max_tokens": 500,
        "temperature": 0.2
    }
    return requests.post(url, headers=headers, json=data)

try:
    print("Enviando request 1 para Groq...")
    response = make_call(messages)
    res_json = response.json()
    reply_msg = res_json['choices'][0]['message']
    
    messages.append(reply_msg)
    
    if 'tool_calls' in reply_msg and reply_msg['tool_calls']:
        print("Recebeu tool calls. Simulando resposta do cliente...")
        tool_call_id = reply_msg['tool_calls'][0]['id']
        # Simula resposta
        messages.append({
            "role": "tool",
            "content": "Hábito 'Acordar às 5' criado.\\nTarefa 'Ler 10 páginas' criada.",
            "tool_call_id": tool_call_id
        })
        
        print("Enviando request 2 para Groq...")
        response2 = make_call(messages)
        res_json2 = response2.json()
        print("Sucesso Request 2! Resposta final:")
        print(json.dumps(res_json2['choices'][0]['message'], indent=2, ensure_ascii=False))
except Exception as e:
    print("Exceção:", str(e))
