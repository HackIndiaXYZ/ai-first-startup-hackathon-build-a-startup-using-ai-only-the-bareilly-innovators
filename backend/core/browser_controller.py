import asyncio
import os
import threading
import urllib.parse
from playwright.async_api import async_playwright


class BrowserController:
    """
    Playwright-based browser controller using a dedicated background event loop.
    This avoids the 'event loop already running' crash when called from FastAPI/uvicorn.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrowserController, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.playwright = None
        self.browser_context = None
        self.current_page = None

        # Determine paths
        core_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(os.path.dirname(core_dir), "data", "browser_profile")
        os.makedirs(data_dir, exist_ok=True)
        self.user_data_dir = data_dir

        # Dedicated event loop in a background thread for Playwright
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="PlaywrightLoop")
        self._thread.start()

    def _run_loop(self):
        """Run the dedicated event loop forever in a background thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_async(self, coro, timeout=30):
        """Schedule a coroutine on the dedicated Playwright loop and block until done."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    async def _ensure_started(self):
        if self.browser_context is None:
            print(" Starting Playwright Browser Context...")
            self.playwright = await async_playwright().start()
            self.browser_context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,
                channel="chrome",
                args=["--start-maximized"],
                no_viewport=True
            )
            pages = self.browser_context.pages
            self.current_page = pages[0] if pages else await self.browser_context.new_page()

    async def _get_new_page(self):
        await self._ensure_started()
        try:
            return await self.browser_context.new_page()
        except Exception as e:
            print(" Browser context was closed. Restarting...")
            self.browser_context = None
            if self.playwright:
                try: await self.playwright.stop()
                except Exception: pass
                self.playwright = None
            await self._ensure_started()
            return await self.browser_context.new_page()

    async def _get_current_page(self):
        await self._ensure_started()
        try:
            if not self.current_page or self.current_page.is_closed():
                pages = self.browser_context.pages
                self.current_page = pages[-1] if pages else await self.browser_context.new_page()
            return self.current_page
        except Exception as e:
            print(" Browser context was closed. Restarting...")
            self.browser_context = None
            if self.playwright:
                try: await self.playwright.stop()
                except Exception: pass
                self.playwright = None
            await self._ensure_started()
            return self.current_page

    # ── WhatsApp ─────────────────────────────────────────────────────────────
    async def _send_whatsapp(self, number: str, message: str) -> str:
        await self._ensure_started()
        print(f" Sending WhatsApp via Playwright to {number}")
        clean_number = "".join(filter(str.isdigit, number))
        if len(clean_number) == 10:
            clean_number = "91" + clean_number

        encoded_message = urllib.parse.quote(message)
        url = f"https://web.whatsapp.com/send?phone={clean_number}&text={encoded_message}"

        page = await self._get_new_page()
        self.current_page = page
        await page.goto(url)

        try:
            # Wait for either the chat to load (send button appears) or QR code
            print(" Waiting for WhatsApp Web to load...")
            send_button_selector = 'span[data-icon="send"]'
            await page.wait_for_selector(send_button_selector, timeout=20000)
            await page.click(send_button_selector)
            await asyncio.sleep(2) # Wait for message to actually send
            await page.close()
            # Bring focus back to previous page
            if self.browser_context.pages:
                self.current_page = self.browser_context.pages[-1]
                await self.current_page.bring_to_front()
            return f"WhatsApp message sent successfully to {number}."
        except Exception as e:
            return "Could not send WhatsApp message. You might need to scan the QR code."

    def send_whatsapp_message(self, number: str, message: str) -> str:
        return self._run_async(self._send_whatsapp(number, message))

    # ── YouTube ─────────────────────────────────────────────────────────────
    async def _play_youtube(self, query: str) -> str:
        try:
            import urllib.request
            import urllib.parse
            import re
            import webbrowser
            
            print(f" Searching YouTube for '{query}'...")
            html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + urllib.parse.quote(query))
            video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
            if video_ids:
                url = f"https://www.youtube.com/watch?v={video_ids[0]}"
                webbrowser.open(url)
                return f"Playing '{query}' on YouTube in your default browser."
            return "Could not find video on YouTube."
        except Exception as e:
            return f"Failed to play YouTube video: {e}"

    def play_youtube(self, query: str) -> str:
        return self._run_async(self._play_youtube(query))

    # ── Search / Navigation ───────────────────────────────────────────────────
    async def _search_google(self, query: str) -> str:
        page = await self._get_new_page()
        self.current_page = page
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        await page.goto(url)
        return f"Searched Google for {query}."

    def search_google(self, query: str) -> str:
        return self._run_async(self._search_google(query))

    async def _open_url(self, url: str) -> str:
        page = await self._get_new_page()
        self.current_page = page
        if not url.startswith('http'):
            url = 'https://' + url
        await page.goto(url)
        return f"Opened {url}."

    def open_url(self, url: str) -> str:
        return self._run_async(self._open_url(url))

    # ── Page Reading ──────────────────────────────────────────────────────────
    async def _read_page(self) -> str:
        page = await self._get_current_page()
        if not page:
            return "No page is currently open."
        text = await page.evaluate("document.body.innerText")
        # Return first 2000 chars to avoid overwhelming the TTS / LLM
        if len(text) > 2000:
            return text[:2000] + "... (truncated)"
        return text

    def read_current_page(self) -> str:
        return self._run_async(self._read_page())

    # ── Scrolling & View ──────────────────────────────────────────────────────
    async def _scroll(self, direction: str) -> str:
        page = await self._get_current_page()
        if not page:
            return "No page is open to scroll."
        if direction == "down":
            await page.evaluate("window.scrollBy({ top: window.innerHeight * 0.8, behavior: 'smooth' })")
            return "Scrolled down."
        elif direction == "up":
            await page.evaluate("window.scrollBy({ top: -window.innerHeight * 0.8, behavior: 'smooth' })")
            return "Scrolled up."
        elif direction == "top":
            await page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' })")
            return "Scrolled to top."
        elif direction == "bottom":
            await page.evaluate("window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })")
            return "Scrolled to bottom."
        return "Unknown scroll direction."

    def scroll(self, direction: str) -> str:
        return self._run_async(self._scroll(direction))

    async def _toggle_fullscreen(self) -> str:
        page = await self._get_current_page()
        if not page:
            return "No page to fullscreen."
        await page.keyboard.press("F11")
        return "Toggled full screen."

    def toggle_fullscreen(self) -> str:
        return self._run_async(self._toggle_fullscreen())

    # ── Tabs ──────────────────────────────────────────────────────────────────
    async def _manage_tabs(self, action: str) -> str:
        page = await self._get_current_page()
        if not self.browser_context:
            return "Browser offline."
        pages = self.browser_context.pages
        if not pages:
            return "No tabs open."

        current_idx = pages.index(page) if page in pages else 0

        if action == "new":
            self.current_page = await self._get_new_page()
            return "Opened new tab."
        elif action == "close":
            await self.current_page.close()
            pages = self.browser_context.pages
            if pages:
                self.current_page = pages[-1]
                await self.current_page.bring_to_front()
            else:
                self.current_page = None
            return "Closed tab."
        elif action == "next":
            if pages:
                next_idx = (current_idx + 1) % len(pages)
                self.current_page = pages[next_idx]
                await self.current_page.bring_to_front()
            return "Switched to next tab."
        elif action == "prev":
            if pages:
                prev_idx = (current_idx - 1) % len(pages)
                self.current_page = pages[prev_idx]
                await self.current_page.bring_to_front()
            return "Switched to previous tab."

        return "Unknown tab action."

    def manage_tabs(self, action: str) -> str:
        return self._run_async(self._manage_tabs(action))

    async def _list_tabs(self) -> str:
        if not self.browser_context:
            return "Browser offline."
        pages = self.browser_context.pages
        if not pages:
            return "No tabs open."
        tab_titles = []
        for i, page in enumerate(pages):
            try:
                title = await page.title()
                tab_titles.append(f"[{i+1}] {title}")
            except Exception:
                pass
        return "Open browser tabs:\n" + "\n".join(tab_titles)

    def list_tabs(self) -> str:
        return self._run_async(self._list_tabs())


# Singleton instance
browser_controller = BrowserController()
