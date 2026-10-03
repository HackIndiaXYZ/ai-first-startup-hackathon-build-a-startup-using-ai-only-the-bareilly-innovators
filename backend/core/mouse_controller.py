"""
SIVI — Advanced Mouse Controller
==================================
Full voice-driven mouse automation:
  - Click (left/right/double/middle) at current position or coordinates
  - Smooth movement with natural easing
  - Drag-and-drop
  - Scroll (with amount control)
  - Screen-region shortcuts (top-left, center, etc.)
  - Context menu (right-click) shortcut
  - Cursor position query
"""

import pyautogui
import time
import ctypes

# Disable corner failsafe — Sivi controls the mouse intentionally
pyautogui.FAILSAFE = False

# --- Screen info ---
def _screen_size():
    return pyautogui.size()


def _region_to_coords(region: str):
    """
    Map region names to (x, y) coordinates.
    e.g. 'center' → center of screen, 'top left' → (50, 50)
    """
    sw, sh = _screen_size()
    region = region.lower().strip()
    mapping = {
        "center":           (sw // 2,    sh // 2),
        "top":              (sw // 2,    50),
        "bottom":           (sw // 2,    sh - 50),
        "left":             (50,         sh // 2),
        "right":            (sw - 50,    sh // 2),
        "top left":         (50,         50),
        "top right":        (sw - 50,    50),
        "bottom left":      (50,         sh - 50),
        "bottom right":     (sw - 50,    sh - 50),
        "top center":       (sw // 2,    50),
        "bottom center":    (sw // 2,    sh - 50),
    }
    return mapping.get(region, None)


class MouseController:
    def __init__(self):
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.05  # Small global pause between actions

    # ── Click ────────────────────────────────────────────────────────

    def click(self, button="left", double=False, x=None, y=None):
        """Click at current position or at (x,y) if provided."""
        if x is not None and y is not None:
            pyautogui.moveTo(int(x), int(y), duration=0.2)
        if double:
            pyautogui.doubleClick(button=button)
            loc = f"at ({x},{y})" if x is not None else "at current position"
            return f"Double-clicked {button} button {loc}."
        else:
            pyautogui.click(button=button)
            loc = f"at ({x},{y})" if x is not None else "at current position"
            return f"Clicked {button} button {loc}."

    def click_region(self, region: str, button="left", double=False):
        """Click a named region of the screen (e.g. 'center', 'top left')."""
        coords = _region_to_coords(region)
        if not coords:
            return f"Unknown region '{region}'. Try: center, top, bottom, left, right, top left, top right, bottom left, bottom right."
        x, y = coords
        pyautogui.moveTo(x, y, duration=0.25)
        if double:
            pyautogui.doubleClick(button=button)
        else:
            pyautogui.click(button=button)
        return f"{'Double-clicked' if double else 'Clicked'} {button} button at screen region '{region}' ({x},{y})."

    def right_click(self, x=None, y=None):
        """Right-click (context menu) at position or current location."""
        if x is not None and y is not None:
            pyautogui.moveTo(int(x), int(y), duration=0.2)
        pyautogui.click(button='right')
        return "Right-clicked (context menu opened)."

    def middle_click(self, x=None, y=None):
        """Middle-click (useful for opening links in new tab)."""
        if x is not None and y is not None:
            pyautogui.moveTo(int(x), int(y), duration=0.2)
        pyautogui.click(button='middle')
        return "Middle-clicked."

    # ── Movement ─────────────────────────────────────────────────────

    def move_to(self, x: int, y: int, duration: float = 0.3):
        """Smoothly move mouse to absolute coordinates."""
        pyautogui.moveTo(int(x), int(y), duration=duration)
        return f"Moved mouse to ({x}, {y})."

    def move_to_region(self, region: str):
        """Move mouse to a named screen region."""
        coords = _region_to_coords(region)
        if not coords:
            return f"Unknown region '{region}'."
        x, y = coords
        pyautogui.moveTo(x, y, duration=0.3)
        return f"Moved mouse to '{region}' ({x}, {y})."

    def move_by(self, x_offset: int, y_offset: int, duration: float = 0.15):
        """Move mouse by offset relative to current position."""
        pyautogui.move(int(x_offset), int(y_offset), duration=duration)
        dirs = []
        if y_offset < 0: dirs.append("up")
        if y_offset > 0: dirs.append("down")
        if x_offset < 0: dirs.append("left")
        if x_offset > 0: dirs.append("right")
        return f"Moved mouse {'and '.join(dirs)} by {abs(x_offset or y_offset)} pixels."

    def get_position(self):
        """Return the current mouse cursor position."""
        x, y = pyautogui.position()
        return f"Mouse is currently at ({x}, {y})."

    # ── Scroll ───────────────────────────────────────────────────────

    def scroll(self, amount: int, x=None, y=None):
        """
        Scroll up (positive) or down (negative).
        amount: number of 'clicks' — e.g. 5 clicks up = scroll(5)
        """
        if x is not None and y is not None:
            pyautogui.moveTo(int(x), int(y), duration=0.15)
        # pyautogui.scroll takes clicks (not pixels)
        # Convert raw pixel amounts to clicks (approx 120px per click)
        clicks = amount if abs(amount) <= 20 else amount // 120
        pyautogui.scroll(clicks)
        direction = "up" if clicks > 0 else "down"
        return f"Scrolled {direction} ({abs(clicks)} clicks)."

    def scroll_amount(self, direction: str, clicks: int = 3):
        """Scroll by a specific number of clicks in a direction."""
        n = clicks if direction == "up" else -clicks
        pyautogui.scroll(n)
        return f"Scrolled {direction} {clicks} steps."

    # ── Drag ─────────────────────────────────────────────────────────

    def drag_to(self, x: int, y: int, from_x=None, from_y=None, duration: float = 0.5):
        """Drag from current position (or from_x, from_y) to (x, y)."""
        if from_x is not None and from_y is not None:
            pyautogui.moveTo(int(from_x), int(from_y), duration=0.2)
        pyautogui.dragTo(int(x), int(y), duration=duration, button='left')
        return f"Dragged to ({x}, {y})."

    def drag_by(self, x_offset: int, y_offset: int, duration: float = 0.4):
        """Drag mouse by offset from current position."""
        pyautogui.drag(int(x_offset), int(y_offset), duration=duration, button='left')
        return f"Dragged by ({x_offset}, {y_offset})."

    # ── Selection ────────────────────────────────────────────────────

    def select_area(self, x1: int, y1: int, x2: int, y2: int):
        """Click and drag to select an area (e.g. for text selection)."""
        pyautogui.moveTo(x1, y1, duration=0.2)
        pyautogui.mouseDown()
        time.sleep(0.05)
        pyautogui.moveTo(x2, y2, duration=0.3)
        pyautogui.mouseUp()
        return f"Selected area from ({x1},{y1}) to ({x2},{y2})."


mouse_controller = MouseController()
