# Revisao do app - melhorias aplicadas em 2026-05-26

## Decisoes tecnicas

- Manter o Jarvis/Nexus como produto principal e aproveitar o Hermes como referencia de arquitetura: toolsets por contexto, guardrails e comandos mais organizados.
- Reduzir trabalho pesado no boot: rastreador de visao/gestos e agente proativo passam a ser opcionais por configuracao.
- Preservar markdown como formato salvo das notas, mas trocar a experiencia principal para edicao rica inline no proprio painel.
- Manter feedback otimista nos habitos: a UI responde imediatamente e sincroniza em segundo plano.
- Deixar ajustes de STT/startup no painel para evitar edicoes manuais de `.env`/VS Code.

## Alteracoes implementadas

### Voz, STT e inicializacao

- Novas configuracoes persistentes:
  - `STT_ENERGY_THRESHOLD`
  - `STT_DYNAMIC_ENERGY`
  - `STT_PAUSE_THRESHOLD`
  - `STT_NON_SPEAKING_DURATION`
  - `STT_CALIBRATION_SECONDS`
  - `STT_MIN_AUDIO_SECONDS`
  - `START_VISION_TRACKER`
  - `START_HEARTBEAT`
  - `START_PROACTIVE_AGENT`
  - `ENABLE_CLAP_TRIGGER`
  - `CLAP_THRESHOLD`
  - `CLAP_MIN_GAP`
  - `CLAP_MAX_GAP`
  - `CLAP_COOLDOWN`
- O STT deixou de usar threshold fixo em `2500`; o default agora e mais sensivel (`1100`) e configuravel.
- O STT pode ser reconfigurado em tempo real pela API do painel.
- O boot agora importa/inicia rastreador de visao e heartbeat de forma condicional.
- O gatilho por duas palmas continua disponivel, mas agora pode ser ligado/desligado e calibrado.

### Painel de configuracoes

- Adicionada secao "Voz e STT" no painel principal.
- Adicionada secao "Inicializacao e Performance".
- Configuracoes sao salvas no `.env` via API do app.
- TTS, STT e opcoes de boot ficam mais acessiveis sem editar codigo.

### Habitos

- Marcar/desmarcar habitos agora atualiza visualmente na hora.
- Enquanto sincroniza, o item entra em estado `pending`.
- Se o backend falhar, o estado visual e revertido e uma mensagem aparece.
- O XP float aparece imediatamente ao concluir.

### Estudos e notas

- O editor de notas ganhou uma camada rica inline (`contenteditable`) sobre o markdown salvo.
- Titulos `#`, `##`, `###`, listas, tarefas, citacoes, imagens e divisores passam a aparecer formatados no proprio painel de edicao.
- O preview antigo continua no DOM para compatibilidade/TOC, mas nao ocupa mais a experiencia principal.
- O markdown segue sendo o formato gravado, para a IA continuar lendo e escrevendo notas com estabilidade.
- Foram adicionados marcadores/controles esperados para flashcards:
  - `studyStatus`
  - `btnOpenFlashcards`
  - `flashcard-card`

### Operacoes / Business

- Criado `src/ui/nexus_modules/ops.html`.
- O modulo declara e usa:
  - `ops_dashboard`
  - `ops_metric_set`
  - `opsDeck`
  - `opsRecommendations`
  - `opsNarrative`
  - `opsSignalReceipt`
- Isso fecha o contrato que ja existia no service/agente, mas estava sem janela.

## Verificacoes executadas

- `node -e ...` para validar scripts dos HTMLs alterados.
- `python -m pytest tests\test_config_defaults.py tests\test_stt_service_config.py tests\test_nexus_window_theme.py -q`
  - Resultado: `66 passed`
- `python -m pytest tests\test_agent_runtime_modes.py tests\test_agent_runtime_tool_schemas.py tests\test_agent_tool_guardrails.py tests\test_agent_action_executor.py tests\test_agent_prompt_runtime_context.py tests\test_agent_orchestrator_runtime.py tests\test_gemini_tools.py tests\test_llm_provider_order.py tests\test_prompts_vision.py tests\test_nexus_life.py -q`
  - Resultado: `123 passed`
- `python -m compileall src\config.py src\services\stt.py src\main.py src\ui\desktop_app.py src\check_audio.py`
  - Resultado: exit code `0`

## Proximas melhorias recomendadas

- Evoluir o editor rico para um motor dedicado, como ProseMirror/TipTap, quando a experiencia de notas ficar central no app.
- Adicionar medidor visual de volume do microfone no painel para calibrar STT e palmas com feedback ao vivo.
- Guardar preferencias de layout por modulo Nexus.
- Criar uma tela de workflows com gravacao: abrir apps/janelas, pedir para salvar como "Modo estudo", "Modo dormir", "Modo academia".
- Adicionar testes de browser para o editor inline e habitos otimistas.
- Medir tempo de boot com logs por fase para atacar o proximo gargalo real.

## Rodada 2 - motion, performance e editor Affine-like

### Referencia usada

- A pasta `Affine` foi usada como referencia conceitual, principalmente a ideia do BlockSuite de separar editor headless, componentes de toolbar, selecao de blocos e blocos ricos.
- Decisao racional: nao importar o BlockSuite agora, porque isso exigiria migracao grande de stack/build. O app atual segue com HTML/JS simples e markdown como formato canonico, que combina melhor com IA, flashcards e tools atuais.

### Painel principal e boot

- `RuntimeStatus` agora registra fases de inicializacao com `mark_startup_phase`.
- O painel principal renderiza as ultimas fases de startup em tempo real, com tempo acumulado em ms.
- Foram adicionadas preferencias de UI:
  - `UI_MOTION_LEVEL`
  - `UI_DENSITY`
- O painel ganhou controles de movimento/densidade em Configuracoes > Aparencia, sem editar `.env`.
- Status da IA agora troca classe visual entre espera, ouvindo e processando.

### Motion compartilhado do Nexus

- `nexus_frame.css` recebeu tokens de movimento, easing, animacao de entrada de conteudo e `prefers-reduced-motion`.
- Botoes e chrome do Nexus ganharam transicoes mais consistentes, mantendo os requisitos de neon/z-index ja cobertos por teste.

### Editor de notas estilo Notion/Affine

- O editor visivel continua sendo `contenteditable`, mas agora trata linhas como blocos com affordance visual ao hover/foco.
- Novos blocos suportados no editor rico:
  - titulo H1/H2/H3/H4
  - paragrafo
  - lista simples
  - lista numerada
  - checklist clicavel
  - callout
  - codigo em bloco
  - tabela simples
  - imagem por URL ou drop
  - divisor
- O slash menu foi ampliado para criar esses blocos diretamente.
- Atalhos inline agora funcionam como editor moderno:
  - `#` + espaco vira H1
  - `##` + espaco vira H2
  - `###` + espaco vira H3
  - `-` + espaco vira lista
  - `1.` + espaco vira lista numerada
  - `[]` + espaco vira tarefa
  - `>` + espaco vira citacao
- tres crases + espaco vira bloco de codigo
- Tarefas podem ser marcadas/desmarcadas no proprio editor e persistem como `- [x]` / `- [ ]`.
- Colar uma URL de imagem ou arrastar imagem para o editor cria bloco visual de imagem.
- Markdown continua sendo o formato salvo, mantendo compatibilidade com IA, flashcards e banco atual.

### Performance percebida

- Preview/sumario do editor passou a atualizar com debounce separado.
- Autosave foi reduzido para resposta mais rapida sem recalcular tudo a cada tecla.
- Ao salvar uma nota, a UI atualiza cache local, abas, sidebar e cards sem chamar `notes_list` imediatamente em todo save.

### Verificacoes da rodada 2

- Scripts HTML parseados com Node:
  - `panel.html`
  - `notes.html`
  - `habits.html`
  - `ops.html`
- Testes focados:
  - `python -m pytest tests\test_config_defaults.py tests\test_stt_service_config.py tests\test_nexus_window_theme.py -q`
  - Resultado: `68 passed`
- Testes de runtime/agentes/Nexus:
  - `python -m pytest tests\test_agent_runtime_modes.py tests\test_agent_runtime_tool_schemas.py tests\test_agent_tool_guardrails.py tests\test_agent_action_executor.py tests\test_agent_prompt_runtime_context.py tests\test_agent_orchestrator_runtime.py tests\test_gemini_tools.py tests\test_llm_provider_order.py tests\test_prompts_vision.py tests\test_nexus_life.py -q`
  - Resultado: `123 passed`
- Compile Python:
  - `python -m compileall src\config.py src\runtime_status.py src\main.py src\ui\desktop_app.py`
  - Resultado: exit code `0`
