import os
import sys
import subprocess
import re
import webbrowser

# Sanitize app name to prevent command injection
_SAFE_APP_NAME = re.compile(r'^[a-zA-Z0-9\s\-_.]+$')


class AppLauncher:
    def __init__(self):
        # Common Windows application executables, URIs, and web shortcuts
        self.apps = {
            "notepad":       "notepad.exe",
            "calculator":    "calc.exe",
            "calc":          "calc.exe",
            "chrome":        "chrome.exe",
            "browser":       "msedge.exe",
            "edge":          "msedge.exe",
            "explorer":      "explorer.exe",
            "file explorer": "explorer.exe",
            "paint":         "mspaint.exe",
            "cmd":           "cmd.exe",
            "terminal":      "cmd.exe",
            "powershell":    "powershell.exe",
            "task manager":  "taskmgr.exe",
            "control panel": "control.exe",
            "settings":      "ms-settings:",
            "display settings": "ms-settings:display",
            "sound settings": "ms-settings:sound",
            "network settings": "ms-settings:network-status",
            "wifi settings": "ms-settings:network-wifi",
            "bluetooth settings": "ms-settings:bluetooth",
            "windows update": "ms-settings:windowsupdate",
            "camera":        "microsoft.windows.camera:",
            "snipping tool": "SnippingTool.exe",
            "vscode":        "code",
            "code":          "code",
            "visual studio": "code",
            "vlc":           "vlc.exe",
            "spotify":       "spotify.exe",
            "discord":       "discord.exe",
            "steam":         "steam.exe",
            "zoom":          "zoom.exe",
            "slack":         "slack.exe",
            "teams":         "teams.exe",
            "skype":         "skype.exe",
            "whatsapp":      "whatsapp:",
            "telegram":      "tg:",
            "word":          "winword.exe",
            "excel":         "excel.exe",
            "powerpoint":    "powerpnt.exe",
            "ppt":           "powerpnt.exe",
            "youtube":       "https://www.youtube.com",
            "google":        "https://www.google.com",
            "gmail":         "https://mail.google.com",
            "github":        "https://github.com",
            "chatgpt":       "https://chat.openai.com",
            "claude":        "https://claude.ai",
        }

    def launch_app(self, app_name: str) -> str:
        app_name = app_name.lower().strip()

        # Security: validate app name against safe pattern
        if not _SAFE_APP_NAME.match(app_name):
            return f"Invalid application name: '{app_name}'"

        target = self.apps.get(app_name, app_name)
        
        # If it's a URL or URI scheme, open with webbrowser
        if target.startswith("http") or target.endswith(":"):
            try:
                webbrowser.open(target)
                return f"Opening {app_name}."
            except Exception as e:
                return f"Failed to open link: {e}"

        # Native execution
        try:
            if sys.platform == "darwin":
                # For Mac, use open -a to launch applications by name
                subprocess.run(["open", "-a", app_name])
                return f"Opening {app_name}."
            else:
                # os.startfile acts exactly like double-clicking the file or running 'start' in cmd.
                os.startfile(target)
                return f"Opening {app_name}."
        except (FileNotFoundError, OSError):
            # If startfile fails (e.g., unknown .exe), fallback to Windows Taskbar Search
            try:
                import pyautogui
                import time
                pyautogui.press('win')
                time.sleep(0.5)
                pyautogui.write(app_name)
                time.sleep(0.5)
                pyautogui.press('enter')
                return f"Searched and opening {app_name} via Windows Taskbar."
            except Exception:
                return f"Could not find or open application '{app_name}' on this system."

        except Exception as e:
            return f"Failed to open {app_name}: {e}"

    def play_on_youtube(self, query: str) -> str:
        print(f" Playing on YouTube: {query}")
        from urllib.parse import quote_plus
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        webbrowser.open(url)
        return f"Playing {query} on YouTube."

    def google_search(self, query: str) -> str:
        print(f" Searching Google: {query}")
        from urllib.parse import quote_plus
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        webbrowser.open(url)
        return f"Here are the search results for {query}."


app_launcher = AppLauncher()
