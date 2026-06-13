import os
import requests

class NewsFetcher:
    def __init__(self):
        self.api_key = os.getenv("GNEWS_API_KEY")
        self.base_url = "https://gnews.io/api/v4/top-headlines"

    def get_top_headlines(self, category: str = "general", max_results: int = 3) -> str:
        if not self.api_key:
            return "GNews API key is missing. Cannot fetch news."
            
        print(f" Fetching {category} news...")
        params = {
            "category": category,
            "lang": "en",
            "country": "in",
            "max": max_results,
            "apikey": self.api_key
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            articles = data.get("articles", [])
            if not articles:
                return "Could not find any latest news right now."
                
            headlines = [f"Headline {i+1}: {a['title']}." for i, a in enumerate(articles)]
            return " Here are the top headlines. " + " ".join(headlines)
            
        except Exception as e:
            print(f" News API error: {e}")
            return "Failed to fetch news from the server."

news_fetcher = NewsFetcher()
