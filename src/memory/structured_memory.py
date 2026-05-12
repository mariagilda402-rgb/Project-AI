"""
Memória Estruturada — inspirada no Mark-XXXV memory_manager.
Organiza fatos em 6 categorias: identity, preferences, projects, relationships, wishes, notes.
Inclui formatação para prompt, extração inteligente e consolidação.
"""

import json
from datetime import datetime
from threading import Lock
from pathlib import Path

STRUCTURED_MEMORY_PATH = Path("data/structured_memory.json")
_lock = Lock()
MAX_VALUE_LENGTH = 400


def _empty_memory() -> dict:
    return {
        "identity":      {},   # nome, idade, cidade, profissão, idioma, nacionalidade
        "preferences":   {},   # comida, cor, música, filme, jogo, esporte, hobbies
        "projects":      {},   # projetos ativos, metas, coisas sendo construídas
        "relationships": {},   # amigos, família, parceiro, colegas
        "wishes":        {},   # planos futuros, coisas para comprar, viagens
        "notes":         {},   # qualquer outra coisa que vale lembrar
    }


def load_structured_memory() -> dict:
    if not STRUCTURED_MEMORY_PATH.exists():
        return _empty_memory()
    with _lock:
        try:
            data = json.loads(STRUCTURED_MEMORY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                base = _empty_memory()
                for key in base:
                    if key not in data:
                        data[key] = {}
                return data
            return _empty_memory()
        except Exception as e:
            print(f"[StructuredMemory] ⚠️ Load error: {e}")
            return _empty_memory()


def save_structured_memory(memory: dict) -> None:
    if not isinstance(memory, dict):
        return
    STRUCTURED_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        STRUCTURED_MEMORY_PATH.write_text(
            json.dumps(memory, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )


def _truncate_value(val: str) -> str:
    if isinstance(val, str) and len(val) > MAX_VALUE_LENGTH:
        return val[:MAX_VALUE_LENGTH].rstrip() + "…"
    return val


def _recursive_update(target: dict, updates: dict) -> bool:
    """Atualiza recursivamente o dicionário target com os updates."""
    changed = False
    for key, value in updates.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue

        if isinstance(value, dict) and "value" not in value:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
                changed = True
            if _recursive_update(target[key], value):
                changed = True
        else:
            if isinstance(value, dict) and "value" in value:
                new_val = _truncate_value(str(value["value"]))
            else:
                new_val = _truncate_value(str(value))

            entry = {"value": new_val, "updated": datetime.now().strftime("%Y-%m-%d")}
            existing = target.get(key, {})
            if not isinstance(existing, dict) or existing.get("value") != new_val:
                target[key] = entry
                changed = True

    return changed


def update_structured_memory(memory_update: dict) -> dict:
    """Atualiza a memória estruturada com novos fatos."""
    if not isinstance(memory_update, dict) or not memory_update:
        return load_structured_memory()

    memory = load_structured_memory()
    if _recursive_update(memory, memory_update):
        save_structured_memory(memory)
        print(f"[StructuredMemory] 💾 Saved: {list(memory_update.keys())}")
    return memory


def remember(key: str, value: str, category: str = "notes") -> str:
    """Salva um fato na categoria especificada."""
    valid = {"identity", "preferences", "projects", "relationships", "wishes", "notes"}
    if category not in valid:
        category = "notes"
    update_structured_memory({category: {key: {"value": value}}})
    return f"Memorizado: {category}/{key} = {value}"


def forget(key: str, category: str = "notes") -> str:
    """Remove um fato da memória."""
    memory = load_structured_memory()
    cat = memory.get(category, {})
    if key in cat:
        del cat[key]
        memory[category] = cat
        save_structured_memory(memory)
        return f"Esquecido: {category}/{key}"
    return f"Não encontrado: {category}/{key}"


def format_memory_for_prompt(memory: dict | None = None) -> str:
    """Formata a memória estruturada para injeção no system prompt."""
    if memory is None:
        memory = load_structured_memory()
    if not memory:
        return ""

    lines = []

    # Identity
    identity = memory.get("identity", {})
    id_fields = ["name", "age", "birthday", "city", "job", "language", "school", "nationality"]
    for field in id_fields:
        entry = identity.get(field)
        if entry:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"{field.title()}: {val}")
    for key, entry in identity.items():
        if key in id_fields:
            continue
        val = entry.get("value") if isinstance(entry, dict) else entry
        if val:
            lines.append(f"{key.replace('_', ' ').title()}: {val}")

    # Preferences
    prefs = memory.get("preferences", {})
    if prefs:
        lines.append("")
        lines.append("Preferencias:")
        for key, entry in list(prefs.items())[:15]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    # Projects
    projects = memory.get("projects", {})
    if projects:
        lines.append("")
        lines.append("Projetos Ativos:")
        for key, entry in list(projects.items())[:8]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    # Relationships
    rels = memory.get("relationships", {})
    if rels:
        lines.append("")
        lines.append("Pessoas na vida do usuario:")
        for key, entry in list(rels.items())[:10]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    # Wishes
    wishes = memory.get("wishes", {})
    if wishes:
        lines.append("")
        lines.append("Desejos / Planos:")
        for key, entry in list(wishes.items())[:8]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    # Notes
    notes = memory.get("notes", {})
    if notes:
        lines.append("")
        lines.append("Notas:")
        for key, entry in list(notes.items())[:8]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key}: {val}")

    if not lines:
        return ""

    header = "[O QUE VOCE SABE SOBRE O USUARIO — use naturalmente, nunca recite como lista]\n"
    result = header + "\n".join(lines)
    if len(result) > 2000:
        result = result[:1997] + "…"

    return result + "\n"


def should_extract_memory(user_text: str, assistant_text: str, llm_service) -> bool:
    """Stage 1: Verificação rápida YES/NO antes de gastar tokens na extração."""
    try:
        combined = f"User: {user_text[:300]}\nAssistant: {assistant_text[:200]}"
        check = llm_service.chat(
            system_prompt="Responda APENAS YES ou NO.",
            messages=[{
                "role": "user",
                "content": (
                    f"Essa conversa contém ALGUM dos seguintes?\n"
                    f"- Fatos pessoais (nome, idade, cidade, profissão, aniversário)\n"
                    f"- Preferências (comida, cor, música, filme, jogo, esporte, hobby)\n"
                    f"- Projetos ativos ou metas\n"
                    f"- Pessoas na vida do usuário (amigos, família, parceiro)\n"
                    f"- Coisas que o usuário quer fazer ou comprar no futuro\n"
                    f"- Qualquer outro fato que vale lembrar a longo prazo\n\n"
                    f"Conversa:\n{combined}"
                )
            }]
        )
        return check and "YES" in check.upper()
    except Exception as e:
        print(f"[StructuredMemory] ⚠️ Stage1 check failed: {e}")
        return False


def extract_structured_memory(user_text: str, assistant_text: str, llm_service) -> dict:
    """Stage 2: Extração detalhada de fatos em formato JSON estruturado."""
    try:
        combined = f"User: {user_text[:500]}\nAssistant: {assistant_text[:300]}"
        raw = llm_service.chat(
            system_prompt="Você é um extrator de informações pessoais. Responda APENAS com JSON válido.",
            messages=[{
                "role": "user",
                "content": (
                    f"Extraia TODOS os fatos pessoais memorizáveis dessa conversa.\n"
                    f"Retorne APENAS JSON válido. Use {{}} se nada for relevante.\n\n"
                    f"Categorias:\n"
                    f"  identity      → nome, idade, aniversario, cidade, pais, profissao, escola, idioma\n"
                    f"  preferences   → comida, cor, musica, filme, jogo, esporte, hobby, artista, etc.\n"
                    f"  projects      → projetos sendo construidos, metas, trabalhos em andamento\n"
                    f"  relationships → amigos, familia, parceiro, colegas\n"
                    f"  wishes        → planos futuros, coisas para comprar, viagens\n"
                    f"  notes         → qualquer outra coisa que valha lembrar\n\n"
                    f"Formato:\n"
                    f'{{"identity":{{"name":{{"value":"Jamil"}}}},\n'
                    f' "preferences":{{"hobby":{{"value":"programacao"}}}},\n'
                    f' "projects":{{"assistente_ia":{{"value":"Construindo assistente IA pessoal"}}}}}}\n\n'
                    f"Conversa:\n{combined}\n\nJSON:"
                )
            }]
        )

        if not raw:
            return {}
        import re
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        if not raw or raw == "{}":
            return {}
        return json.loads(raw)

    except json.JSONDecodeError:
        return {}
    except Exception as e:
        if "429" not in str(e):
            print(f"[StructuredMemory] ⚠️ Extract failed: {e}")
        return {}
