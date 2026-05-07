import json, time

states = [
    {"status": "listening", "subtitle": "", "emotion": "neutral"},
    {"status": "thinking", "subtitle": "", "emotion": "neutral"},
    {"status": "speaking", "subtitle": "Olá! Eu sou a assistente de IA.", "emotion": "happy"},
    {"status": "error", "subtitle": "TTS falhou: ConnectionError", "emotion": "neutral"},
    {"status": "warning", "subtitle": "Rate limit atingido", "emotion": "neutral"},
    {"status": "success", "subtitle": "Tarefa concluída!", "emotion": "neutral"},
    {"status": "loading", "subtitle": "Conectando à API...", "emotion": "neutral"},
    {"status": "idle", "subtitle": "", "emotion": "neutral"},
]

for s in states:
    with open("data/visualizer_state.json", "w", encoding="utf-8") as f:
        json.dump(s, f)
    print(f"Estado: {s['status']} | {s.get('subtitle','')}")
    time.sleep(2.5)

print("Teste concluído!")
