import pyautogui

class MouseController:
    def __init__(self):
        # Disable pyautogui failsafe for AI control (optional, but prevents sudden crashes if mouse hits corner)
        pyautogui.FAILSAFE = False

    def click(self, button="left", double=False):
        if double:
            pyautogui.doubleClick(button=button)
            return f"Double clicked {button} mouse button."
        else:
            pyautogui.click(button=button)
            return f"Clicked {button} mouse button."

    def move_to(self, x: int, y: int):
        # Move smoothly
        pyautogui.moveTo(x, y, duration=0.25)
        return f"Moved mouse to ({x}, {y})."

    def move_by(self, x_offset: int, y_offset: int):
        pyautogui.move(x_offset, y_offset, duration=0.1)
        return f"Moved mouse by ({x_offset}, {y_offset})."
        
    def scroll(self, amount: int):
        pyautogui.scroll(amount)
        return f"Scrolled {'up' if amount > 0 else 'down'}."

    def drag_to(self, x: int, y: int):
        pyautogui.dragTo(x, y, duration=0.5, button='left')
        return f"Dragged mouse to ({x}, {y})."

mouse_controller = MouseController()
