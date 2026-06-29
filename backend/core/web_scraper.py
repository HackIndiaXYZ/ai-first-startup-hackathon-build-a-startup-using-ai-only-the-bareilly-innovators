import requests

class WebScraper:
    def __init__(self):
        pass

    def get_weather(self, location: str = "") -> str:
        """Fetches current weather for a specific location using wttr.in. If location is empty, uses IP."""
        loc_display = location if location else "current location"
        print(f" Fetching weather for {loc_display}...")
        try:
            # Use clean format to avoid emoji corruption: Location: Condition +Temp
            loc_path = location.strip()
            url = f"https://wttr.in/{loc_path}?format=\"%l:+%C+%t\""
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            weather_data = response.text.strip().replace('"', '')
            if "Unknown location" in weather_data:
                return f"Could not find weather for '{location}'."
                
            return weather_data
        except Exception as e:
            print(f" Weather fetch error: {e}")
            return "Failed to fetch weather information."

web_scraper = WebScraper()
