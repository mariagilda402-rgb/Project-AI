"""
Browser Agent Tool — Integrates Playwright + VisionService for autonomous web navigation.
Inspired by ADA Local.
"""

import json
import re
import time
from typing import Any
from pathlib import Path

from src.tools.base import BaseTool

JS_MARKER_SCRIPT = """
(function() {
    // Remove marcadores antigos
    document.querySelectorAll('.vlm-marker').forEach(e => e.remove());
    
    let counter = 0;
    const elements = document.querySelectorAll('a, button, input, textarea, select, [role="button"], [role="link"], [onclick], [tabindex]:not([tabindex="-1"])');
    window.__vlm_elements = {};
    
    elements.forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0 && rect.top >= 0 && rect.left >= 0 && rect.top < window.innerHeight && rect.left < window.innerWidth) {
            const isHidden = window.getComputedStyle(el).visibility === 'hidden' || window.getComputedStyle(el).opacity === '0';
            if (isHidden) return;
            
            const marker = document.createElement('div');
            marker.className = 'vlm-marker';
            marker.innerText = counter;
            
            Object.assign(marker.style, {
                position: 'fixed',
                left: Math.max(0, rect.left) + 'px',
                top: Math.max(0, rect.top) + 'px',
                backgroundColor: 'rgba(255, 0, 0, 0.8)',
                color: 'white',
                padding: '2px 4px',
                fontSize: '12px',
                fontWeight: 'bold',
                zIndex: 2147483647, // Max z-index
                pointerEvents: 'none',
                borderRadius: '3px',
                border: '1px solid white'
            });
            
            document.body.appendChild(marker);
            
            // Desenha a borda ao redor do elemento
            const border = document.createElement('div');
            border.className = 'vlm-marker border-marker';
            Object.assign(border.style, {
                position: 'fixed',
                left: rect.left + 'px',
                top: rect.top + 'px',
                width: rect.width + 'px',
                height: rect.height + 'px',
                border: '2px dashed red',
                zIndex: 2147483646,
                pointerEvents: 'none'
            });
            document.body.appendChild(border);
            
            window.__vlm_elements[counter] = el;
            counter++;
        }
    });
    return counter;
})();
"""

BROWSER_PROMPT = """Você é um agente de navegação web autônomo.
Seu objetivo é: {goal}

A imagem em anexo mostra a tela atual do navegador. Elementos interativos estão marcados com números em caixas vermelhas.
Analise a tela e o seu objetivo. Decida QUAL A PRÓXIMA AÇÃO a tomar.

REGRAS:
- Retorne APENAS um objeto JSON válido, sem explicações, sem Markdown.
- Se o objetivo foi concluído ou não pode ser feito, retorne a ação 'done'.

FORMATOS VÁLIDOS:
1. Clicar em um elemento: {{"action": "click", "element_id": 5}}
2. Digitar texto: {{"action": "type", "element_id": 2, "text": "seu texto", "enter": true}}
3. Rolar a página: {{"action": "scroll", "direction": "down"}}  // ou "up"
4. Navegar para URL: {{"action": "navigate", "url": "https://google.com"}}
5. Concluir: {{"action": "done", "result": "Resposta final ou resumo do que foi feito"}}
"""

class BrowserAgentTool(BaseTool):
    @property
    def name(self) -> str:
        return "browser_agent"

    @property
    def description(self) -> str:
        return (
            "Navegador Web Autônomo (via Playwright + Visão). "
            "Ele abre um navegador invisível, interage com sites (clica, digita, rola a página) "
            "e lê os resultados usando Visão Computacional. Use-o para extrair informações difíceis "
            "ou interagir com sites complexos."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "O que você quer que o agente faça no navegador (ex: 'pesquisar passagem para SP', 'verificar o primeiro email')."
                },
                "start_url": {
                    "type": "string",
                    "description": "URL inicial opcional (default: https://google.com)"
                }
            },
            "required": ["goal"]
        }

    def execute(self, args: dict[str, Any], context: dict[str, Any] = None) -> str:
        goal = args.get("goal")
        if not goal:
            return "Objetivo (goal) é obrigatório."
        start_url = args.get("start_url") or "https://google.com"
        
        if not context or "vision" not in context or "llm" not in context:
            return "Contexto de LLM/Visão não fornecido. Não posso executar o Browser Agent."
            
        vision_service = context["vision"]
        llm_service = context["llm"]

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return (
                "O pacote 'playwright' não está instalado. "
                "Para ativar o Browser Agent, instale as dependências. Exemplo: pip install playwright && playwright install chromium"
            )

        print(f"[BrowserAgent] 🌐 Iniciando navegação: {goal}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            
            try:
                page.goto(start_url, wait_until="domcontentloaded")
            except Exception as e:
                browser.close()
                return f"Falha ao carregar a página inicial: {e}"

            max_steps = 15
            for step in range(max_steps):
                time.sleep(2)
                
                num_elements = page.evaluate(JS_MARKER_SCRIPT)
                print(f"[BrowserAgent] Passo {step+1}: Encontrou {num_elements} elementos clicáveis.")
                
                # Garante que as imagens não fiquem excessivamente grandes
                screenshot_bytes = page.screenshot(type="png", full_page=False)
                
                # Consulta VLM
                prompt = BROWSER_PROMPT.format(goal=goal)
                
                print(f"[BrowserAgent] Consultando modelo de visão...")
                try:
                    vlm_response = vision_service.describe_screen(prompt, image_bytes=screenshot_bytes)
                except Exception as e:
                    browser.close()
                    return f"Erro na consulta de visão: {e}"
                    
                # Remove os marcadores imediatamente para não atrapalhar clicks ou types
                page.evaluate("document.querySelectorAll('.vlm-marker').forEach(e => e.remove());")
                
                vlm_response = vlm_response.strip()
                vlm_response = re.sub(r"```(?:json)?", "", vlm_response).strip().rstrip("`").strip()
                
                print(f"[BrowserAgent] Resposta bruta do VLM:\n{vlm_response}")
                
                action_obj = None
                try:
                    action_obj = json.loads(vlm_response)
                except json.JSONDecodeError:
                    match = re.search(r"\{.*\}", vlm_response, re.DOTALL)
                    if match:
                        try:
                            action_obj = json.loads(match.group(0))
                        except:
                            pass
                
                if not action_obj or not isinstance(action_obj, dict):
                    print("[BrowserAgent] ⚠️ VLM não retornou JSON válido.")
                    continue
                
                action = action_obj.get("action")
                print(f"[BrowserAgent] 🤖 Ação: {action}")
                
                try:
                    if action == "done":
                        result = action_obj.get("result", "Nenhuma resposta final fornecida.")
                        browser.close()
                        return f"Navegação concluída: {result}"
                        
                    elif action == "click":
                        el_id = action_obj.get("element_id")
                        if el_id is not None:
                            page.evaluate(f"if (window.__vlm_elements[{el_id}]) window.__vlm_elements[{el_id}].click();")
                        else:
                            print("[BrowserAgent] ⚠️ ID do elemento não fornecido no click.")
                            
                    elif action == "type":
                        el_id = action_obj.get("element_id")
                        text = action_obj.get("text", "")
                        enter = action_obj.get("enter", False)
                        if el_id is not None:
                            page.evaluate(f"if (window.__vlm_elements[{el_id}]) window.__vlm_elements[{el_id}].focus();")
                            page.keyboard.type(text)
                            if enter:
                                page.keyboard.press("Enter")
                        else:
                            print("[BrowserAgent] ⚠️ ID do elemento não fornecido no type.")
                            
                    elif action == "scroll":
                        direction = action_obj.get("direction", "down")
                        if direction == "down":
                            page.mouse.wheel(0, 800)
                        else:
                            page.mouse.wheel(0, -800)
                            
                    elif action == "navigate":
                        url = action_obj.get("url")
                        if url:
                            page.goto(url, wait_until="domcontentloaded")
                            
                    else:
                        print(f"[BrowserAgent] ⚠️ Ação desconhecida: {action}")
                
                except Exception as e:
                    print(f"[BrowserAgent] ⚠️ Erro ao executar ação '{action}': {e}")
                    
            browser.close()
            return "Navegação interrompida. Máximo de passos atingido (15)."
