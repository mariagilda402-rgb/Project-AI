# Nexus Life OS - Handoff prompt completo (2026-05-26)

Use este arquivo como prompt/contexto inicial para outra IA continuar a implementacao deste projeto. Ele foi escrito para funcionar sem depender do historico do chat original.

## Papel da IA que vai continuar

Voce esta trabalhando em `D:\Documentos\Projeto AI`, um app desktop Python com UI via PyWebView/HTML/JS e banco SQLite. Continue o projeto com cuidado de produto e engenharia. O objetivo e transformar o app em um "Jarvis pessoal" chamado Nexus Life OS: assistente com voz, agentes, automacao de PC, organizacao pessoal, estudos, habitos, treino, financas, noticias, memoria e workflows.

Regras importantes:

- Nao use `git add .`.
- Nao commite `.env`, chaves, bancos locais, caches, modelos, venvs, logs, screenshots ou repos de referencia.
- Leia o estado real com `git status --short`, `rg` e arquivos do projeto antes de mexer.
- Nao reverta mudancas que voce nao fez.
- Use testes focados antes de afirmar que algo esta pronto.
- Para UI, valide scripts HTML e, se possivel, faca QA visual renderizado.
- Mantenha a visao de produto: tudo deve poder ser usado pela interface e tambem por comando natural do agente.

## Visao do produto

O Nexus Life OS deve funcionar como um sistema operacional pessoal com IA no centro. O usuario quer algo proximo de Jarvis:

- conversar por texto/voz;
- pedir para abrir apps, navegador, Spotify, YouTube, bloco de notas e janelas internas;
- criar e executar workflows como "modo estudo", "modo dormir", "modo academia" e "modo noticias";
- salvar uma sequencia real de janelas/apps/comandos como workflow reutilizavel;
- usar agentes especializados, mas sem obrigar o usuario a dizer "entre no modo X" toda hora;
- detectar contexto automaticamente e escolher ferramentas com guardrails;
- ter painel bonito, rapido e configuravel, sem depender de editar `.env` pelo VS Code.

A experiencia ideal e:

1. O usuario fala ou digita um pedido natural.
2. O orquestrador detecta modo/contexto.
3. A LLM so planeja a acao em JSON/tool call.
4. Um executor local valida permissao, risco e contexto.
5. A UI mostra estado, historico, resultado e opcoes de ajuste.

## Decisoes conceituais aprovadas

- Manter psicologo e coach motivacional como desejo central do produto, mas implementar com limites responsaveis: reflexao guiada, motivacao, diario emocional, tendencias de humor, alertas de risco e recomendacao de ajuda humana em crise.
- Manter janela dedicada de noticias. O usuario quer abrir "modo noticias" quando pedir, ver videos em tempo real se quiser, legendas/resumo/fontes e buscar assuntos especificos.
- Usar `hermes-agent-main` como referencia local de arquitetura de comandos/contexto, mas nao copiar cegamente nem commitar a pasta.
- Usar `Affine` como referencia local para editor estilo Notion/Obsidian/Affine, mas sem importar o BlockSuite agora. O app atual continua HTML/JS simples e markdown canonico.
- Priorizar automacao natural: o usuario nao deve precisar ficar especificando modo manualmente; o sistema deve inferir quando for seguro.
- Configuracoes devem ir para UI sempre que possivel, evitando editar codigo ou `.env` manualmente.

## O que foi implementado neste chat

### Runtime de agente e comandos

- Foram criados/ajustados modulos de runtime de agente:
  - `src/agent/action_executor.py`
  - `src/agent/mode_resolver.py`
  - `src/agent/runtime_modes.py`
  - `src/agent/tool_guardrails.py`
  - `src/agent/toolsets.py`
- O objetivo e separar:
  - deteccao de modo;
  - toolsets permitidos;
  - guardrails;
  - execucao de acoes;
  - prompt com contexto organizado.
- A IA deve planejar; o executor decide se executa.

### Configuracoes e boot

- `src/config.py` ganhou configuracoes para STT, TTS, startup, clap trigger, motion e densidade.
- `.env.example` foi expandido com defaults seguros e documentados.
- `src/runtime_status.py` foi criado para registrar estado e fases de inicializacao.
- `src/main.py` passou a marcar fases de boot como settings, STT, TTS, LLM, tools, agent, optional services, clap e UI.
- `src/ui/desktop_app.py` ganhou APIs para ler/salvar configuracoes de voz, STT, startup, seguranca e aparencia.

### STT, voz e palmas

- O STT ficou mais sensivel: threshold default deixou de ser fixo alto e passou a ser configuravel.
- Configuracoes adicionadas incluem:
  - `STT_ENERGY_THRESHOLD`
  - `STT_DYNAMIC_ENERGY`
  - `STT_PAUSE_THRESHOLD`
  - `STT_NON_SPEAKING_DURATION`
  - `STT_CALIBRATION_SECONDS`
  - `STT_MIN_AUDIO_SECONDS`
- Clap trigger configuravel:
  - `ENABLE_CLAP_TRIGGER`
  - `CLAP_THRESHOLD`
  - `CLAP_MIN_GAP`
  - `CLAP_MAX_GAP`
  - `CLAP_COOLDOWN`
- TTS ganhou suporte/ajustes para providers e workers externos:
  - XTTS
  - StyleTTS2
  - Kokoro
  - Piper
  - Edge
  - RVC/fallbacks.

### Painel principal

- `src/ui/panel.html` recebeu:
  - controles de aparencia;
  - motion level;
  - densidade visual;
  - configuracoes de voz/STT/startup;
  - status visual de IA;
  - fases recentes de inicializacao;
  - integracao com API para salvar preferencias.
- O painel deve continuar sendo o centro de configuracao e observabilidade.

### Nexus modules e UI

- `src/ui/nexus_modules/` contem janelas HTML do Nexus, incluindo financas, habitos, notas, noticias, progresso, quiz, tarefas, goals, memory graph e ops.
- `src/ui/nexus_modules/nexus_frame.css` recebeu tokens de movimento, easing, animacao de entrada e `prefers-reduced-motion`.
- Melhorias visuais devem respeitar o estilo dark/neon/glass, mas com performance e legibilidade.

### Habitos

- A experiencia de marcar/desmarcar habitos foi otimizada:
  - feedback otimista imediato;
  - estado pending enquanto sincroniza;
  - rollback visual em caso de falha;
  - XP float imediato ao concluir.

### Estudos e notas

- `src/ui/nexus_modules/notes.html` foi evoluido para editor rico inline com markdown canonico.
- O usuario queria parar de editar `# Titulo` em um painel e ver o resultado apenas no preview. Agora a ideia e formatar no proprio editor.
- Recursos adicionados ao editor:
  - H1/H2/H3/H4;
  - paragrafos;
  - listas;
  - listas numeradas;
  - checklists clicaveis;
  - callouts;
  - bloco de codigo;
  - tabelas simples;
  - imagem por URL ou drop;
  - divisor;
  - slash menu expandido;
  - atalhos tipo Notion (`# `, `## `, `- `, `1. `, `[] `, `> `, tres crases + espaco).
- Markdown continua sendo o formato salvo para compatibilidade com IA, flashcards e banco atual.

### Noticias

- A direcao aprovada e manter janela dedicada de noticias, acionada por comando como:
  - "Abra o modo noticias e procure as ultimas noticias"
  - "Abra o modo noticias e procure noticias sobre IA"
- O painel deve permitir video, legenda/resumo em tempo real, fontes e historico.

### Operacoes

- Foi criado/ajustado `src/ui/nexus_modules/ops.html` para fechar contrato com servico/agente de operacoes/business.

### Documentacao ja existente

Leia tambem:

- `docs/2026-05-26-revisao-app-melhorias.md`
- `docs/superpowers/plans/2026-05-26-jarvis-agent-runtime-phase-1.md`
- `docs/superpowers/plans/2026-05-26-jarvis-agent-runtime-phase-2.md`
- `docs/superpowers/plans/2026-05-26-ui-motion-performance-phase.md`
- `docs/superpowers/plans/2026-05-26-affine-notes-polish-plan.md`

## Arquitetura atual relevante

- `src/main.py`: boot principal e montagem de servicos.
- `src/config.py`: settings vindas de `.env`.
- `src/runtime_status.py`: snapshot de runtime/startup.
- `src/ui/desktop_app.py`: bridge principal do painel e janelas.
- `src/ui/nexus_desktop_bridge.py`: bridge dos modulos Nexus.
- `src/ui/nexus_modules/*.html`: janelas HTML do Nexus.
- `src/database/nexus_db.py`: SQLite e dados do Nexus.
- `src/services/nexus_service.py`: regras de negocio do Nexus.
- `src/services/llm.py`: providers LLM.
- `src/services/stt.py`: speech-to-text.
- `src/services/tts.py`: text-to-speech.
- `src/tools/*.py`: tools disponiveis para agentes.
- `tests/`: testes de config, agentes, guardrails, Nexus, TTS, STT e UI contracts.

## Verificacoes executadas anteriormente

Comandos que passaram durante este chat:

```powershell
python -m pytest tests\test_config_defaults.py tests\test_stt_service_config.py tests\test_nexus_window_theme.py -q
```

Resultado anterior: `68 passed`.

```powershell
python -m pytest tests\test_agent_runtime_modes.py tests\test_agent_runtime_tool_schemas.py tests\test_agent_tool_guardrails.py tests\test_agent_action_executor.py tests\test_agent_prompt_runtime_context.py tests\test_agent_orchestrator_runtime.py tests\test_gemini_tools.py tests\test_llm_provider_order.py tests\test_prompts_vision.py tests\test_nexus_life.py -q
```

Resultado anterior: `123 passed`.

```powershell
python -m compileall src\config.py src\runtime_status.py src\main.py src\ui\desktop_app.py
```

Resultado anterior: exit code `0`.

Antes de afirmar sucesso novamente, rode verificacoes frescas.

## Proximo passo recomendado

Implementar "workflow recorder":

- Usuario abre apps/janelas e executa comandos.
- Usuario diz: "salve isso como modo estudo".
- Sistema captura snapshot de contexto:
  - apps abertos;
  - janelas Nexus abertas;
  - URLs relevantes;
  - playlist ou comando de musica;
  - timer/foco;
  - tools usadas.
- Sistema cria workflow editavel.
- Usuario pode dizer: "ative modo estudo" e o executor roda a sequencia com confirmacoes para acoes sensiveis.

Este e o maior upgrade para aproximar o app do comportamento Jarvis.

## Prompt curto para a proxima IA

Continue o Nexus Life OS em `D:\Documentos\Projeto AI`. Leia este arquivo, `docs/2026-05-26-revisao-app-melhorias.md` e o estado real do Git. Nao commite dados locais, `.env`, bancos, modelos, caches ou repos de referencia. Priorize o proximo ciclo: workflow recorder e automacao Jarvis natural, mantendo guardrails. Preserve markdown como formato canonico das notas enquanto melhora a UX inline estilo Notion/Affine. Valide com testes e scan de secrets antes de commit/push.
