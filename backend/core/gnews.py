import os
import requests
import xml.etree.ElementTree as ET

class NewsFetcher:
    def __init__(self):
        self.api_key = os.getenv("GNEWS_API_KEY")
        self.base_url = "https://newsdata.io/api/1/news"

    def get_top_headlines_raw(self, category: str = "general", max_results: int = 5) -> list:
        # Always use Google News RSS for better national news quality
        return self._fetch_rss(category, max_results)

    def _fetch_rss(self, category: str, max_results: int) -> list:
        print(" Using Google News RSS fallback...")
        try:
            url = "https://news.google.com/rss?hl=hi&gl=IN&ceid=IN:hi"
            category_map = {
                "technology": "CAAqKAgKIiJDQkFTRXdvSkwyMHZNR1ptZHpWbUVnSnJieG9DUzFJb0FBUAE",
                "sports": "CAAqKAgKIiJDQkFTRXdvSkwyMHZNR3QwTlRFU0VnSnJieG9DUzFJb0FBUAE",
                "business": "CAAqKAgKIiJDQkFTRXdvSkwyMHZNRGx6TVdZU0VnSnJieG9DUzFJb0FBUAE",
                "entertainment": "CAAqKAgKIiJDQkFTRXdvSkwyMHZNREpxYW5RU0VnSnJieG9DUzFJb0FBUAE"
            }
            if category.lower() in category_map:
                url = f"https://news.google.com/rss/topics/{category_map[category.lower()]}?hl=hi&gl=IN&ceid=IN:hi"
            
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            articles = []
            for item in root.findall('.//item')[:max_results]:
                title = item.find('title').text if item.find('title') is not None else "No title"
                articles.append({"title": title})
            return articles
        except Exception as e:
            print(f" RSS fetch error: {e}")
            return []

    def get_top_headlines(self, category: str = "general", max_results: int = 3) -> str:
        articles = self.get_top_headlines_raw(category, max_results)
        if not articles:
             return "मुझे अभी कोई ताज़ा ख़बर नहीं मिल रही है। (No news found)"
             
        headlines = [f"ख़बर {i+1}: {a['title']}." for i, a in enumerate(articles)]
        return "यहाँ कुछ ताज़ा ख़बरें हैं। (Here are the top headlines) " + " ".join(headlines)

news_fetcher = NewsFetcher()
