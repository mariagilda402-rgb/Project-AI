import os
import hashlib
from pathlib import Path
import shutil

class TTSCache:
    """
    Sistema de cache persistente para evitar renderização (TTS + RVC)
    repetitiva de frases muito usadas (ex: "Sim, senhor", "Aguarde").
    """
    def __init__(self, cache_dir: str = "data/tts_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _generate_hash(self, text: str, voice_id: str, provider: str) -> str:
        """Gera um hash único baseado no texto limpo e nas configurações de voz."""
        clean_text = text.strip().lower()
        key = f"{clean_text}|{voice_id}|{provider}"
        return hashlib.md5(key.encode("utf-8")).hexdigest()

    def get_cached_file(self, text: str, voice_id: str, provider: str) -> Path | None:
        """Retorna o caminho do arquivo de áudio cacheado, se existir."""
        if not text.strip():
            return None
            
        file_hash = self._generate_hash(text, voice_id, provider)
        cached_path = self.cache_dir / f"{file_hash}.wav"
        
        if cached_path.exists():
            return cached_path
        return None

    def save_to_cache(self, text: str, voice_id: str, provider: str, source_wav_path: Path | str) -> Path:
        """Copia o áudio gerado para o cache."""
        file_hash = self._generate_hash(text, voice_id, provider)
        cached_path = self.cache_dir / f"{file_hash}.wav"
        
        # Copia o arquivo final gerado (após TTS e RVC)
        shutil.copy2(str(source_wav_path), str(cached_path))
        return cached_path

    def clear_cache(self):
        """Limpa todos os arquivos do cache."""
        for f in self.cache_dir.glob("*.wav"):
            try:
                f.unlink()
            except Exception:
                pass
