import psutil
import platform
import logging
import sys

logger = logging.getLogger("sivi.system_monitor")

def _get_os_info():
    os_name = platform.system()
    if os_name == "Windows":
        try:
            if sys.getwindowsversion().build >= 22000:
                return "Windows 11"
        except Exception:
            pass
    return f"{os_name} {platform.release()}"

class SystemMonitor:
    def __init__(self):
        pass

    def get_system_status(self) -> str:
        """Returns a natural language summary of the PC's health."""
        self.os_info = _get_os_info()
        try:
            # Optimized: Reduced interval from 0.5 to 0.1 to prevent blocking the async bridge_server event loop
            cpu_usage = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory()
            ram_percent = ram.percent
            ram_free_gb = round(ram.available / (1024 ** 3), 1)
            
            import os
            root_drive = os.path.abspath(os.sep)
            disk = psutil.disk_usage(root_drive)
            disk_free_gb = round(disk.free / (1024 ** 3), 1)

            battery = psutil.sensors_battery()
            battery_status = ""
            if battery:
                plugged = "plugged in" if battery.power_plugged else "on battery"
                battery_status = f" Battery is at {battery.percent}% ({plugged})."

            from datetime import datetime
            now = datetime.now()
            current_time = now.strftime("%I:%M %p")
            current_date = now.strftime("%A, %B %d, %Y")

            report = (f"The current time is {current_time} on {current_date}. "
                      f"Your system is running {self.os_info}. "
                      f"CPU usage is at {cpu_usage}%. "
                      f"You are using {ram_percent}% of your RAM, with {ram_free_gb} GB free. "
                      f"Your C drive has {disk_free_gb} GB of free space left.{battery_status}")
            
            if cpu_usage > 85:
                report += " Warning: CPU usage is quite high, you might want to close some heavy applications."
            if ram_percent > 90:
                report += " Warning: You are almost out of RAM."
                
            return report
        except Exception as e:
            logger.error(f"Error reading system status: {e}")
            return "I am having trouble reading the system sensors right now."

system_monitor = SystemMonitor()
