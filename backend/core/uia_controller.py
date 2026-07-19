import logging
import time
from typing import Optional, List, Dict, Any
import uiautomation as auto

logger = logging.getLogger("sivi.uia_controller")
auto.SetGlobalSearchTimeout(3)  # Fail fast if element not found

class UIAController:
    """
    Microsoft UIAutomation Controller for Sivi.
    Provides true native access to the DOM/accessibility trees of desktop apps.
    """
    def __init__(self):
        self.last_window: Optional[auto.WindowControl] = None

    def _find_window(self, app_name: str) -> Optional[auto.WindowControl]:
        """Find a top-level window matching the app name."""
        try:
            # First try exact match, then substring match
            win = auto.WindowControl(searchDepth=1, Name=app_name)
            if win.Exists(0, 0):
                return win
            
            # Substring match (RegexName)
            win = auto.WindowControl(searchDepth=1, RegexName=f".*{app_name}.*")
            if win.Exists(0, 0):
                return win
                
            return None
        except Exception as e:
            logger.error(f"UIA Error finding window {app_name}: {e}")
            return None

    def click_element(self, app_name: str, element_name: str) -> str:
        """Finds an element by name inside an app and clicks it natively."""
        win = self._find_window(app_name)
        if not win:
            return f"Error: Could not find window for '{app_name}'."
            
        try:
            # Search for the element inside the window
            control = win.Control(Name=element_name)
            if not control.Exists(1, 0):
                # Try regex matching
                control = win.Control(RegexName=f".*{element_name}.*")
                if not control.Exists(1, 0):
                    return f"Error: Could not find element '{element_name}' in '{app_name}'."

            # Native click (bypasses mouse cursor)
            control.SetFocus()
            time.sleep(0.1)
            control.Click(simulateMove=False)
            return f"Successfully clicked '{element_name}' in '{app_name}'."
            
        except Exception as e:
            logger.error(f"UIA click failed: {e}")
            return f"Failed to click element: {str(e)}"

    def type_into_element(self, app_name: str, element_name: str, text: str) -> str:
        """Finds an input box by name and injects text natively."""
        win = self._find_window(app_name)
        if not win:
            return f"Error: Could not find window for '{app_name}'."
            
        try:
            # Find an edit control or document control
            control = win.EditControl(Name=element_name)
            if not control.Exists(1, 0):
                control = win.EditControl(RegexName=f".*{element_name}.*")
                if not control.Exists(1, 0):
                    return f"Error: Could not find text box '{element_name}'."

            control.SetFocus()
            # Try native value setting if supported, else simulate typing
            try:
                control.GetValuePattern().SetValue(text)
            except Exception:
                control.SendKeys(text)
                
            return f"Typed text into '{element_name}'."
            
        except Exception as e:
            logger.error(f"UIA type failed: {e}")
            return f"Failed to type: {str(e)}"

    def read_window_content(self, app_name: str) -> str:
        """Recursively extracts all text from a window's UI tree."""
        win = self._find_window(app_name)
        if not win:
            return f"Error: Could not find window for '{app_name}'."
            
        try:
            texts = []
            for control, depth in auto.WalkControl(win, includeTop=True, maxDepth=5):
                name = control.Name
                if name and name.strip():
                    # Deduplicate consecutive identical names
                    if not texts or texts[-1] != name:
                        texts.append(name.strip())
            
            content = " | ".join(texts)
            return content[:2000] if content else "Window appears empty or blocks UIA."
        except Exception as e:
            logger.error(f"UIA read failed: {e}")
            return f"Failed to read window: {str(e)}"

uia_controller = UIAController()
