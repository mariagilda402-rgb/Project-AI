from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Callable

from google import genai
from google.genai import types
from openai import OpenAI
from src.services.rate_limit import SlidingWindowRateLimiter

logger = logging.getLogger(__name__)

# Palavras/codigos comuns em falhas transitórias do Gemini (sobrecarga, rate limit).
_TRANSIENT_HINTS = (
    "503",
    "429",
    "UNAVAILABLE",
    "RESOURCE_EXHAUSTED",
    "HIGH DEMAND",
    "TOO MANY REQUESTS",
    "DEADLINE EXCEEDED",
)

# Erros 400 da Groq quando o modelo gera function calls malformadas — não adianta retries.
_TOOL_USE_FAILED_HINTS = ("tool_use_failed", "failed_generation", "failed to call a function")


def gemini_error_looks_transient(exc: BaseException) -> bool:
    text = str(exc).upper()
    return any(h in text for h in _TRANSIENT_HINTS)


def _is_tool_use_failed(exc: BaseException) -> bool:
    """Erro 400 da Groq: modelo gerou tool call malformado. Retry não resolve."""
    text = str(exc).lower()
    return any(h in text for h in _TOOL_USE_FAILED_HINTS)


def sleep_before_gemini_retry(exc: BaseException, failed_attempt: int) -> None:
    """Pausa entre tentativas; mais longa em sobrecarga (503) / rate limit."""
    if gemini_error_looks_transient(exc):
        delay = min(120.0, 12.0 * (2 ** (failed_attempt - 1)))
    else:
        delay = min(8.0, 2 ** (failed_attempt - 1))
    logger.debug("Gemini: aguardando %.1fs antes da proxima tentativa.", delay)
    time.sleep(delay)


class LLMService:
    def __init__(
        self,
        gemini_api_key: str,
        gemini_model: str,
        openrouter_api_key: str = "",
        openrouter_model: str = "",
        nvidia_api_key: str = "",
        nvidia_model: str = "",
        groq_api_key: str = "",
        groq_model: str = "",
        gemini_max_rpm: int = 10,
        gemini_retry_attempts: int = 3,
        primary_llm_provider: str = "gemini",
        http_timeout: float = 180.0,
        fallback_gemini: bool = False,
    ) -> None:
        self.primary_llm_provider = primary_llm_provider
        self.fallback_gemini = fallback_gemini
        self._http_timeout = max(30.0, min(600.0, http_timeout))
        self.gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None
        self.gemini_model = gemini_model

        self.openrouter_client = (
            OpenAI(
                api_key=openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=self._http_timeout,
            )
            if openrouter_api_key
            else None
        )
        self.openrouter_model = openrouter_model

        self.nvidia_client = (
            OpenAI(
                api_key=nvidia_api_key,
                base_url="https://integrate.api.nvidia.com/v1",
                timeout=self._http_timeout,
            )
            if nvidia_api_key
            else None
        )
        self.nvidia_model = nvidia_model

        self.groq_client = (
            OpenAI(
                api_key=groq_api_key,
                base_url="https://api.groq.com/openai/v1",
                timeout=self._http_timeout,
            )
            if groq_api_key
            else None
        )
        self.groq_model = (groq_model or "").strip()

        self.gemini_limiter = SlidingWindowRateLimiter(max_requests_per_minute=gemini_max_rpm)
        self.gemini_retry_attempts = max(1, gemini_retry_attempts)

    def wants_gemini_native_tools(self) -> bool:
        """Function calling nativo do Gemini só quando ele é o provedor principal do chat."""
        return self.primary_llm_provider == "gemini" and self.gemini_client is not None

    def wants_nvidia_native_tools(self) -> bool:
        """Tools no formato OpenAI em https://integrate.api.nvidia.com/v1/chat/completions"""
        return (
            self.primary_llm_provider == "nvidia"
            and self.nvidia_client is not None
            and bool(self.nvidia_model)
        )

    def wants_groq_native_tools(self) -> bool:
        """
        Desativado temporariamente para o Groq devido a um bug no modelo llama-3.3-70b-versatile
        onde ele gera tool calls malformados (código 400, tool_use_failed).
        Força o uso do fallback de marcadores ([tool:nome:arg]) que é muito mais estável.
        """
        return False

    def _chat_provider_order(self, skip_gemini: bool) -> list[str]:
        all_p = ["gemini", "openrouter", "nvidia", "groq"]
        primary = self.primary_llm_provider
        if primary not in all_p:
            primary = "gemini"
        order = [primary] + [p for p in all_p if p != primary]
        if skip_gemini:
            order = [p for p in order if p != "gemini"]
        elif primary != "gemini" and not self.fallback_gemini:
            # Evita gastar cota Gemini quando o usuario escolheu outro provedor principal.
            order = [p for p in order if p != "gemini"]
        return order

    def _sleep_before_gemini_retry(self, exc: BaseException, failed_attempt: int) -> None:
        sleep_before_gemini_retry(exc, failed_attempt)

    def chat_with_functions(
        self,
        system_instruction: str,
        messages: list[dict[str, str]],
        tools: list[types.Tool],
        on_function_call: Callable[[str, dict[str, Any]], str],
        max_rounds: int = 8,
        force_tool: bool = False,
    ) -> str:
        """
        Loop Gemini com function calling nativo. Executa callbacks locais e devolve texto final.
        """
        if not self.gemini_client or not tools:
            return ""
        contents = self._messages_to_gemini_contents(messages)
        if not contents:
            return ""
            
        mode = types.FunctionCallingConfigMode.ANY if force_tool else types.FunctionCallingConfigMode.AUTO
        
        config = types.GenerateContentConfig(
            system_instruction=system_instruction.strip(),
            tools=tools,
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode=mode,
                )
            ),
        )
        last_text = ""
        for _ in range(max_rounds):
            resp = self._generate_gemini_with_config(contents, config)
            if not resp or not resp.candidates:
                break
            cand = resp.candidates[0]
            if not cand.content or not cand.content.parts:
                break
            parts = list(cand.content.parts)
            contents.append(cand.content)
            function_calls: list[types.FunctionCall] = []
            text_chunks: list[str] = []
            for part in parts:
                if part.function_call:
                    function_calls.append(part.function_call)
                if part.text:
                    text_chunks.append(part.text)
            if function_calls:
                fr_parts: list[types.Part] = []
                for fc in function_calls:
                    args = self._normalize_function_args(fc.args)
                    print(f"\n[🛠️ GEMINI TOOL CALL] {fc.name}({args})")
                    try:
                        out = on_function_call(fc.name or "", args)
                    except Exception as exc:
                        logger.warning("Tool %s falhou: %s", fc.name, exc)
                        out = f"Erro ao executar {fc.name}: {exc}"
                    fr_parts.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                id=fc.id,
                                name=fc.name,
                                response={"output": out},
                            )
                        )
                    )
                contents.append(types.Content(role="user", parts=fr_parts))
                continue
            last_text = "".join(text_chunks).strip()
            break
        else:
            if not last_text:
                last_text = (
                    "Limite de rodadas com ferramentas atingido. "
                    "Tente simplificar o pedido."
                )
        return last_text

    def chat_with_openai_tools(
        self,
        system_instruction: str,
        messages: list[dict[str, str]],
        tools: list[dict],
        client: OpenAI,
        model: str,
        on_function_call: Callable[[str, dict[str, Any]], str],
        max_rounds: int = 8,
    ) -> str:
        """
        Function calling compativel com OpenAI (usado na API NVIDIA NIM).
        Ver: https://docs.nvidia.com/nim/vision-language-models/latest/function-calling.html
        """
        if not client or not model.strip() or not tools:
            return ""
        api_messages: list[Any] = [
            {"role": "system", "content": system_instruction.strip()},
        ]
        for m in messages:
            role = m.get("role", "user")
            if role == "system":
                continue
            body = (m.get("content") or "").strip()
            if not body:
                continue
            api_messages.append({"role": role, "content": body})

        last_text = ""
        for _ in range(max_rounds):
            resp = None
            for attempt in range(1, self.gemini_retry_attempts + 1):
                try:
                    self.gemini_limiter.wait_for_slot()
                    resp = client.chat.completions.create(
                        model=model,
                        messages=api_messages,
                        tools=tools,
                        tool_choice="auto",
                    )
                    break
                except Exception as exc:
                    logger.warning(
                        "LLM tools OpenAI-compat (tentativa %s/%s): %s",
                        attempt,
                        self.gemini_retry_attempts,
                        exc,
                    )
                    # tool_use_failed (400): modelo gerou call malformado — retry não ajuda.
                    if _is_tool_use_failed(exc):
                        logger.info("tool_use_failed detectado — abortando function calling.")
                        return last_text
                    if attempt == self.gemini_retry_attempts:
                        return last_text
                    sleep_before_gemini_retry(exc, attempt)
            if not resp or not resp.choices:
                break
            msg = resp.choices[0].message
            tool_calls = msg.tool_calls or []
            if tool_calls:
                asst: dict[str, Any] = {
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments or "{}",
                            },
                        }
                        for tc in tool_calls
                    ],
                }
                api_messages.append(asst)
                for tc in tool_calls:
                    raw_args = tc.function.arguments or "{}"
                    try:
                        args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        args = {}
                    if not isinstance(args, dict):
                        args = {}
                    print(f"\n[🛠️ OPENAI/GROQ TOOL CALL] {tc.function.name}({args})")
                    try:
                        out = on_function_call(tc.function.name, args)
                    except Exception as exc:
                        logger.warning("Tool %s falhou: %s", tc.function.name, exc)
                        out = f"Erro ao executar {tc.function.name}: {exc}"
                    api_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": str(out),
                        }
                    )
                continue
            last_text = (msg.content or "").strip()
            break
        else:
            if not last_text:
                last_text = (
                    "Limite de rodadas com ferramentas atingido. "
                    "Tente simplificar o pedido."
                )
        return last_text

    def _generate_gemini_with_config(
        self,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> types.GenerateContentResponse | None:
        client = self.gemini_client
        if not client:
            return None
        for attempt in range(1, self.gemini_retry_attempts + 1):
            try:
                self.gemini_limiter.wait_for_slot()
                return client.models.generate_content(
                    model=self.gemini_model,
                    contents=contents,
                    config=config,
                )
            except Exception as exc:
                logger.warning(
                    "Gemini (tools) falhou (tentativa %s/%s): %s",
                    attempt,
                    self.gemini_retry_attempts,
                    exc,
                )
                if attempt == self.gemini_retry_attempts:
                    return None
                self._sleep_before_gemini_retry(exc, attempt)
        return None

    @staticmethod
    def _normalize_function_args(raw: Any) -> dict[str, Any]:
        if raw is None:
            return {}
        if isinstance(raw, dict):
            return dict(raw)
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return dict(parsed) if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    @staticmethod
    def _merge_messages_for_openai_chat(
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """
        Uma unica mensagem `system` no inicio (exigencia Groq/OpenAI).
        Qualquer outro `system` no historico (ex.: preferencias) entra fundido no bloco system.
        """
        sys_parts: list[str] = []
        if (system_prompt or "").strip():
            sys_parts.append(system_prompt.strip())
        rest: list[dict[str, str]] = []
        for msg in messages:
            role = (msg.get("role") or "user").strip().lower()
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            if role == "system":
                sys_parts.append(content)
            elif role in ("user", "assistant"):
                rest.append({"role": role, "content": content})
            else:
                rest.append({"role": "user", "content": f"[{role}]\n{content}"})
        merged = "\n\n".join(s for s in sys_parts if s)
        if not merged:
            merged = "Ajude o usuario."
        return [{"role": "system", "content": merged}, *rest]

    @staticmethod
    def _messages_to_gemini_contents(
        messages: list[dict[str, str]],
    ) -> list[types.Content]:
        out: list[types.Content] = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                continue
            gemini_role = "model" if role == "assistant" else "user"
            body = (msg.get("content") or "").strip()
            if not body:
                continue
            out.append(
                types.Content(role=gemini_role, parts=[types.Part(text=body)])
            )
        return out

    def chat(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        *,
        skip_gemini: bool = False,
    ) -> str:
        has_backend = bool(
            self.gemini_client
            or self.openrouter_client
            or self.nvidia_client
            or self.groq_client
        )
        order = self._chat_provider_order(skip_gemini)
        if skip_gemini and (
            self.openrouter_client or self.nvidia_client or self.groq_client
        ):
            logger.debug(
                "Chat: ordem %s (Gemini omitido nesta rodada).",
                order,
            )
        for provider in order:
            if provider == "gemini":
                result = self._try_gemini(system_prompt, messages)
            elif provider == "openrouter":
                result = self._try_openrouter(system_prompt, messages)
            elif provider == "groq":
                result = self._try_groq(system_prompt, messages)
            else:
                result = self._try_nvidia(system_prompt, messages)
            if result:
                return result

        if not has_backend:
            return (
                "Nenhuma LLM cloud configurada. Defina LLM_PROVIDER e a chave do provedor "
                "(GEMINI_API_KEY, OPENROUTER_API_KEY, NVIDIA_API_KEY ou GROQ_API_KEY)."
            )
        return (
            "As LLMs configuradas falharam (rede, cota, modelo ou erro da API). "
            "Veja mensagens [llm] no terminal ou defina logging.basicConfig(level=logging.WARNING)."
        )

    def _try_gemini(self, system_prompt: str, messages: list[dict[str, str]]) -> str:
        if not self.gemini_client:
            return ""
        prompt = self._to_single_prompt(system_prompt, messages)
        for attempt in range(1, self.gemini_retry_attempts + 1):
            try:
                self.gemini_limiter.wait_for_slot()
                resp = self.gemini_client.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt,
                )
                return (resp.text or "").strip()
            except Exception as exc:
                logger.warning(
                    "Gemini falhou (tentativa %s/%s): %s",
                    attempt,
                    self.gemini_retry_attempts,
                    exc,
                )
                if attempt == self.gemini_retry_attempts:
                    return ""
                self._sleep_before_gemini_retry(exc, attempt)
        return ""

    def classify_intent(self, user_text: str) -> str:
        """
        Classifica em uma chamada curta: vision | action | chat.
        Usado quando nenhuma palavra-chave obvia casou (opcional no orquestrador).
        """
        if not self.gemini_client:
            return "chat"
        prompt = (
            "Classifique a mensagem do usuario em exatamente UMA opcao.\n"
            '- "vision": quer que voce VEJA/analise/leia/descreva o que esta na TELA, '
            "monitor, janela, site, video do YouTube aberto, erro na tela, \"o que aparece aqui\".\n"
            '- "action": quer EXECUTAR algo no PC ou registrar dados: abrir app, alarme, '
            "gasto, despesa, habito, tarefa, lembrete pratico.\n"
            '- "chat": conversa, opiniao, pergunta geral sem precisar ver a tela nem executar tool.\n'
            "Responda SOMENTE um JSON de uma linha, sem markdown:\n"
            '{"intent":"vision"}\n'
            "ou {\"intent\":\"action\"} ou {\"intent\":\"chat\"}\n\n"
            f"Mensagem: {user_text.strip()}"
        )
        for attempt in range(1, self.gemini_retry_attempts + 1):
            try:
                self.gemini_limiter.wait_for_slot()
                resp = self.gemini_client.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt,
                )
                raw = (resp.text or "").strip()
                match = re.search(r"\{[^}]+\}", raw)
                if match:
                    payload = json.loads(match.group(0))
                    intent = str(payload.get("intent", "chat")).lower().strip()
                    if intent in {"vision", "action", "chat"}:
                        return intent
            except Exception as exc:
                logger.warning(
                    "Gemini (classify_intent) falhou (tentativa %s/%s): %s",
                    attempt,
                    self.gemini_retry_attempts,
                    exc,
                )
                if attempt == self.gemini_retry_attempts:
                    break
                self._sleep_before_gemini_retry(exc, attempt)
        return "chat"

    def _try_openrouter(self, system_prompt: str, messages: list[dict[str, str]]) -> str:
        if not self.openrouter_client or not self.openrouter_model:
            return ""
        try:
            completion = self.openrouter_client.chat.completions.create(
                model=self.openrouter_model,
                messages=self._merge_messages_for_openai_chat(system_prompt, messages),
            )
            return (completion.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.warning("OpenRouter chat falhou: %s", exc)
            return ""

    def _try_nvidia(self, system_prompt: str, messages: list[dict[str, str]]) -> str:
        if not self.nvidia_client or not self.nvidia_model:
            return ""
        try:
            completion = self.nvidia_client.chat.completions.create(
                model=self.nvidia_model,
                messages=self._merge_messages_for_openai_chat(system_prompt, messages),
            )
            return (completion.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.warning("NVIDIA chat falhou: %s", exc)
            return ""

    def _try_groq(self, system_prompt: str, messages: list[dict[str, str]]) -> str:
        if not self.groq_client or not self.groq_model:
            return ""
        try:
            completion = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=self._merge_messages_for_openai_chat(system_prompt, messages),
            )
            return (completion.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.warning("Groq chat falhou: %s", exc)
            return ""

    @staticmethod
    def _to_single_prompt(system_prompt: str, messages: list[dict[str, str]]) -> str:
        lines = [f"Sistema: {system_prompt.strip()}"]
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        lines.append("assistant:")
        return "\n".join(lines)
