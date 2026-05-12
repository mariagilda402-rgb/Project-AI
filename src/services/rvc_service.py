import os
from pathlib import Path
import json

class RVCManager:
    """
    Gerencia a engine RVC (Retrieval-based Voice Conversion) usando rvc-python.
    Roda primariamente na GPU se disponível (CUDA/DirectML) ou CPU como fallback.
    """
    def __init__(self, models_dir: str = "data/rvc_models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.rvc = None
        self.current_model = None
        self.is_ready = False
        self._init_engine()

    def _init_engine(self):
        try:
            from rvc_python.infer import RVCInference
            # Tenta forçar DirectML se não achar CUDA? rvc-python suporta cuda:0 ou cpu.
            # Se der erro com cuda:0, ele falha pro cpu.
            self.rvc = RVCInference(device="cpu") # Por padrão usaremos CPU para máxima compatibilidade na AMD, se não houver backend custom.
            self.is_ready = True
            print("[RVC] Motor inicializado (Modo CPU Fallback).")
        except ImportError:
            print("[RVC] rvc-python não instalado. Rode: pip install rvc-python")
        except Exception as e:
            print(f"[RVC] Falha ao iniciar engine: {e}")

    def load_model(self, model_name: str) -> bool:
        """Carrega um modelo .pth se existir na pasta model_name."""
        if not self.is_ready or not self.rvc:
            return False

        if self.current_model == model_name:
            return True # Já está carregado
            
        model_path = self.models_dir / model_name / f"{model_name}.pth"
        
        if not model_path.exists():
            model_path = self.models_dir / f"{model_name}.pth"

        if not model_path.exists():
            print(f"[RVC] Modelo não encontrado: {model_path}")
            return False

        try:
            self.rvc.load_model(str(model_path))
            self.current_model = model_name
            print(f"[RVC] Modelo '{model_name}' carregado com sucesso.")
            return True
        except Exception as e:
            print(f"[RVC] Erro ao carregar modelo '{model_name}': {e}")
            return False

    def get_config(self, model_name: str) -> dict:
        """Lê o config.json do modelo para ajustar pitch, protect, etc."""
        config_path = self.models_dir / model_name / "config.json"
        if config_path.exists():
            try:
                import json
                return json.loads(config_path.read_text("utf-8"))
            except Exception:
                pass
        return {"pitch": 0, "index_rate": 0.5, "protect": 0.33}

    def convert_audio(self, input_wav: str, output_wav: str, model_name: str) -> bool:
        """Converte o arquivo de áudio usando o modelo e o índice .index se disponível."""
        if not self.is_ready:
            return False

        if not self.load_model(model_name):
            return False

        config = self.get_config(model_name)
        index_path = self.models_dir / model_name / f"{model_name}.index"
        if not index_path.exists():
            index_path = self.models_dir / f"{model_name}.index"

        # Parâmetros
        f0_up_key = config.get("pitch", 0)
        index_rate = config.get("index_rate", 0.5)
        protect = config.get("protect", 0.33)
        f0_method = config.get("f0_method", "rmvpe")

        try:
            # A rvc-python geralmente aceita o index no infer_file ou detecta automaticamente se na mesma pasta
            self.rvc.infer_file(
                input_wav,
                output_wav,
                f0up_key=f0_up_key,
                f0method=f0_method,
                index_rate=index_rate,
                protect=protect,
                index_path=str(index_path) if index_path.exists() else None
            )
            return True
        except Exception as e:
            print(f"[RVC] Erro na conversão: {e}")
            return False
