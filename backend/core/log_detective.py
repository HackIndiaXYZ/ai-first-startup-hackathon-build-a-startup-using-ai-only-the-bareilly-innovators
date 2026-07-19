import os
import sys
import time
import threading
import requests
import re
import logging

logger = logging.getLogger("sivi.log_detective")

class LogDetective:
    """
    Sivi's Background Log & Server Crash Detective.
    Tails a log file continuously and alerts Gemini instantly if an Exception or Error signature is detected.
    """
    def __init__(self):
        self._active_monitors = {}
        # We assume the Bridge Server is running on port 8000
        self.bridge_url = os.getenv("BRIDGE_URL", "http://localhost:8000")

    def _send_alert(self, log_file: str, error_snippet: str):
        """Send a proactive alert to Sivi via the Bridge Server."""
        msg = (
            f"[SYSTEM_EVENT: DEVELOPER ALERT] I detected a crash/error in the server logs at '{os.path.basename(log_file)}'. "
            f"Here is the error snippet: {error_snippet}. Proactively warn the Boss and ask if they want me to help fix it!"
        )
        try:
            requests.post(
                f"{self.bridge_url}/voice/send-text",
                json={"text": msg},
                timeout=5
            )
            logger.info(f"Sent crash alert to Sivi for {log_file}")
        except Exception as e:
            logger.error(f"LogDetective failed to reach bridge server: {e}")

    def _tail_log(self, file_path: str):
        """Background thread worker to tail the file."""
        if not os.path.exists(file_path):
            logger.error(f"Cannot monitor missing file: {file_path}")
            return
            
        logger.info(f"Started monitoring log file: {file_path}")
        
        # Regex patterns that indicate a crash/exception
        error_patterns = [
            re.compile(r'(?i)exception:?'),
            re.compile(r'(?i)traceback \(most recent call last\)'),
            re.compile(r'(?i)error:?'),
            re.compile(r'(?i)fatal:?'),
            re.compile(r'(?i)panic:?')
        ]
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                # Go to the end of the file
                f.seek(0, 2)
                
                # Cooldown to prevent spamming Sivi with the same continuous stack trace
                last_alert_time = 0
                cooldown_seconds = 60 
                
                while self._active_monitors.get(file_path, False):
                    line = f.readline()
                    if not line:
                        time.sleep(0.5)
                        continue
                        
                    # Check if line matches an error signature
                    for pattern in error_patterns:
                        if pattern.search(line):
                            now = time.time()
                            if now - last_alert_time > cooldown_seconds:
                                # Found an error! Read the next 3 lines to grab the stack context
                                context = line.strip()
                                for _ in range(3):
                                    next_line = f.readline()
                                    if next_line:
                                        context += " | " + next_line.strip()
                                
                                self._send_alert(file_path, context)
                                last_alert_time = now
                            break
        except Exception as e:
            logger.error(f"Error while tailing log {file_path}: {e}")
        finally:
            self._active_monitors.pop(file_path, None)
            logger.info(f"Stopped monitoring log file: {file_path}")

    def start_monitoring(self, file_path: str) -> str:
        """Starts monitoring a log file in a background thread."""
        file_path = os.path.abspath(file_path)
        if file_path in self._active_monitors and self._active_monitors[file_path]:
            return f"Already monitoring {file_path}"
            
        if not os.path.exists(file_path):
            return f"Error: Log file '{file_path}' does not exist."
            
        self._active_monitors[file_path] = True
        t = threading.Thread(target=self._tail_log, args=(file_path,), daemon=True)
        t.start()
        
        return f"Started proactive crash detective on '{file_path}'"

    def stop_monitoring(self, file_path: str) -> str:
        """Stops monitoring a log file."""
        file_path = os.path.abspath(file_path)
        if file_path in self._active_monitors:
            self._active_monitors[file_path] = False
            return f"Stopped monitoring '{file_path}'"
        return f"Was not monitoring '{file_path}'"

log_detective = LogDetective()
