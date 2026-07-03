import json, requests

groq_key = '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'

tools = [{
    "type": "function",
    "function": {
        "name": "nexus",
        "description": "Interage com o app Nexus. Use para CRIAR ou LER dados do app. Sempre passe todos os comandos num único array.",
        "parameters": {
            "type": "object",
            "properties": {
                "commands": {
                    "type": "array",
                    "description": "Lista de comandos a executar em ordem",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": [
                                    "create_habit", "create_task", "create_flashcard",
                                    "create_diary_entry", "create_expense",
                                    "list_habits", "list_tasks", "list_flashcards",
                                    "list_diaries", "list_finances", "daily_briefing"
                                ]
                            },
                            "payload": {
                                "type": "object",
                                "description": "create_habit: {name}. create_task: {name}. create_flashcard: {front, back}. create_diary_entry: {content}. create_expense: {description, amount, type?}. list_*: {}.",
                                "properties": {
                                    "name":        {"type": "string", "description": "Nome do hábito ou tarefa"},
                                    "title":       {"type": "string", "description": "Alternativa a name para tarefas"},
                                    "front":       {"type": "string"},
                                    "back":        {"type": "string"},
                                    "content":     {"type": "string"},
                                    "description": {"type": "string"},
                                    "amount":      {"type": "number"},
                                    "type":        {"type": "string", "enum": ["income", "expense"]},
                                    "limit":       {"type": "number"}
                                }
                            }
                        },
                        "required": ["action", "payload"]
                    }
                }
            },
            "required": ["commands"]
        }
    }
}]

messages = [
    {"role": "system", "content": "Você é o Jarvis, assistente pessoal integrado ao app Nexus. Seja direto e natural — responda de forma curta e amigável. Use a ferramenta nexus para criar ou consultar qualquer dado do app (hábitos, tarefas, flashcards, diário, finanças). Só adote tom de psicólogo/mentor se o usuário pedir explicitamente."},
    {"role": "user", "content": "Cria um hábito de beber água e uma tarefa de lavar a louça"}
]

res = requests.post("https://api.groq.com/openai/v1/chat/completions",
    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
    json={"model": "llama-3.3-70b-versatile", "messages": messages, "tools": tools, "tool_choice": "auto", "max_tokens": 500}
)

data = res.json()
msg = data['choices'][0]['message']
print("=== TOOL CALL ARGUMENTS (NEW SCHEMA) ===")
if msg.get('tool_calls'):
    args = json.loads(msg['tool_calls'][0]['function']['arguments'])
    print(json.dumps(args, indent=2, ensure_ascii=False))
    print("\n=== FIELD NAMES USED ===")
    for cmd in args['commands']:
        print(f"action: {cmd['action']}, payload keys: {list(cmd.get('payload',{}).keys())}")
else:
    print("No tool call! Content:", msg.get('content'))
