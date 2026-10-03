import os
import sys
import ctypes
import subprocess
import pyautogui
import time
from datetime import datetime
from pathlib import Path

from core.process_manager import process_manager
from core.network_diagnostics import network_diagnostics
class SystemController:
    def __init__(self):
        pass

    # ── Volume ────────────────────────────────────────────────────

    def volume_up(self, amount: int = 10):
        try:
            import win32api
            import win32con
            VK_VOLUME_UP = 0xAF
            presses = max(1, amount // 2)
            for _ in range(presses):
                win32api.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                win32api.keybd_event(VK_VOLUME_UP, 0, win32con.KEYEVENTF_KEYUP, 0)
            return "Volume increased."
        except Exception:
            presses = max(1, amount // 2)
            pyautogui.press('volumeup', presses=presses)
            return "Volume increased."

    def volume_down(self, amount: int = 10):
        try:
            import win32api
            import win32con
            VK_VOLUME_DOWN = 0xAE
            presses = max(1, amount // 2)
            for _ in range(presses):
                win32api.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                win32api.keybd_event(VK_VOLUME_DOWN, 0, win32con.KEYEVENTF_KEYUP, 0)
            return "Volume decreased."
        except Exception:
            presses = max(1, amount // 2)
            pyautogui.press('volumedown', presses=presses)
            return "Volume decreased."

    def mute_volume(self):
        try:
            import win32api
            import win32con
            VK_VOLUME_MUTE = 0xAD
            win32api.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
            win32api.keybd_event(VK_VOLUME_MUTE, 0, win32con.KEYEVENTF_KEYUP, 0)
            return "Volume muted/unmuted."
        except Exception:
            pyautogui.press('volumemute')
            return "Volume muted/unmuted."

    def set_volume(self, level: int) -> str:
        """Set volume to exact percentage using win32api."""
        level = max(0, min(100, level))
        try:
            import win32api
            import win32con
            VK_VOLUME_DOWN = 0xAE
            VK_VOLUME_UP = 0xAF
            
            # Mute completely first
            for _ in range(50):
                win32api.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                win32api.keybd_event(VK_VOLUME_DOWN, 0, win32con.KEYEVENTF_KEYUP, 0)
                
            # Increase to target level
            for _ in range(level // 2):
                win32api.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                win32api.keybd_event(VK_VOLUME_UP, 0, win32con.KEYEVENTF_KEYUP, 0)
                
            return f"Volume set to approximately {level}%."
        except Exception as e:
            return f"Could not set volume: {e}"

    # ── Power ─────────────────────────────────────────────────────

    def lock_screen(self):
        ctypes.windll.user32.LockWorkStation()
        return "Screen locked."

    def shutdown(self):
        os.system("shutdown /s /t 5")
        return "Shutting down in 5 seconds."

    def restart(self):
        os.system("shutdown /r /t 5")
        return "Restarting in 5 seconds."

    def sleep_mode(self, delay: int = 5):
        import threading
        def _sleep():
            time.sleep(delay)
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        
        threading.Thread(target=_sleep, daemon=True).start()
        return "Okk sir, system sleep mode me ja rha hai."

    # ── Brightness ────────────────────────────────────────────────

    def brightness_up(self, amount: int = 10):
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 f"$b = (Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness;"
                 f"$new = [math]::Min(100, $b + {amount});"
                 f"(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, $new)"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return "Boss, this monitor does not support software brightness controls."
            return "Brightness increased."
        except Exception as e:
            return f"Boss, this monitor does not support software brightness controls."

    def brightness_down(self, amount: int = 10):
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 f"$b = (Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness;"
                 f"$new = [math]::Max(0, $b - {amount});"
                 f"(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, $new)"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return "Boss, this monitor does not support software brightness controls."
            return "Brightness decreased."
        except Exception as e:
            return f"Boss, this monitor does not support software brightness controls."

    # ── Screenshot ────────────────────────────────────────────────

    def take_screenshot(self) -> str:
        """Take a real screenshot and save to Desktop with timestamp."""
        try:
            from PIL import ImageGrab
            desktop = Path(os.path.expanduser("~/Desktop"))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = desktop / f"Screenshot_{timestamp}.png"
            img = ImageGrab.grab()
            img.save(str(filename))
            return f"Screenshot saved to Desktop as Screenshot_{timestamp}.png"
        except ImportError:
            # Fallback: use Win+Shift+S (Snipping Tool)
            pyautogui.hotkey('win', 'printscreen')
            return "Screenshot taken and saved to Pictures folder."
        except Exception as e:
            return f"Screenshot failed: {e}"

    # ── Clipboard ─────────────────────────────────────────────────

    def read_clipboard(self) -> str:
        try:
            import pyperclip
            content = pyperclip.paste()
            return content if content else "Clipboard is empty."
        except ImportError:
            try:
                result = subprocess.run(
                    ["powershell", "-Command", "Get-Clipboard"],
                    capture_output=True, text=True, timeout=3
                )
                return result.stdout.strip() or "Clipboard is empty."
            except Exception as e:
                return f"Could not read clipboard: {e}"

    def write_clipboard(self, text: str) -> str:
        try:
            import pyperclip
            pyperclip.copy(text)
            return f"Copied to clipboard: {text[:50]}{'...' if len(text) > 50 else ''}"
        except ImportError:
            try:
                # Safe: pipe text via stdin instead of string interpolation
                # This prevents PowerShell injection attacks
                result = subprocess.run(
                    ["powershell", "-Command", "Set-Clipboard -Value $input"],
                    input=text, capture_output=True, timeout=3, text=True
                )
                return "Text copied to clipboard."
            except Exception as e:
                return f"Could not write to clipboard: {e}"

    # ── Connectivity ──────────────────────────────────────────────

    def wifi_on(self) -> str:
        try:
            result = subprocess.run(
                ["netsh", "interface", "set", "interface", "Wi-Fi", "enable"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return "WiFi enabled successfully."
            # Fallback: open action center
            pyautogui.hotkey('win', 'a')
            return "Opened Action Center. Please toggle WiFi there."
        except Exception as e:
            pyautogui.hotkey('win', 'a')
            return "Opened Action Center to toggle WiFi."

    def wifi_off(self) -> str:
        try:
            result = subprocess.run(
                ["netsh", "interface", "set", "interface", "Wi-Fi", "disable"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return "WiFi disabled successfully."
            pyautogui.hotkey('win', 'a')
            return "Opened Action Center. Please toggle WiFi there."
        except Exception as e:
            pyautogui.hotkey('win', 'a')
            return "Opened Action Center to toggle WiFi."

    def bluetooth_on(self) -> str:
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
                 "[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null; "
                 "$radios = [Windows.Devices.Radios.Radio]::GetRadiosAsync().GetAwaiter().GetResult(); "
                 "$bt = $radios | Where-Object { $_.Kind -eq 'Bluetooth' }; "
                 "if ($bt) { $bt.SetStateAsync('On').GetAwaiter().GetResult() } "],
                capture_output=True, text=True, timeout=10
            )
            return "Bluetooth enabled."
        except Exception as e:
            os.startfile("ms-settings:bluetooth")
            return "Opened Bluetooth settings."

    def bluetooth_off(self) -> str:
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
                 "[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null; "
                 "$radios = [Windows.Devices.Radios.Radio]::GetRadiosAsync().GetAwaiter().GetResult(); "
                 "$bt = $radios | Where-Object { $_.Kind -eq 'Bluetooth' }; "
                 "if ($bt) { $bt.SetStateAsync('Off').GetAwaiter().GetResult() } "],
                capture_output=True, text=True, timeout=10
            )
            return "Bluetooth disabled."
        except Exception as e:
            os.startfile("ms-settings:bluetooth")
            return "Opened Bluetooth settings."

    # ── Media ─────────────────────────────────────────────────────

    def media_play_pause(self):
        pyautogui.press('playpause')
        return "Toggled play/pause."

    def media_next(self):
        pyautogui.press('nexttrack')
        return "Skipped to next track."

    def media_prev(self):
        pyautogui.press('prevtrack')
        return "Went to previous track."

    # ── Phase 2: Advanced System Control ──────────────────────────

    def list_processes(self):
        procs = process_manager.get_running_processes(limit=10)
        if not procs: return "Could not retrieve process list."
        res = "Top Processes:\n"
        for p in procs:
            res += f"- {p['name']} (PID: {p['pid']}) - {p['memory_mb']}MB\n"
        return res

    def kill_process(self, process_identifier: str):
        return process_manager.kill_process(process_identifier)

    def get_network_info(self):
        status = network_diagnostics.get_network_status()
        ips = network_diagnostics.get_ip_address()
        return f"{status}\nLocal IP: {ips.get('local_ip')}\nPublic IP: {ips.get('public_ip')}"

    def ping_host(self, host: str):
        return network_diagnostics.ping_host(host)

    def get_disk_info(self):
        try:
            import psutil
            res = "Disk Usage:\n"
            for part in psutil.disk_partitions(all=False):
                if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''):
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    free_gb = round(usage.free / (1024**3), 1)
                    total_gb = round(usage.total / (1024**3), 1)
                    res += f"- {part.device}: {free_gb}GB free of {total_gb}GB ({usage.percent}% used)\n"
                except Exception:
                    pass
            return res
        except Exception as e:
            return f"Error getting disk info: {e}"

    def empty_recycle_bin(self):
        try:
            import winshell
            winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
            return "Recycle bin emptied successfully."
        except Exception as e:
            return f"Failed to empty recycle bin: {e}"

    def get_system_uptime(self):
        try:
            import psutil
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            return f"System has been running for {hours} hours and {minutes} minutes (since {boot_time.strftime('%I:%M %p')})."
        except Exception as e:
            return "Could not determine system uptime."


system_controller = SystemController()
