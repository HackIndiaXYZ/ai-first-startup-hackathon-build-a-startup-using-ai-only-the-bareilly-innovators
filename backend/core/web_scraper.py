import requests

class WebScraper:
    def __init__(self):
        pass

    def get_weather(self, location: str) -> str:
        """Fetches current weather for a specific location using wttr.in"""
        print(f" Fetching weather for {location}...")
        try:
            # wttr.in returns a plain text string when format=3 (Location: Condition + Temp)
            # format=4 is Location: Condition Temperature Wind
            url = f"https://wttr.in/{location}?format=4"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            weather_data = response.text.strip()
            if "Unknown location" in weather_data:
                return f"Could not find weather for '{location}'."
                
            return f"Weather update: {weather_data}"
        except Exception as e:
            print(f" Weather fetch error: {e}")
            return "Failed to fetch weather information."

web_scraper = WebScraper()
