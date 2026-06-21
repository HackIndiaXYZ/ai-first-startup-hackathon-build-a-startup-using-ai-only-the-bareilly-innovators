import sys
import os

# Add backend directory to sys.path so we can import vision_agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from core.vision_agent import vision_agent

print("Taking screenshot and analyzing...")
res = vision_agent.find_ui_element("The 'New group' button inside the 'New chat' modal.")
print(f"Result: {res}")

