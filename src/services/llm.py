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
from src.telemetry.events import log_event

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
    """Pausa curta entre tentativas para rotação rápida."""
    text = str(exc)
    if "GenerateRequestsPerDay" in text:
        logger.error("Cota DIÁRIA do Gemini excedida! Abortando tentativas.")
        raise Exception("Cota diária do Gemini excedida.")

    if gemini_error_looks_transient(exc):
        # Como temos rotação, esperamos pouco: 1s, 2s, 4s...
        delay = min(10.0, 1.0 * (2 ** (failed_attempt - 1)))
    else:
        delay = min(2.0, 0.5 * (2 ** (failed_attempt - 1)))

    logger.debug("Gemini: Rotação rápida em %.1fs...", delay)
    time.sleep(delay)


# Global instance reference — used by tools that need LLM access (e.g. CodeHelperTool)
_global_llm_instance: "LLMService | None" = None


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
        ollama_model: str = "",
        ollama_base_url: str = "",
        gemini_max_rpm: int = 10,
        gemini_retry_attempts: int = 3,
        primary_llm_provider: str = "gemini",
        http_timeout: float = 180.0,
        fallback_gemini: bool = False,
        runtime_status: Any | None = None,
    ) -> None:
        self.primary_llm_provider = primary_llm_provider
        self.fallback_gemini = fallback_gemini
        self._http_timeout = max(30.0, min(600.0, http_timeout))
        self._runtime_status = runtime_status

        # Rotação de chaves Gemini com Cooldown
        self.gemini_keys = []
        for k in gemini_api_key.split(","):
            val = k.strip()
            if val:
                # Cada chave tem: { 'key': str, 'client': genai.Client, 'blocked_until': float }
                self.gemini_keys.append({
                    'key': val,
                    'client': genai.Client(api_key=val),
                    'blocked_until': 0.0
                })

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

        self.ollama_client = (
            OpenAI(
                api_key="ollama",
                base_url=ollama_base_url or "http://localhost:11434/v1",
                timeout=self._http_timeout,
            )
            if ollama_model
            else None
        )
        self.ollama_model = ollama_model

        # Rastreia qual provedor/modelo foi usado na ultima chamada
        self.last_provider: str = primary_llm_provider
        self.last_model: str = ""

        self.current_key_idx = 0
        self.gemini_model = gemini_model

        # Ajusta RPM total baseado no número de chaves (ex: 12 RPM por chave para segurança)
        total_rpm = max(10, len(self.gemini_keys) * 12)
        self.gemini_limiter = SlidingWindowRateLimiter(max_requests_per_minute=total_rpm)
        self.gemini_retry_attempts = max(1, gemini_retry_attempts)

    def _get_active_gemini_client(self):
        """Busca a próxima chave que não está em cooldown."""
        now = time.time()

        # 1. Tenta achar uma chave que não está bloqueada
        for _ in range(len(self.gemini_keys)):
            candidate = self.gemini_keys[self.current_key_idx]
            idx_usado = self.current_key_idx
            self.current_key_idx = (self.current_key_idx + 1) % len(self.gemini_keys)

            if now >= candidate['blocked_until']:
                logger.info(f"[Gemini] Utilizando Chave #{idx_usado}")
                return candidate['client']

        # 2. Se todas estiverem bloqueadas, descobrimos qual é a que vai expirar primeiro
        next_available_idx = 0
        min_blocked_until = self.gemini_keys[0]['blocked_until']
        for idx, key_data in enumerate(self.gemini_keys):
            if key_data['blocked_until'] < min_blocked_until:
                min_blocked_until = key_data['blocked_until']
                next_available_idx = idx

        # Calcula quanto tempo precisamos esperar de verdade
        sleep_time = max(0.1, min_blocked_until - now)
        # Capa o sleep para no máximo 5 segundos para não travar totalmente
        sleep_time = min(5.0, sleep_time)

        logger.warning(f"Todas as chaves Gemini em cooldown. Aguardando {sleep_time:.1f}s para liberar chave #{next_available_idx}...")
        time.sleep(sleep_time)

        # Atualiza o índice para usar essa chave que esperou
        self.current_key_idx = (next_available_idx + 1) % len(self.gemini_keys)
        logger.info(f"[Gemini] Utilizando Chave #{next_available_idx} após cooldown.")
        return self.gemini_keys[next_available_idx]['client']

    def _mark_key_as_blocked(self):
        """Marca a chave atual como bloqueada por tempo proporcional ao número de chaves."""
        # A chave usada foi a anterior à current_key_idx devido ao incremento
        idx = (self.current_key_idx - 1) % len(self.gemini_keys)

        # Se tiver poucas chaves, o cooldown é menor para não congelar a aplicação
        cooldown = 3.0 if len(self.gemini_keys) == 1 else (10.0 if len(self.gemini_keys) == 2 else 30.0)

        self.gemini_keys[idx]['blocked_until'] = time.time() + cooldown
        logger.error(f"Chave Gemini {idx} bloqueada por {cooldown}s devido a Rate Limit.")

    def change_provider(self, new_provider: str, model_name: str = "") -> str:
        """Alterna o provedor de LLM em tempo de execução (hot-swap)."""
        valid_providers = {"gemini", "openrouter", "nvidia", "groq", "ollama"}
        p = new_provider.lower().strip()
        if p not in valid_providers:
            return f"Provedor inválido. Opções: {valid_providers}"

        self.primary_llm_provider = p

        # Opcional: Atualiza o modelo específico do provedor
        if model_name:
            if p == "gemini": self.gemini_model = model_name
            elif p == "openrouter": self.openrouter_model = model_name
            elif p == "nvidia": self.nvidia_model = model_name
            elif p == "groq": self.groq_model = model_name
            elif p == "ollama": self.ollama_model = model_name

        return f"Provedor alterado para {p}" + (f" (modelo: {model_name})" if model_name else "")

    def wants_gemini_native_tools(self) -> bool:
        """Function calling nativo do Gemini só quando ele é o provedor principal do chat."""
        return self.primary_llm_provider == "gemini" and len(self.gemini_keys) > 0

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

    def _provider_has_backend(self, provider: str) -> bool:
        """True apenas se o cliente HTTP/modelo estiver configurado (evita ordem fantasma)."""
        p = (provider or "").strip().lower()
        if p == "gemini":
            return len(self.gemini_keys) > 0
        if p == "openrouter":
            return self.openrouter_client is not None and bool((self.openrouter_model or "").strip())
        if p == "nvidia":
            return self.nvidia_client is not None and bool((self.nvidia_model or "").strip())
        if p == "groq":
            return self.groq_client is not None and bool((self.groq_model or "").strip())
        if p == "ollama":
            return self.ollama_client is not None and bool((self.ollama_model or "").strip())
        return False

    def _chat_provider_order(self, skip_gemini: bool) -> list[str]:
        all_p = ["gemini", "openrouter", "nvidia", "groq", "ollama"]
        primary = self.primary_llm_provider
        if primary not in all_p:
            primary = "gemini"
        order = [primary] + [p for p in all_p if p != primary]
        if skip_gemini:
            order = [p for p in order if p != "gemini"]
        elif primary != "gemini" and not self.fallback_gemini:
            # Evita gastar cota Gemini quando o usuario escolheu outro provedor principal.
            order = [p for p in order if p != "gemini"]
        return [p for p in order if self._provider_has_backend(p)]

    def _sleep_before_gemini_retry(self, exc: BaseException, failed_attempt: int) -> None:
        sleep_before_gemini_retry(exc, failed_attempt)

    def chat_with_functions_stream(
        self,
        system_instruction: str,
        messages: list[dict[str, str]],
        tools: list[types.Tool],
        on_function_call: Callable[[str, dict[str, Any]], str],
        max_rounds: int = 8,
        force_tool: bool = False,
    ):
        """Versão com stream. Retorna um gerador de strings."""
        if not self.gemini_keys or not tools:
            return
        contents = self._messages_to_gemini_contents(messages)
        if not contents:
            return

        mode = types.FunctionCallingConfigMode.ANY if force_tool else types.FunctionCallingConfigMode.AUTO
        config = types.GenerateContentConfig(
            system_instruction=system_instruction.strip(),
            tools=tools,
            tool_config=types.ToolConfig(function_calling_config=types.FunctionCallingConfig(mode=mode)),
        )
        self.last_provider = "gemini"
        self.last_model = self.gemini_model

        total_attempts = self.gemini_retry_attempts * len(self.gemini_keys)

        for _ in range(max_rounds):
            resp = None
            for attempt in range(1, total_attempts + 1):
                client = self._get_active_gemini_client()
                if not client: return
                try:
                    self.gemini_limiter.wait_for_slot()
                    resp = client.models.generate_content(
                        model=self.gemini_model,
                        contents=contents,
                        config=config,
                    )
                    break
                except Exception as exc:
                    if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                        self._mark_key_as_blocked()
                        if attempt == total_attempts:
                            print(f"\\n[Erro Crítico Gemini] Todas as tentativas falharam (Rate Limit): {exc}")
                            return
                        continue
                    if attempt == total_attempts:
                        print(f"\\n[Erro Crítico Gemini] Falha ao conectar com a API: {exc}")
                        return
                    self._sleep_before_gemini_retry(exc, attempt)

            if not resp or not resp.candidates:
                break
            cand = resp.candidates[0]
            if not cand.content or not cand.content.parts:
                break
            parts = list(cand.content.parts)
            contents.append(cand.content)

            function_calls = [p.function_call for p in parts if p.function_call]
            if function_calls:
                fr_parts: list[types.Part] = []
                for fc in function_calls:
                    args = self._normalize_function_args(fc.args)
                    print(f"\n[🛠️ GEMINI TOOL CALL] {fc.name}({args})")
                    try:
                        out = on_function_call(fc.name or "", args)
                    except Exception as exc:
                        out = f"Erro ao executar {fc.name}: {exc}"
                    fr_parts.append(types.Part(function_response=types.FunctionResponse(id=fc.id, name=fc.name, response={"output": out})))
                contents.append(types.Content(role="user", parts=fr_parts))
                continue

            # Final round: return the text stream using generate_content_stream
            # Wait, we already have the text in `parts`. Since we used generate_content (blocking), we have the full text.
            # To stream the text, we would need to call generate_content_stream initially, but tools don't work well with stream.
            # We will just yield the text in chunks here to simulate the generator, or better, we can invoke generate_content_stream for the final call.
            # But we already made the API call! If we want true streaming, we must use `generate_content_stream` instead of `generate_content` above.
            for p in parts:
                if p.text:
                    yield p.text
            break

    def chat_with_functions(self, *args, **kwargs) -> str:
        # Retro-compatibilidade
        res = ""
        for chunk in self.chat_with_functions_stream(*args, **kwargs):
            if chunk: res += chunk
        return res

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
        # Multiplica tentativas pelo numero de chaves para garantir cobertura
        total_attempts = self.gemini_retry_attempts * len(self.gemini_keys)

        for attempt in range(1, total_attempts + 1):
            client = self._get_active_gemini_client()
            if not client:
                return None

            try:
                self.gemini_limiter.wait_for_slot()
                return client.models.generate_content(
                    model=self.gemini_model,
                    contents=contents,
                    config=config,
                )
            except Exception as exc:
                if "Cota diária" in str(exc):
                    logger.error("Cota diária abortando chamada de tool.")
                    return None

                # Se for erro de rate limit, bloqueia a chave específica
                if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                    self._mark_key_as_blocked()
                    continue

                logger.warning(
                    "Gemini (tools) falhou (tentativa %s/%s): %s",
                    attempt,
                    total_attempts,
                    exc,
                )
                if attempt == total_attempts:
                    return None
                try:
                    self._sleep_before_gemini_retry(exc, attempt)
                except Exception as sleep_exc:
                    if "Cota diária" in str(sleep_exc):
                        return None
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
            len(self.gemini_keys) > 0
            or self.openrouter_client
            or self.nvidia_client
            or self.groq_client
            or self.ollama_client
        )
        order = self._chat_provider_order(skip_gemini)
        if skip_gemini and (
            self.openrouter_client or self.nvidia_client or self.groq_client or self.ollama_client
        ):
            logger.debug(
                "Chat: ordem %s (Gemini omitido nesta rodada).",
                order,
            )
        failed: list[str] = []
        for provider in order:
            result = ""
            if provider == "gemini":
                result = self._try_gemini(system_prompt, messages)
                if result:
                    self.last_provider, self.last_model = "gemini", self.gemini_model
            elif provider == "openrouter":
                result = self._try_openrouter(system_prompt, messages)
                if result:
                    self.last_provider, self.last_model = "openrouter", self.openrouter_model
            elif provider == "groq":
                result = self._try_groq(system_prompt, messages)
                if result:
                    self.last_provider, self.last_model = "groq", self.groq_model
            elif provider == "ollama":
                result = self._try_ollama(system_prompt, messages)
                if result:
                    self.last_provider, self.last_model = "ollama", self.ollama_model
            else:
                result = self._try_nvidia(system_prompt, messages)
                if result:
                    self.last_provider, self.last_model = "nvidia", self.nvidia_model
            if result:
                if failed:
                    log_event(
                        "llm_provider_recovered",
                        {"after_failures": failed, "used": provider},
                    )
                if self._runtime_status:
                    self._runtime_status.clear_llm_error()
                return result
            failed.append(provider)
            log_event("llm_provider_fail", {"provider": provider})

        if not order and has_backend:
            log_event("llm_no_route", {"skip_gemini": skip_gemini})
            if self._runtime_status:
                self._runtime_status.set_llm_error(
                    "Nenhum provedor disponível nesta rota (ex.: skip_gemini sem fallback)."
                )
            return (
                "Não há provedor LLM disponível para esta tentativa (ordem vazia). "
                "Verifique chaves no .env ou desative skip_gemini."
            )

        if not has_backend:
            if self._runtime_status:
                self._runtime_status.set_llm_error("Nenhuma LLM configurada.")
            return (
                "Nenhuma LLM cloud configurada. Defina LLM_PROVIDER e a chave do provedor "
                "(GEMINI_API_KEY, OPENROUTER_API_KEY, NVIDIA_API_KEY ou GROQ_API_KEY)."
            )
        err_detail = ", ".join(failed) if failed else "nenhuma rota"
        if self._runtime_status:
            self._runtime_status.set_llm_error(f"Todas falharam: {err_detail}")
        return (
            "As LLMs configuradas falharam (rede, cota, modelo ou erro da API). "
            "Veja mensagens [llm] no terminal ou defina logging.basicConfig(level=logging.WARNING)."
        )

    def chat_stream(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        *,
        skip_gemini: bool = False,
    ):
        """Versão de chat com stream (generator). Retorna iterador de strings."""
        has_backend = bool(
            len(self.gemini_keys) > 0
            or self.openrouter_client
            or self.nvidia_client
            or self.groq_client
            or self.ollama_client
        )
        order = self._chat_provider_order(skip_gemini)

        # Apenas tenta o Gemini para stream por enquanto
        for provider in order:
            if provider == "gemini":
                prompt = self._to_single_prompt(system_prompt, messages)
                total_attempts = self.gemini_retry_attempts * len(self.gemini_keys)
                for attempt in range(1, total_attempts + 1):
                    client = self._get_active_gemini_client()
                    if not client: yield ""; return
                    try:
                        self.gemini_limiter.wait_for_slot()
                        resp_stream = client.models.generate_content_stream(
                            model=self.gemini_model,
                            contents=prompt,
                        )
                        self.last_provider, self.last_model = "gemini", self.gemini_model
                        for chunk in resp_stream:
                            if chunk.text:
                                yield chunk.text
                        return
                    except Exception as exc:
                        if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                            self._mark_key_as_blocked()
                            continue
                        if attempt == total_attempts:
                            print(f"\\n[Erro Crítico Gemini] Stream falhou: {exc}")
                            yield ""
                            return
                        try:
                            self._sleep_before_gemini_retry(exc, attempt)
                        except Exception:
                            yield ""; return

            # Se cair em outros providers, cai no fallback iterando sobre a string (fake stream rápido)
            else:
                res = self.chat(system_prompt, messages, skip_gemini=skip_gemini)
                for chunk in res.split(" "):
                    yield chunk + " "
                return

    def _try_gemini(self, system_prompt: str, messages: list[dict[str, str]]) -> str:
        prompt = self._to_single_prompt(system_prompt, messages)
        total_attempts = self.gemini_retry_attempts * len(self.gemini_keys)

        for attempt in range(1, total_attempts + 1):
            client = self._get_active_gemini_client()
            if not client:
                return ""

            try:
                self.gemini_limiter.wait_for_slot()
                resp = client.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt,
                )
                return (resp.text or "").strip()
            except Exception as exc:
                if "Cota diária" in str(exc): return ""

                if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                    self._mark_key_as_blocked()
                    continue

                logger.warning(
                    "Gemini falhou (tentativa %s/%s): %s",
                    attempt,
                    total_attempts,
                    exc,
                )
                if attempt == total_attempts:
                    return ""
                try:
                    self._sleep_before_gemini_retry(exc, attempt)
                except Exception as sleep_exc:
                    if "Cota diária" in str(sleep_exc): return ""
        return ""

    def classify_intent(self, user_text: str) -> str:
        """
        Classifica em uma chamada curta: vision | action | chat.
        """
        if not self.gemini_keys:
            return "chat"

        client = self._get_active_gemini_client()
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
                resp = client.models.generate_content(
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
                if "Cota diária" in str(exc): break
                logger.warning(
                    "Gemini (classify_intent) falhou (tentativa %s/%s): %s",
                    attempt,
                    self.gemini_retry_attempts,
                    exc,
                )
                if attempt == self.gemini_retry_attempts:
                    break
                try:
                    self._sleep_before_gemini_retry(exc, attempt)
                except Exception as sleep_exc:
                    if "Cota diária" in str(sleep_exc): break
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

    def _try_ollama(self, system_prompt: str, messages: list[dict[str, str]]) -> str:
        if not self.ollama_client or not self.ollama_model:
            return ""
        try:
            completion = self.ollama_client.chat.completions.create(
                model=self.ollama_model,
                messages=self._merge_messages_for_openai_chat(system_prompt, messages),
            )
            return (completion.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.warning("Ollama chat falhou: %s", exc)
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

    def generate_embedding(self, text: str) -> list[float]:
        """Gera embedding matemático para um texto usando text-embedding-004 com rotação."""
        if not self.gemini_keys or not text.strip():
            return []

        total_attempts = self.gemini_retry_attempts * len(self.gemini_keys)

        for attempt in range(1, total_attempts + 1):
            client = self._get_active_gemini_client()
            if not client: break

            try:
                self.gemini_limiter.wait_for_slot()
                result = client.models.embed_content(
                    model='models/text-embedding-004',
                    contents=text.strip(),
                )
                if hasattr(result, "embeddings") and result.embeddings:
                    return result.embeddings[0].values
                elif hasattr(result, "embedding") and result.embedding:
                    return result.embedding.values if hasattr(result.embedding, "values") else result.embedding
                return []
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    self._mark_key_as_blocked()
                    continue

                if attempt == total_attempts: break
                time.sleep(0.5)
        return []
