import os
import sys
import logging
from datetime import datetime, timedelta
import requests

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

logger = logging.getLogger("sivi.task_queue")

def _execute_sivi_command(command_string: str, instruction: str):
    """
    Callback function that fires when a scheduled job triggers.
    Sends the command or notification directly to Sivi's bridge server.
    """
    bridge_url = os.getenv("BRIDGE_URL", "http://localhost:8000")
    try:
        # First send the notification to Sivi to speak
        msg = f"[SYSTEM_EVENT: CRON TRIGGER] The scheduled task '{instruction}' is now executing."
        requests.post(f"{bridge_url}/voice/send-text", json={"text": msg}, timeout=15)
        
        # Then we send the actual parsed command payload to the bridge to execute
        # In a fully integrated system, the bridge server would have a /execute-command endpoint.
        # For now, we simulate execution by sending a system text that forces Gemini to do it.
        execute_msg = f"Boss's scheduled task triggered: {command_string}. Please execute it now."
        requests.post(f"{bridge_url}/voice/send-text", json={"text": execute_msg}, timeout=15)
        
        logger.info(f"Executed scheduled task: {instruction}")
    except Exception as e:
        logger.error(f"Failed to execute scheduled task '{instruction}': {e}")


class PersistentTaskQueue:
    """
    Never-Dying Task Queue. Uses APScheduler with a SQLite backend to ensure 
    Sivi never forgets an alarm or scheduled task even if the PC restarts.
    """
    def __init__(self):
        # Setup data directory
        if getattr(sys, 'frozen', False):
            data_dir = os.path.join(os.path.dirname(sys.executable), "data")
        else:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
            
        os.makedirs(data_dir, exist_ok=True)
        db_path = os.path.join(data_dir, "sivi_jobs.sqlite")
        
        jobstores = {
            'default': SQLAlchemyJobStore(url=f'sqlite:///{db_path}')
        }
        executors = {
            'default': ThreadPoolExecutor(5)
        }
        job_defaults = {
            'coalesce': True,
            'max_instances': 1
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Kolkata'
        )
        self.scheduler.start()
        logger.info("Persistent Task Queue started.")

    def schedule_task(self, command_string: str, instruction: str, delay_seconds: int) -> str:
        """Schedules a Sivi command to run after delay_seconds."""
        run_date = datetime.now() + timedelta(seconds=delay_seconds)
        try:
            self.scheduler.add_job(
                _execute_sivi_command,
                'date',
                run_date=run_date,
                args=[command_string, instruction],
                id=f"job_{datetime.now().timestamp()}",
                replace_existing=True
            )
            return f"Scheduled task: '{instruction}' to run in {delay_seconds} seconds. It is saved permanently."
        except Exception as e:
            logger.error(f"Error scheduling task: {e}")
            return "Failed to schedule task."

    def list_pending_tasks(self) -> str:
        """Lists all upcoming scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        if not jobs:
            return "No scheduled tasks in the queue."
            
        result = []
        for j in jobs:
            result.append(f"- {j.args[1]} (Scheduled for: {j.next_run_time.strftime('%I:%M %p')})")
        return "\n".join(result)

task_queue = PersistentTaskQueue()
