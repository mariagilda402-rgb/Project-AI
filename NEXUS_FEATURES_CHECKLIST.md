# Nexus Life OS — checklist de funcionalidades

Referência do objetivo: **vida pessoal integrada** (finanças, hábitos, estudos, tarefas, progresso) com **mesma base de dados** para ti e para a IA (`nexus_command` / `run_finance_command`), agora com **módulos em janelas desktop** (tema claro minimalista) em vez de depender do HUD web.

## Infra e dados

- [x] SQLite central `data/nexus.db` (NexusDatabase)
- [x] Telemetria em ações relevantes (API / hábitos / flashcards)
- [x] Notificação opcional ao HUD web (`/api/nexus_event`) quando o visualizador corre

## Finanças (Aether)

- [x] Transações receita/despesa com `occurred_at`, notas, marcação de dívida
- [x] Resumo mensal + lista no módulo desktop **Finanças**
- [x] Registo rápido no desktop (equivalente a `finance_add` / REST POST)
- [x] Abrir janela ao `finance_add` pela IA (toast no boot)

## Hábitos (Chronos)

- [x] Hábitos ativos, streak, XP ao concluir
- [x] CRUD desktop: adicionar, concluir hoje, arquivar (`habit_add` / `habit_complete` / soft delete)
- [x] Preset JSON de hábitos (`preset_apply_json`) + abertura animada da janela Hábitos
- [x] Ao `habit_add` pela IA: fila → janela **Hábitos** com highlight do novo id

## Tarefas

- [x] Lista, criar, concluir, apagar (`task_*` no bridge)
- [x] Módulo desktop **Tarefas**
- [x] Ao `task_add` pela IA: highlight na janela

## Notas (MindPalace)

- [x] Listar / obter / criar / patch / apagar (`study_notes`)
- [x] Módulo desktop **Notas**
- [x] Ao `note_save` pela IA: abrir **Notas** com highlight do id (quando disponível)

## Estudo SRS

- [x] Flashcards devidos, revisão SM-2 (`flashcard_review`)
- [x] Módulo desktop **SRS**

## Progresso / simulados

- [x] Estatísticas por área (`study_stats`)
- [x] Módulo desktop **Progresso** (tabela)
- [x] Quiz seed + `quiz_random` / REST `/api/nexus/quiz/sample`
- [x] Módulo desktop **Quiz** (uma questão de cada vez, pontuação, `study_log_result` + `quiz_attempts`)

## Metas e loja (dados existentes)

- [x] Metas na BD + notificador HUD
- [x] UI desktop **Metas e recompensas** (listar / nova meta / progresso / listar recompensas / resgatar com regra 1/dia)
- [x] Recompensas e resgate via serviço + módulo desktop

## Navegação e IA

- [x] `open_ui` / `open_nexus_ui(tab)` → janela desktop mapeada (dashboard→overview, board→tasks, …)
- [x] Uma janela Nexus de cada vez: abrir módulo fecha o anterior
- [x] Fila `nexus_signals` + janela scheduler oculta para abrir a partir do worker da IA
- [x] Painel → Configurações: botões para cada módulo
- [x] Botão chat “Nexus” → overview desktop (fallback navegador se `APP_INSTANCE` indisponível)

## HUD web (legado)

- [x] `http://localhost:5123/nexus/` (Vite) mantido para quem preferir; não é o fluxo principal pedido agora

---

**Próximos incrementos sugeridos:** arrastar tarefas (kanban), tema escuro opcional nas definições do módulo.
