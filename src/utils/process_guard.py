import os
import sys
import atexit
import signal
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# GUARDA ANTI-ZUMBI: Mata instâncias anteriores do Jarvis antes de qualquer
# import pesado. Resolve o problema de 100+ processos acumulados.
# ══════════════════════════════════════════════════════════════════════════════

# Caminho para o root (Projeto AI) saindo de src/utils
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_PID_FILE = _ROOT_DIR / "data" / "jarvis.pid"

def enforce_single_instance():
    """Executa a limpeza de instâncias zumbis e registra handlers de saída."""
    _kill_previous_instances()
    atexit.register(_cleanup_on_exit)
    
    signal.signal(signal.SIGTERM, _signal_handler)
    try:
        signal.signal(signal.SIGINT, _signal_handler)
    except (OSError, ValueError):
        pass  # Pode falhar em threads secundárias


def _kill_previous_instances():
    """Mata qualquer processo Python anterior que esteja rodando main.py."""
    my_pid = os.getpid()
    my_ancestors = set()
    try:
        import psutil
        curr = psutil.Process(my_pid).parent()
        while curr:
            my_ancestors.add(curr.pid)
            curr = curr.parent()
    except Exception:
        pass

    # 1. Tenta ler o PID do lockfile anterior
    if _PID_FILE.exists():
        try:
            old_pid = int(_PID_FILE.read_text().strip())
            if old_pid != my_pid and old_pid not in my_ancestors:
                try:
                    import psutil
                    proc = psutil.Process(old_pid)
                    if "python" in proc.name().lower():
                        print(f"[Guarda] Encerrando instância anterior (PID {old_pid})...")
                        # Mata toda a árvore de processos filhos
                        children = proc.children(recursive=True)
                        for child in children:
                            if child.pid == my_pid or child.pid in my_ancestors:
                                continue
                            try:
                                child.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                        proc.kill()
                        proc.wait(timeout=5)
                        print(f"[Guarda] PID {old_pid} encerrado com sucesso.")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass  # Já morreu
                except ImportError:
                    # Fallback sem psutil: tenta taskkill no Windows
                    try:
                        os.system(f'taskkill /PID {old_pid} /F /T >nul 2>&1')
                    except Exception:
                        pass
                except Exception as e:
                    print(f"[Guarda] Erro ao matar PID {old_pid}: {e}")
        except (ValueError, OSError):
            pass

    # 2. Varredura geral: mata qualquer python.exe rodando main.py (exceto eu e meus pais)
    try:
        import psutil
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["pid"] == my_pid or proc.info["pid"] in my_ancestors:
                    continue
                if "python" not in (proc.info["name"] or "").lower():
                    continue
                cmdline = proc.info.get("cmdline") or []
                cmd_str = " ".join(cmdline).lower()
                if "src\\main.py" in cmd_str or "src/main.py" in cmd_str:
                    print(f"[Guarda] Matando processo zumbi: PID {proc.info['pid']}")
                    children = proc.children(recursive=True)
                    for child in children:
                        if child.pid == my_pid or child.pid in my_ancestors:
                            continue
                        try:
                            child.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except ImportError:
        pass  # Sem psutil, a limpeza por PID file já cobre o caso principal

    # 3. Grava o PID atual no lockfile
    try:
        _PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PID_FILE.write_text(str(my_pid))
    except OSError:
        pass


def _cleanup_on_exit():
    """Remove o PID file ao sair normalmente."""
    try:
        if _PID_FILE.exists() and _PID_FILE.read_text().strip() == str(os.getpid()):
            _PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _signal_handler(signum, frame):
    _cleanup_on_exit()
    os._exit(0)
