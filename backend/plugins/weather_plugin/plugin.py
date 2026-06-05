import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base_plugin import BasePlugin
import requests


class WeatherPlugin(BasePlugin):
    def get_name(self) -> str:
        return "Weather"

    def get_commands(self) -> list[str]:
        return ["weather", "temperature", "forecast"]

    def execute(self, command: str, args: str) -> str:
        city = args.strip() or "Delhi"
        try:
            url = f"https://wttr.in/{city}?format=%C+%t+%h"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return f"Weather in {city}: {resp.text.strip()}."
            return f"Could not get weather for {city}."
        except Exception as e:
            return f"Weather error: {e}"

    def on_load(self):
        print("    Weather plugin ready.")
