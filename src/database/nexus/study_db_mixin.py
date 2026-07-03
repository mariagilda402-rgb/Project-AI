import sqlite3
import json
from pathlib import Path
from datetime import datetime, date, timedelta



class NexusStudyDBMixin:
    def list_study_notes(self, subject: str | None = None):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            if subject:
                rows = conn.execute(
                    "SELECT * FROM study_notes WHERE subject = ? ORDER BY updated_at DESC",
                    (subject,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM study_notes ORDER BY updated_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def get_study_note(self, note_id: int):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM study_notes WHERE id = ?", (note_id,)).fetchone()
            return dict(row) if row else None

    def update_study_note(self, note_id: int, title=None, content=None, subject=None, color=None):
        fields = []
        vals = []
        if title is not None:
            fields.append("title = ?")
            vals.append(title)
        if content is not None:
            fields.append("content = ?")
            vals.append(content)
        if subject is not None:
            fields.append("subject = ?")
            vals.append(subject)
        if color is not None:
            fields.append("color = ?")
            vals.append(color)
        if not fields:
            return
        fields.append("updated_at = CURRENT_TIMESTAMP")
        vals.append(note_id)
        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE study_notes SET {', '.join(fields)} WHERE id = ?",
                vals,
            )
            conn.commit()

    def append_study_note_media(self, note_id: int, media_item: dict):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT media_links FROM study_notes WHERE id = ?", (note_id,)
            ).fetchone()
            if not row:
                return None
            try:
                media = json.loads(row["media_links"] or "[]")
                if not isinstance(media, list):
                    media = []
            except (TypeError, json.JSONDecodeError):
                media = []
            media.append(media_item)
            conn.execute(
                """
                UPDATE study_notes
                SET media_links = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (json.dumps(media, ensure_ascii=False), note_id),
            )
            conn.commit()
            return media

    def delete_study_note(self, note_id: int):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM flashcards WHERE note_id = ?", (note_id,))
            conn.execute("DELETE FROM study_notes WHERE id = ?", (note_id,))
            conn.commit()

    def list_flashcards_due(self, limit: int = 50):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT f.*, n.subject, n.title as note_title FROM flashcards f
                LEFT JOIN study_notes n ON n.id = f.note_id
                WHERE datetime(f.next_review) <= datetime('now')
                ORDER BY datetime(f.next_review) LIMIT ?
            """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def update_flashcard_srs(
        self,
        card_id: int,
        ease_factor: float,
        interval: int,
        repetitions: int,
        next_review: str,
    ):
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE flashcards SET ease_factor=?, interval=?, repetitions=?, next_review=?
                WHERE id=?
            """,
                (ease_factor, interval, repetitions, next_review, card_id),
            )
            conn.commit()

    def seed_quiz_if_empty(self):
        """Banco inicial ENEM-like, idempotente, com explicacoes para revisao."""
        samples = [
            {
                "area": "Matemática",
                "stem": "Uma família reduziu o consumo mensal de energia de 240 kWh para 204 kWh. Qual foi a redução percentual?",
                "options": ["12%", "15%", "18%", "36%"],
                "correct_index": 1,
                "skill": "Porcentagem",
                "difficulty": "media",
                "explanation": "A reducao foi de 36 kWh. Dividindo 36 por 240, obtemos 0,15, ou seja, 15%.",
            },
            {
                "area": "Matemática",
                "stem": "Em uma função afim f(x)=2x+3, qual é o valor de f(5)?",
                "options": ["10", "11", "13", "15"],
                "correct_index": 2,
                "skill": "Função afim",
                "difficulty": "facil",
                "explanation": "Substitua x por 5: f(5)=2*5+3=13.",
            },
            {
                "area": "Matemática",
                "stem": "Um reservatório comporta 1200 litros e está com 35% da capacidade. Quantos litros faltam para enchê-lo?",
                "options": ["420", "650", "780", "900"],
                "correct_index": 2,
                "skill": "Grandezas e porcentagem",
                "difficulty": "media",
                "explanation": "35% de 1200 sao 420 litros. Faltam 1200-420=780 litros.",
            },
            {
                "area": "Português",
                "stem": "Na frase 'Ela estudou muito, portanto foi bem na prova', a palavra 'portanto' indica:",
                "options": ["oposição", "conclusão", "adição", "condição"],
                "correct_index": 1,
                "skill": "Conectivos argumentativos",
                "difficulty": "facil",
                "explanation": "'Portanto' introduz uma consequencia/conclusao em relacao ao que foi dito antes.",
            },
            {
                "area": "Português",
                "stem": "Em textos dissertativo-argumentativos, a tese é:",
                "options": ["um exemplo secundário", "a opinião central defendida", "a citação obrigatória", "o resumo final"],
                "correct_index": 1,
                "skill": "Tese e argumentação",
                "difficulty": "facil",
                "explanation": "A tese e o ponto de vista central que o texto defende com argumentos.",
            },
            {
                "area": "Português",
                "stem": "A expressão 'chuva de ideias' é um exemplo de linguagem:",
                "options": ["literal", "figurada", "técnica", "jurídica"],
                "correct_index": 1,
                "skill": "Figuras de linguagem",
                "difficulty": "media",
                "explanation": "A expressao nao descreve chuva real; usa sentido figurado para indicar muitas ideias.",
            },
            {
                "area": "Ciências da Natureza",
                "stem": "Durante a fotossíntese, a fase clara produz principalmente:",
                "options": ["glicose e oxigênio", "ATP e NADPH", "DNA e RNA", "sais minerais"],
                "correct_index": 1,
                "skill": "Fotossíntese",
                "difficulty": "media",
                "explanation": "A fase clara transforma energia luminosa em ATP e NADPH, usados no ciclo de Calvin.",
            },
            {
                "area": "Ciências da Natureza",
                "stem": "Ao ligar vários aparelhos em uma mesma tomada, o risco de aquecimento aumenta principalmente por causa:",
                "options": ["da queda da gravidade", "do aumento da corrente elétrica", "da redução da frequência", "da ausência de tensão"],
                "correct_index": 1,
                "skill": "Eletricidade",
                "difficulty": "media",
                "explanation": "Mais aparelhos demandam maior corrente; o efeito Joule aumenta o aquecimento dos condutores.",
            },
            {
                "area": "Ciências da Natureza",
                "stem": "A mitocôndria é associada principalmente à:",
                "options": ["digestão intracelular", "respiração celular", "fotossíntese", "síntese de proteínas"],
                "correct_index": 1,
                "skill": "Citologia",
                "difficulty": "facil",
                "explanation": "Mitocondrias participam da respiracao celular e produzem ATP.",
            },
            {
                "area": "Ciências Humanas",
                "stem": "A Revolução Industrial intensificou a urbanização porque:",
                "options": ["eliminou todas as fábricas", "concentrou empregos nas cidades", "proibiu o comércio", "reduziu a produção"],
                "correct_index": 1,
                "skill": "Industrialização e urbanização",
                "difficulty": "facil",
                "explanation": "A concentracao de fabricas e empregos atraiu trabalhadores para os centros urbanos.",
            },
            {
                "area": "Ciências Humanas",
                "stem": "No Brasil, a política do café com leite na Primeira República relacionava-se ao predomínio de elites de:",
                "options": ["São Paulo e Minas Gerais", "Amazonas e Pará", "Bahia e Pernambuco", "Rio Grande do Sul e Ceará"],
                "correct_index": 0,
                "skill": "Primeira República",
                "difficulty": "media",
                "explanation": "Cafe remete a Sao Paulo e leite a Minas Gerais, estados com forte influencia politica no periodo.",
            },
            {
                "area": "Ciências Humanas",
                "stem": "O conceito de cidadania envolve, além de deveres, o acesso a direitos:",
                "options": ["apenas privados", "civis, políticos e sociais", "somente comerciais", "exclusivos de governantes"],
                "correct_index": 1,
                "skill": "Cidadania",
                "difficulty": "facil",
                "explanation": "Cidadania inclui direitos civis, politicos e sociais, alem da participacao na vida coletiva.",
            },
        ]
        with self._get_connection() as conn:
            for item in samples:
                row = conn.execute(
                    "SELECT id FROM quiz_questions WHERE stem = ?", (item["stem"],)
                ).fetchone()
                options_json = json.dumps(item["options"], ensure_ascii=False)
                if row:
                    conn.execute(
                        """
                        UPDATE quiz_questions
                        SET area=?, options_json=?, correct_index=?,
                            explanation=COALESCE(NULLIF(explanation, ''), ?),
                            skill=COALESCE(NULLIF(skill, ''), ?),
                            difficulty=COALESCE(NULLIF(difficulty, ''), ?),
                            source=COALESCE(NULLIF(source, ''), ?)
                        WHERE id=?
                    """,
                        (
                            item["area"],
                            options_json,
                            int(item["correct_index"]),
                            item["explanation"],
                            item["skill"],
                            item["difficulty"],
                            "ENEM-like seed",
                            row[0],
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO quiz_questions
                        (area, stem, options_json, correct_index, explanation, skill, difficulty, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            item["area"],
                            item["stem"],
                            options_json,
                            int(item["correct_index"]),
                            item["explanation"],
                            item["skill"],
                            item["difficulty"],
                            "ENEM-like seed",
                        ),
                    )
            conn.commit()

    def start_quiz_attempt(self, area: str | None):
        with self._get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO quiz_attempts (area) VALUES (?)", (area,)
            )
            conn.commit()
            return cur.lastrowid

    def finish_quiz_attempt(self, attempt_id: int, score_pct: float):
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE quiz_attempts SET finished_at = CURRENT_TIMESTAMP, score_pct = ?
                WHERE id = ?
            """,
                (score_pct, attempt_id),
            )
            conn.commit()

    def add_quiz_answer(self, attempt_id, question_id, chosen_index, correct: int):
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO quiz_answers (attempt_id, question_id, chosen_index, correct)
                VALUES (?, ?, ?, ?)
            """,
                (attempt_id, question_id, chosen_index, correct),
            )
            conn.commit()

    def get_quiz_attempt(self, attempt_id: int):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM quiz_attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_quiz_attempt_answers(self, attempt_id: int):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT
                    a.id AS answer_id,
                    a.attempt_id,
                    a.question_id,
                    a.chosen_index,
                    a.correct,
                    q.area,
                    q.stem,
                    q.options_json,
                    q.correct_index,
                    q.explanation,
                    q.skill,
                    q.difficulty,
                    q.source
                FROM quiz_answers a
                JOIN quiz_questions q ON q.id = a.question_id
                WHERE a.attempt_id = ?
                ORDER BY a.id
            """,
                (attempt_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def random_quiz_questions(self, n: int, area: str | None):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            if area:
                rows = conn.execute(
                    "SELECT * FROM quiz_questions WHERE area = ? ORDER BY RANDOM() LIMIT ?",
                    (area, n),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM quiz_questions ORDER BY RANDOM() LIMIT ?", (n,)
                ).fetchall()
            return [dict(r) for r in rows]

