from src.services.nexus_service import NexusService, get_nexus_service
import json
import re
from datetime import date, timedelta
import unicodedata


def _parse_pt_date_fragment(text: str) -> str | None:
    """Retorna ISO date (YYYY-MM-DD) para fragmentos comuns em PT."""
    t = text.lower()
    today = date.today()
    if "hoje" in t:
        return today.isoformat()
    if "ontem" in t:
        return (today - timedelta(days=1)).isoformat()
    if "anteontem" in t or "ante ontem" in t:
        return (today - timedelta(days=2)).isoformat()
    return None


def _fold_text(text: str) -> str:
    folded = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def _clean_money_description(text: str) -> str:
    cleaned = re.sub(r"\b(hoje|ontem|anteontem|ante ontem|ontem de ontem)\b", "", text)
    cleaned = re.sub(r"\b(apague|apagar|remova|remover|delete|deletar|excluir|cancele|cancelar)\b", "", cleaned)
    cleaned = re.sub(r"\b(corrija|corrigir|atualize|atualizar|altere|alterar|mude|mudar|edite|editar)\b", "", cleaned)
    cleaned = re.sub(r"\b(o|a|um|uma|meu|minha|gasto|receita|ganho|lucro|movimento|transacao|transacao financeira|financeiro|financeira)\b", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" .,:;-")


def _strip_jarvis_wake(text: str) -> str:
    return re.sub(r"^\s*(jarvis|j[áa]rvis|nexus)\s*,?\s*", "", text or "", flags=re.I).strip()


def _clean_phrase(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip(" .,:;-")
    return cleaned


def _nexus_tab_from_text(text: str) -> str | None:
    folded = _fold_text(text)
    if any(x in folded for x in ["flashcard", "srs", "revisao espacada", "repeticao espacada"]):
        return "study"
    if any(x in folded for x in ["noticia", "noticias", "manchete", "manchetes", "jornal"]):
        return "news"
    if any(x in folded for x in ["grafo", "grafo neural", "rede neural", "mapa da memoria", "memoria neural"]):
        return "memory_graph"
    if any(x in folded for x in ["estudo", "estudos", "nota", "notas", "mindpalace", "editor"]):
        return "notes"
    if any(x in folded for x in ["habito", "habitos", "rotina"]):
        return "habits"
    if any(x in folded for x in ["financa", "financas", "financeiro", "aether"]):
        return "finance"
    if any(x in folded for x in ["tarefa", "tarefas", "board", "quadro", "kanban"]):
        return "tasks"
    if any(x in folded for x in ["progresso", "relatorio"]):
        return "progress"
    if any(x in folded for x in ["loja", "recompensa", "recompensas", "meta", "metas"]):
        return "goals"
    if any(x in folded for x in ["quiz", "simulado", "simulados", "enem"]):
        return "quiz"
    if any(x in folded for x in ["painel", "dashboard", "visao geral", "hud", "nexus"]):
        return "dashboard"
    return None


def _extract_compound_nexus_steps(text: str) -> list[dict]:
    raw = _strip_jarvis_wake(text)
    ordered_steps: list[tuple[int, dict]] = []

    expense_pattern = re.compile(
        r"(?:adicione|adicionar|registre|registrar)\s+(?:o\s+)?gasto(?:\s+de)?\s+"
        r"(\d+(?:[.,]\d+)?)\s*reais(?:\s+(?:em|com)\s+(.+?))?"
        r"(?=,|\s+e\s+(?:adicione|adicionar|registre|registrar|abra|abrir|mostre|mostrar|crie|criar)|$)",
        re.I,
    )
    for match in expense_pattern.finditer(raw):
        category = _clean_phrase(match.group(2) or "Geral")
        ordered_steps.append(
            (
                match.start(),
                {
                    "action": "finance_add",
                    "type": "expense",
                    "amount": match.group(1).replace(",", "."),
                    "category": category[:1].upper() + category[1:] if category else "Geral",
                    "description": category or "Gasto via comando composto",
                },
            )
        )

    habit_pattern = re.compile(
        r"(?:adicione|adicionar|crie|criar|registre|registrar)\s+(?:o\s+)?h[áa]bito"
        r"(?:\s+de)?\s+(.+?)(?:\s+(?:às|as)\s+(\d{1,2})(?::(\d{2}))?\s*(?:horas|h)?)?"
        r"(?=,|\s+e\s+(?:abra|abrir|adicione|adicionar|registre|registrar|crie|criar)|$)",
        re.I,
    )
    for match in habit_pattern.finditer(raw):
        name = _clean_phrase(match.group(1))
        if not name:
            continue
        hour = match.group(2)
        minute = match.group(3) or "00"
        description = ""
        if hour:
            description = f"Horario sugerido: {int(hour):02d}:{int(minute):02d}"
        ordered_steps.append(
            (
                match.start(),
                {
                    "action": "habit_add",
                    "name": name[:1].upper() + name[1:],
                    "description": description,
                    "xp_reward": "50",
                },
            )
        )

    open_pattern = re.compile(
        r"(?:abra|abrir|mostre|mostrar)\s+(?:a\s+|o\s+)?(?:janela|aba|painel|tela)?"
        r"\s*(?:de|do|da)?\s*([^,.;]+?)(?=,|\s+e\s+(?:adicione|adicionar|registre|registrar|crie|criar)|$)",
        re.I,
    )
    for match in open_pattern.finditer(raw):
        tab = _nexus_tab_from_text(match.group(1))
        if tab:
            ordered_steps.append((match.start(), {"action": "open_ui", "tab": tab}))

    return [step for _, step in sorted(ordered_steps, key=lambda item: item[0])]


class NexusManagerSkill:
    def __init__(self, nexus: NexusService | None = None):
        self.nexus = nexus or get_nexus_service()

    def handle_command(self, text):
        compound_steps = _extract_compound_nexus_steps(text)
        if len(compound_steps) >= 2:
            raw = self.nexus.handle_structured_command(
                {"action": "nexus_batch", "steps": compound_steps}
            )
            try:
                result = json.loads(raw)
                total = len(result.get("steps") or compound_steps)
                return f"{total} ações Nexus executadas em sequência, Sir."
            except json.JSONDecodeError:
                return raw

        t = text.lower()
        folded_t = _fold_text(t)
        if any(x in folded_t for x in ["abra", "abrir", "mostre", "mostrar"]):
            tab = _nexus_tab_from_text(t)
            if tab:
                return self.nexus.open_nexus_ui(tab)

        wants_window_theme = any(x in folded_t for x in ["tema", "visual", "preset"]) and any(
            x in folded_t for x in ["janela", "painel", "tela", "nexus", "modulo", "modulo"]
        )
        if wants_window_theme and any(x in folded_t for x in ["gere", "gerar", "crie", "criar"]):
            tab = _nexus_tab_from_text(t) or "dashboard"
            result = self.nexus.generate_window_theme_preset(tab, text)
            if result.get("ok"):
                return result.get("message") or "Tema Nexus gerado, Sir."
            return result.get("error") or "Nao consegui gerar o tema Nexus."
        if wants_window_theme and any(x in folded_t for x in ["aplique", "aplicar", "usar", "ative", "ativar"]):
            tab = _nexus_tab_from_text(t) or "dashboard"
            listing = self.nexus.list_window_themes()
            preset_id = ""
            for preset in listing.get("presets", []):
                folded_name = _fold_text(preset.get("name") or preset.get("id") or "")
                if folded_name and folded_name in folded_t:
                    preset_id = preset["id"]
                    break
            if not preset_id:
                preset_id = "light-crystal" if "claro" in folded_t else "dark-neon"
            result = self.nexus.apply_window_theme(tab, preset_id)
            if result.get("ok"):
                return result.get("message") or "Tema Nexus aplicado, Sir."
            return result.get("error") or "Nao consegui aplicar o tema Nexus."
        
        # 1. FINANCE: Ganhos e Gastos
        od = _parse_pt_date_fragment(t)
        # Ex: "ganhei 100 reais de lucro"
        income_match = re.search(r"(ganhei|recebi|lucro de)\s*(\d+(?:[.,]\d+)?)\s*reais", t)
        if income_match:
            val = float(income_match.group(2).replace(",", "."))
            return self.nexus.add_income(
                val, "Geral", "Entrada via voz", occurred_at=od, notes=None
            )

        # Ex: "gastei 50 reais com comida"
        expense_match = re.search(r"(gastei|paguei)\s*(\d+(?:[.,]\d+)?)\s*reais", t)
        if expense_match:
            val = float(expense_match.group(2).replace(",", "."))
            cat = "Geral"
            if "com " in t:
                rest = t.split("com ", 1)[1].strip()
                if rest:
                    cat = rest.split()[0].capitalize()
            return self.nexus.add_expense(
                val, cat, "Gasto via voz", occurred_at=od, notes=None, is_debt=0
            )

        add_gasto = re.search(
            r"(?:adicione|adicionar|registre|registrar)\s+(?:o\s+)?gasto(?:\s+de)?\s+(\d+(?:[.,]\d+)?)\s*reais",
            t,
        )
        if add_gasto:
            val = float(add_gasto.group(1).replace(",", "."))
            cat = "Geral"
            if " em " in t:
                cat = t.split(" em ", 1)[1].strip().split()[0].capitalize()
            return self.nexus.add_expense(
                val, cat, text.strip(), occurred_at=od, notes=None, is_debt=0
            )

        delete_finance = any(x in t for x in ["apague", "apagar", "remova", "remover", "delete", "deletar", "excluir", "cancele"]) and any(
            x in t for x in ["gasto", "receita", "ganho", "lucro", "movimento", "transa"]
        )
        if delete_finance:
            tx_type = "income" if any(x in t for x in ["receita", "ganho", "lucro"]) else "expense"
            amount = None
            amount_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:reais|r\$)?", t)
            if amount_match:
                amount = float(amount_match.group(1).replace(",", "."))
            m_desc = re.search(
                r"(?:com|em|de)\s+(.+?)(?:\s+(?:de\s+)?(?:hoje|ontem|anteontem|ante ontem|ontem de ontem)|$)",
                t,
            )
            desc = _clean_money_description(m_desc.group(1) if m_desc else t)
            result = self.nexus.delete_finance_transaction(
                description=desc or None,
                tx_type=tx_type,
                occurred_at=od,
                amount=amount,
            )
            return result["message"]

        update_finance = any(
            x in t
            for x in ["corrija", "corrigir", "atualize", "atualizar", "altere", "alterar", "mude", "mudar", "edite", "editar"]
        ) and any(
            x in t for x in ["gasto", "receita", "ganho", "lucro", "movimento", "transa"]
        )
        if update_finance:
            tx_type = "income" if any(x in t for x in ["receita", "ganho", "lucro"]) else "expense"
            new_amount = None
            amount_match = re.search(r"(?:para|pra|por)\s*(\d+(?:[.,]\d+)?)\s*(?:reais|r\$)?", t)
            if amount_match:
                new_amount = float(amount_match.group(1).replace(",", "."))
            search_text = t[: amount_match.start()] if amount_match else t
            m_desc = re.search(
                r"(?:com|em|de)\s+(.+?)(?:\s+(?:de\s+)?(?:hoje|ontem|anteontem|ante ontem|ontem de ontem)|$)",
                search_text,
            )
            desc = _clean_money_description(m_desc.group(1) if m_desc else search_text)
            result = self.nexus.update_finance_transaction(
                target_description=desc or None,
                target_type=tx_type,
                target_occurred_at=od,
                amount=new_amount,
            )
            return result["message"]

        if (
            "crie um preset" in t
            or "criar preset" in t
            or "preset para" in t
            or "plano de habitos" in t
            or "plano de hÃ¡bitos" in t
        ):
            goals = t
            if " para " in goals:
                goals = goals.split(" para ", 1)[1]
            goals = goals.replace("crie um preset", "").replace("criar preset", "").replace("preset", "").strip()
            return self.nexus.build_lifestyle_preset_from_goals(goals or text)

        # 1b. HABITS: Editar dias/nome
        _DAY_NAMES = {
            "segunda": 0, "seg": 0,
            "terca": 1, "terça": 1, "ter": 1,
            "quarta": 2, "qua": 2,
            "quinta": 3, "qui": 3,
            "sexta": 4, "sex": 4,
            "sabado": 5, "sábado": 5, "sab": 5,
            "domingo": 6, "dom": 6,
        }
        edit_habit = any(x in t for x in ["mude", "mudar", "altere", "alterar", "edite", "editar"]) and any(
            x in t for x in ["hábito", "habito", "academia", "treino", "estudo"]
        )
        if not edit_habit:
            # Also match "mude X para ..."
            edit_habit = re.search(r"(mude|altere|edite)\s+\w+\s+para\s+", t) is not None
        if edit_habit:
            habits = self.nexus.db.get_habits()
            # Try to find the habit name in the text
            target_habit = None
            for h in habits:
                if _fold_text(h["name"]) in _fold_text(t):
                    target_habit = h
                    break
            if target_habit:
                # Parse day names from the text
                words = _fold_text(t).split()
                parsed_days = []
                for w in words:
                    if w in {_fold_text(k): v for k, v in _DAY_NAMES.items()}:
                        parsed_days.append({_fold_text(k): v for k, v in _DAY_NAMES.items()}[w])
                    elif w in _DAY_NAMES:
                        parsed_days.append(_DAY_NAMES[w])
                if parsed_days:
                    import json as _json
                    self.nexus.db.update_habit(
                        target_habit["id"],
                        days_of_week=_json.dumps(sorted(set(parsed_days))),
                    )
                    from src.utils.nexus_notifier import broadcast_nexus_state
                    broadcast_nexus_state(self.nexus)
                    day_labels = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom"}
                    days_str = ", ".join(day_labels.get(d, str(d)) for d in sorted(set(parsed_days)))
                    return f"Hábito '{target_habit['name']}' atualizado para {days_str}, Sir."

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
            folded_request = _fold_text(t)
            for r in rewards:
                folded_name = _fold_text(r["name"])
                reward_words = [w for w in folded_name.split() if len(w) >= 4]
                if folded_name in folded_request or any(w in folded_request for w in reward_words):
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
            self.nexus.open_nexus_ui("board")
            return "Quadro estratégico projetado, Sir."
        
        if "abrir notas" in t or "abrir editor" in t or "mindpalace" in t or "notion" in t:
            self.nexus.open_nexus_ui("notes")
            return "Workspace MindPalace inicializado. Pronto para suas anotações."

        if "abrir nexus" in t or "abrir painel" in t:
            return self.nexus.open_nexus_ui("dashboard")

        if "voltar para o dashboard" in t or "mostrar hud" in t or "visão geral" in t:
            self.nexus.open_nexus_ui("dashboard")
            return "Retornando à visão tática geral."

        # 11. TAREFAS
        if "adicione tarefa" in t or "nova tarefa" in t:
            title = (
                t.replace("adicione tarefa", "")
                .replace("nova tarefa", "")
                .strip()
                or "Tarefa"
            )
            due = _parse_pt_date_fragment(t)
            tid = self.nexus.db.add_task(title[:200], due, 10)
            from src.utils.nexus_notifier import broadcast_nexus_state

            broadcast_nexus_state(self.nexus)
            try:
                from src.ui.nexus_signals import enqueue_nexus_desktop_open

                enqueue_nexus_desktop_open("tasks", {"highlight_id": tid, "animate": "add"})
            except Exception:
                pass
            return f"Tarefa #{tid} criada, Sir."

        if "concluí tarefa" in t or "completei tarefa" in t:
            m = re.search(r"#?(\d+)", t)
            if m:
                self.nexus.db.complete_task(int(m.group(1)))
                from src.utils.nexus_notifier import broadcast_nexus_state

                broadcast_nexus_state(self.nexus)
                return "Tarefa marcada como concluída."

        return None
