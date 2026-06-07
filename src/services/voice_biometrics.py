import os
from pathlib import Path
import json
import logging
import time
import speech_recognition as sr

class VoiceBiometrics:
    def __init__(self, model_dir="data/voice_models"):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        self.ready = False
        self.verifier = None
        self._load_model()

    def _load_model(self):
        try:
            # Importa speechbrain dinamicamente para não quebrar caso não exista
            from speechbrain.inference.speaker import SpeakerRecognition
            # Modelo super leve (~80MB) para biometria (ECAPA-TDNN)
            self.verifier = SpeakerRecognition.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb", 
                savedir=os.path.join(self.model_dir, "ecapa-voxceleb"),
                run_opts={"device": "cpu"} # Força CPU para não pesar
            )
            self.ready = True
            logging.info("🎤 [VoiceBiometrics] Modelo ECAPA-TDNN carregado com sucesso.")
        except Exception as e:
            logging.error(f"🎤 [VoiceBiometrics] Erro ao carregar modelo: {e}")
            self.ready = False

    def extract_embedding(self, audio_data: sr.AudioData):
        """
        Recebe o AudioData do speech_recognition e extrai a impressão digital (embedding)
        """
        if not self.ready or not self.verifier:
            return None
            
        import tempfile
        import soundfile as sf
        import torchaudio
        
        try:
            # O SpeechBrain e torchaudio lidam melhor com arquivos temporários para formatar correto
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                # O AudioData do sr nos dá os bytes crus
                tmp.write(audio_data.get_wav_data())
                tmp_path = tmp.name

            # Extração
            signal, fs = torchaudio.load(tmp_path)
            embeddings = self.verifier.encode_batch(signal)
            
            # Limpeza
            try:
                os.remove(tmp_path)
            except Exception:
                pass
                
            # Flatten tensor para array numpy
            emb_array = embeddings.squeeze().detach().cpu().numpy()
            return emb_array
        except Exception as e:
            logging.error(f"🎤 [VoiceBiometrics] Erro ao extrair embedding: {e}")
            return None

    def compare_embeddings(self, emb1, emb2, threshold=0.25):
        """
        Compara dois embeddings. O threshold recomendado do ECAPA é entre 0.25 e 0.35.
        """
        if emb1 is None or emb2 is None:
            return False, 0.0
            
        try:
            import torch
            from torch.nn.functional import cosine_similarity
            t1 = torch.tensor(emb1).unsqueeze(0)
            t2 = torch.tensor(emb2).unsqueeze(0)
            score = cosine_similarity(t1, t2).item()
            return score > threshold, score
        except Exception as e:
            logging.error(f"🎤 [VoiceBiometrics] Erro na comparação: {e}")
            return False, 0.0

    def identify_speaker(self, db_conn, current_embedding, threshold=0.25):
        """
        Compara o embedding atual com todos no DB e retorna (name, access_level) do locutor, ou None.
        """
        if current_embedding is None:
            return None, 1
            
        try:
            cursor = db_conn.cursor()
            cursor.execute("SELECT name, access_level, voice_embedding FROM voice_profiles")
            profiles = cursor.fetchall()
            
            best_match = None
            best_score = 0.0
            
            for profile in profiles:
                name = profile[0]
                access_level = profile[1]
                emb_str = profile[2]
                if emb_str:
                    try:
                        import numpy as np

                        db_emb = np.array(json.loads(emb_str), dtype=np.float32)
                        match, score = self.compare_embeddings(current_embedding, db_emb, threshold)
                        if match and score > best_score:
                            best_score = score
                            best_match = (name, access_level)
                    except Exception:
                        pass
                        
            return best_match
        except Exception as e:
            logging.error(f"🎤 [VoiceBiometrics] Erro ao identificar locutor no DB: {e}")
            return None

    def save_profile(self, db_conn, name: str, access_level: int, embedding):
        """
        Salva ou atualiza um perfil de voz no DB.
        """
        if embedding is None:
            return False
            
        try:
            emb_str = json.dumps(embedding.tolist())
            cursor = db_conn.cursor()
            
            # Check se ja existe
            exists = cursor.execute("SELECT id FROM voice_profiles WHERE name = ?", (name,)).fetchone()
            if exists:
                cursor.execute(
                    "UPDATE voice_profiles SET access_level = ?, voice_embedding = ? WHERE name = ?",
                    (access_level, emb_str, name)
                )
            else:
                cursor.execute(
                    "INSERT INTO voice_profiles (name, access_level, voice_embedding) VALUES (?, ?, ?)",
                    (name, access_level, emb_str)
                )
            db_conn.commit()
            return True
        except Exception as e:
            logging.error(f"🎤 [VoiceBiometrics] Erro ao salvar perfil: {e}")
            return False

    def remove_profile(self, db_conn, name: str):
        """
        Remove um perfil do DB.
        """
        try:
            cursor = db_conn.cursor()
            cursor.execute("DELETE FROM voice_profiles WHERE name = ?", (name,))
            db_conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"🎤 [VoiceBiometrics] Erro ao remover perfil: {e}")
            return False

    def get_admin_count(self, db_conn):
        """Retorna quantos admins (level 100) existem."""
        try:
            cursor = db_conn.cursor()
            return cursor.execute("SELECT COUNT(*) FROM voice_profiles WHERE access_level = 100").fetchone()[0]
        except Exception:
            return 0
