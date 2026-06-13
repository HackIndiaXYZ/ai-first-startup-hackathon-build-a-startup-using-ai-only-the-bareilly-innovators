import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.basicConfig(level=logging.ERROR)

def test_all():
    results = []
    
    # 1. Test Command Parser
    try:
        from command_parser import parse_command
        cmd1 = parse_command("open chrome")
        cmd2 = parse_command("play music")
        cmd3 = parse_command("remember I like pizza")
        if cmd1.type == "OPEN_APP" and cmd2.type == "MEDIA_PLAY_PAUSE" and cmd3.type == "REMEMBER":
            results.append("âœ… Command Parser: SUCCESS")
        else:
            results.append("âŒ Command Parser: FAILED")
    except Exception as e:
        results.append(f"âŒ Command Parser: ERROR {e}")

    # 2. Test Memory Vault
    try:
        from memory_vault import memory_vault
        memory_vault.remember("Test Memory")
        ctx = memory_vault.get_memory_context()
        if "Test Memory" in ctx:
            results.append("âœ… Memory Vault: SUCCESS")
        else:
            results.append("âŒ Memory Vault: FAILED")
    except Exception as e:
        results.append(f"âŒ Memory Vault: ERROR {e}")

    # 3. Test System Monitor
    try:
        from system_monitor import system_monitor
        status = system_monitor.get_system_status()
        if "CPU usage" in status and "RAM" in status:
            results.append("âœ… System Monitor: SUCCESS")
        else:
            results.append("âŒ System Monitor: FAILED")
    except Exception as e:
        results.append(f"âŒ System Monitor: ERROR {e}")

    # 4. Test Window Reader
    try:
        from window_reader import window_reader
        windows = window_reader.get_active_windows()
        if isinstance(windows, str) and len(windows) > 5:
            results.append("âœ… Window Reader: SUCCESS")
        else:
            results.append("âŒ Window Reader: FAILED")
    except Exception as e:
        results.append(f"âŒ Window Reader: ERROR {e}")

    # 5. Test Mouse & Keyboard Controller
    try:
        from mouse_controller import mouse_controller
        from keyboard_controller import keyboard_controller
        mouse_controller.move_by(0, 0)
        keyboard_controller.press_key('shift')
        results.append("âœ… Hardware Controllers (Mouse/Keyboard): SUCCESS")
    except Exception as e:
        results.append(f"âŒ Hardware Controllers: ERROR {e}")

    # 6. Test System Controller (Clipboard & Media)
    try:
        from system_controller import system_controller
        system_controller.write_clipboard("Test Sivi")
        clip = system_controller.read_clipboard()
        if clip == "Test Sivi":
            results.append("âœ… System Controller (Clipboard): SUCCESS")
        else:
            results.append("âŒ System Controller (Clipboard): FAILED")
    except Exception as e:
        results.append(f"âŒ System Controller: ERROR {e}")

    # 7. Test Notification Monitor (Async)
    try:
        from notification_monitor import notification_monitor
        loop = asyncio.get_event_loop() if asyncio.get_event_loop().is_running() else asyncio.new_event_loop()
        alerts = loop.run_until_complete(notification_monitor._get_new_notifications_async())
        results.append(f"âœ… Notification Monitor: SUCCESS (Found {len(alerts)} alerts)")
    except Exception as e:
        results.append(f"âŒ Notification Monitor: ERROR {e}")

    print("\n--- DEEP MODULE TEST REPORT ---")
    for r in results:
        print(r)

if __name__ == "__main__":
    test_all()
