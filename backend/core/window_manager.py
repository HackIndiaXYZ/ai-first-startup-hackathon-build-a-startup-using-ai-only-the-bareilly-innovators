import win32gui
import win32con

class WindowManager:
    def __init__(self):
        pass

    def _get_window_handle(self, window_title: str):
        # A simple enumeration to find a window by substring
        found_hwnd = None
        def callback(hwnd, extra):
            nonlocal found_hwnd
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                if window_title.lower() in title:
                    found_hwnd = hwnd
        win32gui.EnumWindows(callback, None)
        return found_hwnd

    def minimize_window(self, window_title: str = None):
        if not window_title:
            hwnd = win32gui.GetForegroundWindow()
        else:
            hwnd = self._get_window_handle(window_title)
            
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return "Window minimized."
        return f"Could not find window: {window_title}"

    def maximize_window(self, window_title: str = None):
        if not window_title:
            hwnd = win32gui.GetForegroundWindow()
        else:
            hwnd = self._get_window_handle(window_title)
            
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return "Window maximized."
        return f"Could not find window: {window_title}"

    def close_window(self, window_title: str = None):
        if not window_title:
            hwnd = win32gui.GetForegroundWindow()
        else:
            hwnd = self._get_window_handle(window_title)
            
        if hwnd:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return "Window closed."
        return f"Could not find window: {window_title}"

window_manager = WindowManager()
