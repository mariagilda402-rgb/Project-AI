import json
from src.tools.base import Tool, ToolResult
from src.database.nexus_db import NexusDatabase

class HealthJournalTool(Tool):
    name = "health_journal"
    description = "Gerencia treinos, calorias/proteinas, diário e registros de humor (mood). Use comandos como 'workout|tipo|duracao_min|calorias', 'metrics|peso|bf|calorias|proteinas', 'journal|conteudo', 'mood|nota(1-10)|notas'."
    critical = False

    def __init__(self):
        self.db = NexusDatabase()

    def run(self, command: str) -> ToolResult:
        cmd = (command or "").strip()
        if not cmd:
            return ToolResult(False, "Comando vazio.")

        parts = [p.strip() for p in cmd.split("|")]
        action = parts[0].lower()

        if action == "workout":
            if len(parts) < 4:
                return ToolResult(False, "Use workout|tipo|duracao_min|calorias|[notas]")
            t, d, c = parts[1], parts[2], parts[3]
            n = parts[4] if len(parts) > 4 else ""
            wid = self.db.add_fitness_workout(t, int(d), int(c), n)
            return ToolResult(True, f"Treino registrado com sucesso (ID: {wid}).")
            
        elif action == "metrics":
            if len(parts) < 5:
                return ToolResult(False, "Use metrics|peso|bf|calorias|proteinas|[notas]")
            w, bf, c, p = parts[1], parts[2], parts[3], parts[4]
            n = parts[5] if len(parts) > 5 else ""
            mid = self.db.add_fitness_metrics(float(w), float(bf), int(c), int(p), n)
            return ToolResult(True, f"Métricas registradas com sucesso (ID: {mid}).")
            
        elif action == "journal":
            if len(parts) < 2:
                return ToolResult(False, "Use journal|conteudo|[psicologo_feedback]")
            content = parts[1]
            feedback = parts[2] if len(parts) > 2 else ""
            jid = self.db.add_journal_entry(content, feedback)
            return ToolResult(True, f"Diário registrado com sucesso (ID: {jid}). Use journal_feedback|id|feedback se quiser adicionar resposta do psicólogo separadamente depois.")
            
        elif action == "journal_feedback":
            if len(parts) < 3:
                return ToolResult(False, "Use journal_feedback|id|feedback")
            jid, feedback = parts[1], parts[2]
            self.db.update_journal_feedback(int(jid), feedback)
            return ToolResult(True, f"Feedback do psicólogo atualizado para o diário {jid}.")
            
        elif action == "mood":
            if len(parts) < 2:
                return ToolResult(False, "Use mood|nota(1-10)|[notas]")
            score = parts[1]
            notes = parts[2] if len(parts) > 2 else ""
            mid = self.db.add_mood_log(int(score), notes)
            return ToolResult(True, f"Humor registrado (Nota {score}). ID: {mid}.")
            
        return ToolResult(False, f"Ação desconhecida: {action}")
