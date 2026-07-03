# 📘 NEXUS AI — GUIA COMPLETO DO PROJETO

> Este documento é um tutorial completo do projeto para uma IA (Codex, Claude, GPT, etc.) que está começando a trabalhar nele do zero. Leia tudo antes de fazer qualquer alteração.

---

## 🧭 VISÃO GERAL

**Nome do Projeto:** Nexus AI (também chamado de "Jarvis" internamente)

**O que é:** Um assistente de IA pessoal completo composto por **dois sistemas integrados**:

1. **Backend Python** (`src/`) — O "cérebro" do Jarvis. Roda no PC da usuária. Gerencia voz, IA, automações, memória, e ferramentas poderosas.
2. **App Mobile Android** (`mobile/`) — Um app de produtividade pessoal (estilo "second brain") que roda dentro de um WebView Android nativo. O Jarvis pode controlar e ler o estado do app pelo protocolo `nexus_command`.

**Onde fica o projeto:** `d:\Downloads\Projeto AI\`

**Linguagem:** Python (backend) + HTML/CSS/JavaScript puro (frontend mobile, sem frameworks)

**Sistema operacional da usuária:** Windows 11

---

## 📁 ESTRUTURA DE PASTAS — VISÃO COMPLETA

```
d:\Downloads\Projeto AI\
│
├── src/                          # Backend Python (Jarvis/Nexus PC)
│   ├── main.py                   # Ponto de entrada. Inicializa tudo.
│   ├── config.py                 # Carrega settings do .env (dataclass Settings)
│   ├── runtime_status.py         # Estado em tempo real (UI painel)
│   │
│   ├── agent/                    # Núcleo de IA
│   │   ├── orchestrator.py       # AgentOrchestrator: gerencia mensagens, tools, streaming
│   │   ├── agent_model.py        # AgentManager: múltiplos agentes com personalidades
│   │   ├── prompts.py            # System prompts (function calling, marker, visão, RAG)
│   │   ├── gemini_tools.py       # Definição das tools no formato SDK Gemini/OpenAI
│   │   ├── planner.py            # Planner: divide goal em steps, executa em cadeia
│   │   ├── mode_resolver.py      # Detecta modo: estudo, finanças, rotina, etc.
│   │   ├── toolsets.py           # Toolset por modo (quais tools estão disponíveis)
│   │   ├── tool_guardrails.py    # Limite de chamadas de tool por turno
│   │   ├── tool_markers.py       # Parser de marcadores [tool:argumento]
│   │   ├── action_executor.py    # Executa tool calls (com guardrails e allow-list)
│   │   ├── worker_agent.py       # Worker isolado para tarefas pesadas
│   │   └── runtime_modes.py     # Enum de modos de runtime
│   │
│   ├── services/                 # Serviços de infraestrutura
│   │   ├── llm.py                # LLMService: Gemini, Groq, NVIDIA, OpenRouter, Ollama
│   │   ├── stt.py                # STT: reconhecimento de voz (Groq Whisper / Google)
│   │   ├── tts.py                # TTS: síntese de voz (Edge, ElevenLabs, OpenAI, Fish...)
│   │   ├── tts_cache.py          # Cache de áudio TTS
│   │   ├── vision.py             # VisionService: screenshot + análise visual (Gemini/Groq)
│   │   ├── vision_tracker.py     # Tracker de rosto (autenticação por face)
│   │   ├── gemini_live.py        # Modo Live: voz bidirecional em tempo real (Gemini)
│   │   ├── nexus_service.py      # API REST interna do Nexus (Flask) — ~200KB, core do app
│   │   ├── nexus_api.py          # Endpoints adicionais da API
│   │   ├── nexus_cloud_agent.py  # Agente de nuvem (Supabase sync)
│   │   ├── heartbeat.py          # Consolidação periódica de memória (30min)
│   │   ├── cron_scheduler.py     # Agendador de tarefas recorrentes
│   │   ├── proactive_agent.py    # Agente proativo: fala espontaneamente
│   │   ├── mcp_client.py         # Cliente MCP (Model Context Protocol)
│   │   ├── audio_events.py       # Eventos de áudio (notificações sonoras)
│   │   ├── audio_fx.py           # Efeitos de áudio (EQ, reverb)
│   │   ├── clap_detector.py      # Detector de palma dupla (ativa Jarvis)
│   │   ├── sync_service.py       # Sync entre PC e mobile
│   │   ├── rate_limit.py         # Rate limiting de chamadas à API
│   │   ├── voice_auth_service.py # Autenticação por voz (embedding comparison)
│   │   ├── voice_recognition.py  # Reconhecimento de quem está falando
│   │   ├── visualizer.py         # Visualizador de onda de áudio (tray/overlay)
│   │   ├── visualizer_app.py     # App PyQt do visualizador
│   │   └── super_productivity.py # Integração com app SuperProductivity
│   │
│   ├── database/
│   │   ├── nexus_db.py           # NexusDatabase: TODA a lógica SQLite. ~1700 linhas.
│   │   └── pg_wrapper.py         # Wrapper que suporta SQLite E PostgreSQL
│   │
│   ├── memory/
│   │   ├── store.py              # MemoryStore: memória de curto/longo prazo em JSON
│   │   ├── vector_db.py          # SemanticMemory: ChromaDB para RAG semântico
│   │   └── structured_memory.py  # Extração automática de memória estruturada (LLM)
│   │
│   ├── tools/                    # Ferramentas que o Jarvis pode chamar
│   │   ├── registry.py           # ToolRegistry: registra e despacha todas as tools
│   │   ├── app_manager.py        # Abre/fecha apps do Windows
│   │   ├── browser_agent.py      # Agente de navegador (Playwright)
│   │   ├── clipboard.py          # Leitura/escrita do clipboard
│   │   ├── cmd_control.py        # Executa comandos CMD/PowerShell
│   │   ├── code_helper.py        # Auxiliar de código (snippets, execução)
│   │   ├── critical_confirm.py   # Bus de confirmação para ações críticas
│   │   ├── desktop.py            # Automação de desktop (pyautogui)
│   │   ├── dev_agent.py          # Agente de desenvolvimento (escrita de código)
│   │   ├── file_manager.py       # Gerenciador de arquivos
│   │   ├── file_processor.py     # Processamento de arquivos (PDF, DOCX, etc.)
│   │   ├── finance.py            # Tool de finanças (wrapper de nexus_command)
│   │   ├── habit_tracker.py      # Tool de rastreamento de hábitos
│   │   ├── hacker_mode.py        # Modo hacker: scripts e automações avançadas
│   │   ├── health_journal.py     # Diário de saúde e bem-estar
│   │   ├── image_generator.py    # Geração de imagens (DALL-E / local)
│   │   ├── media_control.py      # Controle de mídia (volume, play/pause)
│   │   ├── memory_manager.py     # Gestão da memória do Jarvis
│   │   ├── mcp_tool.py           # Tool para servidores MCP
│   │   ├── news.py               # Busca de notícias
│   │   ├── nexus.py              # Tool nexus_command (ponte para o app mobile)
│   │   ├── persona_manager.py    # Gerencia personalidades dos agentes
│   │   ├── settings_manager.py   # Edita settings em tempo de execução
│   │   ├── skill_manager.py      # Carrega skills dinâmicas
│   │   ├── spotify.py            # Controle do Spotify
│   │   ├── system_control.py     # Controles do sistema (shutdown, restart, etc.)
│   │   ├── system_info.py        # Informações do sistema (CPU, RAM, disco)
│   │   ├── timer.py              # Timers e alarmes
│   │   ├── toggle_live.py        # Liga/desliga modo Live (voz bidirecional)
│   │   ├── user_manager.py       # Gerencia usuários e perfis de voz
│   │   ├── visualizer_control.py # Controla o visualizador de áudio
│   │   ├── voice_auth.py         # Autenticação de usuário por voz
│   │   ├── web_search.py         # Busca na web (DuckDuckGo/Google)
│   │   ├── whatsapp.py           # Envio de mensagens WhatsApp (via pyautogui)
│   │   └── workflow.py           # Execução de workflows salvos
│   │
│   ├── skills/                   # Skills especiais (mais complexas que tools)
│   │   ├── nexus_manager.py      # Gerencia o app Nexus Mobile do PC
│   │   ├── web_agent_tool.py     # Agente web avançado
│   │   ├── change_voice.py       # Muda a voz do Jarvis
│   │   ├── system_exit.py        # Desliga o Jarvis com segurança
│   │   ├── smart_home_tool.py    # Integração com casa inteligente
│   │   ├── weather_tool.py       # Clima atual
│   │   ├── bitcoin_tool.py       # Preço do Bitcoin
│   │   ├── cad_tool.py           # CAD e modelagem
│   │   └── printer_tool.py       # Impressão
│   │
│   ├── ui/                       # Interface Desktop (painel de controle)
│   │   ├── desktop_app.py        # App PyQt5/Webview da janela do Jarvis
│   │   ├── nexus_desktop_bridge.py # Bridge JS ↔ Python para o painel
│   │   ├── panel.html            # Painel de controle HTML (~123KB)
│   │   ├── nexus_signals.py      # Sinais PyQt entre threads
│   │   └── nexus_window_api.py   # API da janela (redimensionar, mover)
│   │
│   └── utils/
│       └── window_context.py     # Detecta janela ativa (contexto proativo)
│
├── mobile/                       # App Android (WebView)
│   ├── index.html                # Toda a UI do app (~150KB, SPA completo)
│   ├── app.js                    # Toda a lógica JavaScript (~370KB)
│   ├── style.css                 # Todos os estilos (~63KB)
│   ├── manifest.json             # PWA manifest
│   ├── sw.js                     # Service Worker (cache offline)
│   ├── version.json              # Versão atual do bundle
│   └── youtube-player.html       # Player de YouTube embutido
│
├── mobile-apk/                   # Fonte do app Android nativo (Kotlin/Java)
├── platform-tools/               # ADB tools (adb.exe etc.)
├── data/                         # Dados persistentes do Jarvis
│   ├── nexus.db                  # SQLite principal (hábitos, finanças, notas...)
│   ├── memory.json               # Memória de curto e longo prazo
│   ├── jarvis.pid                # PID lockfile anti-zumbi
│   └── visualizer_state.json     # Estado do visualizador
├── scripts/                      # Scripts utilitários
│   ├── push_mobile_bundle_adb.py # Deploy do app mobile via ADB ⭐ MAIS IMPORTANTE
│   ├── deploy_mobile.py          # Deploy alternativo
│   └── cache_bust.py             # Atualiza cache do app
├── .env                          # Chaves de API e configurações (NÃO commitar)
├── .env.example                  # Template de configuração
├── requirements.txt              # Dependências Python
└── nexus_storage.db              # DB alternativo/legado
```

---

## 📱 APP MOBILE — ARQUITETURA DETALHADA

### Como funciona

O app roda dentro de um WebView Android nativo. Não é um app web separado — é uma SPA (Single Page Application) servida **localmente pelo próprio APK**. A comunicação PC ↔ mobile acontece via API REST do `nexus_service.py`.

### Arquivos principais

| Arquivo | Tamanho | Responsabilidade |
|---|---|---|
| `mobile/index.html` | ~150KB | Toda a estrutura HTML, modais, views, formulários |
| `mobile/app.js` | ~370KB | Toda a lógica: navegação, CRUD, Jarvis, XP, etc. |
| `mobile/style.css` | ~63KB | Design system completo: cores, glassmorphism, animações |

### Design System (CSS Variables)

```css
--bg-base: #0a0a0f        /* Fundo escuro principal */
--bg-card: #12121a        /* Cards e seções */
--accent-purple: #6c5ce7  /* Cor primária (roxo) */
--accent-pink: #fd79a8    /* Cor de destaque (rosa) */
--accent-green: #00d279   /* Sucesso, completado */
--accent-blue: #74b9ff    /* Informação */
--accent-primary: var(--accent-purple)
--border-glass: rgba(255,255,255,0.1)
--text-secondary: rgba(255,255,255,0.5)
```

### Navegação entre Views

O app usa um sistema de views ocultas. Não há roteamento — todas as telas existem no DOM e são mostradas/escondidas:

```javascript
// Trocar de view:
navigateTo('view-home')     // Home
navigateTo('view-tasks')    // Tarefas
navigateTo('view-habits')   // Hábitos
navigateTo('view-finance')  // Finanças
navigateTo('view-studies')  // Estudos
navigateTo('view-routines') // Rotinas
navigateTo('view-journal')  // Diário
navigateTo('view-settings') // Configurações
```

Views especiais (overlays):
- `#pomodoro-view` — abre sobre a view atual (z-index alto)
- `#flashcard-view` — overlay de flashcards
- `#note-editor-full` — editor fullscreen de notas
- `#vision-board-modal` — Vision Board fullscreen
- `#finance-goal-modal` — modal de meta financeira
- `#budget-form-modal` — modal de orçamento

### LocalDB — Persistência no App Mobile

```javascript
// O LocalDB é um wrapper de localStorage com suporte a JSON
// Uso:
const data = LocalDB.get('habits');         // lê
LocalDB.set('habits', data);               // salva

// Chaves principais:
// 'habits'              — array de hábitos
// 'habit_logs'          — logs de conclusão de hábitos
// 'tasks'               — array de tarefas
// 'finance_transactions' — transações financeiras
// 'finance_goals'       — metas de economia
// 'finance_budgets'     — orçamento por categoria
// 'flashcards'          — flashcards para revisão
// 'subjects'            — matérias de estudo
// 'notes'               — notas das matérias
// 'routines'            — rotinas programadas
// 'journal_entries'     — entradas do diário
// 'user_profile'        — XP, nível, pontos
// 'vision_board'        — imagens do moodboard
// 'pomo_sessions'       — histórico de sessões Pomodoro
// 'alarms'              — alarmes programados
// 'goals'               — metas gerais
```

### Sistema de XP no App Mobile

```javascript
// Ganhar XP:
awardXP(amount, reason)    // ex: awardXP(50, 'Hábito concluído')

// Perder XP (anti-exploit):
deductXP(amount, reason)   // ex: deductXP(50, 'Hábito desmarcado')

// Tabela de XP por dificuldade/prioridade:
// Fácil / Baixa prioridade = 10 XP
// Médio / Média prioridade = 25 XP
// Difícil / Alta prioridade = 50 XP
```

### Sistema de Confirmação Customizado

Nunca use `window.confirm()` — use sempre o modal customizado:

```javascript
// Correto:
window.showConfirm('Tem certeza?', () => {
    // ação confirmada
});

// O modal HTML é #custom-confirm-modal em index.html
```

---

## 🤖 JARVIS NO APP MOBILE

### Como o Jarvis se comunica com o app

Dentro do app Android existe um objeto `window.AndroidNative` que permite comunicação com o backend Python via WebSocket/API. O Jarvis usa um sistema de **tools (ferramentas)** chamadas `nexus_command`.

### Tools do Jarvis no app (jarvisTools em app.js)

O objeto `jarvisTools` processa comandos do Jarvis. Cada `action` tem um comportamento:

```javascript
// Exemplos de actions disponíveis:
'list_tasks'        → lista tarefas pendentes
'list_habits'       → lista hábitos ativos
'list_transactions' → lista transações financeiras
'list_goals'        → lista metas
'get_app_state'     → retorna estado completo (hábitos + tarefas + finanças)
'daily_briefing'    → mesmo que get_app_state
'complete_task'     → marca tarefa como concluída (param: id ou nome)
'uncomplete_task'   → desmarca tarefa
'complete_habit'    → marca hábito como feito hoje
'uncomplete_habit'  → desmarca hábito
'create_task'       → cria nova tarefa (param: name, priority, due_date)
'create_habit'      → cria novo hábito (param: name, xp, period)
'delete_task'       → deleta tarefa (param: id)
'delete_habit'      → deleta hábito (param: id)
'add_transaction'   → adiciona transação financeira
'add_note'          → adiciona nota de estudo
'create_flashcard'  → cria flashcard
'list_flashcards'   → lista flashcards para revisar
'navigate'          → navega para uma view (param: view = 'tasks', 'finance', etc.)
'show_notification' → mostra notificação no app
'start_pomodoro'    → inicia o Pomodoro
'start_quiz'        → inicia quiz de estudos
```

### Como o Jarvis chama essas tools

No backend Python (`src/tools/nexus.py`), o Jarvis manda um comando JSON:

```python
# Protocolo: nexus_command com JSON
payload = {
    "action": "get_app_state"
}
# ou:
payload = {
    "action": "complete_task",
    "id": "123"
}
```

### Importante: get_app_state como Tool (não injeção automática)

O estado do app (lista de tarefas/hábitos) **NÃO** é injetado no prompt do Jarvis em toda mensagem. O Jarvis só vê o estado quando ele mesmo chama a tool `get_app_state`. Isso foi uma decisão de design da usuária para economizar tokens.

---

## ⚙️ CONFIGURAÇÃO (.env)

O arquivo `.env` fica na raiz do projeto. As variáveis mais importantes:

```dotenv
# LLM Principal
GEMINI_API_KEY=              # Google Gemini (principal)
GEMINI_MODEL=gemini-2.5-flash
LLM_PROVIDER=gemini          # gemini | openrouter | nvidia | groq

# Alternativas de LLM
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
OPENROUTER_API_KEY=
NVIDIA_API_KEY=

# TTS (Voz do Jarvis)
TTS_PROVIDER=edge            # edge | elevenlabs | openai | murf | fish | kokoro | piper | styletts2
TTS_PROVIDER_ORDER=edge,kokoro,openai,elevenlabs
OPENAI_API_KEY=              # Para OpenAI TTS

# STT (Reconhecimento de Voz)
USE_MIC=false                # true = usa microfone
STT_LANGUAGE=pt-BR
GROQ_API_KEY=                # Para Groq Whisper STT (mais rápido)

# Funcionalidades
ENABLE_VISUALIZER=false      # Visualizador de áudio
START_VISION_TRACKER=false   # Rastreamento de rosto
START_HEARTBEAT=true         # Consolidação de memória
START_PROACTIVE_AGENT=false  # Jarvis fala espontaneamente
ENABLE_CLAP_TRIGGER=true     # Palma dupla ativa Jarvis
STUDY_PROFESSOR_MODE=false   # Modo professor (foca em didática)

# Painel
PANEL_HOTKEY=win+shift+a     # Atalho para abrir o painel
```

---

## 🗄️ BANCO DE DADOS SQLite — ESQUEMA COMPLETO

Arquivo: `data/nexus.db` (gerenciado por `src/database/nexus_db.py`)

### Tabelas principais

```sql
-- Usuário e XP
nexus_user (id, xp, level, points, last_update)

-- Finanças
finance_transactions (id, type, amount, category, description,
                      necessity_score, created_at, occurred_at, notes, is_debt)
finance_budgets (id, category, monthly_limit, created_at)
finance_goals (id, name, target_amount, current_amount, target_date, created_at)
finance_investments (id, ticker, type, quantity, avg_price, currency, created_at)

-- Hábitos
habits (id, name, description, days_of_week, target_time,
        xp_reward, current_streak, max_streak, active, created_at)
habit_logs (id, habit_id, completed_at)

-- Tarefas
tasks (id, title, due_date, done_at, habit_id, points_reward, created_at)

-- Estudos
study_notes (id, subject, title, content, media_links, color,
             created_at, updated_at)
flashcards (id, note_id, front, back, ease_factor, interval,
            repetitions, next_review)
study_stats (id, subject, total_questions, correct_answers, last_attempt)

-- Quiz
quiz_questions (id, area, stem, options_json, correct_index,
                explanation, skill, difficulty, source)
quiz_attempts (id, started_at, finished_at, area, score_pct)
quiz_answers (id, attempt_id, question_id, chosen_index, correct)

-- Metas
nexus_goals (id, name, target_date, progress, status)

-- Saúde
fitness_workouts (id, date, type, duration_minutes, calories_burned, notes, created_at)
fitness_metrics (id, date, weight, body_fat_percentage, calories_consumed, protein_grams, notes, created_at)
nutrition_logs (id, date, meal_name, calories, protein_g, carbs_g, fat_g, created_at)
body_measurements (id, date, weight_kg, body_fat_pct, notes, created_at)
workout_plans, workout_sessions, workout_sets

-- Diário / Humor
journal_entries (id, date, content, psychologist_feedback, created_at)
mood_logs (id, date, mood_score, notes, created_at)

-- Recompensas
nexus_rewards (id, name, cost, description)
reward_redemptions (id, redemption_date, reward_id, created_at)

-- Automação
cron_jobs (id, name, schedule, command, active, last_run, next_run, created_at)
calendar_events (id, title, event_date, event_time, duration_minutes,
                 reminder_minutes, created_at)
workflows (id, name, description, steps_json, tags, risk_level,
           last_executed, created_at)

-- Autenticação
voice_profiles (id, name, access_level, voice_embedding, created_at)

-- Presets
lifestyle_presets (id, name, config_json, is_active, created_at)
```

---

## 🧠 ARQUITETURA DO AGENTE (Backend Python)

### Fluxo de uma mensagem

```
Usuário fala/digita
        ↓
main.py: _process_and_respond()
        ↓
AgentOrchestrator.handle_user_message()
        ├── Contexto: data/hora/janela ativa
        ├── RAG: busca na SemanticMemory (ChromaDB)
        ├── Histórico: últimas 10 mensagens
        └── ModeResolver: detecta modo (estudo, finanças...)
              ↓
        LLMService.chat_with_functions_stream() [Gemini]
        ou
        LLMService.chat_with_openai_tools() [Groq/NVIDIA]
              ↓
        Modelo chama tools → ActionExecutor.execute()
              ↓ (loop tool calls)
        Resposta final (streaming)
              ↓
        TTSService.speak() — fala em paralelo ao streaming
              ↓
        Post-process (async):
          ├── memory.add_short_term()
          ├── _extract_semantic_memory() → ChromaDB
          └── _extract_structured_memory() → JSON
```

### Provedores de LLM disponíveis

| Provider | Variável | Modelo padrão | Function Calling |
|---|---|---|---|
| Gemini (Google) | `GEMINI_API_KEY` | `gemini-2.5-flash` | ✅ Nativo SDK |
| Groq | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | ✅ OpenAI-compat |
| NVIDIA NIM | `NVIDIA_API_KEY` | `meta/llama-3.1-70b-instruct` | ✅ OpenAI-compat |
| OpenRouter | `OPENROUTER_API_KEY` | `qwen/qwen3-30b-a3b:free` | ⚠️ Marcadores |
| Ollama (local) | sem chave | `qwen3:1.7b` | ⚠️ Marcadores |

### Provedores de TTS

| Provider | Qualidade | Latência | Requer |
|---|---|---|---|
| `edge` | Boa | Baixa | Internet, gratuito |
| `elevenlabs` | Excelente | Média | `ELEVENLABS_API_KEYS` |
| `openai` | Boa | Média | `OPENAI_API_KEY` |
| `kokoro` | Boa | Baixa | Instalação local |
| `styletts2` | Excelente | Baixa | Instalação local |
| `piper` | OK | Muito baixa | Instalação local |
| `fish` | Boa | Média | `FISH_AUDIO_API_KEY` |
| `murf` | Boa | Média | `MURF_API_KEY` |

### Sistema de Memória

```
Memória de Curto Prazo:
  → data/memory.json → chave "short_term"
  → Últimas N mensagens (user + assistant)
  → Resumido pelo LLM quando ultrapassa limite

Memória de Longo Prazo:
  → data/memory.json → chave "long_term"
  → preferences: preferências detectadas automaticamente
  → persona_evolution: ajustes de personalidade do Jarvis

Memória Semântica (RAG):
  → ChromaDB local
  → Fatos extraídos automaticamente pelo LLM após cada turno
  → Busca por embedding na próxima conversa
  → Coleção separada por agente

Memória Estruturada:
  → data/structured_memory.json
  → Extraída em 2 estágios: YES/NO → JSON detalhado
  → Campos: nome, preferências, projetos, humor, rotina, etc.
```

### Multi-Agentes

O sistema suporta múltiplos agentes com personalidades diferentes:

```python
# Cada agente tem:
agent.id          # identificador único
agent.name        # nome (ex: "Jarvis", "Aria")
agent.persona     # prompt de personalidade
agent.tts_voice   # voz TTS específica
agent.tts_provider # provider TTS
agent.memory_collection  # coleção ChromaDB separada

# Modos multi-agentes:
# 1. Round-Robin: cada agente responde em sequência
# 2. Debate: agentes debatem um tema em rodadas
# 3. Chamada por Nome: "Aria, me ajude com X"
# 4. Delegação: Jarvis delega para outro agente via delegate_to_agent
```

### Tools Principais do Jarvis (Function Calling)

| Tool | Descrição |
|---|---|
| `analyze_screen` | Captura e analisa a tela |
| `search_web` | Busca na web |
| `run_utility` | Clipboard, timer, mídia, notas |
| `manage_memory` | Salva/recupera memórias |
| `nexus_command` | Controla o app mobile |
| `whatsapp_send` | Envia mensagem no WhatsApp |
| `control_spotify` | Controla o Spotify |
| `manage_files` | Gerencia arquivos |
| `open_windows_app` | Abre apps do Windows |
| `toggle_live` | Ativa modo Live (voz bidirecional) |
| `delegate_to_agent` | Delega para outro agente |
| `agent_task` | Planner: divide e executa goal |
| `save_memory` | Salva memória estruturada silenciosa |
| `run_productivity_command` | Comandos de produtividade |
| `run_finance_command` | Comandos financeiros |

---

## 📲 DEPLOY DO APP MOBILE

### Script principal de deploy

```bash
python "d:\Downloads\Projeto AI\scripts\push_mobile_bundle_adb.py"
```

Esse script:
1. Detecta o dispositivo Android conectado via ADB
2. Faz push de todos os arquivos de `mobile/` para o app (run-as)
3. Mata e reinicia o app automaticamente

### O que é deployado

```
mobile/version.json   → controle de versão
mobile/index.html     → HTML completo
mobile/style.css      → estilos
mobile/app.js         → JavaScript
mobile/youtube-player.html → player YT
mobile/manifest.json  → PWA manifest
mobile/sw.js          → Service Worker
```

### Localização no Android

```
/data/data/com.nexus.mobile/files/mobile_bundle/
```

---

## 🖥️ PAINEL DE CONTROLE (Desktop)

Arquivo: `src/ui/panel.html` (~123KB)

O painel é uma janela PyQt5/WebView que abre no PC. Ele mostra:
- Chat com o Jarvis
- Status do sistema (LLM, STT, TTS)
- Configurações em tempo real
- Logs do sistema
- Gestão de agentes
- Visualizador de onda de áudio

Atalho padrão: `Win+Shift+A`

---

## 🔌 API REST INTERNA (nexus_service.py)

O Jarvis expõe uma API local (Flask) para o app mobile e para o painel. O arquivo é enorme (~200KB) e contém todos os endpoints CRUD para:

- `/api/habits` — CRUD de hábitos
- `/api/tasks` — CRUD de tarefas
- `/api/finance` — CRUD de transações
- `/api/notes` — CRUD de notas
- `/api/flashcards` — CRUD de flashcards
- `/api/quiz` — Quizzes e estatísticas
- `/api/goals` — CRUD de metas
- `/api/user` — Perfil, XP, nível
- `/api/jarvis/message` — Enviar mensagem para o Jarvis
- `/api/sync` — Sincronização PC ↔ mobile
- `/api/status` — Estado do runtime

---

## 🚧 REGRAS E CONVENÇÕES IMPORTANTES

### Para o app mobile

1. **Nunca use `window.confirm()`** — use `window.showConfirm(msg, callback)`
2. **IDs são sempre comparados como String** — use `String(id)` para evitar bugs de tipo
3. **LocalDB é a fonte da verdade no mobile** — não altere dados sem passar pelo LocalDB
4. **XP tem anti-exploit** — `deductXP()` quando desmarcar tarefas/hábitos
5. **Modais de formulário** ficam no final do `<body>` em `index.html`
6. **Views têm `id="view-*"` e classe `view`** — alternadas por `navigateTo()`
7. **Imersivo ao editar** — notas e subjects devem esconder header/nav ao abrir, restaurar ao fechar

### Para o backend Python

1. **Guarda Anti-Zumbi** — `_kill_previous_instances()` é chamado no início do `main.py`. NÃO remova.
2. **Singleton de instância** — `data/jarvis.pid` controla isso
3. **Tools críticas precisam de confirmação** — verifique `REQUIRE_CRITICAL_CONFIRMATION`
4. **Rate Limiting** — Gemini tem limite de RPM configurável (`GEMINI_MAX_RPM`)
5. **Streaming é padrão** — respostas são geradas em stream para baixa latência
6. **Memória RAG é por coleção** — cada agente tem sua própria coleção ChromaDB
7. **Fallback de LLM** — se o provider principal falhar, tenta outros na ordem configurada

### Padrão de imports Python

```python
# Imports relativos dentro de src/:
from src.services.llm import LLMService
from src.database.nexus_db import NexusDatabase
from src.agent.orchestrator import AgentOrchestrator
```

### Padrão de Tool

```python
class MinhaToolTool(BaseTool):
    name = "minha_tool"
    description = "Descrição curta"
    markers = ["minha_tool"]  # para o sistema de marcadores

    def run(self, argument: str) -> ToolResult:
        # lógica
        return ToolResult(ok=True, message="Resultado aqui")
```

---

## 🎨 CONVENÇÕES DE UI (Mobile)

### Classes CSS reutilizáveis

```css
.glass          /* card com efeito glassmorphism */
.view           /* uma view/tela do app */
.active-view    /* view atualmente visível */
.view-header    /* cabeçalho de uma view */
.page-title     /* título de página */
.icon-btn       /* botão de ícone circular */
.form-field     /* campo de formulário */
.study-chip     /* chip/tag de filtro */
.list-container /* container de lista com scroll */
.modal-overlay  /* overlay de modal (position:fixed, fullscreen) */
.focus-sound-btn /* botão de som de foco no Pomodoro */
```

### Animações disponíveis

```css
.pulse-glow     /* pulso de brilho */
.slide-up       /* desliza de baixo para cima */
fa-spin         /* ícone girando (loading) */
```

### Ícones

O projeto usa **Font Awesome 6** (via CDN). Exemplo:
```html
<i class="fa-solid fa-brain"></i>
<i class="fa-solid fa-tasks"></i>
<i class="fa-solid fa-fire"></i>
```

---

## 📋 FUNCIONALIDADES DO APP MOBILE — RESUMO

| Seção | Views | Funcionalidades |
|---|---|---|
| **Home** | `view-home` | Briefing do dia, hábitos do dia, atalhos rápidos, chat com Jarvis |
| **Tarefas** | `view-tasks` | Lista de tarefas, Kanban (A fazer/Fazendo/Feito), filtros, prioridade |
| **Hábitos** | `view-habits` | Lista de hábitos com streak, heatmap de 30 dias, completar hábitos |
| **Finanças** | `view-finance` | Transações, gráfico pizza/barras, Metas de Economia, Orçamento por categoria |
| **Estudos** | `view-studies` | Matérias, notas com editor rico, Flashcards (SRS), Quiz ENEM, Pomodoro |
| **Rotinas** | `view-routines` | Rotinas programadas por horário/dia |
| **Diário** | `view-journal` | Diário pessoal, log de humor, feedback do "psicólogo Jarvis" |
| **Configurações** | `view-settings` | Perfil, XP/Nível, tema, configurações do Jarvis |
| **Vision Board** | `#vision-board-modal` | Galeria de imagens dos sonhos/objetivos de vida |
| **Pomodoro** | `#pomodoro-view` | Timer Pomodoro, Sons de Foco (Chuva, Lareira, Cafeteria, Lofi) |

---

## 🔊 SONS DE FOCO (Pomodoro)

Adicionado recentemente. Funcionamento:

```javascript
// Chaves de sound:
// 'rain'  → Chuva
// 'fire'  → Lareira  
// 'cafe'  → Cafeteria
// 'lofi'  → Lofi

window.toggleFocusSound('rain');  // liga/desliga

// Audio element: #focus-audio (dentro de #pomodoro-view)
// Parar ao fechar: closePomodoro() chama audio.pause()
```

---

## 💡 DICAS PARA EDITAR O PROJETO

### Ao editar o app mobile

1. Edite `mobile/index.html` e/ou `mobile/app.js` e/ou `mobile/style.css`
2. Faça deploy com: `python "d:\Downloads\Projeto AI\scripts\push_mobile_bundle_adb.py"`
3. O app reinicia automaticamente no celular

### Ao editar o backend

1. Edite os arquivos em `src/`
2. Reinicie o Jarvis (o guarda anti-zumbi mata a instância anterior automaticamente)
3. Inicie com: `python -m src.main` na raiz do projeto

### Ao adicionar uma nova Tool ao Jarvis

1. Crie o arquivo em `src/tools/nova_tool.py`
2. Herde de `BaseTool` e implemente `run()`
3. Registre em `src/tools/registry.py`
4. Importe e adicione em `src/main.py`
5. Se necessário, adicione a definição OpenAI/Gemini em `src/agent/gemini_tools.py`

### Ao adicionar uma nova View no app mobile

1. Adicione o HTML em `mobile/index.html` com `id="view-minha-view"` e `class="view"`
2. Adicione o link de navegação na bottom nav
3. Implemente a lógica JS em `mobile/app.js`
4. Chame `loadMinhaView()` no callback de `navigateTo()`

---

## ⚠️ PROBLEMAS CONHECIDOS E SOLUÇÕES

| Problema | Causa | Solução |
|---|---|---|
| Jarvis não fala nada | TTS não configurado | Verificar `TTS_PROVIDER` no .env |
| App mobile trava ao abrir | Bundle desatualizado | Fazer deploy via ADB |
| XP infinito ao marcar/desmarcar | Bug corrigido | `deductXP()` implementado |
| Jarvis abre 100+ processos | Bug do guarda ausente | `_kill_previous_instances()` corrigido |
| Confirmação mostra alert feio | Uso de `window.confirm()` | Substituir por `showConfirm()` |
| IDs não encontrados para delete | Comparação `==` vs `===` | Usar `String(id) === String(item.id)` |

---

## 🔗 ARQUIVOS MAIS IMPORTANTES

Em ordem de importância para edição do dia a dia:

1. `mobile/app.js` — lógica completa do app mobile
2. `mobile/index.html` — estrutura HTML do app mobile  
3. `mobile/style.css` — estilos do app mobile
4. `src/services/nexus_service.py` — API REST (CRUD completo)
5. `src/agent/orchestrator.py` — núcleo do agente
6. `src/database/nexus_db.py` — banco de dados SQLite
7. `src/services/llm.py` — serviço de LLM
8. `src/config.py` — carrega configurações do .env
9. `scripts/push_mobile_bundle_adb.py` — deploy no celular
10. `.env` — chaves e configurações

---

*Documento gerado em: 2026-06-22 | Versão do projeto: latest | Mantido por: Antigravity AI*
