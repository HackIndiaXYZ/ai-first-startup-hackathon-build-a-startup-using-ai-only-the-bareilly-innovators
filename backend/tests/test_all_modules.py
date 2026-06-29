import requests
import time

API_URL = "http://localhost:8000"

def test_command(module_name, command):
    print(f"\n[{module_name}] Testing: '{command}'")
    try:
        response = requests.post(f"{API_URL}/command", json={"command": command})
        if response.status_code == 200:
            data = response.json()
            print(f" Response: {data.get('response')}")
        else:
            print(f" HTTP Error: {response.status_code}")
    except Exception as e:
        print(f" Connection Error: {e}")
    time.sleep(1) # Small delay between requests

def run_all_tests():
    print(" Starting SIVI System Tests...\n")
    
    # 1. App Launcher
    test_command("App Launcher", "open calculator")
    test_command("App Launcher", "search Python API")
    
    # 2. System Controller
    test_command("System Controller", "volume up by 10")
    test_command("System Controller", "mute")
    
    # 3. Window Manager
    test_command("Window Manager", "minimize calculator")
    
    # 4. Keyboard Controller
    test_command("Keyboard", "type Hello SIVI")
    
    # 5. News
    test_command("News", "what's the news")
    
    # 6. Medical AI
    test_command("Medical AI", "I have a headache")
    
    # 7. File Manager
    test_command("File Manager", "create file test_sivi.txt")
    test_command("File Manager", "list files in Desktop")
    
    # 8. Plugin System
    test_command("Plugin System", "list plugins")
    test_command("Calculator Plugin", "calculate 15 * 3")
    test_command("Weather Plugin", "weather Mumbai")

    # 9. Hindi Translation
    test_command("Hindi Voice", "kya news hai")

if __name__ == "__main__":
    run_all_tests()
