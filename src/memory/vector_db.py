from __future__ import annotations

import os
import logging
import traceback
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Retorna um erro amigável se o pacote não estiver instalado
try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None


class SemanticMemory:
    """
    Gerencia a Memória Semântica de longo prazo (JARVIS Style) usando ChromaDB.
    Armazena fatos e preferências como vetores matemáticos para busca por similaridade.
    """
    _instance: SemanticMemory | None = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, persist_dir: str = "data/chroma_db"):
        if self._initialized:
            return
            
        self.enabled = chromadb is not None
        if not self.enabled:
            print("[VectorDB] ChromaDB não instalado. Memória semântica desativada.")
            self._initialized = True
            return

        path = Path(persist_dir)
        path.mkdir(parents=True, exist_ok=True)
        
        try:
            # PersistentClient salva os dados no disco local
            self.client = chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))
            self.collection = self.client.get_or_create_collection(
                name="user_memories",
                metadata={"hnsw:space": "cosine"} # Usa similaridade de cosseno, melhor para embeddings LLM
            )
            print(f"[VectorDB] Inicializado com sucesso. Memórias totais: {self.collection.count()}")
        except Exception as e:
            logger.error(f"[VectorDB] Falha crítica ao inicializar ChromaDB: {e}")
            logger.debug(traceback.format_exc())
            self.enabled = False
            
        self._initialized = True

    def save_memory(self, text: str, embedding: list[float], metadata: dict[str, Any] | None = None) -> bool:
        """Salva uma nova memória no banco vetorial."""
        if not self.enabled:
            return False
            
        import uuid
        memory_id = uuid.uuid4().hex
        
        try:
            self.collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata or {}]
            )
            return True
        except Exception as e:
            logger.error(f"[VectorDB] Erro ao salvar memória: {e}")
            logger.debug(traceback.format_exc())
            return False

    def search_memories(self, query_embedding: list[float], top_k: int = 3, threshold: float = 1.3) -> list[str]:
        """
        Busca memórias relevantes usando um vetor de query.
        threshold: Distância máxima aceitável (menor = mais parecido).
        """
        if not self.enabled or self.collection.count() == 0:
            return []
            
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self.collection.count()),
                include=["documents", "distances"]
            )
            
            memories = []
            if results["documents"] and results["distances"]:
                docs = results["documents"][0]
                distances = results["distances"][0]
                
                for doc, dist in zip(docs, distances):
                    # Chroma com cosine devolve distância (1 - cosine_similarity).
                    # Geralmente valores < 0.3 são altamente relevantes, mas depende do modelo.
                    # Filtramos por threshold para evitar "alucinações" puxando memórias nada a ver.
                    if dist <= threshold:
                        memories.append(doc)
                        
            return memories
        except Exception as e:
            logger.error(f"[VectorDB] Erro na busca de memórias: {e}")
            logger.debug(traceback.format_exc())
            return []
