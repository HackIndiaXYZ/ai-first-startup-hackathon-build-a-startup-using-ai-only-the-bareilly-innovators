import os
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

    def _type_text_safe(self, text: str):
        """Type text using clipboard paste for 100% reliability and speed."""
        try:
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
        except ImportError:
            try:
                subprocess.run(
                    ["powershell", "-Command", f"Set-Clipboard -Value '{text}'"],
                    capture_output=True, timeout=3
                )
                pyautogui.hotkey('ctrl', 'v')
            except Exception as e:
                # Absolute fallback
                pyautogui.write(text, interval=0.02)

    def _ensure_whatsapp_focused(self, timeout: float = 5.0) -> bool:
        """Wait for WhatsApp Desktop window to appear and focus it.
        Returns True if WhatsApp is focused, False otherwise.
        """
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
        """Navigate to a contact's chat using the sidebar search bar.
        
        Uses pywinauto to find the search Edit control (NOT Ctrl+F which
        searches within the current chat). Falls back to Ctrl+K for newer
        WhatsApp versions if pywinauto can't find the search box.
        """
        try:
            if _pywinauto_available:
                try:
                    app = Application(backend="uia").connect(title_re=".*WhatsApp.*", timeout=5)
                    dlg = app.top_window()
                    dlg.set_focus()
                    time.sleep(0.3)
                except Exception as e:
                    time.sleep(2.0)

            # Press Escape to close any open overlay / go back to chat list
            pyautogui.press('escape')
            time.sleep(0.3)

            search_clicked = False
            if _pywinauto_available:
                try:
                    app = Application(backend="uia").connect(title_re=".*WhatsApp.*", timeout=3)
                    dlg = app.top_window()
                    edits = dlg.descendants(control_type="Edit")
                    for edit in edits:
                        txt = edit.window_text().lower()
                        # The sidebar search typically has "search" in its placeholder text
                        if "search" in txt:
                            edit.click_input()
                            search_clicked = True
                            break
                except Exception as e:
                    print(f" pywinauto search box lookup failed: {e}")

            if not search_clicked:
                # Fallback: Ctrl+F is the standard shortcut to search chats in WhatsApp Desktop
                pyautogui.hotkey('ctrl', 'f')

            time.sleep(0.5)

            # Clear any existing text in the search box
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)

            # Type the contact name with Unicode support
            self._type_text_safe(contact_name)
            time.sleep(2.0)  # Increased wait for search results to load

            # Select the first search result
            pyautogui.press('down')
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(1.5)  # Wait for chat to load after selection
            return True

        except Exception as e:
            print(f" Failed to navigate to contact: {e}")
            return False

    # ── Main Actions ─────────────────────────────────────────────────────────

    def send_whatsapp_message(self, number: str, message: str) -> str:
        clean_number = self._clean_number(number)

        if clean_number and len(clean_number) >= 10:
            # Phone number path: use WhatsApp deep link with pre-filled text
            encoded_message = urllib.parse.quote(message)
            os.startfile(f"whatsapp://send?phone={clean_number}&text={encoded_message}")
            def _wait_and_send():
                # Wait for WhatsApp to open and load the chat
                if not self._ensure_whatsapp_focused(timeout=6.0):
                    print(" WhatsApp did not open in time.")
                    return
                # Wait extra time for the deep link to resolve and chat to appear
                if not self._wait_for_chat_loaded(timeout=8.0):
                    print(" Chat did not load in time, pressing Enter anyway.")
                # Press Enter to send the pre-filled message
                time.sleep(0.5)
                pyautogui.press('enter')
            threading.Thread(target=_wait_and_send, daemon=True).start()
        else:
            # Contact name path: open WhatsApp and search for contact
            os.startfile("whatsapp://")
            def _search_and_send():
                if not self._ensure_whatsapp_focused(timeout=6.0):
                    print(" WhatsApp did not open in time.")
                    return
                self._navigate_to_contact(number)
                if message:
                    # Wait for chat input to be ready
                    self._wait_for_chat_loaded(timeout=5.0)
                    time.sleep(0.5)
                    self._type_text_safe(message)
                    time.sleep(0.5)
                    pyautogui.press('enter')
            threading.Thread(target=_search_and_send, daemon=True).start()

        return f"Sending message to {number} via WhatsApp Desktop."

    def read_chat(self, contact: str = None) -> str:
        """Read recent messages from the currently open chat, or navigate to a contact first."""
        if not _pywinauto_available:
            return "pywinauto not installed."

        try:
            # If a contact name was provided, navigate to their chat first
            if contact:
                os.startfile("whatsapp://")
                if not self._ensure_whatsapp_focused(timeout=6.0):
                    return "WhatsApp did not open in time."
                self._navigate_to_contact(contact)
                time.sleep(1.0)

            app = Application(backend="uia").connect(title_re=".*WhatsApp.*", timeout=3)
            dlg = app.top_window()
            dlg.set_focus()

            # Find the message list
            list_items = dlg.descendants(control_type="ListItem")
            messages = []

            for item in list_items[-10:]:
                texts = [child.window_text() for child in item.children() if child.window_text()]
                if texts:
                    msg = " ".join(texts).strip()
                    if msg and len(msg) > 1 and "read" not in msg.lower():
                        messages.append(msg)

            if messages:
                recent = "\n".join(messages[-3:])
                source = f" from {contact}" if contact else ""
                return f"Recent messages{source}:\n{recent}"
            return "Could not read messages. Chat might be empty or UI changed."
        except Exception as e:
            return f"Failed to read chat (ensure WhatsApp Desktop is open and focused): {e}"

    def voice_video_call(self, number: str, call_type: str) -> str:
        if not _pywinauto_available:
            return "pywinauto not installed."
        clean_number = self._clean_number(number)

        def _invoke_call():
            if clean_number and len(clean_number) >= 10:
                os.startfile(f"whatsapp://send?phone={clean_number}")
                if not self._ensure_whatsapp_focused(timeout=6.0):
                    print(" WhatsApp did not open in time.")
                    return
                self._wait_for_chat_loaded(timeout=6.0)
            else:
                os.startfile("whatsapp://")
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
                        pyautogui.press('enter')
                        time.sleep(1)
                        pyautogui.press('enter')  # Send
            except Exception as e:
                print(f" Failed to attach: {e}")

        if clean_number and len(clean_number) >= 10:
            os.startfile(f"whatsapp://send?phone={clean_number}")
        else:
            os.startfile("whatsapp://")

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
            os.startfile(f"whatsapp://send?phone={clean_number}")
        else:
            os.startfile("whatsapp://")

        threading.Thread(target=_record, daemon=True).start()
        return f"Recording voice note for {duration} seconds."


whatsapp_desktop_controller = WhatsAppDesktopController()
