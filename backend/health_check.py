import os
import sys

sys.path.insert(0, r"c:\Users\Acer\Desktop\alok\sivi\backend\core")

print("Initializing Sivi Core Modules for Health Check...\n" + "="*50)

# Import the controller to trigger all module initializations
try:
    from sivi_controller import controller
    print("\n[OK] Controller Initialized Successfully.\n")
    
    status = controller.get_module_status()
    print("Module Status Report:")
    print("-" * 50)
    for mod in status:
        icon = "[ACTIVE]" if mod["status"] == "active" else "[FAILED]"
        if mod["status"] == "no-key":
            icon = "[NO-KEY]"
        elif mod["status"] == "not-configured":
            icon = "[NOT-CONFIGURED]"
        print(f"{icon} {mod['name']:<20} | Status: {mod['status']}")
        
    print("-" * 50)
    
except Exception as e:
    import traceback
    print("\n[FAIL] FAILED TO INITIALIZE MODULES:")
    traceback.print_exc()

