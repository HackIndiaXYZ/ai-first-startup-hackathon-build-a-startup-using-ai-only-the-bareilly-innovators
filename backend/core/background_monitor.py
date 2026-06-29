import os
import time
import requests
import psutil
from dotenv import load_dotenv
from notification_monitor import notification_monitor

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
BRIDGE_URL = os.getenv("BRIDGE_URL", "http://localhost:8000")

class BackgroundMonitor:
    """
    Proactive Event Monitor for SIVI.
    Runs continuously in the background and sends events to Gemini Live
    when certain thresholds are met, making Sivi a proactive assistant.
    """
    def __init__(self):
        self.last_battery_alert = 0
        self.battery_threshold = 20 # Alert when battery falls below 20%
        self.plugged_in_state = None
        self.last_active_window = ""
        self.window_tracking_enabled = True
        
    def _send_to_bridge(self, text: str):
        try:
            requests.post(
                f"{BRIDGE_URL}/voice/send-text",
                json={"text": text},
                timeout=5
            )
        except Exception as e:
            pass # Bridge is probably offline, just ignore

    def check_battery(self):
        try:
            battery = psutil.sensors_battery()
            if not battery:
                return

            percent = battery.percent
            plugged = battery.power_plugged

            # 1. Plugged / Unplugged State Changes
            if self.plugged_in_state is None:
                self.plugged_in_state = plugged
            elif self.plugged_in_state != plugged:
                self.plugged_in_state = plugged
                if plugged:
                    self._send_to_bridge(f"[SYSTEM_EVENT: User just plugged in the charger. Battery is at {percent}%. Acknowledge this proactively.]")
                    self.last_battery_alert = 0 # Reset low battery alert
                else:
                    self._send_to_bridge(f"[SYSTEM_EVENT: User just unplugged the charger. Battery is at {percent}%. Acknowledge this proactively.]")

            # 2. Low Battery Alert (Trigger once per session when it drops below threshold)
            if not plugged and percent <= self.battery_threshold:
                current_time = time.time()
                # Only alert once every 30 minutes for low battery
                if current_time - self.last_battery_alert > 1800:
                    self.last_battery_alert = current_time
                    alert_msg = (
                        f"[SYSTEM_EVENT: CRITICAL - PC Battery just dropped to {percent}%. "
                        f"Proactively interrupt the user to warn them. You can also output [CMD: brightness down] to save battery if you want.]"
                    )
                    self._send_to_bridge(alert_msg)
        except Exception as e:
            print(f"Battery check failed: {e}")

    def check_notifications(self):
        try:
            new_alerts = notification_monitor.get_new_notifications()
            for alert in new_alerts:
                self._send_to_bridge(f"[SYSTEM_EVENT: {alert}. Proactively inform the user about this notification.]")
        except Exception as e:
            print(f"Notification check failed: {e}")

    def run(self):
        print("Starting Proactive Background Monitor...")
        while True:
            self.check_battery()
            self.check_notifications()
            time.sleep(10) # Check every 10 seconds

if __name__ == "__main__":
    monitor = BackgroundMonitor()
    monitor.run()
