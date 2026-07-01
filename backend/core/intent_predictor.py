"""
SIVI AI — Intent Predictor (Proactive Intelligence)
Analyzes time-of-day, recent command patterns, and active context
to generate proactive, human-like suggestions before the user even asks.
"""

import os
import time
import logging
from datetime import datetime

logger = logging.getLogger("sivi.intent_predictor")

class IntentPredictor:
    """
    Lightweight, rule-based proactive engine.
    No API calls — all logic is local pattern matching.
    """

    def __init__(self):
        self._last_suggestion_time: float = 0
        self._last_suggestion_type: str = ""
        self._command_history: list[str] = []
        # Minimum gap between proactive suggestions (in seconds)
        self.SUGGESTION_COOLDOWN = 600  # 10 minutes

    def record_command(self, cmd_type: str):
        """Call this every time a command is executed to track patterns."""
        self._command_history.append(cmd_type)
        # Keep only last 20 commands
        if len(self._command_history) > 20:
            self._command_history.pop(0)

    def _cooldown_ok(self, suggestion_type: str) -> bool:
        """Prevent spamming the same suggestion type."""
        if self._last_suggestion_type == suggestion_type:
            if time.time() - self._last_suggestion_time < self.SUGGESTION_COOLDOWN:
                return False
        return True

    def _mark_sent(self, suggestion_type: str):
        self._last_suggestion_time = time.time()
        self._last_suggestion_type = suggestion_type

    def get_proactive_suggestion(self, sivi_connected: bool, orb_state: str) -> str | None:
        """
        Returns a proactive system message to send to Gemini, or None.
        Only fires when Sivi is idle and connected — never interrupts speaking.
        """
        if not sivi_connected or orb_state not in ("listening", "idle"):
            return None

        now = datetime.now()
        hour = now.hour
        minute = now.minute

        # ── Morning Briefing (9:00 AM sharp) ─────────────────────────
        if hour == 9 and minute == 0 and self._cooldown_ok("morning_briefing"):
            self._mark_sent("morning_briefing")
            return (
                "[PROACTIVE: It is 9:00 AM. Greet the user and offer a morning briefing: "
                "tell them today's calendar events and the current weather. "
                "Keep it under 3 sentences. Be warm and energetic.]"
            )

        # ── End-of-Day Summary (7:00 PM) ─────────────────────────────
        if hour == 19 and minute == 0 and self._cooldown_ok("evening_summary"):
            self._mark_sent("evening_summary")
            return (
                "[PROACTIVE: It is 7:00 PM. Check in with the user. "
                "Ask if they want a summary of their day or any help before they wrap up. "
                "Be relaxed and caring, 1 sentence only.]"
            )

        # ── Late Night Care (past midnight) ──────────────────────────
        if hour == 0 and minute == 0 and self._cooldown_ok("midnight_care"):
            self._mark_sent("midnight_care")
            return (
                "[PROACTIVE: It is midnight. The user is still up. "
                "Gently remind them to take a break and rest. Be warm, not robotic. 1 sentence.]"
            )

        # ── Pattern: User opened YouTube → offer to search for something ──
        recent = self._command_history[-3:] if len(self._command_history) >= 3 else []
        if "OPEN_APP" in recent and self._cooldown_ok("youtube_suggest"):
            if self._command_history and "youtube" in str(self._command_history[-1]).lower():
                self._mark_sent("youtube_suggest")
                return (
                    "[PROACTIVE: User just opened YouTube. Casually ask if they want you to "
                    "search for a specific song or video. 1 short sentence.]"
                )

        return None


# Module-level singleton
intent_predictor = IntentPredictor()
