import os
import sys
import asyncio
from dotenv import load_dotenv

# Load env
load_dotenv(os.path.join(r"c:\Users\Acer\Desktop\alok\sivi\backend", ".env"))

# Import mobile handoff
sys.path.insert(0, r"c:\Users\Acer\Desktop\alok\sivi\backend\core")
from mobile_handoff import mobile_handoff

async def test_handoff():
    print("Is configured:", mobile_handoff.is_configured())
    res = await mobile_handoff.send_text_async("Hello Boss! Ye Sivi ki taraf se ek test message hai. Handoff bilkul theek chal raha hai! 🚀")
    print("Send result:", res)
    await mobile_handoff.close()

if __name__ == "__main__":
    asyncio.run(test_handoff())
