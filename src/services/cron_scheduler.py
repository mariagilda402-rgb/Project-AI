import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from src.database.nexus_db import NexusDatabase
from datetime import datetime

logger = logging.getLogger(__name__)

class NexusCronScheduler:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(NexusCronScheduler, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.scheduler = BackgroundScheduler()
            self.db = NexusDatabase()
            self.jobs = {}
            self.initialized = True
        
    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            self._load_jobs_from_db()
            logger.info("Nexus Cron Scheduler started.")
            
            # Auto-run proactive suggestions and morning briefing on startup
            def run_startup_checks():
                try:
                    from src.services.nexus_service import get_nexus_service
                    service = get_nexus_service()
                    service.generate_morning_briefing()
                    service.get_proactive_suggestions()
                    logger.info("Proactive checks executed on startup.")
                except Exception as e:
                    logger.error(f"Failed to run proactive checks on startup: {e}")
            
            # Run in a separate thread to avoid blocking startup
            threading.Thread(target=run_startup_checks, daemon=True).start()
            
    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Nexus Cron Scheduler stopped.")
            
    def _load_jobs_from_db(self):
        """Loads all active jobs from the database into the scheduler."""
        with self.db._get_connection() as conn:
            cur = conn.cursor()
            try:
                # We expect columns: id, name, schedule, command, active
                cur.execute("SELECT id, name, schedule, command, active FROM cron_jobs WHERE active = 1")
                rows = cur.fetchall()
                for row in rows:
                    job_id, name, schedule, command, active = row
                    self._add_to_scheduler(job_id, schedule, command)
            except Exception as e:
                logger.error(f"Failed to load cron jobs from DB: {e}")

    def _add_to_scheduler(self, db_id, schedule_str, command_str):
        """Adds a job to APScheduler."""
        try:
            # Simple cron format parsing: "min hour day month day_of_week"
            parts = schedule_str.strip().split()
            if len(parts) == 5:
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4]
                )
            else:
                logger.warning(f"Invalid cron format for job {db_id}: {schedule_str}")
                return

            job = self.scheduler.add_job(
                self._execute_job,
                trigger=trigger,
                args=[db_id, command_str],
                id=str(db_id),
                replace_existing=True
            )
            self.jobs[str(db_id)] = job
            logger.info(f"Loaded cron job {db_id} with schedule '{schedule_str}'")
        except Exception as e:
            logger.error(f"Error adding job {db_id} to scheduler: {e}")

    def _execute_job(self, db_id, command_str):
        """Executes the cron job command."""
        logger.info(f"Executing cron job {db_id}: {command_str}")
        try:
            # Update last_run in DB
            with self.db._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE cron_jobs SET last_run = ? WHERE id = ?", (datetime.now().isoformat(), db_id))
                conn.commit()

            # The command is executed by passing it to the Orchestrator or NexusCloudAgent
            # For now, we will enqueue it to the nexus_commands table as if it came from the user
            # so the agent can pick it up, or if it's a direct system command we handle it directly.
            
            with self.db._get_connection() as conn:
                cur = conn.cursor()
                # Insert as a pending command for the Cloud Agent to process
                # We prefix it with CRON_EXEC to let the agent know it's a cron job if needed
                cur.execute(
                    "INSERT INTO nexus_commands (command, source, status) VALUES (?, 'cron', 'pending')",
                    (command_str,)
                )
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error executing cron job {db_id}: {e}")

    def add_job(self, name: str, schedule: str, command: str) -> int:
        """Adds a new cron job to the database and scheduler."""
        with self.db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO cron_jobs (name, schedule, command, active) VALUES (?, ?, ?, 1)",
                (name, schedule, command)
            )
            conn.commit()
            job_id = cur.lastrowid
            
        self._add_to_scheduler(job_id, schedule, command)
        return job_id

    def remove_job(self, job_id: int):
        """Removes a cron job from the database and scheduler."""
        with self.db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE cron_jobs SET active = 0 WHERE id = ?", (job_id,))
            conn.commit()
            
        if str(job_id) in self.jobs:
            self.scheduler.remove_job(str(job_id))
            del self.jobs[str(job_id)]
            
    def get_jobs(self) -> list:
        """Returns a list of all active cron jobs."""
        with self.db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name, schedule, command, last_run FROM cron_jobs WHERE active = 1")
            rows = cur.fetchall()
            
        result = []
        for row in rows:
            job_id, name, schedule, command, last_run = row
            result.append({
                "id": job_id,
                "name": name,
                "schedule": schedule,
                "command": command,
                "last_run": last_run
            })
        return result
