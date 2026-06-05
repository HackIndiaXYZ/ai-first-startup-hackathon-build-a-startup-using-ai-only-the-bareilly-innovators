import logging
import asyncio

try:
    from winsdk.windows.ui.notifications.management import UserNotificationListener
    _WINSDK_AVAILABLE = True
except ImportError:
    _WINSDK_AVAILABLE = False

logger = logging.getLogger("sivi.notification_monitor")

class NotificationMonitor:
    def __init__(self):
        self.seen_ids = set()
        self.first_run = True

    async def _get_new_notifications_async(self) -> list:
        if not _WINSDK_AVAILABLE:
            return []
            
        try:
            listener = UserNotificationListener.current
            status = await listener.request_access_async()
            
            if status != 1: # 1 means Allowed
                return []

            notifs = await listener.get_notifications_async(1) # 1 = Toast
            new_alerts = []
            
            for n in notifs:
                if n.id not in self.seen_ids:
                    self.seen_ids.add(n.id)
                    
                    if not self.first_run:
                        app_name = n.app_info.display_info.display_name if n.app_info else "System"
                        bindings = n.notification.visual.bindings
                        text = ""
                        if bindings:
                            text_elements = bindings[0].get_text_elements()
                            text = " ".join([t.text for t in text_elements])
                        
                        if text:
                            new_alerts.append(f"Notification from {app_name}: {text}")
            
            self.first_run = False
            return new_alerts
        except Exception as e:
            print(f"Notification read error: {e}")
            return []

    def get_new_notifications(self) -> list:
        # Run async function in a synchronous wrapper
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._get_new_notifications_async())

notification_monitor = NotificationMonitor()
