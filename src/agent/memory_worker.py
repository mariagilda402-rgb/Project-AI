"""
memory_worker.py
================
Gerencia consolidação de memória em background após cada resposta do Jarvis.

Responsabilidades:
- Extração semântica (ChromaDB via RAG)
- Extração estruturada em JSON
- Sumarização de histórico quando necessário
- Logging no heartbeat diário
"""
from __future__ import annotations

import logging
import threading
import traceback

logger = logging.getLogger(__name__)


def post_process_async(
    *,
    text: str,
    final: str,
    speaker_name: str,
    access_level: int,
    llm,
    memory,
    semantic_memory,
    agent_manager,
    clean_response_fn,
):
    """Grava resposta no histórico e dispara tarefas de consolidação de memória.

    Args:
        text: Mensagem original do usuário.
        final: Resposta gerada pelo Jarvis.
        speaker_name: Nome do falante identificado.
        access_level: Nível de acesso do falante (0=desconhecido, 100=admin).
        llm: Instância do LLMService.
        memory: Instância do MemoryStore.
        semantic_memory: Instância do SemanticMemory.
        agent_manager: Instância do AgentManager.
        clean_response_fn: Função que limpa tags de function calling da resposta.
    """
    final = clean_response_fn(final)
    memory.add_short_term("assistant", final)
    memory.maybe_store_preference(text, final, consent_for_sensitive=True)

    provider = getattr(llm, "last_provider", llm.primary_llm_provider)
    model = getattr(llm, "last_model", "")
    print(f"\n[🤖 LLM] {provider.upper()} | {model}", flush=True)

    maybe_summarize(memory=memory, llm=llm)

    try:
        from src.services.heartbeat import append_daily_log
        append_daily_log(f"User: {text[:80].replace(chr(10), ' ')} → AI: {final[:80].replace(chr(10), ' ')}")
    except Exception:
        pass

    # Consolidação de memória em thread de background para não bloquear a resposta
    def _worker():
        if semantic_memory.enabled:
            collection = agent_manager.get_active_agent().memory_collection
            extract_semantic_memory(
                user_text=text,
                assistant_text=final,
                collection_name=collection,
                speaker_name=speaker_name,
                access_level=access_level,
                llm=llm,
                semantic_memory=semantic_memory,
                agent_manager=agent_manager,
            )
        extract_structured_memory_async(user_text=text, assistant_text=final, llm=llm)

    threading.Thread(target=_worker, daemon=True).start()


def extract_semantic_memory(
    *,
    user_text: str,
    assistant_text: str,
    collection_name: str,
    speaker_name: str,
    access_level: int,
    llm,
    semantic_memory,
    agent_manager,
):
    """Extrai fatos definitivos da conversa e os persiste no ChromaDB (RAG)."""
    from src.agent.prompts import EXTRACT_MEMORY_PROMPT

    prompt = f"Usuário ({speaker_name}) disse: {user_text}\nVocê respondeu: {assistant_text}"
    try:
        extracted = llm.chat(
            system_prompt=EXTRACT_MEMORY_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        if extracted and "vazio" not in extracted.lower():
            lines = [l.strip() for l in extracted.split("\n") if l.strip() and "vazio" not in l.lower()]
            for fact in lines:
                emb = llm.generate_embedding(fact)
                if emb:
                    semantic_memory.save_memory(
                        fact, emb,
                        metadata={"speaker_name": speaker_name, "access_level": access_level},
                        collection_name=collection_name,
                    )
                    agent_name = agent_manager.get_active_agent().name
                    print(f"[RAG {agent_name}] Novo fato aprendido sobre {speaker_name}: {fact}")
    except Exception as e:
        logger.error(f"[RAG JARVIS] Erro na thread de extração de memória: {e}")
        logger.debug(traceback.format_exc())


def extract_structured_memory_async(*, user_text: str, assistant_text: str, llm):
    """Extração de memória estruturada em 2 estágios (YES/NO → JSON detalhado)."""
    try:
        from src.memory.structured_memory import (
            should_extract_memory,
            extract_structured_memory,
            update_structured_memory,
        )
        if not should_extract_memory(user_text, assistant_text, llm):
            return
        data = extract_structured_memory(user_text, assistant_text, llm)
        if data:
            update_structured_memory(data)
            print(f"[StructuredMemory] 💾 Auto-extraído: {list(data.keys())}")
    except Exception as e:
        if "429" not in str(e):
            print(f"[StructuredMemory] ⚠️ Extração async falhou: {e}")


def maybe_summarize(*, memory, llm) -> None:
    """Se há mensagens suficientes no histórico, resume as mais antigas com a LLM."""
    if not memory.should_summarize():
        return
    old_msgs = memory.get_messages_for_summary()
    if not old_msgs:
        return

    lines = [f"{m.get('role','user')}: {m.get('content','')[:300]}" for m in old_msgs]
    summary_prompt = (
        "Resuma a conversa abaixo em no maximo 4 frases em portugues, "
        "preservando: (1) topicos discutidos, (2) decisoes tomadas, "
        "(3) dados importantes mencionados (nomes, valores, horarios). "
        "Nao invente nada que nao esteja na conversa.\n\n"
        + "\n".join(lines)
    )
    summary = llm.chat(
        "Voce e um assistente que faz resumos concisos.",
        [{"role": "user", "content": summary_prompt}],
        skip_gemini=True,
    )
    if summary and len(summary) > 10:
        memory.apply_summary(summary)
