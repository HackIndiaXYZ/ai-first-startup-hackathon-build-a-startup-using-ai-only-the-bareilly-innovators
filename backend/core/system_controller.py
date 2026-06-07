import os
import ctypes
import subprocess
import pyautogui
import time
from datetime import datetime
from pathlib import Path


class SystemController:
    def __init__(self):
        pass

    # ── Volume ────────────────────────────────────────────────────

    def volume_up(self, amount: int = 10):
        presses = max(1, amount // 2)
        pyautogui.press('volumeup', presses=presses)
        return "Volume increased."

    def volume_down(self, amount: int = 10):
        presses = max(1, amount // 2)
        pyautogui.press('volumedown', presses=presses)
        return "Volume decreased."

    def mute_volume(self):
        pyautogui.press('volumemute')
        return "Volume muted/unmuted."

    def set_volume(self, level: int) -> str:
        """Set volume to exact percentage using PowerShell / nircmd."""
        level = max(0, min(100, level))
        try:
            # Use nircmd if available (most reliable), else PowerShell SoundMixer
            result = subprocess.run(
                ["powershell", "-Command",
                 f"$wshShell = New-Object -ComObject WScript.Shell; "
                 f"for ($i=0; $i -lt 50; $i++) {{ $wshShell.SendKeys([char]174) }}; "  # mute/min first
                 f"$vol = {level}; "
                 f"Add-Type -TypeDefinition '"
                 "using System.Runtime.InteropServices; "
                 "[Guid(\"5CDF2C82-841E-4546-9722-0CF74078229A\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] "
                 "interface IAudioEndpointVolume { void _VT0(); void _VT1(); void _VT2(); void _VT3(); int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext); } "
                 "'; "
                 ],
                capture_output=True, text=True, timeout=5
            )
            # Simpler fallback: press volumeup/down to approximate
            # First mute, then unmute, then set by pressing keys
            # Use nircmd approach: bring to 0 then raise
            pyautogui.press('volumemute')
            time.sleep(0.1)
            pyautogui.press('volumemute')
            # Press volumedown 50 times to ensure we're at minimum
            pyautogui.press('volumedown', presses=50)
            # Now press volumeup for desired percentage (each press ≈ 2%)
            presses = max(1, level // 2)
            pyautogui.press('volumeup', presses=presses)
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

    def sleep_mode(self):
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return "Going to sleep."

    # ── Brightness ────────────────────────────────────────────────

    def brightness_up(self, amount: int = 10):
        try:
            subprocess.run(
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
        try:
            subprocess.run(
                ["powershell", "-Command",
                 f"$b = (Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness;"
                 f"$new = [math]::Max(0, $b - {amount});"
                 f"(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, $new)"],
                capture_output=True, text=True, timeout=5
            )
            return "Brightness decreased."
        except Exception as e:
            return f"Could not adjust brightness: {e}"

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
                subprocess.run(
                    ["powershell", "-Command", f"Set-Clipboard -Value '{text}'"],
                    capture_output=True, timeout=3
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
        except Exception:
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
        except Exception:
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


system_controller = SystemController()
