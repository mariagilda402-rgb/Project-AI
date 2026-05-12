from src.database.nexus_db import NexusDatabase
from src.utils.nexus_notifier import broadcast_nexus_state, log_nexus_event
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class NexusService:
    def __init__(self):
        self.db = NexusDatabase()
        
    def add_expense(self, amount, category, description, necessity=5):
        """Registra um gasto e atualiza o estado financeiro."""
        try:
            self.db.add_transaction("expense", amount, category, description, necessity)
            log_nexus_event(f"Gasto registrado: R$ {amount:.2f} ({category})")
            broadcast_nexus_state(self)
            return f"Gasto de R$ {amount:.2f} em '{category}' registrado, Sir."
        except Exception as e:
            logger.error(f"Erro ao adicionar gasto: {e}")
            return "Houve um erro ao processar a transação financeira."

    def add_income(self, amount, category, description):
        """Registra um ganho."""
        try:
            self.db.add_transaction("income", amount, category, description, 10)
            log_nexus_event(f"Lucro registrado: R$ {amount:.2f}")
            broadcast_nexus_state(self)
            return f"Entrada de R$ {amount:.2f} registrada com sucesso."
        except Exception as e:
            logger.error(f"Erro ao adicionar ganho: {e}")
            return "Erro ao registrar lucro."

    def complete_habit(self, habit_name):
        """Marca um hábito como concluído e premia com XP + bônus de streak."""
        try:
            habits = self.db.get_habits()
            target = next((h for h in habits if habit_name.lower() in h['name'].lower()), None)
            
            if not target:
                return f"Não encontrei o hábito '{habit_name}' na sua lista, Sir."
            
            self.db.log_habit_completion(target['id'])
            
            base_xp = target.get('xp_reward', 50)
            streak = target.get('current_streak', 0) + 1
            bonus = min(base_xp, int(base_xp * (streak * 0.1)))
            total_xp = base_xp + bonus
            
            self.db.add_xp(total_xp)
            log_nexus_event(f"HABIT DONE: {target['name']} (+{total_xp} XP)")
            broadcast_nexus_state(self)
            
            return f"Hábito '{target['name']}' concluído! +{total_xp} XP (Streak: {streak}). Muito bem, Sir."
        except Exception as e:
            logger.error(f"Erro ao concluir hábito: {e}")
            return "Falha ao registrar conclusão do hábito."

    def get_summary(self):
        """Retorna um resumo rápido para o Jarvis falar."""
        stats = self.db.get_user_stats()
        return f"Sir, seu nível atual é {stats['level']} com {stats['points']} pontos disponíveis para troca."

    def get_rewards(self):
        """Lista todas as recompensas disponíveis."""
        with self.db._get_connection() as conn:
            rows = conn.execute("SELECT name, cost, description FROM nexus_rewards").fetchall()
            return [{"name": r[0], "cost": r[1], "description": r[2]} for r in rows]

    def set_focus_mode(self, active=True):
        """Ativa ou desativa o ambiente de foco (Silêncio + Música)."""
        import subprocess
        try:
            status = "ATIVADO" if active else "DESATIVADO"
            val = 0 if active else 1
            # Garante que a chave existe antes de setar
            setup_cmd = 'if (!(Test-Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings")) { New-Item -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings" -Force }'
            set_cmd = f'Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings" -Name "NOC_GLOBAL_SETTING_TOASTS_ENABLED" -Value {val}'
            
            subprocess.run(["powershell", "-Command", f"{setup_cmd}; {set_cmd}"], capture_output=True)
            
            if active:
                from src.tools.spotify import SpotifyTool
                sp = SpotifyTool()
                sp.search_and_play("Lofi Study Focus")
            
            log_nexus_event(f"PROTOCOL: Focus Mode {status}")
            broadcast_nexus_state(self)
            
            return f"Modo de Foco {status}, Sir. Ambiente preparado."
        except Exception as e:
            logger.error(f"Erro no modo foco: {e}")
            return "Falha ao ajustar o protocolo de foco."

    def process_reward(self, reward_name):
        """Tenta resgatar uma recompensa pelo nome."""
        with self.db._get_connection() as conn:
            reward = conn.execute("SELECT cost FROM nexus_rewards WHERE name LIKE ?", (f"%{reward_name}%",)).fetchone()
            if not reward:
                return False, f"Não encontrei a recompensa '{reward_name}', Sir."
            
            cost = reward[0]
            stats = self.db.get_user_stats()
            
            if stats['points'] >= cost:
                with self.db._get_connection() as conn_up:
                    conn_up.execute("UPDATE nexus_user SET points = points - ? WHERE id = 1", (cost,))
                    conn_up.commit()
                log_nexus_event(f"REWARD: {reward_name} Resgatada")
                broadcast_nexus_state(self)
                return True, f"Recompensa '{reward_name}' liberada! Aproveite, Sir."
            return False, f"Saldo insuficiente, Sir."

    # --- MINDPALACE (ESTUDOS) ---

    def create_note(self, subject, title, content, media=None):
        """Cria uma nova nota de estudo."""
        try:
            with self.db._get_connection() as conn:
                conn.execute("""
                    INSERT INTO study_notes (subject, title, content, media_links)
                    VALUES (?, ?, ?, ?)
                """, (subject, title, content, json.dumps(media or [])))
                conn.commit()
            log_nexus_event(f"MINDPALACE: Nota '{title}' arquivada.")
            broadcast_nexus_state(self)
            return f"Nota '{title}' sobre {subject} foi salva no seu MindPalace, Sir."
        except Exception as e:
            logger.error(f"Erro ao criar nota: {e}")
            return "Erro ao arquivar nota."

    def add_flashcard(self, note_id, front, back):
        """Adiciona um flashcard a uma nota específica."""
        try:
            with self.db._get_connection() as conn:
                conn.execute("""
                    INSERT INTO flashcards (note_id, front, back)
                    VALUES (?, ?, ?)
                """, (note_id, front, back))
                conn.commit()
            log_nexus_event(f"MINDPALACE: Flashcard gerado.")
            return "Flashcard adicionado com sucesso."
        except Exception as e:
            logger.error(f"Erro ao adicionar flashcard: {e}")
            return "Erro ao criar flashcard."

    def get_review_count(self):
        """Retorna quantos flashcards precisam de revisão hoje."""
        with self.db._get_connection() as conn:
            now = datetime.now().isoformat()
            count = conn.execute("SELECT COUNT(*) FROM flashcards WHERE next_review <= ?", (now,)).fetchone()[0]
            return count

    def log_study_result(self, subject, correct=True):
        """Registra o resultado de uma questão de estudo."""
        try:
            with self.db._get_connection() as conn:
                if correct:
                    conn.execute("""
                        UPDATE study_stats 
                        SET total_questions = total_questions + 1, correct_answers = correct_answers + 1, last_attempt = CURRENT_TIMESTAMP
                        WHERE subject = ?
                    """, (subject,))
                else:
                    conn.execute("""
                        UPDATE study_stats 
                        SET total_questions = total_questions + 1, last_attempt = CURRENT_TIMESTAMP
                        WHERE subject = ?
                    """, (subject,))
                conn.commit()
            
            xp = 30 if correct else 10
            self.db.add_xp(xp)
            
            status = "ACERTOU" if correct else "ERROU"
            log_nexus_event(f"ESTUDO: {subject} ({status})")
            broadcast_nexus_state(self)
            
            return f"Resultado registrado, Sir. +{xp} XP em {subject}."
        except Exception as e:
            logger.error(f"Erro ao registrar estudo: {e}")
            return "Falha ao salvar desempenho."

    def get_study_stats(self):
        """Retorna as estatísticas de estudo para o HUD."""
        import sqlite3
        with self.db._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM study_stats").fetchall()
            return [dict(r) for r in rows]

    # --- STRATEGY ENGINE (PRESETS) ---

    def save_lifestyle_preset(self, name):
        """Salva o estado atual de hábitos como um preset."""
        try:
            habits = self.db.get_habits()
            config = json.dumps(habits)
            with self.db._get_connection() as conn:
                conn.execute("""
                    INSERT INTO lifestyle_presets (name, config_json)
                    VALUES (?, ?)
                """, (name, config))
                conn.commit()
            log_nexus_event(f"STRATEGY: Preset '{name}' salvo.")
            return f"Preset de vida '{name}' foi imortalizado, Sir."
        except Exception as e:
            logger.error(f"Erro ao salvar preset: {e}")
            return "Falha ao salvar configuração estratégica."

    def load_lifestyle_preset(self, name):
        """Carrega um preset de vida, substituindo os hábitos atuais."""
        try:
            with self.db._get_connection() as conn:
                row = conn.execute("SELECT config_json FROM lifestyle_presets WHERE name LIKE ?", (f"%{name}%",)).fetchone()
                if not row:
                    return f"Não encontrei o preset '{name}', Sir."
                
                new_habits = json.loads(row[0])
                # Limpa hábitos atuais e insere os do preset
                conn.execute("UPDATE habits SET active = 0")
                for h in new_habits:
                    conn.execute("""
                        INSERT OR REPLACE INTO habits (id, name, description, xp_reward, active)
                        VALUES (?, ?, ?, ?, 1)
                    """, (h['id'], h['name'], h['description'], h['xp_reward']))
                conn.commit()
            
            log_nexus_event(f"STRATEGY: Preset '{name}' ativado.")
            broadcast_nexus_state(self)
            return f"Protocolo '{name}' ativado. Todos os sistemas reconfigurados."
        except Exception as e:
            logger.error(f"Erro ao carregar preset: {e}")
            return "Falha na reconfiguração estratégica."

    # --- GRAND OBJECTIVES (METAS) ---

    def add_goal(self, name, target_date=None):
        """Adiciona um grande objetivo de longo prazo."""
        try:
            with self.db._get_connection() as conn:
                conn.execute("""
                    INSERT INTO nexus_goals (name, target_date)
                    VALUES (?, ?)
                """, (name, target_date))
                conn.commit()
            log_nexus_event(f"GOAL: '{name}' Estabelecido.")
            broadcast_nexus_state(self)
            return f"Meta '{name}' registrada no horizonte estratégico, Sir."
        except Exception as e:
            logger.error(f"Erro ao adicionar meta: {e}")
            return "Falha ao registrar objetivo."

    def update_goal_progress(self, name, progress):
        """Atualiza o progresso (0-100) de uma meta de forma precisa."""
        try:
            with self.db._get_connection() as conn:
                # Busca a meta que melhor coincide
                row = conn.execute("SELECT name FROM nexus_goals WHERE name LIKE ? ORDER BY length(name) ASC", (f"%{name}%",)).fetchone()
                if not row:
                    return f"Não encontrei nenhuma meta parecida com '{name}', Sir."
                
                real_name = row[0]
                conn.execute("""
                    UPDATE nexus_goals SET progress = ? WHERE name = ?
                """, (progress, real_name))
                conn.commit()
            
            log_nexus_event(f"GOAL UPDATE: {real_name} ({progress}%)")
            broadcast_nexus_state(self)
            return f"Meta '{real_name}' avançou para {progress}%. Mantenha o ritmo, Sir."
        except Exception as e:
            logger.error(f"Erro ao atualizar meta: {e}")
            return "Falha ao sincronizar progresso."

    def get_goals(self):
        """Retorna a lista de metas ativas."""
        import sqlite3
        with self.db._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM nexus_goals WHERE status = 'active'").fetchall()
            return [dict(r) for r in rows]

    def change_aura(self, color_name):
        """Muda a cor do HUD (Aura)."""
        mapping = {
            "ciano": "cyan",
            "vermelho": "red",
            "roxo": "purple",
            "esmeralda": "emerald",
            "verde": "emerald",
            "stark": "red"
        }
        theme = mapping.get(color_name.lower(), "cyan")
        payload = {
            "type": "theme_change",
            "theme": theme
        }
        from src.utils.nexus_notifier import notify_nexus_update
        notify_nexus_update(payload)
        log_nexus_event(f"AURA: Mudança para {theme.upper()}")
        return f"Aura alterada para {color_name}, Sir. Sistemas recalibrados."
    def change_hud_tab(self, tab_name):
        """Muda a aba ativa no HUD."""
        payload = {
            "type": "tab_change",
            "tab": tab_name
        }
        from src.utils.nexus_notifier import notify_nexus_update
        notify_nexus_update(payload)
        log_nexus_event(f"NAV: Alternado para aba {tab_name.upper()}")
        return True

    def open_nexus_ui(self):
        """Abre o Dashboard do Nexus no navegador padrão."""
        import webbrowser
        webbrowser.open("http://localhost:5123/nexus")
        log_nexus_event("SYSTEM: Interface Nexus projetada no navegador.")
        return "Abrindo a interface Nexus, Sir. Projeção tática iniciada."
