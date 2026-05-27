# Contexto Completo: Nexus Life OS

## 1. A Visão Geral
O projeto **Nexus Life OS** é um ecossistema de produtividade pessoal gamificado de alta fidelidade construído com Python no backend (usando SQLite) e HTML/CSS/JS via `pywebview` no frontend. A interface precisa ter uma estética "Dark Neon Glassmorphism", consistente com um assistente de IA avançado (estilo Jarvis).

O objetivo é integrar três pilares principais que podem ser controlados **tanto pela interface gráfica quanto por comandos de voz/texto via IA**:
1. **Finanças Avançadas:** Registro rápido de gastos/receitas pela IA ("gastei 150 em mousepad"), gráficos, categorias e saldo mensal.
2. **Hábitos Gamificados:** Presets de hábitos gerenciados por IA (ex: "aplique o preset de estudante"), streak baseado em dias da semana específicos, barra de XP, níveis e uma Loja de Recompensas integrada (ex: 200 pts para um dia de folga).
3. **Estudos (MindPalace):** Um sistema misturando Notion/Obsidian com Anki. Editor de notas rico com suporte a imagens, Flashcards com repetição espaçada (SRS), simulados estilo ENEM, e um "Modo Professor" onde a IA interage, explica e tira dúvidas sobre o conteúdo.

## 2. Arquitetura e Comunicação Frontend-Backend
*   **Interface Gráfica (`pywebview`):** As janelas do sistema são instâncias do webview renderizando arquivos HTML (os módulos).
*   **Bridge JS-Python (`nexus_boot.js` e `nexus_desktop_bridge.py`):** Todo o frontend chama funções no backend usando `await nxBridge("metodo", args)`.
*   **Persistência (`nexus_db.py`):** Banco SQLite com tabelas para hábitos (`habits`, `habit_logs`), tarefas, finanças (`finance_transactions`), metas, flashcards, e dados de gamificação do usuário (`nexus_user`).
*   **IA Manager (`nexus_manager.py`):** Intercepta comandos de voz/texto e os mapeia para ações do sistema (ex: Regex para adicionar dinheiro ou marcar hábito concluído).

## 3. O Erro Crítico do Passado (E como não repeti-lo)
Ao longo do desenvolvimento, um erro grave atrapalhou o progresso da estilização e criação da interface: **a IA tentava editar os arquivos de CSS externos ou o arquivo principal da janela, mas o visual do módulo nunca mudava.**

### Por que isso acontecia?
O arquivo `desktop_app.py` processa dinamicamente as janelas. Ele pega o conteúdo do módulo (`habits.html`, por exemplo) e o **injeta dentro de um frame principal** que já tem um arquivo CSS pesado (`nexus_frame.css`).
1.  **Caminhos quebram:** O `desktop_app.py` injeta uma tag `<base>` dinâmica, o que faz com que qualquer `<link rel="stylesheet" href="estilo.css">` dentro de um módulo aponte para um caminho que não existe ("arquivo não encontrado").
2.  **Sobrescrita do `nexus_frame.css`:** O arquivo `nexus_frame.css` tem seletores muito fortes que afetam botões e inputs globais, destruindo a aparência customizada de módulos específicos se a especificidade não for alta o suficiente.
3.  **Editando a Janela Errada:** A IA no passado tentou alterar o `desktop_app.py` ou criou arquivos separados em vez de modificar diretamente a interface do módulo que abre quando o usuário clica em "Hábitos".

### A Regra de Ouro da Interface (O que VOCÊ deve fazer)
Para editar o visual de qualquer janela de módulo (como `habits.html`, `finance.html`, `study.html`):
1.  **NUNCA use CSS externo.** Não faça chamadas como `<link rel="stylesheet">`.
2.  **Tudo deve ser Inline (`<style>`).** Coloque todo o CSS necessário dentro do bloco `<style>` no próprio arquivo `.html` do módulo.
3.  **Ultrapasse a Especificidade:** Para garantir que seus estilos não sejam sobrescritos pelo `nexus_frame.css`, envolva seu design em um container ou use seletores muito específicos. É altamente recomendado colocar um prefixo como `#nx-app-wrapper` ou `.nx-chrome-inner` antes de estilizar os elementos do painel principal (ex: `#nx-app-wrapper .meu-botao { ... }`).
4.  Consulte o arquivo `docs/NEXUS_WINDOW_STYLING_GUIDE.md` caso tenha dúvidas técnicas sobre a arquitetura do frame.

## 4. O Estado Atual (Últimas Atualizações)
Na última grande sessão, refizemos completamente a base de quase todos os módulos para implementar o plano de gamificação:
*   `habits.html`: Refatorado com `<style>` inline, com Barra de XP animada com shimmer, Heatmap baseado no log de hábitos, cálculo de streak consertado e seleção por "dias da semana".
*   `finance.html`: Refatorado com visualização de Saldo Líquido, Receitas, Despesas, abas para transações e lista com ícones.
*   `goals.html` (Loja e Metas): Agora inclui visualização do saldo de pontos do usuário com abas separando a lojinha de resgate de recompensas e a visualização de metas com barras de progresso.
*   `overview.html`: O Dashboard principal agora é interativo com widgets que mostram finanças rápidas, hábitos que faltam no dia atual e botões para todos os outros módulos.
*   **Referências de Visual:** Para a área de hábitos, pesquisamos projetos como "HabitTrove" (focado em um dashboard gamificado de alta densidade) e "AnyHabit" (focado em minimalismo limpo e visualização de dados) para inspirar as futuras expansões visuais, a ideia é misturar ambos usando o "Dark Neon".

## 5. Próximos Passos (Onde focar agora)
Se você for continuar o desenvolvimento, suas prioridades devem ser:
1.  **IA Presets para Hábitos:** Consolidar a habilidade da IA (usando a tool `habit_tracker.py`) para gerar "perfis de hábitos" dinamicamente (ex: "crie um perfil para me preparar para a maratona") e atualizar o SQLite apagando e substituindo hábitos de forma segura.
2.  **Aprimorar o Modo Professor (MindPalace):** A página `notes.html` (e `study.html`) foi estruturada, mas a IA precisa conseguir ler as notas abertas para tirar dúvidas (via `notes_list` ou acesso ao texto selecionado) e gerar Flashcards automaticamente a partir delas.
3.  **Polimento Visual:** Implementar gráficos de verdade (usando alguma biblioteca como Chart.js injetada inline ou CDN se tiver internet) no `progress.html` e `finance.html`.
4.  **Voz Universal:** Ampliar o Regex do `nexus_manager.py` para entender mais nuances finaceiras (ex: "apagar meu gasto com lanche de ontem") ou de metas ("resgatar folga").
