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
        # REMOVED: self._init_engine() to save memory. Will lazy load when needed.

    def _init_engine(self):
        try:
            from rvc_python.infer import RVCInference
            import rvc_python
            from pathlib import Path
            import os

            # Corrige o KeyError: 'rmvpe_root'
            os.environ["rmvpe_root"] = str(Path(rvc_python.__file__).parent)

            # Inicializa como CPU (O modelo de voz PyTorch do rvc-python dá erro de dtype no DirectML,
            # então forçamos rodar em CPU e usamos o extrator de pitch 'pm' para máxima performance)
            self.rvc = RVCInference(device="cpu")
            self.rvc.config.is_half = False

            print("[RVC] Motor inicializado (Modo CPU, FP32).")
            self.is_ready = True
        except ImportError:
            print("[RVC] rvc-python não instalado. Rode: pip install rvc-python")
        except Exception as e:
            print(f"[RVC] Falha ao iniciar engine: {e}")

    def load_model(self, model_name: str, index_path: str = "") -> bool:
        """Carrega um modelo .pth se existir na pasta model_name."""
        if not self.is_ready:
            self._init_engine()

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
            self.rvc.load_model(str(model_path), index_path=index_path)
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
        return {"pitch": 0, "index_rate": 0.75, "protect": 0.33, "f0_method": "rmvpe"}

    def convert_audio(self, input_wav: str, output_wav: str, model_name: str) -> bool:
        """Converte o arquivo de áudio usando o modelo e o índice .index se disponível."""
        # Lazy-init: inicializa engine se ainda não foi feito
        if not self.is_ready:
            self._init_engine()
        if not self.is_ready:
            print("[RVC] Engine não disponível após init. Abortando conversão.")
            return False

        config = self.get_config(model_name)

        # Localiza o arquivo .index
        index_path = self.models_dir / model_name / f"{model_name}.index"
        if not index_path.exists():
            index_path = self.models_dir / f"{model_name}.index"

        idx_str = str(index_path) if index_path.exists() else ""

        # Sempre carrega o modelo passando o index_path correto
        if not self.load_model(model_name, index_path=idx_str):
            return False

        # Parâmetros
        f0_up_key = config.get("pitch", 0)
        index_rate = config.get("index_rate", 0.5)
        protect = config.get("protect", 0.33)
        f0_method = config.get("f0_method", "rmvpe")

        try:
            # RVC-Python configura parâmetros por meio do set_params antes da inferência
            self.rvc.set_params(
                f0up_key=f0_up_key,
                f0method=f0_method,
                index_rate=index_rate,
                protect=protect
            )
            # A rvc-python realiza inferência passando apenas os caminhos
            self.rvc.infer_file(input_wav, output_wav)
            return True
        except Exception as e:
            import traceback
            print(f"[RVC] Erro na conversão: {e}")
            traceback.print_exc()
            return False
