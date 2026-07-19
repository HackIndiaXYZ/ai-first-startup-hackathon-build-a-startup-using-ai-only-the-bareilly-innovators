import os
import time
import asyncio
import threading
import logging
from playwright.async_api import async_playwright

logger = logging.getLogger("sivi.whatsapp_web")

class WhatsAppWebController:
    def __init__(self):
        self.user_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sivi_whatsapp_data')
        self.playwright = None
        self.browser = None
        self.page = None
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="WAWebLoop")
        self._thread.start()
        
        # Start initialization
        asyncio.run_coroutine_threadsafe(self._init_browser(), self._loop)

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _init_browser(self):
        try:
            self.playwright = await async_playwright().start()
            
            is_fresh = not os.path.exists(self.user_data_dir)
            logger.info(f"Initializing WhatsApp Web (Headless: {not is_fresh})")
            
            try:
                self.browser = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    channel="chrome", 
                    headless=not is_fresh,
                    args=['--disable-blink-features=AutomationControlled']
                )
            except Exception as e:
                logger.warning(f"Failed to launch Chrome channel: {e}. Trying bundled chromium...")
                self.browser = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=not is_fresh,
                    args=['--disable-blink-features=AutomationControlled']
                )
            
            self.page = self.browser.pages[0] if self.browser.pages else await self.browser.new_page()
            
            await self.page.goto("https://web.whatsapp.com")
            logger.info("WhatsApp Web loaded. Waiting for authentication...")
            
            try:
                # Wait for the chat list which indicates successful login
                await self.page.wait_for_selector('div[aria-label="Chat list"]', timeout=120000) # 2 minutes for QR
                logger.info("WhatsApp Web authenticated and ready.")
            except Exception as e:
                logger.warning("Timeout waiting for WhatsApp Web authentication. If you didn't scan QR, restart Sivi.")
                
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")

    def _run_sync(self, coro, timeout=15):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    # ── Main Actions ─────────────────────────────────────────────────────────

    async def _read_chat_async(self, contact: str = None) -> str:
        if not self.page:
            return "WhatsApp Web is not initialized yet."

        try:
            if not contact:
                # Find unread chats in the sidebar
                unread_elements = await self.page.query_selector_all('[aria-label*="unread"]')
                
                if unread_elements:
                    chats = []
                    for el in unread_elements:
                        chat_container = await el.evaluate_handle('el => el.closest("[role=\'listitem\']")')
                        if chat_container:
                            text = await chat_container.inner_text()
                            if text:
                                clean_text = " | ".join(text.split('\n'))
                                chats.append(clean_text)
                    if chats:
                        return "Unread chats found: " + " || ".join(chats)
            else:
                # Search box logic for whatsapp web
                search_box = self.page.locator('div[title="Search input textbox"], div[title="Search"], div[title="Search or start new chat"], div[contenteditable="true"]').first
                if not await search_box.count():
                    return "Could not find search box."
                
                await search_box.fill("")
                await search_box.type(contact)
                await self.page.keyboard.press("Enter")
                await asyncio.sleep(2)

            message_elements = await self.page.query_selector_all('div.message-in, div.message-out')
            if not message_elements:
                return "No messages found in the active chat."
                
            messages = []
            for el in message_elements[-5:]:
                text = await el.inner_text()
                if text:
                    clean_text = " ".join(text.split('\n'))
                    messages.append(clean_text)
                    
            if messages:
                return "Recent messages: " + " | ".join(messages)
            return "Chat is empty."

        except Exception as e:
            logger.error(f"Read chat failed: {e}")
            return f"Failed to read chat: {e}"

    def read_chat(self, contact: str = None) -> str:
        return self._run_sync(self._read_chat_async(contact))

    async def _send_message_async(self, number: str, message: str) -> str:
        if not self.page:
            return "WhatsApp Web is not initialized yet."
            
        try:
            clean_number = "".join(filter(str.isdigit, number))
            if len(clean_number) == 10:
                clean_number = "91" + clean_number
                
            if clean_number:
                await self.page.goto(f"https://web.whatsapp.com/send?phone={clean_number}")
                edit_box = self.page.locator('div[title="Type a message"], div[title="Type a message"], div[contenteditable="true"]').last
                await edit_box.wait_for(timeout=15000, state="visible")
            else:
                search_box = self.page.locator('div[title="Search input textbox"], div[title="Search"], div[title="Search or start new chat"], div[contenteditable="true"]').first
                if not await search_box.count():
                    return "Search box not found."
                await search_box.fill("")
                await search_box.type(number)
                await self.page.keyboard.press("Enter")
                await asyncio.sleep(2)
                edit_box = self.page.locator('div[title="Type a message"], div[title="Type a message"], div[contenteditable="true"]').last

            if await edit_box.count():
                await edit_box.type(message)
                await self.page.keyboard.press("Enter")
                return "Message sent successfully."
            else:
                return "Failed to find the message input box."
                
        except Exception as e:
            logger.error(f"Send message failed: {e}")
            return f"Failed to send message: {e}"

    def send_whatsapp_message(self, number: str, message: str) -> str:
        return self._run_sync(self._send_message_async(number, message), timeout=20)


whatsapp_web_controller = WhatsAppWebController()
