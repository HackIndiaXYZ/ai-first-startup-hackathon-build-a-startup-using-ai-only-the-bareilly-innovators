"""
Sivi — MCP Router
Handles routing commands to Model Context Protocol (MCP) stdio servers.
"""

import asyncio
import logging
import json

logger = logging.getLogger("sivi.mcp_router")

class MCPRouter:
    def __init__(self):
        self.servers = {}

    def register_server(self, name: str, command: list[str]):
        """Register an MCP stdio server."""
        self.servers[name] = command

    async def call_tool(self, server_name: str, tool_name: str, args: dict) -> str:
        """Call a tool on an MCP server over stdio."""
        if server_name not in self.servers:
            return f"MCP server '{server_name}' not registered."
            
        command = self.servers[server_name]
        try:
            # We use a simple subprocess run for stdio MCP. 
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": args
                }
            }
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=json.dumps(request).encode() + b'\n')
            
            if process.returncode != 0:
                logger.error(f"MCP Server error: {stderr.decode()}")
                return f"MCP Error: {stderr.decode()}"
                
            response = json.loads(stdout.decode())
            if "error" in response:
                return f"MCP Error: {response['error']['message']}"
                
            return json.dumps(response.get("result", {}))
            
        except Exception as e:
            logger.error(f"Failed to call MCP tool: {e}")
            return f"Error executing MCP tool: {e}"

mcp_router = MCPRouter()

# Example registration
# mcp_router.register_server("filesystem", ["npx", "-y", "@modelcontextprotocol/server-filesystem", "C:\\"])
