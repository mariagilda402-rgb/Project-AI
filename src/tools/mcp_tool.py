import json
import asyncio
from typing import Any, Callable
from google.generativeai import types
from src.tools.base import BaseTool
from src.services.mcp_client import MCPServerManager

class MCPTool(BaseTool):
    def __init__(self, mcp_manager: MCPServerManager):
        super().__init__()
        self.mcp_manager = mcp_manager
        
    @property
    def declarations(self) -> list[types.FunctionDeclaration]:
        return [
            types.FunctionDeclaration(
                name="mcp_call",
                description=(
                    "Chama uma ferramenta de um servidor MCP (Model Context Protocol). "
                    "Use isso para interagir com o sistema de arquivos local, buscas avançadas e outros recursos configurados via MCP."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "server": types.Schema(
                            type=types.Type.STRING,
                            description="Nome do servidor MCP (ex: 'sqlite', 'filesystem')."
                        ),
                        "tool": types.Schema(
                            type=types.Type.STRING,
                            description="Nome da ferramenta no servidor MCP."
                        ),
                        "arguments": types.Schema(
                            type=types.Type.STRING,
                            description="Argumentos da ferramenta em formato JSON string."
                        )
                    },
                    required=["server", "tool", "arguments"]
                ),
            ),
            types.FunctionDeclaration(
                name="mcp_list_tools",
                description="Lista todas as ferramentas disponíveis em um servidor MCP configurado.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "server": types.Schema(
                            type=types.Type.STRING,
                            description="Nome do servidor MCP."
                        )
                    },
                    required=["server"]
                ),
            ),
        ]

    def get_handlers(self) -> dict[str, Callable[..., Any]]:
        return {
            "mcp_call": self.handle_mcp_call,
            "mcp_list_tools": self.handle_mcp_list_tools
        }

    def handle_mcp_call(self, server: str, tool: str, arguments: str) -> str:
        try:
            args_dict = json.loads(arguments)
        except json.JSONDecodeError:
            return "Erro: 'arguments' deve ser uma string JSON válida."

        # The orchestrator calls this synchronously, so we run the async method
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            # If we are somehow inside an event loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, self.mcp_manager.call_tool(server, tool, args_dict)).result()
        else:
            result = loop.run_until_complete(self.mcp_manager.call_tool(server, tool, args_dict))
            
        return result

    def handle_mcp_list_tools(self, server: str) -> str:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                tools = pool.submit(asyncio.run, self.mcp_manager.list_tools(server)).result()
        else:
            tools = loop.run_until_complete(self.mcp_manager.list_tools(server))
            
        if not tools:
            return f"Nenhuma ferramenta encontrada no servidor '{server}' ou servidor não conectado."
            
        result = []
        for t in tools:
            # Format nicely
            schema = getattr(t, 'inputSchema', {})
            result.append(f"- {t.name}: {t.description}\n  Schema: {json.dumps(schema)}")
        
        return "\n".join(result)
