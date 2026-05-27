# Visão Geral e Progresso: Projeto AI (JARVIS)

Este documento resume a arquitetura, as funcionalidades atuais e o progresso de desenvolvimento do Assistente Virtual JARVIS, um agente autônomo com inteligência artificial operando localmente no sistema operacional Windows.

---

## 1. Arquitetura Central (O Núcleo)
O núcleo do sistema foi construído em Python, com foco em uma estrutura assíncrona, robusta e modular baseada no conceito de Orquestração Multi-Agente (*Multi-Agent Orchestrator*).

- **Orquestrador Central (`src/agent/orchestrator.py`):** Gerencia a fila de tarefas, despacha funções e toma decisões de roteamento baseadas em contexto.
- **Agente Proativo (`src/services/proactive_agent.py`):** Um módulo independente que "assiste" a tela do usuário de tempos em tempos (Vision) e puxa assunto espontaneamente, simulando a presença real de uma IA observadora.
- **Memória Estruturada (VectorDB):** Armazenamento de preferências, fatos e conversas de longo prazo em banco de dados vetorial para contexto histórico.

## 2. Modelos de Linguagem e Integrações (LLM)
O cérebro da IA possui flexibilidade total de provedores para evitar interrupções.

- **Múltiplos Provedores:** Suporte nativo ao Google Gemini (primário para raciocínio e visão), Groq (transcrições rápidas Whisper), NVIDIA (Nemotron/Llama 3.3) e OpenRouter.
- **Sistema de Fallback e Rate Limits:** Caso um provedor atinja limite de taxa (Rate Limit) ou uma chave caia, o sistema automaticamente rotaciona a chave da API (utilizando o rastreio por conta do Google Cloud) ou troca para o modelo reserva sem interromper o usuário.

## 3. Visão e Audição (Módulos Sensoriais)
- **Audição (STT - Speech-to-Text):** Monitoramento contínuo do microfone com calibração automática de ruído ambiente e detecção de ativação por palmas (ClapDetector).
- **Voz (TTS - Text-to-Speech):** Respostas fluidas e de baixíssima latência utilizando primariamente o **Edge TTS** (nuvem) e o **Kokoro** (inferência local CPU).
- **Visão:** Captura de tela passiva e ativa em segundo plano para entender contexto em tempo real do que o usuário está fazendo, lendo ou jogando.

## 4. Interface Gráfica e Visualizadores (UI)
O sistema possui interfaces visuais construídas em Tecnologias Web (HTML/JS/CSS) e renderizadas nativamente na área de trabalho via **PyWebView**.

- **A Orb (Ghost Window):** Um visualizador 3D estilo "energia/plasma" transparente que flutua no canto da tela do usuário. O visualizador pulsa reativamente com o áudio da voz. O modo **Ghost Click** torna a Orb imune ao mouse, permitindo clicar "através" dela sem atrapalhar a navegação.
- **Painel de Gerenciamento (Jarvis Control Panel):** Uma janela dark-matte de alto nível (com bordas perfeitamente arredondadas e efeito de contorno Neon rotativo RGB). Permite ao usuário:
  - Ver os logs do terminal e conversas.
  - Ajustar chaves da API e tema dinâmico.
  - Orquestrar Modos de Conversa Avançados (ex: Round-Robin, Debate de IA).
  - Configurar e instanciar novos agentes virtuais personalizados.

## 5. Ferramentas, Habilidades e Automações (Skills)
O sistema permite a injeção de "habilidades dinâmicas", executadas pela IA de forma autônoma (Function Calling).

- **Controle do Sistema:** Controle do hardware e SO Windows (Volume, apps, fechar processos, ler clipboard).
- **Automação Web e Agente de Navegação:** Busca de informações da internet, leitura de clima, preço do Bitcoin e resumo de notícias (`NewsTool`).
- **Engenharia e Criação 3D:** Geração e modelagem paramétrica usando `build123d` e manipulação de arquivos CAD.
- **IoT & Smart Home:** Integração com tomadas e lâmpadas inteligentes TP-Link/Kasa.
- **Controle de Mídia:** Gerenciador dedicado do Spotify para leitura, pular de faixas e play/pause de forma silenciosa.

---

## 6. Últimos Marcos Concluídos
- ✅ **Estabilidade de Interface e Renderização:** Resolução de bugs no WebGL, conflitos de DWM do Windows para transparência total das janelas e resolução de sobreposição de elementos na UI (CSS Flexbox).
- ✅ **Proteção de Chaves de API:** Remoção bem-sucedida do rastreamento público de variáveis de ambiente (`.env`) no GitHub (Secret Scanning), contornando desativações globais feitas pela Google.
- ✅ **Design UI/UX Aprimorado:** Remoção de poluições visuais, fixação da "Borda Neon Andante", permitindo que o usuário defina as cores da UI dinamicamente no painel.

## 7. Próximos Desafios (Roadmap)
- Refinar de forma absoluta os prompts do sistema e o analisador de Output do Nemotron/NVIDIA para impedir vazamento das "Thought Chains" e alucinações de instrução em tela.
- Estabilizar a inicialização dos pacotes e módulos `.onnx` para TTS local (Kokoro).
- Otimização do tempo de reposta entre o áudio captado e a geração final do TTS para criar uma conversação ultra-realista.
