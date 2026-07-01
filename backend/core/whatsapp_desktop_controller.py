import os
import sys
import time
import subprocess
import urllib.parse
import threading
import pyautogui

try:
    from pywinauto import Application
    _pywinauto_available = True
except ImportError:
    _pywinauto_available = False


class WhatsAppDesktopController:
    def __init__(self):
        self.app_name = "WhatsApp"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _clean_number(self, number: str) -> str:
        """Extract digits from a string and add country code if needed."""
        clean_number = "".join(filter(str.isdigit, number))
        if len(clean_number) == 10:
            clean_number = "91" + clean_number
        return clean_number

    def _open_url(self, url: str):
        if sys.platform == "darwin":
            subprocess.run(["open", url])
        else:
            os.startfile(url)

    def _type_text_safe(self, text: str):
        """Type text safely, falling back to pyautogui.write."""
        ctrl_key = 'command' if sys.platform == 'darwin' else 'ctrl'
        try:
            import pyperclip
            pyperclip.copy(text)
            if sys.platform == 'darwin':
                pyautogui.hotkey('command', 'v')
            else:
                pyautogui.hotkey(ctrl_key, 'v')
        except ImportError:
            # Absolute fallback
            pyautogui.write(text, interval=0.01)

    def _press_enter(self):
        """Robustly press the Enter key across macOS and Windows."""
        if sys.platform == "darwin":
            try:
                # key code 36 is explicitly the Return key
                subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 36'])
            except Exception:
                pyautogui.press('enter')
        else:
            pyautogui.press('enter')

    def _ensure_whatsapp_focused(self, timeout: float = 5.0) -> bool:
        """Wait for WhatsApp Desktop window to appear and focus it.
        Returns True if WhatsApp is focused, False otherwise.
        """
        if sys.platform == "darwin":
            try:
                subprocess.run(["osascript", "-e", 'tell application "WhatsApp" to activate'])
                time.sleep(2.0)
                return True
            except Exception:
                time.sleep(timeout)
                return True

        if not _pywinauto_available:
            time.sleep(timeout)
            return True  # Best effort — assume it opened

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                app = Application(backend="uia").connect(title_re=".*WhatsApp.*", timeout=1)
                dlg = app.top_window()
                dlg.set_focus()
                time.sleep(0.3)
                return True
            except Exception as e:
                time.sleep(0.5)
        return False

    def _wait_for_chat_loaded(self, timeout: float = 5.0) -> bool:
        """Wait until the message input box is visible (indicates chat is loaded)."""
        if not _pywinauto_available:
            time.sleep(timeout)
            return True

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                app = Application(backend="uia").connect(title_re=".*WhatsApp.*", timeout=1)
                dlg = app.top_window()
                edits = dlg.descendants(control_type="Edit")
                for edit in edits:
                    txt = edit.window_text().lower()
                    if "message" in txt or "type a message" in txt:
                        return True
            except Exception as e:
                pass
            time.sleep(0.5)
        return False

    def _navigate_to_contact(self, contact_name: str) -> bool:
        """Navigate to a contact's chat using the Vision Agent."""
        try:
            from core.vision_agent import vision_agent
            
            # Wait for WhatsApp to fully render
            time.sleep(1.0)
            
            print(f" Vision navigating to contact: {contact_name}")
            
            # Try to find the contact directly in the recent chats sidebar
            coords = vision_agent.find_ui_element(f"The chat specifically named '{contact_name}' in the left sidebar recent chats list.")
            
            if coords:
                print(f" Found '{contact_name}' in recent chats. Clicking it.")
                pyautogui.click(coords[0], coords[1])
                time.sleep(0.5)
                return True
                
            print(f" '{contact_name}' not found in recent chats. Searching globally...")
            
            # If not found, find the global search bar
            search_coords = vision_agent.find_ui_element("The 'Search' box or magnifying glass icon at the top of the left sidebar.")
            
            if search_coords:
                print(" Found Search bar. Clicking it.")
                pyautogui.click(search_coords[0], search_coords[1])
                time.sleep(0.2)
                
                # Clear any existing text
                if sys.platform == 'darwin':
                    subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "a" using command down'])
                else:
                    pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.1)
                
                # Type the name
                self._type_text_safe(contact_name)
                time.sleep(1.0) # Wait for search results
                
                # Use vision to find the top search result
                result_coords = vision_agent.find_ui_element(f"The top search result matching '{contact_name}' below the search bar.")
                if result_coords:
                    print(" Found search result. Clicking it.")
                    pyautogui.click(result_coords[0], result_coords[1])
                    time.sleep(0.5)
                    return True
                else:
                    print(" Could not find contact in search results. Trying to hit Down Arrow and Enter as fallback.")
                    # Fallback to pure UI keys if vision fails on the search result
                    if sys.platform == 'darwin':
                        subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 125'])
                    else:
                        pyautogui.press('down')
                    time.sleep(0.1)
                    self._press_enter()
                    time.sleep(0.5)
                    return True
            
            print(" Vision Agent failed to find the Search bar. Falling back to Command+F.")
            # Absolute fallback to the old keyboard shortcuts if Vision entirely fails
            if sys.platform == 'darwin':
                subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "f" using command down'])
                time.sleep(0.5)
            else:
                pyautogui.hotkey('ctrl', 'f')
                time.sleep(0.2)
                
            self._type_text_safe(contact_name)
            time.sleep(0.8)
            if sys.platform == 'darwin':
                subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 125'])
            else:
                pyautogui.press('down')
            time.sleep(0.3)
            self._press_enter()
            time.sleep(1.5)
            return True

        except Exception as e:
            print(f" Failed to navigate to contact: {e}")
            return False

    # ── Main Actions ─────────────────────────────────────────────────────────

    def send_whatsapp_message(self, number: str, message: str) -> str:
        # Use exclusively UI automation (Search bar -> Type -> Enter) as requested by user.
        # This avoids Mac deep-link confirmation popups and ensures the chat is fully focused.
        self._open_url("whatsapp://")
        
        def _search_and_send():
            if not self._ensure_whatsapp_focused(timeout=6.0):
                print(" WhatsApp did not open in time.")
                return
            
            # Use the search bar to find the contact
            if not self._navigate_to_contact(number):
                print(f" Failed to navigate to {number}.")
                return
            
            if message:
                # Wait for chat input to be ready. 
                # On Mac, wait exactly 1s. A 5s delay often causes the user to move the mouse and lose focus.
                if sys.platform == "darwin":
                    time.sleep(1.0)
                else:
                    self._wait_for_chat_loaded(timeout=5.0)
                
                time.sleep(0.5)
                self._type_text_safe(message)
                time.sleep(0.5)
                self._press_enter()
                
        threading.Thread(target=_search_and_send, daemon=True).start()
        return f"Sending message to {number} via WhatsApp Desktop."

    def read_chat(self, contact: str = None) -> str:
        """Read recent messages from the currently open chat, or navigate to a contact first."""
        try:
            # Always ensure WhatsApp is open and focused first
            self._open_url("whatsapp://")
            if not self._ensure_whatsapp_focused(timeout=6.0):
                return "WhatsApp did not open in time."

            # If a contact name was provided, navigate to their chat first
            if contact:
                self._navigate_to_contact(contact)
                time.sleep(1.5)
            else:
                time.sleep(0.5)

            # Pywinauto's descendants() search on WhatsApp's UI tree takes 30+ seconds and causes timeouts.
            # Using the native Vision Agent (screen_reader) is 10x faster and more accurate.
            from core.screen_reader import screen_reader
            return screen_reader.read_screen(f"Please read the most recent WhatsApp messages visible on the screen. Format as 'Name: Message'.")
        except Exception as e:
            return f"Failed to read chat (ensure WhatsApp Desktop is open and focused): {e}"

    def voice_video_call(self, number: str, call_type: str) -> str:
        if not _pywinauto_available:
            return "pywinauto not installed."
        clean_number = self._clean_number(number)

        def _invoke_call():
            if clean_number and len(clean_number) >= 10:
                self._open_url(f"whatsapp://send?phone={clean_number}")
                if not self._ensure_whatsapp_focused(timeout=6.0):
                    print(" WhatsApp did not open in time.")
                    return
                self._wait_for_chat_loaded(timeout=6.0)
            else:
                self._open_url("whatsapp://")
                if not self._ensure_whatsapp_focused(timeout=6.0):
                    print(" WhatsApp did not open in time.")
                    return
                self._navigate_to_contact(number)

            try:
                app = Application(backend="uia").connect(title_re=".*WhatsApp.*", timeout=3)
                dlg = app.top_window()
                call_btn = dlg.child_window(title=call_type, control_type="Button")
                if call_btn.exists(timeout=3):
                    call_btn.invoke()
                else:
                    print(f" Could not find {call_type} button in UI.")
            except Exception as e:
                print(f" Call failed: {e}")

        threading.Thread(target=_invoke_call, daemon=True).start()
        return f"Initiating {call_type} via WhatsApp Desktop for {number}."

    def send_media(self, number: str, filepath: str) -> str:
        if not filepath:
            return "Please specify a file path to send. Example: 'send document report.pdf to 9876543210'"
        clean_number = self._clean_number(number)

        def _attach():
            if clean_number and len(clean_number) >= 10:
                if not self._ensure_whatsapp_focused(timeout=6.0):
                    print(" WhatsApp did not open in time.")
                    return
                self._wait_for_chat_loaded(timeout=6.0)
            else:
                if not self._ensure_whatsapp_focused(timeout=6.0):
                    print(" WhatsApp did not open in time.")
                    return
                self._navigate_to_contact(number)

            try:
                app = Application(backend="uia").connect(title_re=".*WhatsApp.*", timeout=3)
                dlg = app.top_window()
                attach_btn = dlg.child_window(title="Attach", control_type="Button")
                if attach_btn.exists(timeout=3):
                    attach_btn.invoke()
                    time.sleep(0.5)
                    doc_btn = dlg.child_window(title="Document", control_type="Button")
                    if doc_btn.exists():
                        doc_btn.invoke()
                        time.sleep(1)
                        self._type_text_safe(os.path.abspath(filepath))
                        time.sleep(0.5)
                        self._press_enter()
                        time.sleep(1)
                        self._press_enter()  # Send
            except Exception as e:
                print(f" Failed to attach: {e}")

        if clean_number and len(clean_number) >= 10:
            self._open_url(f"whatsapp://send?phone={clean_number}")
        else:
            self._open_url("whatsapp://")

        threading.Thread(target=_attach, daemon=True).start()
        return f"Attaching media for {number}."

    def record_voice_note(self, number: str, duration: int = 5) -> str:
        clean_number = self._clean_number(number)

        def _record():
            if clean_number:
                if not self._ensure_whatsapp_focused(timeout=6.0):
                    print(" WhatsApp did not open in time.")
                    return
                self._wait_for_chat_loaded(timeout=6.0)
            else:
                if not self._ensure_whatsapp_focused(timeout=6.0):
                    print(" WhatsApp did not open in time.")
                    return
                self._navigate_to_contact(number)

            try:
                app = Application(backend="uia").connect(title_re=".*WhatsApp.*", timeout=3)
                dlg = app.top_window()
                mic_btn = dlg.child_window(title="Voice message", control_type="Button")
                if mic_btn.exists(timeout=3):
                    mic_btn.invoke()
                    time.sleep(duration)
                    send_btn = dlg.child_window(title="Send", control_type="Button")
                    if send_btn.exists():
                        send_btn.invoke()
            except Exception as e:
                print(f" Failed to record voice note: {e}")

        if clean_number:
            self._open_url(f"whatsapp://send?phone={clean_number}")
        else:
            self._open_url("whatsapp://")

        threading.Thread(target=_record, daemon=True).start()
        return f"Recording voice note for {duration} seconds."


whatsapp_desktop_controller = WhatsAppDesktopController()
