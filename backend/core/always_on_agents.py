"""
Sivi — Always-On Background Agents
Proactive modules that monitor services (HackerNews, System Health, Email)
and trigger text-to-speech alerts when notable events occur.
"""

import asyncio
import logging
from core.text_llm import text_llm
from core.memory_vault import memory_vault
import urllib.request
import json
import requests

logger = logging.getLogger("sivi.always_on_agents")

class AlwaysOnAgents:
    def __init__(self):
        self.tasks = []
        self._running = False

    def start(self, sivi_controller, bridge_callback=None):
        """Start background polling tasks."""
        self.sivi_controller = sivi_controller
        if bridge_callback:
            self._bridge_callback = bridge_callback
        if self._running: return
        self._running = True
        self.tasks.append(asyncio.create_task(self.poll_hacker_news()))
        # self.tasks.append(asyncio.create_task(self.poll_system_health()))

    def stop(self):
        self._running = False
        for t in self.tasks:
            t.cancel()
        self.tasks = []

    async def poll_hacker_news(self):
        """Poll HackerNews top stories every 2 hours and notify user if something matches their interests."""
        while self._running:
            try:
                # Basic sleep to prevent immediate trigger on boot
                await asyncio.sleep(60 * 60 * 2) # 2 hours
                
                # Fetch top stories
                req = urllib.request.urlopen("https://hacker-news.firebaseio.com/v0/topstories.json")
                top_ids = json.loads(req.read().decode())[:5]
                
                titles = []
                for item_id in top_ids:
                    req = urllib.request.urlopen(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json")
                    item = json.loads(req.read().decode())
                    titles.append(item.get('title', ''))

                context = memory_vault.get_memory_context()
                prompt = f"Top HackerNews stories right now:\n- " + "\n- ".join(titles) + f"\n\nBased on what you know about the user: {context}\nIs there any story highly relevant to them? If yes, give a 1-sentence alert. If no, say NO."
                
                res = await text_llm.complete(prompt=prompt, system="You are Sivi, analyzing news.")
                if res and "NO" not in res.upper() and len(res) > 10:
                    # Deliver alert via bridge server callback
                    try:
                        alert_msg = f"[SYSTEM_EVENT: Breaking tech news: {res}. Alert the user proactively.]"
                        if hasattr(self, '_bridge_callback') and self._bridge_callback:
                            await self._bridge_callback(alert_msg)
                        else:
                            logger.warning("No bridge_callback configured for HackerNews alert.")
                    except Exception as notify_err:
                        logger.error(f"Failed to deliver HN alert to bridge: {notify_err}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"HN Polling Error: {e}")
                await asyncio.sleep(300)

agents = AlwaysOnAgents()
