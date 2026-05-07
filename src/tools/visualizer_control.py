from __future__ import annotations
import json
from pathlib import Path
from .base import ToolResult

class VisualizerControlTool:
    name = "visualizer_control"
    description = "Controla o visualizador (posicao, visibilidade, ativar caixa de texto para input) e microfone (mutar/desmutar)."
    critical = False

    def __init__(self, state_file: str = "data/visualizer_state.json") -> None:
        self.state_file = Path(state_file)

    def run(self, command: str) -> ToolResult:
        lowered = command.lower()
        
        # Carrega estado atual
        state = {}
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except:
                pass

        action_taken = ""
        
        # Modos de Exibicao e Visibilidade
        if any(x in lowered for x in ["esconda", "hide", "feche", "esconder", "sumir"]):
            state["display_mode"] = "hidden"
            action_taken = "Visualizador escondido."
        elif any(x in lowered for x in ["auto", "dinâmico", "dinamico", "suma quando parar", "só quando falar"]):
            state["display_mode"] = "auto"
            action_taken = "Modo automático ativado (aparece só quando falar/pensar)."
        elif any(x in lowered for x in ["sempre visível", "sempre visivel", "fixo", "fique visível"]):
            state["display_mode"] = "always"
            action_taken = "Modo fixo ativado (sempre visível)."
        elif any(x in lowered for x in ["mostre", "show", "apareça", "abrir", "voltar"]):
            # Por padrao, se o usuario so pedir pra aparecer, colocamos em auto
            state["display_mode"] = "auto"
            action_taken = "Visualizador visível (modo auto)."

        # Posicao
        pos_map = {
            "superior direito": "top_right",
            "superior esquerdo": "top_left",
            "inferior direito": "bottom_right",
            "inferior esquerdo": "bottom_left",
            "canto direito": "bottom_right",
            "canto esquerdo": "bottom_left",
            "cima": "top_right",
            "baixo": "bottom_right",
            "centro": "center"
        }

        for key, val in pos_map.items():
            if key in lowered:
                state["position"] = val
                # Se estava escondido, muda para auto ao mover
                if state.get("display_mode") == "hidden":
                    state["display_mode"] = "auto"
                action_taken = f"Visualizador movido para: {key}."
                break

        # Caixa de Texto
        if any(x in lowered for x in ["habilitar caixa de texto", "ativar caixa de texto", "mostrar caixa", "abrir caixa de texto"]):
            state["show_input_box"] = True
            action_taken = "Caixa de texto flutuante habilitada."
        elif any(x in lowered for x in ["desabilitar caixa de texto", "esconder caixa de texto", "fechar caixa de texto", "tirar caixa"]):
            state["show_input_box"] = False
            action_taken = "Caixa de texto flutuante desabilitada."

        # Microfone
        if any(x in lowered for x in ["desabilitar microfone", "desligar microfone", "parar de escutar", "mutar microfone"]):
            state["mic_enabled"] = False
            action_taken = "Microfone desabilitado. Agora só vou escutar se você reativar ou digitar na caixa de texto."
        elif any(x in lowered for x in ["habilitar microfone", "ligar microfone", "voltar a escutar", "desmutar microfone"]):
            state["mic_enabled"] = True
            action_taken = "Microfone habilitado. Voltei a ouvir."

        if not action_taken:
            return ToolResult(False, "Nao entendi o comando. Comandos disponíveis: 'esconda', 'mostrar caixa de texto', 'mutar microfone', 'mover para cima', etc.")

        # Salva novo estado
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            return ToolResult(True, action_taken)
        except Exception as e:
            return ToolResult(False, f"Erro ao atualizar estado do visualizador: {e}")
