"""
SIVI AI -- Notification Monitor
Tracks Windows system notifications using winsdk.
Falls back gracefully if winsdk is not available.

Improvements v2:
  - Priority whitelist: only speak high-priority apps (WhatsApp, Telegram, Calls)
  - Silently log low-priority notifications (Windows updates, system alerts)
  - Configurable debounce per priority tier
  - Accurate notification summary with title + body
"""

import logging
import time
from typing import List

logger = logging.getLogger("sivi.notification_monitor")

try:
    import winsdk.windows.ui.notifications.management as mgmt
    _winsdk_available = True
except (ImportError, OSError):
    _winsdk_available = False


# ── Priority Configuration ────────────────────────────────────────────────────

# Apps that Sivi will SPEAK aloud when a notification arrives
HIGH_PRIORITY_APPS = {
    "whatsapp", "telegram", "discord", "instagram", "signal",
    "messages", "phone link", "your phone", "phone",
    "gmail", "outlook", "mail", "email",
    "zoom", "teams", "skype", "meet",
    "slack",
}

# Debounce windows by tier (seconds)
HIGH_PRIORITY_DEBOUNCE  = 2.0   # speak within 2 seconds
LOW_PRIORITY_DEBOUNCE   = 30.0  # suppress repeated low-priority alerts for 30s


def _normalize_app_name(name: str) -> str:
    """Normalize app name to lowercase, stripping common suffixes."""
    return name.lower().strip().replace(" messenger", "").replace(" - chat", "")


class NotificationMonitor:
    """
    Monitors Windows system notifications.
    Classifies notifications by priority and returns only those worth speaking aloud.
    Debounces: high-priority apps debounce at 2s, low-priority at 30s.
    """

    def __init__(self):
        self._seen_ids: set = set()
        self._recent_app_alerts: dict = {}  # app_name -> last_alert_timestamp

    def _should_speak(self, app_name: str) -> bool:
        """Determine if this app's notification is high-priority enough to speak."""
        normalized = _normalize_app_name(app_name)
        for priority_app in HIGH_PRIORITY_APPS:
            if priority_app in normalized:
                return True
        return False

    def _debounce_window(self, app_name: str) -> float:
        """Return the debounce window for this app in seconds."""
        return HIGH_PRIORITY_DEBOUNCE if self._should_speak(app_name) else LOW_PRIORITY_DEBOUNCE

    def get_new_notifications(self) -> List[str]:
        """
        Return a list of new notification summary strings since last call.
        Only returns HIGH-PRIORITY app notifications (WhatsApp, Telegram, etc).
        Low-priority notifications (system, Windows Update) are suppressed.
        Returns empty list if winsdk is unavailable.
        """
        if not _winsdk_available:
            return []

        try:
            listener = mgmt.UserNotificationListener.current
            try:
                notifications = listener.get_notifications_async(
                    mgmt.NotificationKinds.TOAST
                ).get()
            except Exception as e:
                logger.debug(f"[NotificationMonitor] WinSDK call failed: {e}")
                return []

            now = time.time()
            new_alerts = []

            for notif in notifications:
                nid = notif.id
                if nid in self._seen_ids:
                    continue
                self._seen_ids.add(nid)

                # ── Get app name ──────────────────────────────────────────────
                try:
                    app_name = notif.app_info.display_info.display_name or "Unknown App"
                except Exception:
                    app_name = "Unknown App"

                # ── Priority filter: only speak high-priority ──────────────────
                if not self._should_speak(app_name):
                    logger.debug(f"[NotificationMonitor] Suppressed low-priority: {app_name}")
                    continue

                # ── Debounce ──────────────────────────────────────────────────
                debounce = self._debounce_window(app_name)
                last_time = self._recent_app_alerts.get(app_name, 0)
                if now - last_time < debounce:
                    continue  # Still within debounce window
                self._recent_app_alerts[app_name] = now

                # ── Extract notification text (title + body) ───────────────────
                try:
                    binding = notif.notification.visual.get_binding("ToastGeneric")
                    texts = []
                    if binding:
                        for element in binding.get_text_elements():
                            if element.text and element.text.strip():
                                texts.append(element.text.strip())
                    # First text is usually title, second is body
                    if len(texts) >= 2:
                        summary = f"{texts[0]}: {texts[1]}"
                    elif texts:
                        summary = texts[0]
                    else:
                        summary = "New notification"
                except Exception:
                    summary = "New notification"

                new_alerts.append(f"{app_name}: {summary}")

            # ── Memory management ─────────────────────────────────────────────
            if len(self._seen_ids) > 500:
                self._seen_ids = set(list(self._seen_ids)[-300:])

            # Clean stale debounce entries (older than 5 minutes)
            self._recent_app_alerts = {
                k: v for k, v in self._recent_app_alerts.items()
                if now - v < 300.0
            }

            return new_alerts

        except Exception as e:
            logger.debug(f"[NotificationMonitor] Error: {e}")
            return []


# Module-level singleton
notification_monitor = NotificationMonitor()
