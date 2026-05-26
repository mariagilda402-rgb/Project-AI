import requests
import os
import logging

logger = logging.getLogger(__name__)

def notify_nexus_update(payload):
    """Envia uma atualização do Nexus para o Visualizer (HUD)."""
    port = os.environ.get("VISUALIZER_PORT", "5123")
    url = f"http://localhost:{port}/api/nexus_event"
    try:
        # Tenta enviar para o servidor visual
        requests.post(url, json=payload, timeout=0.5)
    except Exception:
        # Se o visualizador não estiver aberto, apenas ignora
        pass

def log_nexus_event(message):
    """Envia uma mensagem de texto para o log do HUD."""
    payload = {
        "type": "log",
        "message": message
    }
    notify_nexus_update(payload)

def broadcast_nexus_state(service):
    """Envia o estado completo do Nexus para o HUD."""
    stats = service.db.get_user_stats()
    rewards = service.get_rewards()
    habits = service.db.get_habits()
    study_stats = service.get_study_stats()
    goals = service.get_goals()
    try:
        finance_snapshot = service.get_finance_snapshot()
    except Exception:
        finance_snapshot = None
    try:
        tasks = service.db.list_tasks(include_done=False)[:40]
    except Exception:
        tasks = []
    payload = {
        "type": "nexus_sync",
        "stats": stats,
        "rewards": rewards,
        "habits": habits,
        "study_stats": study_stats,
        "goals": goals,
        "finance_snapshot": finance_snapshot,
        "global_streak": service.db.compute_global_streak(),
        "tasks": tasks,
    }
    notify_nexus_update(payload)
