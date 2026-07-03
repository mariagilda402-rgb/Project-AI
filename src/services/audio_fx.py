import os
from pathlib import Path

# Inicializado sob demanda para evitar carregar módulos pesados se não usar FX
_board = None

def get_jarvis_fx_board():
    global _board
    if _board is None:
        try:
            from pedalboard import Pedalboard, Reverb, Compressor, HighpassFilter, LowpassFilter, Gain, PeakFilter
            _board = Pedalboard([
                HighpassFilter(cutoff_frequency_hz=120.0),      # Limpa o "sub" desnecessário
                PeakFilter(cutoff_frequency_hz=3000.0, gain_db=3.0, q=1.0), # Realça a clareza da fala (Presença)
                Compressor(threshold_db=-18, ratio=4.0),        # Voz de rádio/estúdio bem firme
                LowpassFilter(cutoff_frequency_hz=16000.0),     # Tira chiados de alta frequência
                Reverb(room_size=0.08, damping=0.8, dry_level=1.0, wet_level=0.15), # Eco sutil de metal/capacete
                Gain(gain_db=3.5)
            ])
        except ImportError:
            print("[AudioFX] Pedalboard não instalado. Pós-processamento desativado.")
            return None
    return _board

def apply_fx_to_wav(input_wav: Path | str, output_wav: Path | str, preset: str = "jarvis") -> bool:
    """
    Aplica efeitos de estúdio em um arquivo WAV usando Pedalboard e Soundfile.
    Retorna True se sucesso, False se falhar ou biblioteca não estiver presente.
    """
    try:
        from pedalboard.io import AudioFile
        
        board = get_jarvis_fx_board() if preset == "jarvis" else None
        if not board:
            return False
            
        with AudioFile(str(input_wav)) as f:
            audio = f.read(f.frames)
            samplerate = f.samplerate
            
        effected = board(audio, samplerate)
        
        with AudioFile(str(output_wav), 'w', samplerate, effected.shape[0]) as f:
            f.write(effected)
            
        return True
    except Exception as e:
        print(f"[AudioFX] Erro ao aplicar FX: {e}")
        return False
