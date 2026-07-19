import os
import sys

# Ensure backend root is in path so absolute imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    print("Testing Sivi 3.0 Module Imports...")
    
    try:
        from core.database_whisperer import database_whisperer
        print("[OK] Database Whisperer loaded.")
    except Exception as e:
        print(f"[FAIL] Database Whisperer: {e}")
        
    try:
        from core.git_orchestrator import git_orchestrator
        print("[OK] Git Orchestrator loaded.")
    except Exception as e:
        print(f"[FAIL] Git Orchestrator: {e}")
        
    try:
        from core.knowledge_graph import knowledge_graph
        print("[OK] Knowledge Graph loaded.")
    except Exception as e:
        print(f"[FAIL] Knowledge Graph: {e}")
        
    try:
        from core.swarm_manager import swarm_manager
        print("[OK] Swarm Manager loaded.")
    except Exception as e:
        print(f"[FAIL] Swarm Manager: {e}")

    try:
        from core.mobile_handoff import mobile_handoff
        print("[OK] Mobile Handoff loaded.")
    except Exception as e:
        print(f"[FAIL] Mobile Handoff: {e}")

    try:
        from core.offline_fallback import offline_fallback
        print("[OK] Offline Fallback loaded.")
    except Exception as e:
        print(f"[FAIL] Offline Fallback: {e}")
        
    try:
        from core.mcp_router import mcp_router
        print("[OK] MCP Router loaded.")
    except Exception as e:
        print(f"[FAIL] MCP Router: {e}")

    print("Import tests complete.")

if __name__ == "__main__":
    test_imports()
