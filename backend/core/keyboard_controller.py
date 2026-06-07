import pyautogui
import subprocess
import sys

class KeyboardController:
    def __init__(self):
        pass

    def type_text(self, text: str) -> str:
        print(f" Typing text: {text}")

        # Check if text is pure ASCII — pyautogui.write only supports ASCII
        try:
            text.encode('ascii')
            is_ascii = True
        except UnicodeEncodeError:
            is_ascii = False

        if is_ascii:
            # ASCII text: use pyautogui directly with interval for natural typing
            pyautogui.write(text, interval=0.04)
        else:
            # Unicode/Hindi text: copy to clipboard then paste
            try:
                import pyperclip
                pyperclip.copy(text)
                pyautogui.hotkey('ctrl', 'v')
            except ImportError:
                # Fallback: use PowerShell to set clipboard
                try:
                    subprocess.run(
                        ["powershell", "-Command", f"Set-Clipboard -Value '{text}'"],
                        capture_output=True, timeout=3
                    )
                    pyautogui.hotkey('ctrl', 'v')
                except Exception as e:
                    return f"Could not type Unicode text: {e}"

        return f"Typed: {text}"

    def press_key(self, key: str) -> str:
        print(f" Pressing key: {key}")
        key = key.lower().strip()

        # Mapping natural language to pyautogui keys
        key_map = {
            "enter":       "enter",
            "return":      "enter",
            "space":       "space",
            "backspace":   "backspace",
            "delete":      "delete",
            "tab":         "tab",
            "escape":      "esc",
            "esc":         "esc",
            "windows":     "win",
            "home":        "home",
            "end":         "end",
            "page up":     "pageup",
            "page down":   "pagedown",
            "up":          "up",
            "down":        "down",
            "left":        "left",
            "right":       "right",
            "save":        ["ctrl", "s"],
            "copy":        ["ctrl", "c"],
            "paste":       ["ctrl", "v"],
            "cut":         ["ctrl", "x"],
            "undo":        ["ctrl", "z"],
            "redo":        ["ctrl", "y"],
            "select all":  ["ctrl", "a"],
            "close":       ["alt", "f4"],
            "screenshot":  ["win", "shift", "s"],
            "new tab":     ["ctrl", "t"],
            "close tab":   ["ctrl", "w"],
            "next tab":    ["ctrl", "tab"],
            "previous tab":["ctrl", "shift", "tab"],
            "new window":  ["ctrl", "n"],
            "refresh":     "f5",
        }

        if key in key_map:
            mapped = key_map[key]
            if isinstance(mapped, list):
                pyautogui.hotkey(*mapped)
            else:
                pyautogui.press(mapped)
            return f"Pressed {key}."
        else:
            try:
                pyautogui.press(key)
                return f"Pressed {key}."
            except Exception:
                return f"Could not press key '{key}'. Unknown key name."


keyboard_controller = KeyboardController()
