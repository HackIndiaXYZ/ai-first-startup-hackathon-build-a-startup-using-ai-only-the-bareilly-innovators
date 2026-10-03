"""
Sivi — Dynamic Hologram Engine
Fetches rich, verified visual payloads asynchronously for the React UI.
Categorizes topics into PERSON, LOCATION, TECH, GENERAL.
"""

import asyncio
import httpx
import re
import urllib.parse
import logging
from typing import Dict, Any

logger = logging.getLogger("sivi.dynamic_engine")

class DynamicEngine:
    def __init__(self):
        headers = {"User-Agent": "SiviAI/1.0 (https://github.com/alok/sivi; admin@sivi.ai) httpx/0.24.1"}
        self._http = httpx.AsyncClient(timeout=10.0, headers=headers)

    async def fetch_topic_research(self, topic: str) -> Dict[str, Any]:
        """
        Fetches high-res images and verified summaries from Wikipedia.
        Classifies the topic layout for the frontend.
        """
        try:
            # 1. Search for the exact Wikipedia page title
            search_url = "https://en.wikipedia.org/w/api.php"
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": topic,
                "format": "json",
                "utf8": 1,
                "srlimit": 1
            }
            search_resp = await self._http.get(search_url, params=search_params)
            search_data = search_resp.json()
            
            if not search_data.get("query", {}).get("search"):
                return self._fallback_card(topic)
                
            page_title = search_data["query"]["search"][0]["title"]

            # 2. Fetch the rich summary and high-res image
            summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title}"
            resp = await self._http.get(summary_url)
            
            if resp.status_code != 200:
                return self._fallback_card(topic)
                
            data = resp.json()
            
            title = data.get("title", topic)
            description = data.get("description", "").lower()
            extract = data.get("extract", "No summary available.")
            
            # Prefer original high-res image, fallback to thumbnail, then fallback to placeholder
            image_url = None
            if "originalimage" in data:
                image_url = data["originalimage"].get("source")
            elif "thumbnail" in data:
                # Hack to get higher res from thumbnail url
                thumb_url = data["thumbnail"].get("source", "")
                if thumb_url:
                    # e.g. .../thumb/1/1a/Elon_Musk.jpg/320px-Elon_Musk.jpg -> .../Elon_Musk.jpg
                    image_url = thumb_url.split("/thumb/")[0] if "/thumb/" in thumb_url else thumb_url
                    
            if not image_url:
                image_url = await self._scrape_image_fallback(topic)

            # 3. Smart Categorization Heuristics
            category = "GENERAL"
            theme_color = "#3b82f6" # Default blue
            
            person_keywords = ["born", "politician", "entrepreneur", "actor", "musician", "singer", "director", "writer", "scientist", "ceo"]
            location_keywords = ["country", "city", "river", "capital", "town", "state", "continent", "island"]
            tech_keywords = ["company", "software", "technology", "physics", "science", "algorithm", "computer", "space", "astronomy"]
            
            if any(k in description for k in person_keywords):
                category = "PERSON"
                theme_color = "#8b5cf6" # Purple
            elif any(k in description for k in location_keywords):
                category = "LOCATION"
                theme_color = "#10b981" # Emerald Green
            elif any(k in description for k in tech_keywords):
                category = "TECH"
                theme_color = "#06b6d4" # Cyan

            return {
                "title": title,
                "subtitle": data.get("description", "Analyzed by Sivi AI"),
                "summary": extract,
                "image": image_url,
                "category": category,
                "theme_color": theme_color,
                "source": "Wikipedia"
            }

        except Exception as e:
            logger.error(f"[DynamicEngine] Failed to fetch topic '{topic}': {e}")
            return self._fallback_card(topic)
            
    async def _scrape_image_fallback(self, query: str) -> str:
        """Fallback to DuckDuckGo HTML if Wikipedia has no image"""
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query + ' high resolution')}"
            resp = await self._http.get(url)
            html = resp.text
            # Basic regex to extract first image url from duckduckgo
            match = re.search(r'img class="[^"]*" src="([^"]+)"', html)
            if match:
                src = match.group(1)
                if src.startswith("//"): src = "https:" + src
                return src
        except Exception:
            pass
        return "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?q=80&w=1200&auto=format&fit=crop"

    def _fallback_card(self, topic: str) -> Dict[str, Any]:
        return {
            "title": topic.title(),
            "subtitle": "Live Research Context",
            "summary": f"Sivi is currently explaining {topic} to you. Please listen to the audio output for details.",
            "image": "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?q=80&w=1200&auto=format&fit=crop",
            "category": "GENERAL",
            "theme_color": "#6366f1",
            "source": "AI Generation"
        }

    async def close(self):
        await self._http.aclose()

dynamic_engine = DynamicEngine()
