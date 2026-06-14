import os
import json
import logging
import asyncio
from pathlib import Path
from contextlib import AsyncExitStack

# Only import mcp if available
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

logger = logging.getLogger(__name__)

class MCPServerManager:
    def __init__(self, config_path="data/mcp_servers.json"):
        self.config_path = Path(config_path)
        self.servers = {}
        self.sessions = {}
        self.exit_stacks = {}
        self._load_config()

    def _load_config(self):
        if not self.config_path.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            # Create a default empty config
            self.config_path.write_text(json.dumps({
                "servers": {
                    # Example:
                    # "sqlite": {
                    #     "command": "uvx",
                    #     "args": ["mcp-server-sqlite", "--db-path", "data/nexus.db"]
                    # }
                }
            }, indent=4))
        
        try:
            config = json.loads(self.config_path.read_text())
            self.servers = config.get("servers", {})
        except Exception as e:
            logger.error(f"Error loading MCP config: {e}")

    async def connect_server(self, server_name: str):
        """Connects to a specific MCP server and initializes its session."""
        if not HAS_MCP:
            logger.error("mcp sdk not installed.")
            return False

        if server_name not in self.servers:
            logger.error(f"Server {server_name} not found in config.")
            return False

        if server_name in self.sessions:
            return True # Already connected
            
        server_config = self.servers[server_name]
        command = server_config.get("command")
        args = server_config.get("args", [])
        env = server_config.get("env", None)
        
        # Merge environment variables if provided
        server_env = os.environ.copy()
        if env:
            server_env.update(env)

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=server_env
        )

        try:
            exit_stack = AsyncExitStack()
            stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
            read_stream, write_stream = stdio_transport
            session = await exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
            
            await session.initialize()
            
            self.sessions[server_name] = session
            self.exit_stacks[server_name] = exit_stack
            logger.info(f"Connected to MCP server: {server_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {server_name}: {e}")
            return False

    async def disconnect_server(self, server_name: str):
        if server_name in self.exit_stacks:
            await self.exit_stacks[server_name].aclose()
            del self.exit_stacks[server_name]
            del self.sessions[server_name]

    async def list_tools(self, server_name: str):
        """List all tools provided by a specific server."""
        if server_name not in self.sessions:
            connected = await self.connect_server(server_name)
            if not connected:
                return []
                
        session = self.sessions[server_name]
        try:
            tools_response = await session.list_tools()
            return tools_response.tools
        except Exception as e:
            logger.error(f"Error listing tools for {server_name}: {e}")
            return []

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict):
        """Execute a tool on a specific server."""
        if server_name not in self.sessions:
            connected = await self.connect_server(server_name)
            if not connected:
                return f"Error: Failed to connect to server {server_name}"
                
        session = self.sessions[server_name]
        try:
            result = await session.call_tool(tool_name, arguments)
            
            # Formats result text
            texts = [c.text for c in result.content if hasattr(c, 'text')]
            if texts:
                return "\n".join(texts)
            return str(result)
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on {server_name}: {e}")
            return f"Error: {e}"
