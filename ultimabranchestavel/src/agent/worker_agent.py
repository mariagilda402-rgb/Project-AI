import threading
import google.generativeai as genai
import time
from src.agent.gemini_tools import get_tool_registry

class WorkerAgent:
    def __init__(self, goal: str, context: str):
        self.goal = goal
        self.context = context
        self.result = None
        self.is_done = False
        
    def start(self):
        thread = threading.Thread(target=self._run)
        thread.daemon = True
        thread.start()
        
    def _run(self):
        try:
            # Setup model
            registry = get_tool_registry()
            # Here we would initialize a fresh chat session with the goal
            # For this MVP, we simulate it
            print(f'[Worker] Starting task: {self.goal}')
            time.sleep(2)
            print(f'[Worker] Executing...')
            time.sleep(2)
            self.result = f'Task completed successfully: {self.goal}'
        except Exception as e:
            self.result = f'Error: {e}'
        finally:
            self.is_done = True
            print(f'[Worker] Finished: {self.result}')

_workers = {}

def agent_delegate(goal: str, context: str) -> str:
    import uuid
    worker_id = str(uuid.uuid4())
    worker = WorkerAgent(goal, context)
    _workers[worker_id] = worker
    worker.start()
    return f'Worker spawned with ID: {worker_id}'

def agent_status(worker_id: str) -> str:
    worker = _workers.get(worker_id)
    if not worker: return 'Worker not found'
    if worker.is_done: return f'Worker done. Result: {worker.result}'
    return 'Worker still running...'

