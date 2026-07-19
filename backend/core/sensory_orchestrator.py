"""
SIVI 3.0 — Sensory Orchestrator
Periodically checks the user's state (webcam/posture) in the background.
"""

import asyncio
import time
import logging

logger = logging.getLogger("sivi.sensory_orchestrator")

class SensoryOrchestrator:
    def __init__(self):
        self._running = False
        self._task = None
        self._last_check = 0
        self.CHECK_INTERVAL = 900  # 15 minutes
        self._bridge_callback = None
        
    def start(self, bridge_callback=None):
        if self._running:
            return
        self._running = True
        if bridge_callback:
            self._bridge_callback = bridge_callback
        self._task = asyncio.create_task(self._sensory_loop())
        logger.info("[SensoryOrchestrator] Started background monitoring.")
        
    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("[SensoryOrchestrator] Stopped.")
        
    async def _sensory_loop(self):
        while self._running:
            try:
                from core.camera_vision import camera_vision
                wellness = await asyncio.to_thread(camera_vision.analyze_wellness)
                if wellness and ("fatigue" in wellness.lower() or "tired" in wellness.lower() or "stress" in wellness.lower()):
                    if self._bridge_callback:
                        msg = f"[SENSORY ALERT: You noticed Boss looks exhausted/stressed based on the webcam ('{wellness}'). Gently interrupt and ask if they are okay or suggest taking a break.]"
                        await self._bridge_callback(msg)
            except Exception as e:
                logger.debug(f"[SensoryOrchestrator] check failed: {e}")
            # Sleep for the full interval — no need to wake up every 60s just to check a timer
            await asyncio.sleep(self.CHECK_INTERVAL)

sensory_orchestrator = SensoryOrchestrator()
