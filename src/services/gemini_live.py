import asyncio
import threading
import json
import traceback
import os
from pathlib import Path
import sounddevice as sd
from google import genai
from google.genai import types

class GeminiLiveService:
    def __init__(self, api_key: str, tool_registry=None, visualizer=None):
        self.api_key = api_key
        self.tool_registry = tool_registry
        self.visualizer = visualizer
        self.client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
        self.session = None
        self._loop = None
        self._is_running = False
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        
        self.audio_in_queue = asyncio.Queue()
        self.audio_out_queue = asyncio.Queue()
        
        # Configurações de Áudio
        self.CHANNELS = 1
        self.SEND_SAMPLE_RATE = 16000
        self.RECEIVE_SAMPLE_RATE = 24000
        self.CHUNK_SIZE = 1024
        self.MODEL_ID = "gemini-2.0-flash-exp" # Ou o mais recente disponível

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if self.visualizer:
            self.visualizer.set_state("SPEAKING" if value else "LISTENING")

    async def start(self):
        if self._is_running: return
        self._is_running = True
        self._loop = asyncio.get_running_loop()
        
        print("[GeminiLive] 🚀 Iniciando sessão multimodal...")
        
        config = self._build_config()
        
        async with self.client.aio.live.connect(model=self.MODEL_ID, config=config) as session:
            self.session = session
            # Tasks paralelas
            tasks = [
                asyncio.create_task(self._listen_mic()),
                asyncio.create_task(self._send_audio_to_gemini()),
                asyncio.create_task(self._receive_from_gemini()),
                asyncio.create_task(self._play_audio_output())
            ]
            await asyncio.gather(*tasks)

    def stop(self):
        self._is_running = False
        print("[GeminiLive] 🛑 Sessão encerrada.")

    def _build_config(self) -> types.LiveConnectConfig:
        from src.agent.prompts import AGENT_SYSTEM_PROMPT_FUNCTION_CALLING
        
        # Preparar declarações de ferramentas
        tools = []
        if self.tool_registry:
            # Converte as ferramentas do registro para o formato Gemini
            # Simplificado: assumindo que o ToolRegistry tem ferramentas compatíveis
            from src.agent.gemini_tools import build_agent_tool
            dynamic_tools = [t for t in self.tool_registry.tools if hasattr(t, "parameters")]
            tools = [{"function_declarations": [t.parameters for t in dynamic_tools]}]

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=AGENT_SYSTEM_PROMPT_FUNCTION_CALLING,
            tools=tools,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Charon" # Voz masculina sofisticada
                    )
                )
            ),
        )

    async def _listen_mic(self):
        """Captura o áudio do microfone e coloca na fila de saída."""
        loop = asyncio.get_running_loop()

        def callback(indata, frames, time_info, status):
            if not self._is_running: return
            with self._speaking_lock:
                if not self._is_speaking:
                    data = indata.tobytes()
                    loop.call_soon_threadsafe(self.audio_out_queue.put_nowait, data)

        with sd.InputStream(
            samplerate=self.SEND_SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype="int16",
            blocksize=self.CHUNK_SIZE,
            callback=callback,
        ):
            while self._is_running:
                await asyncio.sleep(0.1)

    async def _send_audio_to_gemini(self):
        """Envia os chunks de áudio do microfone para o Gemini."""
        while self._is_running:
            data = await self.audio_out_queue.get()
            await self.session.send(input={"data": data, "mime_type": "audio/pcm"}, end_of_turn=False)

    async def _receive_from_gemini(self):
        """Recebe as respostas (áudio e chamadas de ferramenta) do Gemini."""
        async for response in self.session.receive():
            if not self._is_running: break
            
            # Áudio de resposta
            if response.server_content and response.server_content.model_turn:
                parts = response.server_content.model_turn.parts
                for part in parts:
                    if part.inline_data:
                        await self.audio_in_queue.put(part.inline_data.data)
            
            # Chamada de ferramentas
            if response.tool_call:
                tool_responses = []
                for fc in response.tool_call.function_calls:
                    print(f"[GeminiLive] 🔧 Chamando ferramenta: {fc.name}")
                    result = await self._execute_tool(fc.name, fc.args)
                    tool_responses.append(types.LiveClientToolResponse(
                        function_responses=[types.FunctionResponse(
                            name=fc.name,
                            id=fc.id,
                            response={"result": result}
                        )]
                    ))
                await self.session.send(tool_responses)

    async def _execute_tool(self, name: str, args: dict) -> str:
        if not self.tool_registry: return "Tool registry not available."
        try:
            # Encontra a ferramenta e executa
            for tool in self.tool_registry.tools:
                if tool.name == name:
                    # Executa em um executor para não travar o loop
                    loop = asyncio.get_running_loop()
                    return await loop.run_in_executor(None, lambda: tool.execute(args))
            return f"Tool {name} not found."
        except Exception as e:
            return f"Error executing {name}: {str(e)}"

    async def _play_audio_output(self):
        """Toca o áudio recebido do Gemini."""
        import pyaudio
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=self.CHANNELS,
            rate=self.RECEIVE_SAMPLE_RATE,
            output=True
        )
        
        try:
            while self._is_running:
                data = await self.audio_in_queue.get()
                self.set_speaking(True)
                stream.write(data)
                # Se a fila estiver vazia, terminou de falar (heurística simples)
                if self.audio_in_queue.empty():
                    self.set_speaking(False)
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
