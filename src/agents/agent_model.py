"""
Sistema de Multi-Agentes — Modelo de dados e gerenciador.
Cada agente tem: nome, personalidade, voz, velocidade, e coleção de memória vetorial isolada.
Os agentes são persistidos em data/agents.json.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

AGENTS_FILE = Path("data/agents.json")
TRASH_FILE = Path("data/agents_trash.json")

# Vozes Edge-TTS PT-BR comuns (para sugestão no painel)
EDGE_VOICES_PT_BR = [
    "pt-BR-AntonioNeural",   # Masculina
    "pt-BR-FranciscaNeural", # Feminina
    "pt-BR-ThalitaNeural",   # Feminina
    "pt-BR-GiovannaNeural",  # Feminina (jovem)
]


@dataclass
class AgentProfile:
    """Perfil completo de um agente de IA."""
    id: str = ""
    name: str = "Assistente"
    persona: str = "Você é uma assistente virtual amigável e prestativa."
    # TTS
    tts_provider: str = "edge"           # edge, kokoro, openai, local
    tts_voice: str = "pt-BR-FranciscaNeural"
    tts_speed: float = 1.0               # Multiplicador de velocidade (0.5 a 2.0)
    edge_tts_rate: str = "+10%"
    edge_tts_volume: str = "-20%"
    kokoro_voice: str = "pf_dora"
    # Memória
    memory_collection: str = ""          # Nome da coleção ChromaDB (isolada)
    # Metadados
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = uuid.uuid4().hex[:12]
        if not self.memory_collection:
            # Gera nome de coleção seguro (só alfanuméricos e underscore)
            safe_name = "".join(c if c.isalnum() else "_" for c in self.name.lower())
            self.memory_collection = f"agent_{safe_name}_{self.id[:6]}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


class AgentManager:
    """
    Gerencia o ciclo de vida dos agentes: criar, editar, deletar, restaurar.
    Persiste em JSON local. Thread-safe para acesso básico.
    """

    def __init__(self):
        self._agents: dict[str, AgentProfile] = {}
        self._trash: dict[str, AgentProfile] = {}
        self._active_agent_id: str = ""
        self._load()

    # ── Persistência ──

    def _load(self):
        """Carrega agentes do disco. Cria um agente padrão se não existir nenhum."""
        AGENTS_FILE.parent.mkdir(parents=True, exist_ok=True)

        if AGENTS_FILE.exists():
            try:
                raw = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
                for data in raw.get("agents", []):
                    agent = AgentProfile(**{k: v for k, v in data.items() if k in AgentProfile.__dataclass_fields__})
                    self._agents[agent.id] = agent
                self._active_agent_id = raw.get("active_agent_id", "")
            except Exception as e:
                logger.error(f"[AgentManager] Falha ao carregar agents.json: {e}")

        if TRASH_FILE.exists():
            try:
                raw = json.loads(TRASH_FILE.read_text(encoding="utf-8"))
                for data in raw:
                    agent = AgentProfile(**{k: v for k, v in data.items() if k in AgentProfile.__dataclass_fields__})
                    self._trash[agent.id] = agent
            except Exception as e:
                logger.error(f"[AgentManager] Falha ao carregar lixeira: {e}")

        # Se não existir nenhum agente, cria o padrão
        if not self._agents:
            default = AgentProfile(
                name="Assistente",
                persona=(
                    "Você é uma assistente virtual inteligente, amigável e direta. "
                    "Responda em português BR de forma natural e concisa."
                ),
                tts_provider="edge",
                tts_voice="pt-BR-FranciscaNeural",
            )
            self._agents[default.id] = default
            self._active_agent_id = default.id
            self._save()
            print(f"[AgentManager] Agente padrão criado: '{default.name}' ({default.id})")

        # Garante que active_agent_id é válido
        if self._active_agent_id not in self._agents:
            self._active_agent_id = next(iter(self._agents))

        count = len(self._agents)
        trash_count = len(self._trash)
        print(f"[AgentManager] {count} agente(s) carregado(s). Lixeira: {trash_count}.")

    def _save(self):
        """Salva o estado atual em disco."""
        try:
            AGENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "active_agent_id": self._active_agent_id,
                "agents": [asdict(a) for a in self._agents.values()],
            }
            AGENTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"[AgentManager] Falha ao salvar agents.json: {e}")

        try:
            trash_data = [asdict(a) for a in self._trash.values()]
            TRASH_FILE.write_text(json.dumps(trash_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"[AgentManager] Falha ao salvar lixeira: {e}")

    # ── CRUD ──

    def create_agent(self, name: str, persona: str, **kwargs) -> AgentProfile:
        """Cria um novo agente e retorna o perfil."""
        agent = AgentProfile(name=name, persona=persona, **kwargs)
        self._agents[agent.id] = agent
        self._save()
        print(f"[AgentManager] Novo agente criado: '{agent.name}' ({agent.id})")
        return agent

    def update_agent(self, agent_id: str, **kwargs) -> AgentProfile | None:
        """Atualiza campos de um agente existente."""
        agent = self._agents.get(agent_id)
        if not agent:
            logger.warning(f"[AgentManager] Agente {agent_id} não encontrado para edição.")
            return None
        for key, value in kwargs.items():
            if hasattr(agent, key) and key not in ("id", "created_at", "memory_collection"):
                setattr(agent, key, value)
        agent.updated_at = datetime.now().isoformat()
        self._save()
        return agent

    def delete_agent(self, agent_id: str) -> bool:
        """Move um agente para a lixeira (soft delete). Não apaga memórias."""
        agent = self._agents.pop(agent_id, None)
        if not agent:
            return False
        agent.is_active = False
        self._trash[agent.id] = agent
        # Se o agente deletado era o ativo, muda para outro
        if self._active_agent_id == agent_id and self._agents:
            self._active_agent_id = next(iter(self._agents))
        self._save()
        print(f"[AgentManager] Agente '{agent.name}' movido para a lixeira.")
        return True

    def restore_agent(self, agent_id: str) -> bool:
        """Restaura um agente da lixeira."""
        agent = self._trash.pop(agent_id, None)
        if not agent:
            return False
        agent.is_active = True
        self._agents[agent.id] = agent
        self._save()
        print(f"[AgentManager] Agente '{agent.name}' restaurado da lixeira.")
        return True

    def permanent_delete(self, agent_id: str) -> bool:
        """Deleta permanentemente um agente e suas memórias vetoriais."""
        agent = self._trash.pop(agent_id, None)
        if not agent:
            return False
        # Tenta apagar a coleção ChromaDB associada
        try:
            from src.memory.vector_db import SemanticMemory
            sm = SemanticMemory()
            if sm.enabled:
                sm.client.delete_collection(name=agent.memory_collection)
                print(f"[AgentManager] Memórias vetoriais de '{agent.name}' apagadas.")
        except Exception as e:
            logger.warning(f"[AgentManager] Falha ao apagar coleção ChromaDB '{agent.memory_collection}': {e}")
        self._save()
        print(f"[AgentManager] Agente '{agent.name}' deletado permanentemente.")
        return True

    def clear_agent_memories(self, agent_id: str) -> bool:
        """Apaga apenas as memórias vetoriais de um agente (sem deletar o agente)."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        try:
            from src.memory.vector_db import SemanticMemory
            sm = SemanticMemory()
            if sm.enabled:
                # Recria a coleção vazia
                sm.client.delete_collection(name=agent.memory_collection)
                sm.client.get_or_create_collection(
                    name=agent.memory_collection,
                    metadata={"hnsw:space": "cosine"}
                )
                print(f"[AgentManager] Memórias de '{agent.name}' limpas com sucesso.")
                return True
        except Exception as e:
            logger.warning(f"[AgentManager] Falha ao limpar memórias: {e}")
        return False

    # ── Seleção ──

    def get_active_agent(self) -> AgentProfile:
        """Retorna o agente ativo atual."""
        return self._agents[self._active_agent_id]

    def set_active_agent(self, agent_id: str) -> bool:
        """Define qual agente está ativo."""
        if agent_id not in self._agents:
            return False
        self._active_agent_id = agent_id
        self._save()
        print(f"[AgentManager] Agente ativo: '{self._agents[agent_id].name}'")
        return True

    def list_agents(self) -> list[AgentProfile]:
        """Lista todos os agentes (não inclui lixeira)."""
        return list(self._agents.values())

    def list_trash(self) -> list[AgentProfile]:
        """Lista agentes na lixeira."""
        return list(self._trash.values())

    def find_agent_by_name(self, name: str) -> AgentProfile | None:
        """Busca um agente pelo nome (case-insensitive, parcial)."""
        name_lower = name.strip().lower()
        for agent in self._agents.values():
            if name_lower in agent.name.lower():
                return agent
        return None
