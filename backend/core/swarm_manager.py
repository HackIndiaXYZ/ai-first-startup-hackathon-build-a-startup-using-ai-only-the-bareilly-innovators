import threading
import logging
import os
import requests
import time

logger = logging.getLogger("sivi.swarm_manager")

class SwarmManager:
    """
    Sivi's Multi-Agent Swarm Manager.
    Delegates time-consuming tasks (like deep web research) to background threads ("Junior Agents").
    Once a Junior Agent finishes, it injects the result back into Sivi's consciousness via the Bridge Server.
    """
    def __init__(self):
        self.bridge_url = os.getenv("BRIDGE_URL", "http://localhost:8000")
        
    def _send_alert_to_boss(self, message: str):
        """Pushes a message back to Sivi so she can speak it out loud."""
        try:
            payload = {"text": f"[SWARM_AGENT_REPORT] {message}"}
            requests.post(f"{self.bridge_url}/voice/send-text", json=payload, timeout=15)
        except Exception as e:
            logger.error(f"Swarm agent failed to report back: {e}")

    def _research_worker(self, query: str):
        """The background worker that performs the task."""
        logger.info(f"Swarm Agent started research on: {query}")
        
        try:
            # We import web_scraper here to avoid circular dependencies if it imports swarm
            from web_scraper import web_scraper
            
            # Simulate a deep dive by giving it a moment to 'think'
            time.sleep(2)
            
            # Use the existing web scraper
            search_results = web_scraper.search_google(query)
            
            # Format a concise summary report
            if search_results.startswith("Error") or "offline" in search_results:
                report = f"Boss, my background agent failed to research '{query}'. The web module might be offline."
            else:
                # We truncate to avoid overwhelming the TTS
                truncated = search_results[:600]
                report = f"Boss, my background agent finished researching '{query}'. Here is the summary: {truncated}... (End of report)."
                
            self._send_alert_to_boss(report)
            logger.info(f"Swarm Agent finished research on: {query}")
            
        except Exception as e:
            logger.error(f"Swarm agent crashed: {e}")
            self._send_alert_to_boss(f"Boss, my background agent crashed while researching '{query}'. Error: {e}")

    def delegate_research(self, query: str) -> str:
        """Spawns a junior agent thread to do research."""
        t = threading.Thread(target=self._research_worker, args=(query,), daemon=True)
        t.start()
        return f"Delegated deep research on '{query}' to a background swarm agent. I'll notify you when it's done."

swarm_manager = SwarmManager()
