# Plano de Implementação: Melhorias UI/UX, Controles de Janela e Estabilidade do Nexus

Este plano detalha as soluções para todos os itens levantados. O objetivo principal é garantir um uso fluido do painel unificado, consertar bugs de estado zumbi (processo rodando no fundo) e melhorar a interação visual da Orb e do WebView.

## User Review Required

> [!IMPORTANT]  
> Confirme se o agrupamento da barra lateral listado abaixo está exatamente como deseja.
> Também confirme se a opção de Hard Reset deve apenas limpar o banco de dados das seções Nexus mantendo a estrutura, ou se prefere apagar literalmente o arquivo do banco de dados e forçar o reinício da aplicação.

## Proposed Changes

### 1. Reorganização e Layout

#### [MODIFY] `src/ui/nexus_modules/unified.html`
- Reorganizar a sidebar de acordo com seu pedido, criando grupos ou apenas ordenando de forma que fiquem próximos:
  - **Estudos:** Notas (em cima) -> SRS/Flashcards -> Quiz -> Progresso
  - **Produtividade/Hábitos:** Hábitos -> Tarefas (em baixo de hábitos) -> Metas/Rewards
  - **Finanças:** Finanças (Overview)
- Adicionar no header (Chrome Bar) novos botões: **Minimizar**, **Maximizar/Restaurar** e **Pin (Sempre no Topo)**.

### 2. Controle de Janela, Transparência e Orb

#### [MODIFY] `src/ui/desktop_app.py`
- **Controles da Janela:** Adicionar os métodos `minimize_module`, `maximize_module` e `toggle_always_on_top` dentro da classe `NexusModulePyApi`.
- **Lógica da Orb:** Quando `open_nexus_module` abrir o painel `unified`, forçar a `self.ghost_window.hide()` e esconder a orb via JavaScript (`visibility = hidden`). Ao fechar a janela do painel (`close_module`), restaurar a Orb garantindo que eles nunca fiquem na tela juntos.
- **Bug da Transparência (Quadrado Branco):** Injetar ou garantir que o `<body>` e o `<html>` no `_compose_nexus_module_html` possuam `background: transparent !important;` forçado.

### 3. Melhorias Visuais na Orb

#### [MODIFY] `src/ui/ghost_visualizer.html` (ou similar/orb relacionada)
- Substituir a animação atual (pontos piscando rápido em roxo) por uma animação de "respiração" (tween / pulse) suave.
- Mudar o tema de cores para **Branco ou Verde Esmeralda**, garantindo um aspecto muito mais maduro, suave e profissional (inspirado no Jarvis de fato, menos ruidoso e mais fluido).

### 4. Ciclo de Vida e Processo Zumbi

#### [MODIFY] `src/ui/desktop_app.py` e `src/main.py`
- **Tray Icon Quit:** Atualizar o método `on_tray_quit` para realizar `os._exit(0)` em vez de apenas destruir as janelas (isso resolve o terminal rodando eternamente no fundo).
- **Ctrl+C no Terminal:** Adicionar um tratador na thread do WebView para escutar encerramento do processo principal, e em `main.py`, garantir que uma exceção force o fim do loop e do PyWebView nativamente sem dar "respawn".

### 5. Flashcards (Adição Manual) e Refresh de Dados

#### [MODIFY] `src/ui/nexus_modules/study.html`
- Adicionar um formulário/modal simples para adicionar novos flashcards com os campos: **Frente (Pergunta)** e **Verso (Resposta)**.
- Chamar um novo método na bridge `srs_add_card_manual`.

#### [MODIFY] `src/services/nexus_service.py`
- Criar a função lógica `srs_add_card_manual(front, back, subject)` para persistir o novo card no banco de dados, vinculando a uma Nota "Avulsa" ou recém-criada.
- Adicionar na bridge o suporte para os Resets: `reset_section_data(section)` e `hard_reset_all()`.

#### [MODIFY] `src/ui/nexus_modules/quiz.html` e `progress.html`
- Inserir chamadas lógicas de auto-refresh. Quando você clica na aba de uma seção no `unified.html`, o Painel enviará um sinal `window.postMessage` para os iframes, que escutarão isso e recarregarão seus dados do backend para manter a estatística de % de acerto sempre em tempo real.

## Verification Plan

### Manual Verification
- Clicarei na opção do ícone na bandeja para "Sair" e verificarei se o processo inteiro no terminal morre sem sobras.
- Usarei o comando Ctrl+C no terminal e validarei se a aplicação morre completamente.
- Abrirei o painel e observarei a Orb sumir. Fecharei o painel e observarei a Orb retornar suavemente.
- Criarei um Flashcard Manualmente via interface (Aba Estudos).
- Verificarei se o Redimensionar, Fixar (Pin) e Maximizar estão comportando-se corretamente na janela unificada.
