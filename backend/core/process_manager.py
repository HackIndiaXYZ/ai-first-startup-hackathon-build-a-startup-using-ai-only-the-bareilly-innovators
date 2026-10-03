"""
Sivi — Process Manager
=======================
Handles advanced Windows process management.
Uses psutil to list, search, and kill processes.
"""

import psutil
import logging
import os
import subprocess
from typing import List, Dict, Any, Optional

logger = logging.getLogger("sivi.process_manager")

class ProcessManager:
    def get_running_processes(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns top running processes sorted by memory usage."""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                try:
                    info = proc.info
                    # Memory in MB
                    mem_mb = info['memory_info'].rss / (1024 * 1024) if info['memory_info'] else 0
                    processes.append({
                        "pid": info['pid'],
                        "name": info['name'],
                        "memory_mb": round(mem_mb, 1),
                        "cpu_percent": info['cpu_percent']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Sort by memory descending
            processes.sort(key=lambda x: x["memory_mb"], reverse=True)
            return processes[:limit]
        except Exception as e:
            logger.error(f"[ProcessManager] Error listing processes: {e}")
            return []

    def kill_process(self, process_identifier: str) -> str:
        """Kills a process by exact PID or fuzzy name match."""
        try:
            # Check if it's a PID
            if process_identifier.isdigit():
                pid = int(process_identifier)
                try:
                    p = psutil.Process(pid)
                    p_name = p.name()
                    p.terminate()
                    p.wait(timeout=3)
                    return f"Successfully killed process {p_name} (PID: {pid})."
                except psutil.NoSuchProcess:
                    return f"Process with PID {pid} not found."
            
            # Otherwise, fuzzy match by name
            process_identifier = process_identifier.lower()
            if not process_identifier.endswith(".exe"):
                process_identifier += ".exe"
                
            killed_count = 0
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == process_identifier:
                        proc.terminate()
                        killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if killed_count > 0:
                return f"Successfully killed {killed_count} instance(s) of {process_identifier}."
            else:
                # Try taskkill as fallback
                try:
                    subprocess.run(f"taskkill /f /im {process_identifier}", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return f"Force killed {process_identifier} via Windows taskkill."
                except subprocess.CalledProcessError:
                    return f"Could not find or kill process '{process_identifier}'."
                    
        except Exception as e:
            logger.error(f"[ProcessManager] Error killing {process_identifier}: {e}")
            return f"Error killing process: {e}"

process_manager = ProcessManager()
