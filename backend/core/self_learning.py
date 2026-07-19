"""
Sivi — Self-Learning Engine
Tracks errors, extracts lessons, auto-retries with self-diagnosis.
Makes Sivi genuinely learn from its own mistakes over time.

Architecture:
  1. Error Journal  — persistent log of every failure with full context
  2. Lesson Book    — distilled lessons extracted from repeated failures
  3. Self-Diagnosis — when a command fails, Sivi analyzes WHY and suggests a fix
  4. Auto-Retry     — for certain error types, automatically retry with corrected approach
  5. Pattern Engine — detects recurring failure patterns and prevents them proactively
"""

import os
import json
import time
import logging
import traceback
from datetime import datetime
from typing import Optional
from collections import Counter

logger = logging.getLogger("sivi.self_learning")

import sys
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ERROR_JOURNAL_FILE = os.path.join(DATA_DIR, "sivi_error_journal.json")
LESSON_BOOK_FILE = os.path.join(DATA_DIR, "sivi_lessons.json")

# ── Error categories for pattern detection ────────────────────────

ERROR_CATEGORIES = {
    "PARSE_FAIL":     "Command tag was not recognized by the parser",
    "MODULE_OFFLINE": "The required module/service is offline or not configured",
    "TIMEOUT":        "Command execution timed out",
    "CRASH":          "Command raised an unhandled exception",
    "PERMISSION":     "OS denied permission for the action",
    "NOT_FOUND":      "Target file/app/window not found",
    "NETWORK":        "Network or API request failed",
    "USER_CORRECTED": "User explicitly corrected Sivi's behavior",
}


def _categorize_error(error_msg: str, cmd_type: str = "") -> str:
    """Auto-categorize an error message."""
    msg = error_msg.lower()
    if "not recognized" in msg or "not fully mapped" in msg:
        return "PARSE_FAIL"
    if "offline" in msg or "not configured" in msg or "not installed" in msg:
        return "MODULE_OFFLINE"
    if "timed out" in msg or "timeout" in msg:
        return "TIMEOUT"
    if "permission" in msg or "access denied" in msg or "not permitted" in msg:
        return "PERMISSION"
    if "not found" in msg or "no such file" in msg or "does not exist" in msg:
        return "NOT_FOUND"
    if "network" in msg or "connection" in msg or "urlopen" in msg or "request" in msg:
        return "NETWORK"
    return "CRASH"


class SelfLearningEngine:
    """
    Persistent self-learning system for Sivi.
    
    - Logs every command failure with full context
    - Extracts recurring patterns into distilled lessons
    - Provides self-diagnosis prompts for Gemini to reflect on failures
    - Supports auto-retry for transient errors
    """

    def __init__(self):
        self.error_journal: list[dict] = []
        self.lessons: list[dict] = []
        self._load()

    # ── Persistence ───────────────────────────────────────────────

    def _load(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        
        if os.path.exists(ERROR_JOURNAL_FILE):
            try:
                with open(ERROR_JOURNAL_FILE, "r", encoding="utf-8") as f:
                    self.error_journal = json.load(f)
            except Exception:
                self.error_journal = []
        
        if os.path.exists(LESSON_BOOK_FILE):
            try:
                with open(LESSON_BOOK_FILE, "r", encoding="utf-8") as f:
                    self.lessons = json.load(f)
            except Exception:
                self.lessons = []

    def _save_journal(self):
        try:
            # Keep only last 500 entries to prevent unbounded growth
            if len(self.error_journal) > 500:
                self.error_journal = self.error_journal[-500:]
            with open(ERROR_JOURNAL_FILE, "w", encoding="utf-8") as f:
                json.dump(self.error_journal, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save error journal: {e}")

    def _save_lessons(self):
        try:
            with open(LESSON_BOOK_FILE, "w", encoding="utf-8") as f:
                json.dump(self.lessons, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save lessons: {e}")

    # ── Log an Error ──────────────────────────────────────────────

    def log_error(
        self,
        user_text: str,
        cmd_tag: str,
        cmd_type: str,
        error_msg: str,
        stack_trace: str = "",
    ) -> dict:
        """
        Log a command failure to the error journal.
        Returns the error entry for immediate use.
        """
        category = _categorize_error(error_msg, cmd_type)
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "epoch": time.time(),
            "user_text": user_text,
            "cmd_tag": cmd_tag,
            "cmd_type": cmd_type,
            "error_msg": error_msg,
            "category": category,
            "stack_trace": stack_trace[:500] if stack_trace else "",
            "resolved": False,
            "lesson_extracted": False,
        }
        
        self.error_journal.append(entry)
        self._save_journal()
        
        logger.info(f"[SelfLearn] Logged error: {category} | {cmd_tag} | {error_msg[:80]}")
        
        # Auto-extract lessons if patterns emerge
        self._check_for_patterns(category, cmd_type, cmd_tag)
        
        return entry

    def log_user_correction(self, user_text: str, what_was_wrong: str):
        """Log when the user explicitly corrects Sivi."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "epoch": time.time(),
            "user_text": user_text,
            "cmd_tag": "",
            "cmd_type": "USER_CORRECTION",
            "error_msg": what_was_wrong,
            "category": "USER_CORRECTED",
            "stack_trace": "",
            "resolved": True,
            "lesson_extracted": False,
        }
        self.error_journal.append(entry)
        self._save_journal()
        
        # Immediately create a lesson from user correction
        self.add_lesson(
            source="user_correction",
            lesson=what_was_wrong,
            cmd_type="USER_CORRECTION",
            severity="high",
        )

    # ── Lessons ───────────────────────────────────────────────────

    def add_lesson(
        self,
        source: str,
        lesson: str,
        cmd_type: str = "",
        severity: str = "medium",
    ):
        """Add a lesson to the lesson book. Deduplicates."""
        # Check for duplicate lessons
        for existing in self.lessons:
            if existing["lesson"].lower().strip() == lesson.lower().strip():
                existing["hit_count"] = existing.get("hit_count", 1) + 1
                existing["last_seen"] = datetime.now().isoformat()
                self._save_lessons()
                return
        
        self.lessons.append({
            "timestamp": datetime.now().isoformat(),
            "source": source,        # "pattern_detection" | "user_correction" | "self_diagnosis" | "auto_retry_success"
            "lesson": lesson,
            "cmd_type": cmd_type,
            "severity": severity,     # "low" | "medium" | "high" | "critical"
            "hit_count": 1,
            "last_seen": datetime.now().isoformat(),
        })
        self._save_lessons()
        logger.info(f"[SelfLearn] New lesson: {lesson[:80]}")

    # ── Pattern Detection ─────────────────────────────────────────

    def _check_for_patterns(self, category: str, cmd_type: str, cmd_tag: str):
        """
        Look at the error journal for recurring patterns.
        If the same error type has happened 3+ times for the same command type,
        auto-extract a lesson.
        """
        # Count recent errors (last 24 hours) of the same category + cmd_type
        cutoff = time.time() - (24 * 3600)
        recent_similar = [
            e for e in self.error_journal
            if e.get("epoch", 0) > cutoff
            and e.get("category") == category
            and e.get("cmd_type") == cmd_type
            and not e.get("lesson_extracted")
        ]
        
        if len(recent_similar) >= 3:
            # Extract a lesson from the pattern
            error_msgs = [e["error_msg"] for e in recent_similar[:5]]
            common_msg = error_msgs[0][:100]
            
            lesson_text = f"Command type '{cmd_type}' keeps failing with '{category}': {common_msg}. This has happened {len(recent_similar)} times in the last 24 hours."
            
            if category == "PARSE_FAIL":
                lesson_text += " The [CMD: ...] tag format may be wrong. Check the exact tag syntax in system prompt."
            elif category == "MODULE_OFFLINE":
                lesson_text += " Stop trying this command until the module is back online. Tell the user it's unavailable."
            elif category == "TIMEOUT":
                lesson_text += " This command is too slow. Consider simplifying or breaking it into smaller steps."
            elif category == "NOT_FOUND":
                lesson_text += " The target doesn't exist. Ask the user to verify the name/path before retrying."
            
            self.add_lesson(
                source="pattern_detection",
                lesson=lesson_text,
                cmd_type=cmd_type,
                severity="high",
            )
            
            # Mark journal entries as processed
            for e in recent_similar:
                e["lesson_extracted"] = True
            self._save_journal()

    # ── Self-Diagnosis Prompt ─────────────────────────────────────

    def build_diagnosis_prompt(self, cmd_tag: str, cmd_type: str, error_msg: str) -> str:
        """
        Build a prompt that makes Gemini genuinely reflect on what went wrong
        and figure out how to fix it — like a real AI thinking through its mistakes.
        """
        category = _categorize_error(error_msg, cmd_type)
        
        # Find if we've seen this exact pattern before
        similar_past = [
            e for e in self.error_journal
            if e.get("cmd_type") == cmd_type
            and e.get("category") == category
            and e.get("resolved")
        ]
        
        # Find relevant lessons
        relevant_lessons = [
            l for l in self.lessons
            if l.get("cmd_type") == cmd_type
            or l.get("cmd_type") == "USER_CORRECTION"
        ]
        
        prompt = f"""[SELF-DIAGNOSIS REQUIRED]
A command I just tried has FAILED. I need to think about what went wrong and fix it.

FAILED COMMAND: [CMD: {cmd_tag}]
COMMAND TYPE: {cmd_type}
ERROR: {error_msg}
ERROR CATEGORY: {category} — {ERROR_CATEGORIES.get(category, 'Unknown')}
"""
        
        if relevant_lessons:
            prompt += "\nLESSONS FROM MY PAST MISTAKES:\n"
            for lesson in relevant_lessons[-5:]:
                prompt += f"  - {lesson['lesson']}\n"
        
        if similar_past:
            prompt += f"\nI have seen {len(similar_past)} similar failures before with {cmd_type}.\n"
        
        prompt += """
THINK THROUGH THIS:
1. WHY did this fail? What's the root cause?
2. Can I retry with a different approach (different CMD tag, different parameters)?
3. Should I inform the user, or can I silently fix this?

If you can fix it, output a corrected [CMD: ...] tag.
If it's unfixable (module offline, permission denied), tell the user honestly and concisely.
Do NOT repeat the same failing command."""
        
        return prompt

    # ── Suggest Auto-Retry ────────────────────────────────────────

    def should_auto_retry(self, category: str, cmd_type: str) -> bool:
        """
        Decide if a failed command should be auto-retried.
        Only for transient errors, and only if we haven't already failed too many times.
        """
        retryable = {"TIMEOUT", "NETWORK"}
        if category not in retryable:
            return False
        
        # Check how many times this cmd_type has failed recently
        cutoff = time.time() - 300  # Last 5 minutes
        recent_fails = sum(
            1 for e in self.error_journal
            if e.get("epoch", 0) > cutoff
            and e.get("cmd_type") == cmd_type
            and e.get("category") == category
        )
        
        # Don't retry more than 2 times
        return recent_fails <= 2

    def mark_resolved(self, cmd_type: str, resolution: str = ""):
        """Mark the most recent error for a cmd_type as resolved."""
        for entry in reversed(self.error_journal):
            if entry.get("cmd_type") == cmd_type and not entry.get("resolved"):
                entry["resolved"] = True
                entry["resolution"] = resolution
                self._save_journal()
                break

    # ── Context for System Prompt ─────────────────────────────────

    def get_lessons_context(self) -> str:
        """
        Returns formatted lessons to inject into the system prompt.
        Only includes high-value lessons (high severity or high hit count).
        """
        if not self.lessons:
            return ""
        
        # Sort by importance: severity + hit_count
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        sorted_lessons = sorted(
            self.lessons,
            key=lambda l: (severity_order.get(l.get("severity", "low"), 0), l.get("hit_count", 1)),
            reverse=True,
        )
        
        # Take top 50 most important lessons (Deep Learning)
        top_lessons = sorted_lessons[:50]
        
        if not top_lessons:
            return ""
        
        lines = ["LESSONS I HAVE LEARNED FROM MY PAST MISTAKES (follow these strictly):"]
        for l in top_lessons:
            hit = l.get("hit_count", 1)
            prefix = "⚠️" if l.get("severity") in ("high", "critical") else "•"
            lines.append(f"  {prefix} {l['lesson']}" + (f" (seen {hit}x)" if hit > 1 else ""))
        
        return "\n".join(lines)

    # ── Stats ─────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Return learning stats for the status dashboard."""
        total_errors = len(self.error_journal)
        resolved = sum(1 for e in self.error_journal if e.get("resolved"))
        total_lessons = len(self.lessons)
        
        # Top error categories
        categories = Counter(e.get("category", "UNKNOWN") for e in self.error_journal)
        
        return {
            "total_errors_logged": total_errors,
            "errors_resolved": resolved,
            "total_lessons_learned": total_lessons,
            "top_error_categories": dict(categories.most_common(5)),
        }


# ── Singleton ─────────────────────────────────────────────────────

self_learning = SelfLearningEngine()
