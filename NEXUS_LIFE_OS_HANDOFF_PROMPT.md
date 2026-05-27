# Nexus Life OS - Handoff completo para continuar no Claude Code

Este arquivo é um prompt/contexto de handoff para outra IA continuar o projeto sem depender do histórico deste chat.

Use isto como a fonte principal de contexto antes de mexer no código. A ideia é continuar implementando o Nexus Life OS até ele ficar funcional, bonito e alinhado com a visão original: uma espécie de sistema operacional pessoal, com IA, finanças, hábitos, estudos, tarefas, metas, recompensas e progresso, tudo controlável por interface gráfica e por comandos de voz/texto.

## Como usar este arquivo no Claude Code

Cole este arquivo como contexto inicial para o Claude Code e peça para ele continuar a implementação no repositório.

Antes de implementar qualquer coisa:

1. Leia `NEXUS_CONTEXT_SUMMARY.md`.
2. Leia este arquivo inteiro.
3. Inspecione o estado real do código com `git status --short` e `rg`.
4. Não reverta mudanças não relacionadas. O worktree tem muitas alterações e arquivos não rastreados.
5. Use TDD para features e bugfixes: teste RED, implementar, teste GREEN.
6. Para mudanças visuais em janelas Nexus, faça QA renderizado com Browser/Playwright ou alternativa equivalente.
7. Não use CSS externo dentro dos módulos HTML do Nexus. O CSS do módulo precisa ficar inline no próprio arquivo `.html`.

## Visão do produto

O Nexus Life OS é um sistema de produtividade pessoal gamificado, com IA como operador central.

O usuário quer uma interface estilo "Jarvis", com visual moderno, dark neon glassmorphism, bordas arredondadas com linhas neon e suporte a tema claro/escuro. O app deve parecer um painel pessoal avançado, mas também precisa ser útil de verdade no dia a dia, não só bonito.

A IA deve conseguir operar o sistema por comandos naturais, por exemplo:

- "Adicione o gasto de hoje de 150 reais em mousepad."
- "Adicione o lucro de ontem de 800 reais com freelancing."
- "Corrija o gasto com mousepad para 175 reais."
- "Apague o gasto com lanche de ontem."
- "Marque academia como concluída."
- "Crie um preset para passar no ENEM, juntar dinheiro e conseguir o shape dos sonhos."
- "Resgatar episódio de anime."
- "Crie flashcards dessa nota."
- "Me explique essa matéria como professor."
- "Gere um simulado do ENEM."
- "O que eu devo estudar agora?"

O sistema deve ter duas formas equivalentes de uso:

- Manualmente pela interface gráfica.
- Automaticamente pela IA, usando comandos estruturados e linguagem natural.

## Pilares principais do Nexus Life OS

### 1. Finanças pessoais avançadas

Objetivo: registrar dinheiro com o menor atrito possível, pela IA ou manualmente.

Requisitos da ideia original:

- Registrar despesas e receitas com data flexível:
  - hoje
  - ontem
  - anteontem
  - datas específicas
- Registrar por comando natural:
  - "adicione o gasto de hoje, de 150 reais em mousepad"
  - "adicione lucro de 1200 reais de cliente ontem"
- Ver lucro/prejuízo por mês.
- Navegar entre meses.
- Ver dias específicos.
- Adicionar observações.
- Editar/corrigir transações.
- Apagar transações.
- Ver ganhos totais.
- Ver resultado líquido considerando dívidas:
  - ganhos menos despesas
  - ganhos menos dívidas
  - despesas não relacionadas a dívida
  - percentual de renda comprometido com dívida
- Marcar uma despesa como dívida.
- Mostrar gráficos e categorias.
- Interface deve ser bonita, densa e eficiente, com tema neon igual ao painel.

### 2. Hábitos, tarefas e gamificação

Objetivo: criar um sistema de rotina que ajude o usuário a executar objetivos reais, com streaks, XP, loja de recompensas e IA criando planos.

Requisitos da ideia original:

- Criar hábitos diários ou semanais.
- Selecionar dias da semana em que o hábito vale.
- Marcar hábitos como concluídos.
- Remover/arquivar hábitos.
- Criar tarefas pontuais.
- Concluir tarefas.
- Streak por hábito:
  - contar dias consecutivos em que o hábito foi feito nos dias selecionados.
- Streak global:
  - contar dias em que todos os hábitos esperados foram concluídos.
- Gráfico/heatmap de conclusão.
- Barra de progresso.
- XP e pontos.
- Loja de recompensas:
  - gastar pontos para "episódio de anime", "1h de games", "sorvete", "dia livre", etc.
  - apenas 1 item por dia.
- IA cria presets de hábitos com base em objetivos:
  - "Passar no ENEM"
  - "Juntar dinheiro para investir"
  - "Conseguir shape dos sonhos"
- Preset atual pode ser salvo.
- Preset criado pela IA pode substituir os hábitos atuais.
- O app deve funcionar como um habit tracker normal, mas com IA reduzindo o atrito.

### 3. Estudos / MindPalace

Objetivo: misturar Notion/Obsidian + Anki + professor particular + simulados.

Requisitos da ideia original:

- Janela de estudos/anotações parecida com Notion ou Obsidian.
- Sistema de abas/notas.
- Matérias/assuntos separados.
- Cada matéria pode ter várias notas.
- Abrir uma nota e pedir para a IA:
  - escrever conteúdo nela
  - resumir texto existente
  - complementar conteúdo
  - explicar conteúdo
  - responder perguntas sobre a nota aberta
  - adicionar imagens/referências
- Capturar conteúdo de uma página do navegador/tela e transformar em anotação resumida.
- Criar flashcards a partir:
  - de uma nota
  - de uma matéria inteira
  - dos erros de um simulado
- Flashcards ficam em aba/janela separada.
- Revisão com repetição espaçada.
- IA lembra assuntos não memorizados.
- Pode haver integração entre revisões pendentes e hábitos/tarefas.
- Modo professor:
  - IA explica assunto
  - faz perguntas
  - mostra pontos-chave
  - sugere próximos estudos
- Simulados tipo ENEM:
  - usar bases open-source futuramente
  - gerar simulado
  - corrigir
  - detectar assuntos fracos
  - gerar flashcards dos erros
- Aba Progresso:
  - taxa de acerto
  - gráficos
  - assuntos a melhorar
  - sugestões de IA

## Arquitetura atual do projeto

O projeto é um app Python com SQLite e UI desktop via `pywebview`.

Arquivos e responsabilidades principais:

- `src/database/nexus_db.py`
  - camada SQLite
  - tabelas de usuário, hábitos, logs, finanças, notas, flashcards, tarefas, recompensas, metas, quiz e estatísticas
- `src/services/nexus_service.py`
  - regra de negócio central do Nexus
  - comandos estruturados
  - recibos/aberturas de janelas
  - geração de flashcards
  - modo professor
  - finanças
  - recompensas
  - recomendações de estudo
- `src/ui/nexus_desktop_bridge.py`
  - bridge JS -> Python usada pelas janelas desktop
  - recebe `nxBridge(method, args)` e chama `NexusService`/`NexusDatabase`
- `src/ui/desktop_app.py`
  - cria janelas `pywebview`
  - compõe HTML dos módulos
  - injeta wrapper visual, tema e `window.__NEXUS_BOOT__`
- `src/ui/nexus_modules/*.html`
  - módulos desktop do Nexus
  - cada janela é um arquivo HTML
- `src/ui/nexus_modules/nexus_boot.js`
  - função `nxBridge`
  - leitura do boot payload
  - tema claro/escuro
- `src/ui/nexus_modules/nexus_frame.css`
  - chrome/frame geral das janelas Nexus
  - bordas neon, wrapper, tema
- `src/skills/nexus_manager.py`
  - interpreta comandos naturais locais
  - exemplos: finanças, hábitos, recompensas, presets, estudos
- `src/agent/gemini_tools.py`
  - schema/ferramentas para Gemini/OpenAI chamarem `nexus_command`
- `tests/test_nexus_life.py`
  - testes de regra de negócio e bridge
- `tests/test_nexus_quiz.py`
  - testes de quiz/simulados/flashcards dos erros
- `tests/test_nexus_window_theme.py`
  - testes estáticos dos módulos HTML e contrato visual/JS
- `tests/test_gemini_tools.py`
  - testes dos schemas de ferramentas de IA

## Regra crítica para UI das janelas

Existe uma armadilha importante: os módulos HTML são injetados por `desktop_app.py` dentro de um frame com `nexus_frame.css`.

Por isso:

- Não use `<link rel="stylesheet">` novo dentro de `finance.html`, `habits.html`, etc.
- Não crie CSS externo para um módulo.
- Coloque o CSS do módulo dentro de `<style>` no próprio arquivo.
- Use seletores específicos com `#nx-app-wrapper` quando necessário.
- Se mexer em botões, inputs, cards, headers, etc., lembre que `nexus_frame.css` pode sobrescrever estilos globais.
- Teste a janela renderizada, não só o HTML cru.

Documentação útil:

- `docs/NEXUS_WINDOW_STYLING_GUIDE.md`
- `NEXUS_CONTEXT_SUMMARY.md`

## Estado atual implementado

Esta seção resume o que já existe no projeto conforme o estado atual do código e verificações feitas.

### Frame, janelas e tema

Implementado:

- `desktop_app.py` compõe os módulos com wrapper `#nx-app-wrapper`.
- Existe chrome comum "Nexus Life OS".
- Existe toggle de tema claro/escuro via `nexus_boot.js`.
- Existe `nexus_frame.css` com contrato de tema e neon.
- Janelas têm estética dark/neon/glassmorphism.
- Há testes garantindo:
  - wrapper de tema
  - toggle
  - contrato de light theme
  - neon atrás da superfície interna

Importante:

- O visual dos módulos deve continuar inline.
- Se o próximo agente mudar a UI, testar desktop e mobile quando possível.

### Overview / Dashboard

Arquivo:

- `src/ui/nexus_modules/overview.html`

Implementado:

- Dashboard principal do Nexus.
- Widgets de finanças, hábitos, estudos, metas/recompensas.
- Botões para abrir módulos:
  - Hábitos
  - Finanças
  - Tarefas
  - Notas
  - Flashcards
  - Progresso
  - Loja/Metas
  - Quiz
- Mostra resumo diário:
  - hábitos feitos/total
  - revisões SRS pendentes
  - finanças rápidas
  - recompensas
- Usa bridge para:
  - `user_stats`
  - `global_streak`
  - `habits_list`
  - `finance_snapshot`
  - `flashcards_due`
  - `study_stats_list`
  - `rewards_list`
  - `goals_list`

Ainda pode melhorar:

- Mais densidade de informações.
- Estados vazios mais ricos.
- Ações rápidas reais diretamente no dashboard.
- Personalização de layout.

### Finanças

Arquivos:

- `src/ui/nexus_modules/finance.html`
- `src/services/nexus_service.py`
- `src/database/nexus_db.py`
- `src/ui/nexus_desktop_bridge.py`
- `src/skills/nexus_manager.py`
- `src/agent/gemini_tools.py`

Implementado:

- Adicionar receita/despesa.
- Data por `occurred_at`.
- Observações por `notes`.
- Marcação `is_debt` para dívidas.
- Listar transações por período.
- Apagar transação.
- Editar transação existente.
- Atualização pode ser por ID ou por busca aproximada:
  - descrição
  - categoria
  - data
  - valor
- IA/manager entende correções como:
  - "corrija o gasto com mousepad de hoje para 175 reais"
- `finance_update` existe no service, bridge e tool schema.
- Janela financeira tem:
  - navegação mensal
  - cards de resumo
  - filtro de transações
  - gráfico/tendência visual simples
  - gráfico por categoria
  - painel de insights
  - formulário de add/edit
  - toggle "dívida"
  - campo de observações
  - botões de editar/apagar
- `get_finance_snapshot` expõe `finance_insights`:
  - `cash_after_debt`
  - `non_debt_expense`
  - `debt_ratio_pct`
  - `expense_ratio_pct`
  - `free_after_all_expenses`
- A UI usa "saldo após dívidas" no card de dinheiro livre.

Testes relevantes:

- `test_finance_snapshot_exposes_debt_adjusted_insights`
- `test_finance_update_by_id_edits_transaction_and_enqueues`
- `test_structured_finance_update_finds_transaction_by_description`
- `test_desktop_bridge_updates_finance_transaction`
- `test_nexus_manager_understands_update_expense_amount`
- `test_finance_declares_advanced_monthly_control_panel`
- `test_finance_declares_edit_controls_and_update_bridge`

QA visual feito:

- Janela financeira testada com servidor mock.
- Filtro de dívidas testado.
- Edit mode testado.
- Screenshots salvos em `C:\Users\jamil\AppData\Local\Temp\...` durante as sessões.

O que ainda falta em finanças:

- Orçamentos mensais por categoria.
- Gastos recorrentes.
- Parcelas/dívidas recorrentes com saldo restante.
- Contas/carteiras separadas.
- Gráfico mais robusto com biblioteca ou canvas melhor.
- Relatório anual.
- Exportação CSV/JSON.
- Comandos naturais mais abrangentes:
  - "quanto gastei com comida esse mês?"
  - "qual foi meu lucro de março?"
  - "liste minhas dívidas"
  - "registre uma dívida parcelada"
- Melhor UX de busca por dia específico.

### Hábitos

Arquivos:

- `src/ui/nexus_modules/habits.html`
- `src/services/nexus_service.py`
- `src/database/nexus_db.py`
- `src/ui/nexus_desktop_bridge.py`
- `src/tools/habit_tracker.py`

Implementado:

- Listar hábitos.
- Adicionar hábito.
- Concluir hábito.
- Arquivar/deletar hábito.
- XP e pontos ao concluir.
- Streak por hábito.
- Streak global.
- Histórico/heatmap visual.
- Dias da semana por hábito (`days_of_week`).
- Presets salvos de hábitos.
- Aplicar preset substituindo hábitos ativos.
- Salvar preset atual.
- Listar presets.
- Preset gerado por objetivos:
  - textarea `presetGoals`
  - botão `btnPresetFromGoals`
  - preview de ideias `goalPresetIdeas`
  - chamada `preset_from_goals`
- IA cria hábitos específicos a partir de objetivos como ENEM/shape/dinheiro.
- Receipts/boot animations para hábito concluído e presets.

Testes relevantes:

- streaks
- conclusão de hábito
- preset JSON
- preset por objetivos
- preservação de dias da semana
- controles visuais de preset
- ausência de mojibake em alguns textos

O que ainda falta em hábitos:

- UX mais completa para editar hábito existente.
- Melhor visual para calendário semanal/mensal.
- Estatísticas por hábito:
  - melhor horário
  - taxa de conclusão
  - tendência
- Pausar hábito.
- Dificuldade/importância.
- Integração automática com revisões SRS pendentes:
  - exemplo: criar tarefa/hábito "Revisar flashcards" quando houver flashcards vencidos.
- Regras mais refinadas de streak por dias selecionados.
- Presets com confirmação/preview antes de substituir hábitos.
- Biblioteca de presets prontos:
  - ENEM
  - Shape
  - Investidor
  - Sono
  - Disciplina geral

### Tarefas

Arquivo:

- `src/ui/nexus_modules/tasks.html`

Implementado:

- Listar tarefas.
- Criar tarefa.
- Concluir tarefa.
- Apagar tarefa.
- Prazo (`due_date`).
- Pontos por tarefa (`points_reward`).
- Bridge:
  - `task_list`
  - `task_add`
  - `task_complete`
  - `task_delete`

O que ainda falta em tarefas:

- Editar tarefa.
- Prioridades.
- Recorrência.
- Kanban ou agrupamento.
- Integração visual melhor com hábitos.
- Criação automática a partir de estudo:
  - "revisar flashcards SRS hoje"
  - "refazer erros do simulado"

### Metas e Loja de Recompensas

Arquivos:

- `src/ui/nexus_modules/goals.html`
- `src/services/nexus_service.py`
- `src/database/nexus_db.py`
- `src/ui/nexus_desktop_bridge.py`

Implementado:

- Listar metas.
- Criar nova meta.
- Atualizar progresso de meta por IA/bridge.
- Listar recompensas.
- Resgatar recompensa.
- Pontos são descontados.
- Regra de 1 resgate por dia via tabela `reward_redemptions`.
- `reward_status` retorna:
  - data atual
  - pontos
  - `daily_limit`
  - `remaining_today`
  - `next_available_date`
  - `reset_at`
  - `redeemed_today`
  - recompensa de hoje
  - histórico recente
- UI `goals.html` mostra:
  - pontos atuais
  - status da loja
  - painel de regra diária (`rewardRulePanel`)
  - limite diário
  - restante hoje
  - próxima janela
  - histórico recente (`rewardHistoryList`)
  - cards bloqueados após resgate
  - motivo do bloqueio:
    - limite diário atingido
    - sem pontos
    - liberado hoje
- Botões ficam desabilitados quando não podem resgatar.

Testes relevantes:

- `test_structured_command_redeems_reward_and_updates_goal`
- `test_reward_status_exposes_daily_limit_reset_and_history`
- `test_goals_declares_reward_status_for_one_per_day_rule`
- `test_goals_declares_reward_rule_history_and_reset_panel`

QA visual feito na última sessão:

- Browser plugin:
  - abriu `http://127.0.0.1:14214/goals`
  - título correto
  - DOM não vazio
  - sem overlay de framework
  - sem warnings/errors no console
  - resgate mudou status para "Loja usada hoje"
  - contador restante foi de `1` para `0`
  - histórico passou a conter "Episodio de Anime"
  - primeiro botão ficou desabilitado
- Python Playwright:
  - gerou screenshots desktop, pós-resgate e mobile
  - console sem erros

Screenshots temporários:

- `C:\Users\jamil\AppData\Local\Temp\nexus-goals-reward-rule-desktop.png`
- `C:\Users\jamil\AppData\Local\Temp\nexus-goals-reward-rule-after-redeem.png`
- `C:\Users\jamil\AppData\Local\Temp\nexus-goals-reward-rule-mobile.png`

O que ainda falta na loja:

- Criar recompensas customizadas pela UI.
- Editar custo/descrição da recompensa.
- Categorias de recompensa.
- Recompensas bloqueadas por objetivo.
- Recompensas especiais semanais/mensais.
- Histórico com filtros.
- Explicar melhor para o usuário por que só pode 1 por dia.
- Talvez permitir "cupom" ou exceção comprada com pontos altos.

### MindPalace / Notas

Arquivo:

- `src/ui/nexus_modules/notes.html`

Implementado:

- Listar notas.
- Abrir nota.
- Criar nota.
- Salvar/patch.
- Apagar nota.
- Separar por matéria/subject.
- Resumir nota.
- Modo professor para nota (`note_teach`).
- Modo professor por matéria (`subject_teach`).
- Botão "Professor da matéria" (`btnSubjectTeacher`).
- Anexar mídia/imagens a notas (`note_attach_media`).
- Gerar flashcards da nota atual.
- Gerar flashcards da matéria inteira.
- Preview dos flashcards gerados:
  - painel `flashcardPreview`
  - lista `flashcardPreviewList`
  - botão `btnOpenFlashcards`
  - cards com frente/resposta
- Receipts para:
  - resumo
  - professor
  - professor da matéria
  - mídia anexada
  - flashcards gerados

Backend relacionado:

- `teach_note`
- `teach_subject`
- `generate_flashcards_from_note`
- `generate_flashcards_from_subject`
- `_insert_flashcards`

Testes relevantes:

- geração de flashcards por nota
- bridge gera flashcards
- professor da nota
- professor da matéria
- comando estruturado `subject_teach`
- controles de UI de flashcards e professor
- preview de flashcards

O que ainda falta no MindPalace:

- Editor rico de verdade:
  - Markdown toolbar
  - imagens inline
  - checklist
  - headings
  - links
  - blocos
- Abas reais estilo Notion/Obsidian.
- Backlinks e grafo de conhecimento.
- Capturar conteúdo de navegador/tela automaticamente.
- IA realmente usar visão/tela para criar nota.
- Melhor organização por pastas/matérias.
- Busca global.
- Tags.
- Exportação.
- Histórico/versionamento de nota.
- Modo professor com LLM real, se ainda estiver heurístico/local.

### Flashcards / SRS

Arquivo:

- `src/ui/nexus_modules/study.html`

Implementado:

- Listar flashcards devidos.
- Esconder resposta até revelar.
- Revisão com qualidade 0-5.
- SM-2 no backend.
- Receipts quando flashcards são gerados de nota ou quiz.
- Diferencia origem:
  - nota/matéria
  - erros do Quiz ENEM

Backend:

- `list_flashcards_due`
- `review_flashcard_sm2`
- `flashcard_review`
- `flashcards_due`
- `flashcards_generate`

Testes:

- esconder respostas até revelar
- receipts de geração
- label de origem Quiz ENEM
- geração de flashcards por nota/matéria/quiz

O que ainda falta em SRS:

- Tela de calendário de revisão.
- Estatísticas de memorização.
- Decks por matéria.
- Suspender/deletar/editar card.
- Criar card manualmente.
- Reprogramar card.
- Integrar com hábitos/tarefas:
  - quando houver cards pendentes, sugerir/criar tarefa "Revisar flashcards SRS".
- Notificações/lembretes.
- Sessão focada com cronômetro.

### Quiz / Simulados ENEM

Arquivo:

- `src/ui/nexus_modules/quiz.html`

Implementado:

- Banco seed de questões.
- Sortear questões.
- Iniciar tentativa.
- Registrar respostas.
- Calcular score.
- Revisão da tentativa:
  - acertos
  - erros
  - explicação
  - skill/área
  - pontos fracos
  - próximas ações
- Gerar flashcards dos erros.
- Idempotência para não duplicar flashcards do mesmo erro.
- Botão para revisar flashcards depois de criá-los.

Backend:

- `seed_quiz_if_empty`
- `quiz_random`
- `quiz_attempt_start`
- `quiz_answer`
- `review_quiz_attempt`
- `generate_flashcards_from_quiz_attempt`
- `quiz_flashcards_generate`

Testes:

- quiz review
- flashcards dos erros
- idempotência
- bridge
- structured command
- UI oferece revisão direta

O que ainda falta no Quiz:

- Importar bases open-source reais do ENEM.
- Simulado completo com tempo.
- Tela de resultado mais detalhada.
- Refazer apenas erros.
- Filtro por área/dificuldade/competência.
- Questões com imagens.
- Ranking de assuntos mais fracos.
- Gerar plano de estudo automático pós-simulado.

### Progresso / Recomendações

Arquivo:

- `src/ui/nexus_modules/progress.html`

Implementado:

- Painel geral de estudos.
- Métricas:
  - acerto geral
  - questões feitas
  - flashcards pendentes
  - foco agora
- Painel "Professor Nexus" com próximas ações.
- Lista de pontos fracos.
- Gráfico visual por matéria.
- Tabela/lista detalhada por matéria.
- Chama `study_recommendations`.

Backend:

- `get_study_recommendations`
- considera:
  - estatísticas de estudo
  - flashcards pendentes
  - matérias fracas
  - próximas ações sugeridas

Testes:

- `test_study_recommendations_rank_weak_subjects_and_due_reviews`
- `test_progress_declares_study_recommendations_panel`
- `test_progress_declares_study_strategy_cockpit`
- `test_progress_declares_visual_study_chart`

O que ainda falta no Progresso:

- Botão para transformar flashcards pendentes em tarefa de hoje.
- Plano semanal de estudo.
- Gráficos reais e mais bonitos.
- Evolução temporal.
- Comparação entre simulados.
- Estimativa de prioridade/impacto.
- Recomendações com ações executáveis:
  - criar flashcards
  - criar tarefa
  - abrir matéria
  - fazer quiz filtrado

### IA, comandos estruturados e voz/texto

Arquivos:

- `src/services/nexus_service.py`
- `src/skills/nexus_manager.py`
- `src/agent/gemini_tools.py`
- `src/tools/nexus.py`

Implementado:

- `handle_structured_command` com várias ações.
- `nexus_command` descrito para Gemini/OpenAI.
- Ações anunciadas no schema:
  - `finance_add`
  - `finance_list`
  - `finance_delete`
  - `finance_update`
  - `habit_complete`
  - `habit_add`
  - `task_add`
  - `task_complete`
  - `task_delete`
  - `task_list`
  - `goal_add`
  - `goal_update`
  - `reward_redeem`
  - `reward_status`
  - `preset_apply_json`
  - `preset_from_goals`
  - `open_ui`
  - `note_list`
  - `note_get`
  - `note_save`
  - `note_append`
  - `note_summarize`
  - `note_teach`
  - `subject_teach`
  - `note_attach_media`
  - `flashcards_generate`
  - `flashcard_review`
  - `flashcards_due`
  - `quiz_random`
  - `quiz_attempt_review`
  - `quiz_flashcards_generate`
  - `study_recommendations`
- `NexusManagerSkill` entende algumas frases naturais de:
  - finanças
  - apagar despesa
  - corrigir valor
  - resgatar recompensa
  - criar preset por objetivo
  - concluir hábito
  - modo foco
  - acerto/erro em estudos

O que ainda falta em IA:

- Cobertura muito maior de linguagem natural.
- Resolver ambiguidades com confirmação visual quando necessário.
- Conectar LLM real para:
  - gerar planos melhores
  - professor mais inteligente
  - resumos de notas
  - criação de flashcards melhores
- Memória pessoal de preferências.
- Comandos compostos:
  - "adicione esse gasto e me mostre o mês"
  - "crie hábitos para ENEM e já salve como preset"
  - "transforme meus erros do último simulado em flashcards"
- Voz universal mais robusta.

## Estado de testes e verificação recente

Última verificação relevante feita nesta sessão:

```powershell
python -m py_compile src\services\nexus_service.py
```

Resultado:

- exit code 0

Suite principal:

```powershell
python -m pytest tests\test_nexus_life.py tests\test_nexus_quiz.py tests\test_nexus_window_theme.py tests\test_gemini_tools.py -q
```

Resultado:

- `84 passed in 126.51s`

Observação:

- Esse resultado foi obtido depois da implementação da loja/reward status.
- Depois disso, houve uma tentativa curta de começar uma nova fatia em `progress.html`, mas o teste RED adicionado foi removido para não deixar trabalho pela metade quando o usuário pediu este handoff.

## Últimas mudanças importantes feitas

### 1. Finanças com insights ajustados por dívida

Implementado:

- `finance_insights` em `get_finance_snapshot`
- UI de Finanças usa `cash_after_debt`
- Painel mostra "Saldo após dívidas"
- Testes verdes

### 2. Preview de flashcards no MindPalace

Implementado:

- `flashcardPreview`
- `flashcardPreviewList`
- `btnOpenFlashcards`
- `renderFlashcardPreview`
- Preview após gerar flashcards de nota ou matéria
- Testes verdes

### 3. Loja com regra explícita de 1 resgate por dia

Implementado:

- `get_reward_status` retorna limite/restante/reset/histórico
- `goals.html` mostra:
  - painel de regra
  - histórico recente
  - cards prontos/bloqueados
  - razão do bloqueio
- QA renderizado feito
- Suite principal verde

## Worktree e cuidado com git

O worktree está sujo e contém muitas alterações não relacionadas. Não use:

```powershell
git reset --hard
git checkout -- .
```

Não reverta arquivos aleatórios.

Muitos módulos e testes do Nexus estão como não rastreados em `git status`, por exemplo:

- `src/ui/nexus_modules/`
- `src/ui/nexus_desktop_bridge.py`
- `tests/test_nexus_life.py`
- `tests/test_nexus_quiz.py`
- `tests/test_nexus_window_theme.py`

Isso não significa que devem ser apagados. Eles fazem parte do trabalho atual do Nexus.

## Próxima ordem recomendada de implementação

O usuário pediu para não perguntar muito e escolher a ordem que fizer mais sentido. A ordem abaixo é recomendada por impacto.

### Prioridade 1 - Fechar integração SRS -> tarefas/hábitos

Objetivo:

- Quando houver flashcards pendentes, permitir criar uma tarefa do dia:
  - "Revisar flashcards SRS"
  - prazo hoje
  - pontos proporcionais ou fixos

Onde mexer:

- `src/ui/nexus_modules/progress.html`
- talvez `src/services/nexus_service.py`
- talvez `src/ui/nexus_desktop_bridge.py` se precisar método mais específico

Implementação mínima:

- Em `progress.html`, armazenar quantidade de flashcards pendentes.
- Adicionar botão no painel de ações:
  - `id="btnCreateSrsTask"`
  - status `id="srsTaskStatus"`
- Ao clicar:
  - chamar `nxBridge('task_add', { title: 'Revisar flashcards SRS', due_date: hoje, points_reward: 30 })`
  - mostrar status
  - opcionalmente abrir `tasks`

Teste sugerido:

- `tests/test_nexus_window_theme.py`
- teste estático exigindo:
  - `btnCreateSrsTask`
  - `srsTaskStatus`
  - `createSrsTask`
  - `task_add`
  - `flashcardsDueForTask`

Depois fazer QA renderizado.

### Prioridade 2 - Editar hábitos

Objetivo:

- O usuário precisa conseguir ajustar hábito sem apagar e recriar.

Implementação:

- Backend:
  - `update_habit`
- Bridge:
  - `habit_update`
- UI:
  - botão editar em `habits.html`
  - reusar formulário
  - editar nome, descrição, XP, dias da semana
- Manager/IA:
  - entender "mude academia para segunda quarta sexta"

### Prioridade 3 - Recompensas customizadas

Objetivo:

- Usuário criar itens da própria lojinha:
  - sorvete
  - anime
  - folga
  - cinema
  - etc.

Implementação:

- Backend:
  - add/update/delete reward
- Bridge:
  - `reward_add`
  - `reward_update`
  - `reward_delete`
- UI `goals.html`:
  - formulário compacto para nova recompensa
  - edição de custo

### Prioridade 4 - Captura de conteúdo para MindPalace

Objetivo:

- O usuário abrir página/artigo e pedir para a IA transformar em nota.

MVP:

- Criar método:
  - `note_capture`
  - recebe título, conteúdo/texto, url, subject
  - salva nota com fonte
- UI:
  - campo "colar artigo/texto"
  - botão "Transformar em nota"
- Futuro:
  - integração com visão/tela/navegador.

### Prioridade 5 - Simulados ENEM mais reais

Objetivo:

- Mais questões e sessão de simulado completa.

MVP:

- Importar JSON/CSV de questões.
- Melhorar `seed_quiz_if_empty`.
- Criar modo:
  - 10 questões
  - 30 questões
  - simulado completo
- Timer.
- Resultado por área/skill.

### Prioridade 6 - Gráficos e polish visual

Objetivo:

- Deixar o projeto "tinindo" visualmente.

Módulos a polir:

- `progress.html`
- `finance.html`
- `habits.html`
- `overview.html`

Melhorias:

- gráficos mais sofisticados
- responsividade mobile
- estados vazios ricos
- microinterações
- contraste no tema claro
- evitar texto truncado em cards

## Lista de comandos úteis

Rodar suite principal:

```powershell
python -m pytest tests\test_nexus_life.py tests\test_nexus_quiz.py tests\test_nexus_window_theme.py tests\test_gemini_tools.py -q
```

Rodar testes de janela:

```powershell
python -m pytest tests\test_nexus_window_theme.py -q
```

Rodar testes de regra Nexus:

```powershell
python -m pytest tests\test_nexus_life.py -q
```

Compilar service:

```powershell
python -m py_compile src\services\nexus_service.py
```

Procurar métodos bridge:

```powershell
rg -n "if m ==|reward_status|finance_update|flashcards_generate|study_recommendations" src\ui\nexus_desktop_bridge.py
```

Procurar contratos nos módulos:

```powershell
rg -n "finance_insights|rewardRulePanel|flashcardPreview|presetGoals|subject_teach" src tests
```

## Critérios de qualidade para continuar

Para cada nova fatia:

1. Escrever teste primeiro.
2. Ver o teste falhar pelo motivo certo.
3. Implementar o mínimo.
4. Rodar teste focado.
5. Rodar suite relevante.
6. Se for UI, renderizar e testar interação.
7. Não deixar servidor temporário rodando.
8. Não deixar teste RED pendente.
9. Atualizar este handoff ou criar novo resumo se o chat acabar.

## Prompt curto para o próximo agente

Use este prompt se quiser ser direto no Claude Code:

> Continue o Nexus Life OS neste repositório. Leia `NEXUS_LIFE_OS_HANDOFF_PROMPT.md` e `NEXUS_CONTEXT_SUMMARY.md`. Não pergunte a menos que seja indispensável. Use TDD, não reverta mudanças não relacionadas, e mantenha o visual das janelas em dark/neon glassmorphism com tema claro/escuro. O próximo melhor passo é integrar flashcards SRS pendentes com tarefas/hábitos, depois editar hábitos, recompensas customizadas e captura de conteúdo para MindPalace. Rode os testes relevantes e faça QA visual quando mexer em HTML.

## Resumo executivo

O Nexus Life OS já tem uma base bem avançada:

- janelas desktop com pywebview
- tema neon claro/escuro
- dashboard
- finanças com add/edit/delete, dívidas, insights e gráficos
- hábitos com XP, streak, heatmap e presets por IA
- tarefas
- metas e loja com limite de 1 resgate por dia
- notas/MindPalace
- professor por nota e por matéria
- flashcards SRS
- quiz/simulado básico
- flashcards dos erros do quiz
- progresso com recomendações
- comandos estruturados para IA
- testes cobrindo muita coisa

O que ainda falta para ficar exatamente como a visão original:

- mais automação natural por voz/texto
- editor de notas mais rico
- captura de navegador/tela para notas
- integração SRS com hábitos/tarefas
- simulados ENEM com base real e fluxo completo
- edição completa de hábitos/recompensas
- gráficos mais fortes
- relatórios financeiros mais avançados
- polish visual final em todos os módulos

O projeto está no caminho certo. Continue por fatias pequenas, sempre verificadas, sem quebrar a arquitetura de módulos inline.
