from src.services.nexus_service import NexusService
import re

class NexusManagerSkill:
    def __init__(self):
        self.nexus = NexusService()

    def handle_command(self, text):
        t = text.lower()
        
        # 1. FINANCE: Ganhos e Gastos
        # Ex: "ganhei 100 reais de lucro"
        income_match = re.search(r"(ganhei|recebi|lucro de)\s*(\d+(?:[.,]\d+)?)\s*reais", t)
        if income_match:
            val = float(income_match.group(2).replace(",", "."))
            return self.nexus.add_income(val, "Geral", "Entrada via voz")

        # Ex: "gastei 50 reais com comida"
        expense_match = re.search(r"(gastei|paguei)\s*(\d+(?:[.,]\d+)?)\s*reais", t)
        if expense_match:
            val = float(expense_match.group(2).replace(",", "."))
            # Tenta extrair a categoria
            cat = "Geral"
            if "com " in t:
                cat = t.split("com ")[1].split()[0].capitalize()
            return self.nexus.add_expense(val, cat, "Gasto via voz")

        # 2. ECONOMY: Consulta de Status
        if any(x in t for x in ["meu saldo", "quantos pontos", "meu nível", "meu xp"]):
            return self.nexus.get_summary()

        # 3. HABITS: Conclusão
        if "concluí" in t or "terminei" in t:
            # Tenta pegar o nome do hábito
            # Ex: "concluí o estudo de matemática"
            habit = t.replace("concluí", "").replace("terminei", "").strip()
            if habit:
                return self.nexus.complete_habit(habit)

        # 4. REWARDS: Resgate e Consulta
        if any(x in t for x in ["quanto custa", "preço da recompensa", "loja"]):
            rewards = self.nexus.get_rewards()
            resp = "Aqui estão as recompensas disponíveis, Sir: "
            for r in rewards:
                resp += f"{r['name']} por {r['cost']} pontos; "
            return resp

        if any(x in t for x in ["comprar", "resgatar", "quero assistir", "quero comer"]):
            # Tenta encontrar o nome da recompensa no texto
            rewards = self.nexus.get_rewards()
            for r in rewards:
                if r['name'].lower() in t or r['name'].split()[0].lower() in t:
                    success, msg = self.nexus.process_reward(r['name'])
                    return msg

        if "modo de foco" in t or "modo foco" in t:
            if "desativa" in t or "parar" in t or "sair" in t:
                return self.nexus.set_focus_mode(active=False)
            return self.nexus.set_focus_mode(active=True)

        # 5. ESTUDOS (MindPalace)
        if any(x in t for x in ["acertei", "acertei questão", "questão correta"]):
            # Tenta extrair a matéria
            subject = "Geral"
            for s in ["matemática", "português", "natureza", "humanas"]:
                if s in t: subject = s.capitalize()
            return self.nexus.log_study_result(subject, correct=True)

        if any(x in t for x in ["errei", "errei questão", "questão incorreta"]):
            subject = "Geral"
            for s in ["matemática", "português", "natureza", "humanas"]:
                if s in t: subject = s.capitalize()
            return self.nexus.log_study_result(subject, correct=False)

        if "tome nota" in t or "anote" in t:
            content = t.replace("tome nota", "").replace("anote", "").strip()
            return self.nexus.create_note("Geral", "Nota de Voz", content)

        # 6. FINANÇAS (Aether) - Melhoria de Contexto
        if "necessário" in t or "preciso" in t:
            # Tenta extrair valor e registrar como gasto necessário (score 10)
            return self.nexus.add_expense(amount=0, category="Geral", description=t, necessity=10)

        # 7. STRATEGY ENGINE (PRESETS)
        if "salvar preset" in t or "salvar configuração" in t:
            name = t.replace("salvar preset", "").replace("salvar configuração", "").strip() or "Default"
            return self.nexus.save_lifestyle_preset(name)

        if "ativar preset" in t or "entrar no modo" in t or "protocolo" in t:
            name = t.replace("ativar preset", "").replace("entrar no modo", "").replace("protocolo", "").strip()
            return self.nexus.load_lifestyle_preset(name)

        # 8. GRAND OBJECTIVES (METAS)
        if "adicione a meta" in t or "estabelecer meta" in t:
            name = t.replace("adicione a meta", "").replace("estabelecer meta", "").strip()
            return self.nexus.add_goal(name)

        if "atualize o progresso" in t or "progresso da meta" in t:
            # Tenta extrair a porcentagem
            import re
            match = re.search(r'(\d+)', t)
            progress = int(match.group(1)) if match else 50
            name = t.replace("atualize o progresso", "").replace("progresso da meta", "").replace(str(progress), "").replace("%", "").strip()
            return self.nexus.update_goal_progress(name, progress)

        # 9. AURA SYSTEM (TEMAS)
        if "mudar aura" in t or "mudar cor" in t:
            color = t.replace("mudar aura", "").replace("mudar cor", "").replace("para", "").strip()
            return self.nexus.change_aura(color)

        # 10. NAVEGAÇÃO DE ABAS
        if "abrir quadro" in t or "mostrar board" in t or "kanban" in t:
            self.nexus.open_nexus_ui()
            self.nexus.change_hud_tab("board")
            return "Quadro estratégico projetado, Sir."
        
        if "abrir notas" in t or "abrir editor" in t or "mindpalace" in t or "notion" in t:
            self.nexus.open_nexus_ui()
            self.nexus.change_hud_tab("notes")
            return "Workspace MindPalace inicializado. Pronto para suas anotações."

        if "abrir nexus" in t or "abrir painel" in t:
            return self.nexus.open_nexus_ui()

        if "voltar para o dashboard" in t or "mostrar hud" in t or "visão geral" in t:
            self.nexus.change_hud_tab("dashboard")
            return "Retornando à visão tática geral."

        return None
