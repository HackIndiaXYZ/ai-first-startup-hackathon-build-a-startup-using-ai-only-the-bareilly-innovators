import sys
import pyautogui
import subprocess

if sys.platform == "win32":
    import win32gui
    import win32con
    import win32api
    import win32process


class WindowManager:
    def __init__(self):
        pass

    def _get_window_handle(self, window_title: str):
        if sys.platform != "win32":
            return None
        found_hwnd = None
        search = window_title.lower()
        
        def callback(hwnd, extra):
            nonlocal found_hwnd
            if found_hwnd:
                return  # Already found
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                if search in title:
                    found_hwnd = hwnd
                    return
                # Fallback: match against process name (e.g. "chrome" matches "chrome.exe")
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    import psutil
                    proc = psutil.Process(pid)
                    proc_name = proc.name().lower().replace(".exe", "")
                    if search in proc_name:
                        found_hwnd = hwnd
                except Exception:
                    pass
        
        win32gui.EnumWindows(callback, None)
        return found_hwnd

    def focus_window(self, window_title: str) -> str:
        if sys.platform == "darwin":
            try:
                subprocess.run(["osascript", "-e", f'tell application "{window_title}" to activate'])
                return f"Switched to {window_title}."
            except Exception as e:
                return f"Could not find or focus window: {window_title}"

        # Windows
        hwnd = self._get_window_handle(window_title)
        if hwnd:
            # Need to attach thread input to bypass Windows restrictions on foregrounding
            foreground_hwnd = win32gui.GetForegroundWindow()
            if foreground_hwnd:
                foreground_thread = win32process.GetWindowThreadProcessId(foreground_hwnd)[0]
                current_thread = win32api.GetCurrentThreadId()
                
                if foreground_thread != current_thread:
                    win32process.AttachThreadInput(foreground_thread, current_thread, True)
                    win32gui.SetForegroundWindow(hwnd)
                    win32gui.BringWindowToTop(hwnd)
                    win32process.AttachThreadInput(foreground_thread, current_thread, False)
                else:
                    win32gui.SetForegroundWindow(hwnd)
            else:
                win32gui.SetForegroundWindow(hwnd)
                
            return f"Switched to {window_title}."
        return f"Could not find window: {window_title}"

    def minimize_window(self, window_title: str = None):
        if sys.platform == "darwin":
            try:
                if window_title:
                    script = f'tell application "{window_title}" to tell window 1 to set miniaturized to true'
                else:
                    script = 'tell application "System Events" to tell (first application process whose frontmost is true) to tell window 1 to set value of attribute "AXMinimized" to true'
                subprocess.run(["osascript", "-e", script])
                return f"Window {'minimized' if not window_title else window_title + ' minimized'}."
            except Exception as e:
                return "Could not minimize window."

        # Windows
        hwnd = win32gui.GetForegroundWindow() if not window_title else self._get_window_handle(window_title)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return f"Window {'minimized' if not window_title else window_title + ' minimized'}."
        return f"Could not find window: {window_title}"

    def maximize_window(self, window_title: str = None):
        if sys.platform == "darwin":
            try:
                if window_title:
                    script = f'tell application "{window_title}" to tell window 1 to set zoomed to true'
                else:
                    script = 'tell application "System Events" to tell (first application process whose frontmost is true) to tell window 1 to set value of attribute "AXFullScreen" to true'
                subprocess.run(["osascript", "-e", script])
                return f"Window {'maximized' if not window_title else window_title + ' maximized'}."
            except Exception:
                return "Could not maximize window."

        # Windows
        hwnd = win32gui.GetForegroundWindow() if not window_title else self._get_window_handle(window_title)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return f"Window {'maximized' if not window_title else window_title + ' maximized'}."
        return f"Could not find window: {window_title}"

    def close_window(self, window_title: str = None):
        if sys.platform == "darwin":
            try:
                if window_title:
                    script = f'tell application "{window_title}" to quit'
                else:
                    script = 'tell application "System Events" to tell (first application process whose frontmost is true) to keystroke "q" using command down'
                subprocess.run(["osascript", "-e", script])
                return "Window closed."
            except Exception:
                return "Could not close window."

        # Windows
        hwnd = win32gui.GetForegroundWindow() if not window_title else self._get_window_handle(window_title)
        if hwnd:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return f"Window closed."
        return f"Could not find window: {window_title}"

    def snap_left(self) -> str:
        """Snap the active window to the left half using Win+Left or Ctrl+Option+Left."""
        if sys.platform == "darwin":
            pyautogui.hotkey('ctrl', 'option', 'left')
        else:
            pyautogui.hotkey('win', 'left')
        return "Window snapped to the left."

    def snap_right(self) -> str:
        """Snap the active window to the right half using Win+Right or Ctrl+Option+Right."""
        if sys.platform == "darwin":
            pyautogui.hotkey('ctrl', 'option', 'right')
        else:
            pyautogui.hotkey('win', 'right')
        return "Window snapped to the right."


window_manager = WindowManager()
