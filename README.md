# IA Assistente Autonoma (Windows MVP)

Projeto MVP baseado no plano definido:
- Voz (entrada/saida)
- Visao de tela sob demanda
- Orquestracao com tools
- Memoria curta e longa
- Integracao inicial com produtividade (Super Productivity via conector local)

## 1) Setup

1. Crie e ative um ambiente virtual Python 3.10+.
2. Instale dependencias:
   - `pip install -r requirements.txt`
3. Copie `.env.example` para `.env` e preencha:
   - `GEMINI_API_KEY` (principal)
   - opcionais para fallback: `OPENROUTER_API_KEY`, `NVIDIA_API_KEY`

## 2) Rodar

- Execucao principal:
  - `python -m src.main`
- Diagnostico de audio:
  - `python -m src.check_audio`

### Teste "IA de verdade" (Gemini + tela)

- Confirme `GEMINI_API_KEY` e (opcional) `USE_MIC=true` para voz.
- Diga algo como: **"olha minha tela e me diz o que voce ve"** ou **"veja minha tela e de sua opiniao sobre o video"**.
- O app captura o monitor, envia ao **Gemini multimodal** e responde com o prompt estruturado em `src/agent/prompts.py` (`build_vision_instruction`).
- **Roteamento de tools:** hoje as acoes (gasto, habito, abrir app, etc.) disparam por **palavras-chave** + fila de tools; o chat usa o **prompt de sistema** em `CHAT_SYSTEM_PROMPT`. Para ambiguidade (sem frase obvia), ative `USE_LLM_INTENT_ROUTER=true`: ai o Gemini classifica `vision` / `action` / `chat` antes de responder (uma chamada extra por mensagem quando nao houve match direto).

Modo padrao:
- entrada por texto (mais simples para validar fluxo)
- voz de resposta via `pyttsx3` (fallback local)
- LLM e visao com `Gemini 2.5 Flash` (quando `GEMINI_API_KEY` estiver configurada)
- STT: `SpeechRecognition` + Google (`STT_LANGUAGE`, padrao `pt-BR`) — bom para PT com termos em ingles ocasionais
- TTS configuravel: `local` (padrao) ou `murf`

Para usar microfone:
- defina `USE_MIC=true` no `.env`
- garanta suporte do sistema para `SpeechRecognition`/`PyAudio`
- ajuste `STT_LANGUAGE` se quiser outro idioma primario (ex.: `en-US`)

## 3) Comandos de exemplo

- `abra o bloco de notas`
- `olha minha tela e me diga o que voce ve`
- `adicione habito dormir as 22h`
- `modifique tarefa estudar python para prioridade alta`
- `adicione gasto de hoje feijao 20`
- `me mostre gastos de hoje`
- `crie alarme para 22:00`

## 4) Estrutura

- `src/main.py`: loop principal
- `src/agent/orchestrator.py`: decide entre conversa e tools
- `src/services/*`: STT, TTS, LLM e visao
- `src/tools/*`: tool-calling e automacao
- `src/memory/store.py`: memoria em SQLite
- `src/integrations/super_productivity.py`: conector de tarefas/habitos

## 5) Seguranca

- Acoes criticas pedem confirmacao (configuravel por env)
- Somente tools registradas podem ser executadas
- O agente sugere passos, mas nao modifica codigo sozinho

## 6) Roteamento de provedores

Ordem de tentativa no chat:
1. Gemini (`GEMINI_API_KEY`)
2. OpenRouter (`OPENROUTER_API_KEY`)
3. NVIDIA (`NVIDIA_API_KEY`)

## 7) Controle de cota Gemini

- `GEMINI_MAX_RPM`: limita chamadas por minuto (default: `10`)
- `GEMINI_RETRY_ATTEMPTS`: tentativas com backoff exponencial (default: `3`)

## 8) Voz e reconhecimento (estilo do tutorial)

- `STT_LANGUAGE=pt-BR` (reconhecimento online; costuma lidar melhor com nomes em ingles do que modelos locais so em PT)
- `TTS_PROVIDER=local` ou `TTS_PROVIDER=murf`
- Para Murf:
  - `MURF_API_KEY`
  - `MURF_VOICE_ID`
  - `MURF_API_URL` (default no `.env.example`)
  - O ultimo MP3 gerado fica em `data/cache/murf_last.mp3` (evita apagar o arquivo antes do player abrir no Windows).
  - Por padrao o som toca **dentro do Python** (pygame), sem abrir Groove/Filmes. Se instalar FFmpeg no PATH, pode usar `ffplay` em segundo plano (`-nodisp`). So use `TTS_ALLOW_SYSTEM_PLAYER=true` se quiser voltar a abrir o reprodutor do Windows quando tudo mais falhar.
