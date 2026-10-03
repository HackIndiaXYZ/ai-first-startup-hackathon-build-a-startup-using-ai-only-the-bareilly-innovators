"""
Sivi — Network Diagnostics
==========================
Handles network connectivity checks, IP retrieval, and speed testing.
"""

import socket
import logging
import subprocess
import urllib.request
from typing import Dict, Any

logger = logging.getLogger("sivi.network_diagnostics")

class NetworkDiagnostics:
    def get_network_status(self) -> str:
        """Checks overall network connectivity."""
        try:
            urllib.request.urlopen('http://google.com', timeout=3)
            return "Online — Internet connection is active."
        except Exception:
            return "Offline — No internet connection detected."

    def get_ip_address(self) -> Dict[str, str]:
        """Gets local and public IP addresses."""
        result = {"local_ip": "Unknown", "public_ip": "Unknown"}
        
        # Local IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            result["local_ip"] = s.getsockname()[0]
            s.close()
        except Exception as e:
            logger.warning(f"Failed to get local IP: {e}")
            
        # Public IP
        try:
            public_ip = urllib.request.urlopen('https://api.ipify.org', timeout=3).read().decode('utf8')
            result["public_ip"] = public_ip
        except Exception as e:
            logger.warning(f"Failed to get public IP: {e}")
            
        return result

    def ping_host(self, host: str = "google.com") -> str:
        """Pings a host and returns the latency summary."""
        try:
            # -n 4 is for Windows (send 4 packets)
            output = subprocess.check_output(f"ping -n 4 {host}", shell=True, universal_newlines=True)
            # Extract the summary line at the bottom
            lines = output.split('\n')
            summary = [line.strip() for line in lines if "Average" in line or "Lost" in line]
            return " | ".join(summary) if summary else f"Ping to {host} successful."
        except subprocess.CalledProcessError:
            return f"Failed to ping {host}. The host might be down or unreachable."

network_diagnostics = NetworkDiagnostics()
