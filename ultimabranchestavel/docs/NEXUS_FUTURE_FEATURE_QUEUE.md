# Nexus Future Feature Queue

Este arquivo registra ideias aprovadas/conversadas para não se perderem enquanto continuamos implementando o Nexus Life OS.

## Prioridade Atual

### 1. News Briefing Deck + Spotlight

Substituir a ideia frágil de trocar vídeo em tempo real conforme o Jarvis fala por uma central de notícias mais eficiente:

- cards de notícias com fonte, resumo, contexto e impacto;
- modo Spotlight para a notícia em foco;
- trilha de briefing narrável sem depender de transcrição real de vídeo;
- botões para salvar no MindPalace, criar tarefa de acompanhamento e futuramente gerar flashcards;
- histórico/cache local de briefings;
- vídeo como apoio opcional, não como núcleo obrigatório.

Status em andamento:

- janela de notícias existe;
- histórico/cache existe;
- salvar no MindPalace existe;
- próximo passo: deck/spotlight com “por que importa”, timeline e ações.

## Próximas Grandes Frentes

### 2. Neural Memory Graph

Visualizador em forma de rede neural para representar tudo que o Jarvis sabe e estuda:

- memórias estruturadas (`data/structured_memory.json`);
- notas do MindPalace (`study_notes`);
- notícias salvas;
- tarefas, metas e hábitos;
- arquivos Markdown relevantes (`.md`) como persona, logs e planos;
- conexões por assunto, tags, fonte, data, módulo e relação semântica.

Direção recomendada:

- criar um Knowledge Graph interno como fonte principal;
- permitir import/export Markdown estilo Obsidian;
- usar a rede como superfície visual e também como contexto para o Jarvis responder sobre estudos mesmo com as janelas fechadas.

Status em andamento:

- janela de grafo neural existe;
- grafo agrega notas, flashcards, memória estruturada, tarefas, hábitos, metas, recompensas e Markdown;
- relações locais explicáveis por palavras-chave existem via arestas `relates`;
- busca retorna `ranked_matches` e `memory_graph_context` para o Jarvis responder usando a memória local;
- próximo passo recomendado: contexto mais semântico com embeddings locais/opcionais e import/export Obsidian.

### 3. Particle Neural Core

Evoluir o visualizador/orb do Jarvis para um núcleo de partículas inspirado nos exemplos compartilhados:

- estados visuais: idle, listening, thinking, speaking, executing, alert;
- pulso com energia do TTS;
- partículas se reorganizando em módulos/ações durante comandos Nexus;
- modo Memory Graph, onde o núcleo abre em nós conectados;
- WebGL/Three.js próprio, usando sites como `particles.casberry.in` apenas como referência visual.

Decisão recomendada:

- compensa trocar o rosto visual do Jarvis para Particle Neural Core, desde que seja uma camada de estado do assistente;
- manter a HUD e os painéis Nexus funcionais ao redor;
- primeiro implementar o core como componente visual reaproveitável com estados `idle`, `listening`, `thinking`, `speaking`, `executing` e `alert`;
- depois conectar energia do TTS e eventos Nexus.

Status em andamento:

- camada inicial Particle Neural Core implementada sobre o orb WebGL atual;
- core evoluido para esfera neural organizada, com latitude/meridianos, scan bands, glow e pulsos por estado;
- estados `idle`, `listening`, `thinking`, `speaking`, `executing` e `alert` existem no visual;
- energia do TTS tambem sincroniza o brilho/pulso das particulas durante `speaking`;
- `control_visualizer` pode mudar estado visual e emocao temporaria por comando;
- `set_executing()` e `set_alert()` existem no serviço Python;
- próximo passo recomendado: ligar `set_executing()` automaticamente ao ciclo real de ferramentas/comandos Nexus compostos.

### 4. Business / Ops Command Dashboard

Painel operacional inspirado no vídeo de MRR/downloads/ads/refunds:

- métricas manuais primeiro;
- importação CSV/JSON;
- depois conectores reais se existirem contas/APIs: Stripe, app stores, YouTube/TikTok, Meta Ads etc.;
- recomendações do Jarvis baseadas em métricas;
- metas automáticas e tarefas sugeridas.

## Notas De Design

- Evitar features que pareçam impressionantes mas sejam frágeis, como sincronização forçada de vídeo com fala sem transcrição real.
- Preferir superfícies úteis: fontes, ações, estudo, memória, tarefas e contexto reaproveitável.
- Visual premium deve apoiar a função, não substituir a função.
