import os
import ctypes
import subprocess
import pyautogui
import time

class SystemController:
    def __init__(self):
        pass

    def volume_up(self, amount: int = 10):
        print(f" Increasing volume by {amount}")
        # Windows hotkey for volume up is 'volumeup'
        # pyautogui presses it amount/2 times since each press is usually 2%
        presses = max(1, amount // 2)
        pyautogui.press('volumeup', presses=presses)
        return "Volume increased."

    def volume_down(self, amount: int = 10):
        print(f" Decreasing volume by {amount}")
        presses = max(1, amount // 2)
        pyautogui.press('volumedown', presses=presses)
        return "Volume decreased."
        
    def mute_volume(self):
        print(" Muting volume")
        pyautogui.press('volumemute')
        return "Volume muted."

    def lock_screen(self):
        print(" Locking screen")
        # Windows API call to lock workstation
        ctypes.windll.user32.LockWorkStation()
        return "Screen locked."

    def shutdown(self):
        print(" Shutting down computer")
        os.system("shutdown /s /t 5")
        return "Shutting down in 5 seconds."

    def restart(self):
        print(" Restarting computer")
        os.system("shutdown /r /t 5")
        return "Restarting in 5 seconds."

    def sleep_mode(self):
        print(" Entering sleep mode")
        # Use PowerShell to trigger sleep on Windows
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return "Going to sleep."

    def brightness_up(self, amount: int = 10):
        print(f" Increasing brightness by {amount}")
        try:
            # Use PowerShell to adjust brightness on Windows
            result = subprocess.run(
                ["powershell", "-Command",
                 f"$b = (Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness;"
                 f"$new = [math]::Min(100, $b + {amount});"
                 f"(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, $new)"],
                capture_output=True, text=True, timeout=5
            )
            return "Brightness increased."
        except Exception as e:
            return f"Could not adjust brightness: {e}"

    def brightness_down(self, amount: int = 10):
        print(f" Decreasing brightness by {amount}")
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 f"$b = (Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness;"
                 f"$new = [math]::Max(0, $b - {amount});"
                 f"(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, $new)"],
                capture_output=True, text=True, timeout=5
            )
            return "Brightness decreased."
        except Exception as e:
            return f"Could not adjust brightness: {e}"

    def read_clipboard(self) -> str:
        try:
            import pyperclip
            content = pyperclip.paste()
            return content if content else "Clipboard is empty."
        except ImportError:
            return "pyperclip not installed."

    def write_clipboard(self, text: str) -> str:
        try:
            import pyperclip
            pyperclip.copy(text)
            return "Text copied to clipboard."
        except ImportError:
            return "pyperclip not installed."

    def toggle_wifi(self):
        # Open quick settings as direct toggle requires admin privileges
        pyautogui.hotkey('win', 'a')
        return "Opened Action Center. You can toggle WiFi there."

    def toggle_bluetooth(self):
        # Open Bluetooth settings
        os.startfile("ms-settings:bluetooth")
        return "Opened Bluetooth settings."

    def media_play_pause(self):
        pyautogui.press('playpause')
        return "Toggled play/pause."

    def media_next(self):
        pyautogui.press('nexttrack')
        return "Skipped to next track."

    def media_prev(self):
        pyautogui.press('prevtrack')
        return "Went to previous track."

system_controller = SystemController()
