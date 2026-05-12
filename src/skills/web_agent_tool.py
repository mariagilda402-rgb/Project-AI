from src.tools.base import BaseTool
from typing import Any
import os
import time
import asyncio
import base64
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from google import genai
from google.genai import types

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900
MODEL_ID = "gemini-2.5-computer-use-preview-10-2025"

class WebAgent:
    def __init__(self):
        self.client = genai.Client(api_key=API_KEY)
        self.browser = None
        self.context = None
        self.page = None

    def denormalize_x(self, x: int, width: int) -> int:
        return int((x / 1000) * width)

    def denormalize_y(self, y: int, height: int) -> int:
        return int((y / 1000) * height)

    async def execute_function_calls(self, function_calls):
        results = []
        for call in function_calls:
            call_id = getattr(call, 'id', None)
            fn_name = call.name
            args = call.args
            
            result_data = {}
            try:
                if fn_name == "open_web_browser": pass 
                elif fn_name == "navigate": await self.page.goto(args["url"])
                elif fn_name == "go_back": await self.page.go_back()
                elif fn_name == "go_forward": await self.page.go_forward()
                elif fn_name == "search": await self.page.goto("https://www.google.com")
                elif fn_name == "wait_5_seconds": await asyncio.sleep(5)
                elif fn_name == "click_at":
                    x = self.denormalize_x(args["x"], SCREEN_WIDTH)
                    y = self.denormalize_y(args["y"], SCREEN_HEIGHT)
                    await self.page.mouse.click(x, y)
                elif fn_name == "type_text_at":
                    x = self.denormalize_x(args["x"], SCREEN_WIDTH)
                    y = self.denormalize_y(args["y"], SCREEN_HEIGHT)
                    text = args["text"]
                    press_enter = args.get("press_enter", False)
                    clear_before = args.get("clear_before_typing", True)
                    await self.page.mouse.click(x, y)
                    if clear_before:
                        await self.page.keyboard.press("Control+A") 
                        await self.page.keyboard.press("Backspace")
                    await self.page.keyboard.type(text)
                    if press_enter: await self.page.keyboard.press("Enter")
                elif fn_name == "hover_at":
                    x = self.denormalize_x(args["x"], SCREEN_WIDTH)
                    y = self.denormalize_y(args["y"], SCREEN_HEIGHT)
                    await self.page.mouse.move(x, y)
                elif fn_name == "drag_and_drop":
                    start_x = self.denormalize_x(args["x"], SCREEN_WIDTH)
                    start_y = self.denormalize_y(args["y"], SCREEN_HEIGHT)
                    end_x = self.denormalize_x(args["destination_x"], SCREEN_WIDTH)
                    end_y = self.denormalize_y(args["destination_y"], SCREEN_HEIGHT)
                    await self.page.mouse.move(start_x, start_y)
                    await self.page.mouse.down()
                    await self.page.mouse.move(end_x, end_y)
                    await self.page.mouse.up()
                elif fn_name == "key_combination":
                    key_comb = args.get("keys")
                    await self.page.keyboard.press(key_comb)
                elif fn_name in ["scroll_document", "scroll_at"]:
                    magnitude = args.get("magnitude", 800)
                    direction = args.get("direction", "down")
                    if fn_name == "scroll_at":
                        x = self.denormalize_x(args["x"], SCREEN_WIDTH)
                        y = self.denormalize_y(args["y"], SCREEN_HEIGHT)
                        await self.page.mouse.move(x, y)
                    dx, dy = 0, 0
                    if direction == "down": dy = magnitude
                    elif direction == "up": dy = -magnitude
                    elif direction == "right": dx = magnitude
                    elif direction == "left": dx = -magnitude
                    await self.page.mouse.wheel(dx, dy)
                await asyncio.sleep(1)
            except Exception as e:
                result_data = {"error": str(e)}

            results.append((call_id, fn_name, result_data))
        return results

    async def get_function_responses(self, results):
        screenshot_bytes = await self.page.screenshot(type="png") 
        current_url = self.page.url
        function_responses = []
        for call_id, name, result in results:
            response_data = {"url": current_url}
            response_data.update(result)
            function_responses.append(
                types.FunctionResponse(
                    name=name, id=call_id, response=response_data,
                    parts=[types.FunctionResponsePart(
                        inline_data=types.FunctionResponseBlob(
                            mime_type="image/png", data=screenshot_bytes
                        )
                    )]
                )
            )
        return function_responses, screenshot_bytes

    async def run_task(self, prompt: str) -> str:
        final_response = "Tarefa concluída na web."
        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=False) 
            self.context = await self.browser.new_context(
                viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.page = await self.context.new_page()
            await self.page.goto("https://www.google.com")

            config = types.GenerateContentConfig(
                tools=[types.Tool(computer_use=types.ComputerUse(environment=types.Environment.ENVIRONMENT_BROWSER))],
                thinking_config=types.ThinkingConfig(include_thoughts=True) 
            )

            initial_screenshot = await self.page.screenshot(type="png")
            chat_history = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(prompt),
                        types.Part.from_bytes(data=initial_screenshot, mime_type="image/png")
                    ]
                )
            ]

            MAX_TURNS = 20
            for turn in range(MAX_TURNS):
                try:
                    response = await self.client.aio.models.generate_content(
                        model=MODEL_ID, contents=chat_history, config=config
                    )
                except Exception as e:
                    return f"Erro de API ao navegar: {e}"
                
                if not response.candidates: break
                
                candidate = response.candidates[0]
                model_content = candidate.content
                chat_history.append(model_content)

                has_tool_use = False
                agent_text = ""
                
                for part in model_content.parts:
                    if part.text: agent_text = part.text
                    if part.function_call: has_tool_use = True
                
                if agent_text: final_response = agent_text

                function_calls = [part.function_call for part in model_content.parts if part.function_call]
                
                if not function_calls:
                    if not has_tool_use: break
                    else: continue

                results = await self.execute_function_calls(function_calls)
                function_responses, screenshot_bytes = await self.get_function_responses(results)
                
                response_parts = [types.Part(function_response=fr) for fr in function_responses]
                chat_history.append(types.Content(role="user", parts=response_parts))

            await self.browser.close()
            return final_response

class WebBrowserTool(BaseTool):
    @property
    def name(self) -> str:
        return "browse_web_agent"
        
    @property
    def description(self) -> str:
        return "Abre o navegador e navega pela internet de forma autônoma para realizar uma tarefa. Use esta ferramenta quando o usuário pedir para entrar num site, pesquisar algo na web ou interagir visualmente com um site."
        
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "A tarefa detalhada para o agente web realizar (ex: 'Vá no google, busque por noticias de hoje, entre na primeira e faça um resumo')."
                }
            },
            "required": ["task"]
        }
        
    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        task = args.get("task")
        if not task:
            return "Erro: Tarefa não especificada."
            
        try:
            agent = WebAgent()
            # Retorna a string do resultado da tarefa assíncrona
            return asyncio.run(agent.run_task(task))
        except Exception as e:
            return f"Falha ao executar o web_agent: {e}"
