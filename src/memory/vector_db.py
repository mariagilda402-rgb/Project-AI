from __future__ import annotations

import logging
import traceback
import uuid
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
    Suporta múltiplas coleções (uma por agente) para isolamento de memória.
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
        self._collections: dict[str, Any] = {}  # Cache de coleções por nome
        
        if not self.enabled:
            print("[VectorDB] ChromaDB não instalado. Memória semântica desativada.")
            self._initialized = True
            return

        path = Path(persist_dir)
        path.mkdir(parents=True, exist_ok=True)
        
        try:
            # PersistentClient salva os dados no disco local
            self.client = chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))
            # Coleção padrão (retrocompatibilidade com o que já existia)
            self.collection = self._get_or_create_collection("user_memories")
            total = self.collection.count()
            print(f"[VectorDB] Inicializado com sucesso. Memórias totais (padrão): {total}")
        except Exception as e:
            logger.error(f"[VectorDB] Falha crítica ao inicializar ChromaDB: {e}")
            logger.debug(traceback.format_exc())
            self.enabled = False
            
        self._initialized = True

    def _get_or_create_collection(self, name: str):
        """Obtém ou cria uma coleção ChromaDB por nome (com cache)."""
        if name in self._collections:
            return self._collections[name]
        try:
            coll = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
            self._collections[name] = coll
            return coll
        except Exception as e:
            logger.error(f"[VectorDB] Erro ao criar/obter coleção '{name}': {e}")
            logger.debug(traceback.format_exc())
            return self.collection  # Fallback para a coleção padrão

    def use_collection(self, collection_name: str):
        """Muda a coleção ativa para a de um agente específico."""
        if not self.enabled:
            return
        self.collection = self._get_or_create_collection(collection_name)

    def save_memory(self, text: str, embedding: list[float], metadata: dict[str, Any] | None = None, collection_name: str | None = None) -> bool:
        """Salva uma nova memória no banco vetorial. Se collection_name for passado, salva naquela coleção."""
        if not self.enabled:
            return False
            
        target = self._get_or_create_collection(collection_name) if collection_name else self.collection
        memory_id = uuid.uuid4().hex
        
        try:
            target.add(
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

    def search_memories(self, query_embedding: list[float], top_k: int = 3, threshold: float = 1.3, collection_name: str | None = None) -> list[str]:
        """
        Busca memórias relevantes usando um vetor de query.
        threshold: Distância máxima aceitável (menor = mais parecido).
        """
        target = self._get_or_create_collection(collection_name) if collection_name else self.collection
        
        if not self.enabled or target.count() == 0:
            return []
            
        try:
            results = target.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, target.count()),
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

    def get_collection_count(self, collection_name: str | None = None) -> int:
        """Retorna o número de memórias em uma coleção."""
        if not self.enabled:
            return 0
        target = self._get_or_create_collection(collection_name) if collection_name else self.collection
        try:
            return target.count()
        except Exception:
            return 0
