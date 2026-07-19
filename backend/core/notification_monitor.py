"""
SIVI AI — Notification Monitor
Tracks Windows system notifications using winsdk.
Falls back gracefully if winsdk is not available.
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


class NotificationMonitor:
    """
    Monitors Windows system notifications.
    Returns new notifications since last check.
    Includes 3-second debounce to batch rapid-fire notifications from the same app.
    """

    def __init__(self):
        self._seen_ids: set = set()
        self._last_check: float = time.time()
        self._recent_app_alerts: dict = {}  # app_name -> last_alert_timestamp (for debounce)
        self._debounce_window: float = 3.0  # seconds — batch notifications within this window

    def get_new_notifications(self) -> List[str]:
        """
        Return a list of new notification summary strings since the last call.
        Returns empty list if winsdk is unavailable.
        Debounces: if the same app fires multiple notifications within 3 seconds,
        only the first one is reported.
        """
        if not _winsdk_available:
            return []

        try:
            listener = mgmt.UserNotificationListener.current
            # Wrap the async WinSDK call with a safety timeout
            try:
                notifications = listener.get_notifications_async(
                    mgmt.NotificationKinds.TOAST
                ).get()
            except Exception as e:
                logger.debug(f"[NotificationMonitor] WinSDK get_notifications timed out or failed: {e}")
                return []

            now = time.time()
            new_alerts = []
            for notif in notifications:
                nid = notif.id
                if nid not in self._seen_ids:
                    self._seen_ids.add(nid)
                    try:
                        app_name = notif.app_info.display_info.display_name or "Unknown App"
                    except Exception:
                        app_name = "Unknown App"

                    # Debounce: skip if same app alerted within the last 3 seconds
                    last_time = self._recent_app_alerts.get(app_name, 0)
                    if now - last_time < self._debounce_window:
                        continue  # Skip this notification (batched)
                    self._recent_app_alerts[app_name] = now

                    try:
                        binding = notif.notification.visual.get_binding("ToastGeneric")
                        texts = []
                        if binding:
                            for element in binding.get_text_elements():
                                texts.append(element.text)
                        summary = " — ".join(texts) if texts else "New notification"
                    except Exception:
                        summary = "New notification"

                    new_alerts.append(f"{app_name}: {summary}")

            # Prevent unbounded memory growth
            if len(self._seen_ids) > 500:
                self._seen_ids = set(list(self._seen_ids)[-300:])

            # Clean up old debounce entries (older than 30 seconds)
            self._recent_app_alerts = {
                k: v for k, v in self._recent_app_alerts.items()
                if now - v < 30.0
            }

            return new_alerts

        except Exception as e:
            logger.debug(f"[NotificationMonitor] Failed to read notifications: {e}")
            return []


# Module-level singleton
notification_monitor = NotificationMonitor()
