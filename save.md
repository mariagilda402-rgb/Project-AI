# 🧠 Project AI — Roadmap de Implementação

> **Regra de Ouro:** Cada implementação deve ser feita com cautela para NÃO quebrar funcionalidades existentes. Sempre fazer backup no GitHub antes de cada fase.

---

## ✅ Já Implementado

- [x] Assistente de voz com STT (Whisper/Google) + TTS (Edge/Kokoro)
- [x] Function Calling nativo (Gemini, Groq, NVIDIA)
- [x] Abertura universal de apps via AppCache (Registro Windows + Menu Iniciar)
- [x] Filtro anti-alucinação do STT (Whisper PT-BR)
- [x] Memória de curto prazo (SQLite — `data/memory.db`)
- [x] Memória semântica RAG/JARVIS (ChromaDB — `data/chroma_db/`)
- [x] Extração assíncrona de fatos do usuário (thread em background)
- [x] Visualizador Orb (roda no navegador via Flask, porta 5123)
- [x] Controle do Spotify, gerenciamento de arquivos, utilitários

---

## 🚀 Fase 1 — UI Nativa Desktop (Sair do Navegador)

**Objetivo:** Trazer o visualizador Orb que hoje roda no navegador para uma janela nativa no Windows, mantendo o design 100% idêntico (mesmas animações, cores, efeitos).

### 1.1 — Janela Nativa Transparente (Overlay)
- [x] Criar janela nativa usando **PyWebView** ou **Electron** (embutir o HTML/CSS/JS atual sem alterações visuais)
- [x] A janela deve ser **transparente** e **sempre no topo** (overlay)
- [x] Sem borda de janela (frameless) — igual ao design atual do orb
- [x] **Click-through**: o mouse atravessa a janela e clica no que está por baixo (não interfere no uso do PC)
- [x] O orb pode ser movido para diferentes cantos da tela (inferior direito, inferior esquerdo, superior, etc.)

### 1.2 — Ícone na Bandeja do Sistema (System Tray)
- [x] Ao minimizar a janela principal, o app vai para a bandeja do sistema (ao lado do relógio)
- [x] Duplo clique no ícone da bandeja → abre a **Janela de Gerenciamento** (painel completo)
- [x] No painel de gerenciamento tem várias abas, e na aba principal de inicio terá uma caixa de texto em baixo, e em cima que é o centro da janela tem uma visualização maior da orb.
- [x] Clique direito no ícone → menu rápido (Sair, Abrir Painel, Silenciar Mic, etc.)
- [x] O orb flutuante continua visível mesmo quando a janela de gerenciamento está fechada

### 1.3 — Dois Modos de Exibição
| Modo | Quando Ativa | Comportamento |
|------|-------------|---------------|
| **Modo Overlay (Flutuante)** | Janela minimizada | Orb pequeno no canto da tela, click-through, sempre visível |
| **Modo Painel (Janela)** | Duplo clique na bandeja | Janela completa com todas as configurações e customizações |

---

## 🤖 Fase 2 — Sistema Multi-Agentes

**Objetivo:** Permitir criar múltiplos agentes de IA, cada um com sua própria personalidade, voz, memória e comportamento.

### 2.1 — Estrutura de Dados do Agente
- [x] Criar modelo `Agent` com os seguintes campos:
  - `id` (UUID único)
  - `name` (ex: "JARVIS", "Deadpool", "Assistente Técnico")
  - `persona` (prompt de personalidade completo)
  - `voice` (configuração de voz do TTS: provider, voz específica, velocidade)
  - `voice_speed` (velocidade da fala)
  - `memory_collection` (nome da coleção ChromaDB isolada, ex: `"jarvis_memory"`)
  - `created_at`, `updated_at`
  - `is_active` (se está habilitado no momento)
- [x] Salvar agentes em `data/agents.json` ou numa tabela SQLite dedicada
- [x] Cada agente tem sua própria coleção no ChromaDB (memórias isoladas)

### 2.2 — CRUD de Agentes (no Painel)
- [x] Botão **"+"** para criar novo agente (wizard de criação: nome, personalidade, voz)
- [x] Editar agente existente (alterar personalidade, nome, voz, velocidade)
- [x] Deletar agente (vai para a **Lixeira**, não deleta permanentemente)
- [x] **Lixeira de Agentes e Memórias:**
  - Agentes deletados ficam na lixeira por 30 dias
  - O usuário pode restaurar agentes e suas memórias
  - Opção de deletar permanentemente (irreversível)
- [x] Limpar apenas memórias de um agente específico (sem deletar o agente)

---

## 🔀 Fase 3 — Modos de Operação

**Objetivo:** Dois modos principais de uso da IA, alternáveis pelo painel.

### 3.1 — Modo Agente Único
- [x] O usuário seleciona **um** agente ativo de sua lista
- [x] Toda interação (voz/texto) vai para esse agente
- [x] O agente usa sua personalidade, voz e banco de memória próprio
- [x] Dropdown ou lista no painel para trocar rapidamente de agente

### 3.2 — Modo Multi-Agente
- [x] O usuário seleciona **dois ou mais** agentes ativos simultaneamente
- [x] O sistema suporta os seguintes sub-modos:

#### 3.2.1 — Modo Roda de Respostas (Round-Robin)
> O usuário faz uma pergunta e cada agente responde em sequência.

- [x] O usuário faz uma pergunta (ex: "Me fale por que eu deveria te contratar")
- [x] O Agente 1 responde primeiro
- [x] O Agente 2 responde em seguida
- [x] O Agente 3 responde por último (e assim por diante)
- [x] **Toggle: "Contexto encadeado"**
  - **LIGADO:** Cada agente tem acesso às respostas dos agentes anteriores e pode comentar/rebater
  - **DESLIGADO:** Cada agente responde individualmente, sem ver o que os outros disseram

#### 3.2.2 — Modo Debate Livre
> Os agentes iniciam uma discussão entre si automaticamente.

- [x] O usuário pode fornecer um tema inicial (ex: "Discutam sobre energia nuclear")
- [x] OU o usuário pode mandar um dos agentes **escolher** o tema
- [x] Os agentes se revezam respondendo, sempre com acesso ao que o anterior disse
- [x] O debate continua por N rodadas (configurável) ou até o usuário interromper
- [x] O TTS reproduz cada resposta com a voz do agente correspondente

#### 3.2.3 — Modo Chamada por Nome
> O usuário chama um agente específico pelo nome durante uma conversa.

- [x] Todos os agentes ativos "ouvem", massó o chamado responde
- [x] O STT detecta o nome do agente no início da frase (ex: "JARVIS, que horas são?")
- [x] Os outros agentes ficam em standby silencioso
- [x] Se o usuário não falar nenhum nome, o agente "padrão" responde (ou o último que falou)

### 3.3 — Presets de Modo
- [x] **Entrevista de Emprego:** Cada agente responde como candidato, com contexto encadeado
- [x] **Debate Acadêmico:** Os agentes discutem um tema específico com argumentos e contra-argumentos
- [x] **Brainstorm:** Todos contribuem ideias de forma criativa e desordenada
- [x] **Personalizado:** O usuário define as regras do modo livremente

---

## 🗂️ Fase 4 — Gerenciamento de Memória Avançado

### 4.1 — Visualização de Memórias no Painel
- [x] Listar todas as memórias de cada agente no painel (fatos aprendidos)
- [x] Buscar memórias por texto
- [x] Deletar memórias individuais (enviar para lixeira)
- [x] Exportar/importar memórias (backup em JSON)

### 4.2 — Lixeira Universal
- [x] Memórias deletadas ficam na lixeira
- [x] Agentes deletados ficam na lixeira (com suas memórias preservadas)
- [x] Opção de restaurar qualquer item da lixeira
- [x] Opção de esvaziar lixeira (delete permanente com confirmação)

---

## 📋 Ordem de Implementação Sugerida

| Prioridade | Fase | Descrição | Complexidade |
|:---:|:---:|---|:---:|
| 1 | 2.1 | Estrutura de dados do Agente + persistência | 🟢 Baixa |
| 2 | 3.1 | Modo Agente Único (seleção de agente ativo) | 🟢 Baixa |
| 3 | 2.2 | CRUD de Agentes (criar, editar, deletar) | 🟡 Média |
| 4 | 3.2.1 | Modo Roda de Respostas (Round-Robin) | 🟡 Média |
| 5 | 3.2.3 | Modo Chamada por Nome | 🟡 Média |
| 6 | 3.2.2 | Modo Debate Livre | 🟠 Alta |
| 7 | 1.1 | Janela nativa overlay (PyWebView) | 🟠 Alta |
| 8 | 1.2 | System Tray + Painel de Gerenciamento | 🟠 Alta |
| 9 | 4.1 | Visualização e gerenciamento de memórias | 🟡 Média |
| 10 | 4.2 | Lixeira universal | 🟢 Baixa |
| 11 | 3.3 | Presets de modo | 🟢 Baixa |

---

## 🔧 Notas Técnicas

- **Backup obrigatório** no GitHub antes de cada fase
- **Testes isolados** antes de integrar — cada feature é testada sozinha primeiro
- **Nenhum breaking change** — o sistema deve funcionar no modo agente único (comportamento atual) mesmo depois de adicionar multi-agente
- **ChromaDB** já suporta múltiplas coleções nativamente — perfeito para memória por agente
- **TTS** já suporta múltiplas vozes (Edge TTS tem dezenas de vozes PT-BR masculinas/femininas)
