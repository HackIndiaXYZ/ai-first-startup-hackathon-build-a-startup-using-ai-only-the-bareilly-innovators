import win32gui
import win32con
import win32api
import pyautogui


class WindowManager:
    def __init__(self):
        pass

    def _get_window_handle(self, window_title: str):
        found_hwnd = None
        def callback(hwnd, extra):
            nonlocal found_hwnd
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                if window_title.lower() in title:
                    found_hwnd = hwnd
        win32gui.EnumWindows(callback, None)
        return found_hwnd

    def focus_window(self, window_title: str) -> str:
        hwnd = self._get_window_handle(window_title)
        if hwnd:
            # Need to attach thread input to bypass Windows restrictions on foregrounding
            import win32process
            foreground_hwnd = win32gui.GetForegroundWindow()
            foreground_thread = win32process.GetWindowThreadProcessId(foreground_hwnd)[0]
            current_thread = win32api.GetCurrentThreadId()
            
            if foreground_thread != current_thread:
                win32process.AttachThreadInput(foreground_thread, current_thread, True)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.BringWindowToTop(hwnd)
                win32process.AttachThreadInput(foreground_thread, current_thread, False)
            else:
                win32gui.SetForegroundWindow(hwnd)
                
            return f"Switched to {window_title}."
        return f"Could not find window: {window_title}"

    def minimize_window(self, window_title: str = None):
        hwnd = win32gui.GetForegroundWindow() if not window_title else self._get_window_handle(window_title)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return f"Window {'minimized' if not window_title else window_title + ' minimized'}."
        return f"Could not find window: {window_title}"

    def maximize_window(self, window_title: str = None):
        hwnd = win32gui.GetForegroundWindow() if not window_title else self._get_window_handle(window_title)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return f"Window {'maximized' if not window_title else window_title + ' maximized'}."
        return f"Could not find window: {window_title}"

    def close_window(self, window_title: str = None):
        hwnd = win32gui.GetForegroundWindow() if not window_title else self._get_window_handle(window_title)
        if hwnd:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return f"Window closed."
        return f"Could not find window: {window_title}"

    def snap_left(self) -> str:
        """Snap the active window to the left half using Win+Left."""
        pyautogui.hotkey('win', 'left')
        return "Window snapped to the left."

    def snap_right(self) -> str:
        """Snap the active window to the right half using Win+Right."""
        pyautogui.hotkey('win', 'right')
        return "Window snapped to the right."


window_manager = WindowManager()
