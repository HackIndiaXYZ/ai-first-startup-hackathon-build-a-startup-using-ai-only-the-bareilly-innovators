"""
Sivi — Weather Plugin
Fetches real-time weather information using an open API.
"""

import logging
import httpx
from plugins.base_plugin import SiviPlugin

logger = logging.getLogger("sivi.plugins.weather")

class WeatherPlugin(SiviPlugin):
    @property
    def name(self) -> str:
        return "weather_plugin"
        
    @property
    def description(self) -> str:
        return "Fetches real-time weather for a given city."
        
    def get_supported_commands(self) -> list[str]:
        return [
            r"weather in (?P<city>.*)",
            r"what's the weather in (?P<city>.*)"
        ]
        
    def execute(self, command: str, **kwargs) -> str:
        city = kwargs.get("city")
        if not city:
            return "Please specify a city."
            
        try:
            # Using wttr.in for a simple text-based weather API
            url = f"https://wttr.in/{city}?format=j1"
            import requests
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                temp = data['current_condition'][0]['temp_C']
                desc = data['current_condition'][0]['weatherDesc'][0]['value']
                return f"The weather in {city} is {temp}°C and {desc}."
            else:
                return f"Could not fetch weather for {city} right now."
        except Exception as e:
            logger.error(f"Weather plugin error: {e}")
            return f"An error occurred while fetching the weather for {city}."
