# Nexus Life OS - proximas melhorias priorizadas (2026-05-26)

Este arquivo lista sugestoes racionais para deixar o projeto mais forte, mais automatico e mais alinhado com a visao Jarvis/Nexus.

## Prioridade 1 - Workflow recorder Jarvis

Objetivo: permitir que o usuario abra apps, janelas e comandos, depois diga "salve isso como workflow".

Implementar:

- Tabela/API de workflows com nome, descricao, passos, tags, risco e ultima execucao.
- Captura de contexto atual:
  - janelas Nexus abertas;
  - apps abertos conhecidos;
  - URLs/titulos de navegador quando disponivel;
  - playlist/comando de musica;
  - timer/foco;
  - parametros de agente.
- Comandos naturais:
  - "salve isso como modo estudo";
  - "ative modo estudo";
  - "edite o modo estudo";
  - "adicione abrir Spotify nesse workflow";
  - "rode isso toda segunda as 8".
- UI para revisar e editar cada passo antes de permitir execucao automatica.
- Guardrails:
  - acoes destrutivas sempre pedem confirmacao;
  - workflows nao podem salvar secrets;
  - comandos de teclado/mouse precisam ser explicitos ou gravados com consentimento.

## Prioridade 2 - Orquestrador mais automatico

Objetivo: reduzir a necessidade de "entrar no modo X".

Implementar:

- Roteador de intencao com scoring:
  - PC automation;
  - estudos;
  - notas;
  - habitos;
  - financas;
  - noticias;
  - treino;
  - diario/coach;
  - configuracoes.
- Contexto ativo:
  - janela aberta;
  - agente selecionado;
  - ultima ferramenta usada;
  - pedido atual;
  - risco da acao.
- Fallback quando houver ambiguidade:
  - perguntar uma confirmacao curta;
  - sugerir 2 opcoes;
  - nunca executar acao sensivel no chute.

## Prioridade 3 - Noticias em janela dedicada

Objetivo: preservar a ideia do usuario de abrir uma janela quando pedir "modo noticias".

Implementar:

- Janela de noticias com busca por tema, fontes, timeline e resumo.
- Cards com:
  - titulo;
  - fonte;
  - horario;
  - resumo curto;
  - link;
  - video quando disponivel.
- Modo video:
  - player embutido quando tecnicamente permitido;
  - legenda/transcricao quando disponivel;
  - resumo incremental.
- Comandos:
  - "abra modo noticias";
  - "ultimas noticias sobre IA";
  - "resuma esse video";
  - "salve essa noticia nas notas";
  - "crie flashcards desse assunto".

## Prioridade 4 - Editor Notion/Affine de verdade

Objetivo: aproximar a experiencia de notas de Notion/Obsidian/Affine sem quebrar o backend atual.

Proxima etapa incremental:

- Melhorar selecao de blocos.
- Arrastar e reordenar blocos.
- Toolbar contextual por bloco.
- Comandos slash com busca.
- Templates de nota:
  - aula;
  - resumo;
  - projeto;
  - diario;
  - treino;
  - financas.
- Backlinks estilo Obsidian:
  - `[[Nota]]`;
  - lista de referencias;
  - grafo simples.
- IA contextual:
  - "resuma este bloco";
  - "transforme em flashcards";
  - "explique como professor";
  - "adicione exemplos".

Evolucao futura:

- Avaliar TipTap/ProseMirror ou BlockSuite somente quando houver disposicao para migrar o build/frontend.
- Enquanto isso, manter markdown canonico para facilitar IA, sync e exportacao.

## Prioridade 5 - Psicologo/coach com limites responsaveis

Objetivo: atender o desejo do usuario de ter psicologo e coach motivacional, mas reduzir risco de conselho ruim.

Implementar:

- Modo "Coach emocional" com:
  - diario guiado;
  - perguntas reflexivas;
  - plano de acao pequeno;
  - acompanhamento de humor;
  - tendencias de 7/14/30 dias.
- Modo motivacional com:
  - discurso curto por voz;
  - revisao de metas;
  - reforco de streaks;
  - sugestao de proxima acao.
- Segurança:
  - detectar crise, autoagressao ou risco;
  - responder com apoio imediato e recomendacao de ajuda humana;
  - nao fingir diagnostico medico.

## Prioridade 6 - STT, voz e clap trigger

Objetivo: deixar a ativacao natural e confiavel.

Implementar:

- Medidor visual de microfone no painel.
- Botao "calibrar ambiente".
- Presets:
  - quarto silencioso;
  - ventilador/ruido;
  - microfone longe;
  - headset.
- Clap trigger:
  - tela de calibracao;
  - grafico de picos;
  - opcao de duas palmas, tres palmas ou hotword;
  - cooldown visual.
- Wake behavior:
  - palmas acordam o modo escuta;
  - frase de ativacao opcional;
  - modo push-to-talk como fallback.

## Prioridade 7 - Performance e boot

Objetivo: iniciar rapido e responder mais rapido.

Implementar:

- Dashboard de boot com tempo por fase.
- Lazy load de servicos pesados:
  - vision tracker;
  - TTS pesado;
  - RVC;
  - embeddings;
  - news/video.
- Cache de UI e pre-render seguro.
- Evitar recarregar listas inteiras apos cada acao.
- Medir:
  - tempo ate janela abrir;
  - tempo ate chat aceitar input;
  - tempo STT -> resposta;
  - tempo resposta -> TTS.

## Prioridade 8 - Mobile companion

Objetivo: usar celular como controle remoto e chat leve.

Implementar:

- API local segura no PC.
- Pareamento por QR code ou token local temporario.
- App mobile leve:
  - chat texto/voz;
  - comandos para o PC;
  - notificacoes;
  - habitos;
  - diario;
  - alarmes.
- Permissoes:
  - listar comandos permitidos pelo celular;
  - confirmar acoes sensiveis no PC;
  - revogar dispositivos.

## Prioridade 9 - Seguranca de tools

Objetivo: evitar comandos aleatorios, perigosos ou confusos.

Implementar:

- Registry de ferramentas com:
  - categoria;
  - risco;
  - parametros;
  - exemplos;
  - permissao por agente/modo.
- Dry-run para acoes sensiveis.
- Recibos de execucao:
  - o que foi pedido;
  - o que foi executado;
  - ferramenta usada;
  - status;
  - tempo;
  - erro se houver.
- Painel para ativar/desativar tools por agente.

## Prioridade 10 - Testes e QA visual

Objetivo: manter o app crescendo sem quebrar.

Implementar:

- Testes de contrato para toda tool exposta ao agente.
- Testes de UI para:
  - editor de notas;
  - habitos otimistas;
  - configuracoes;
  - noticias;
  - workflow recorder.
- Teste de parse JS para todo HTML do Nexus.
- Screenshots desktop/mobile quando houver dev server ou Browser disponivel.
- Scan de secrets antes de todo commit.

## Melhor proximo ciclo de implementacao

O proximo ciclo mais valioso e:

1. Workflow recorder minimo.
2. UI de workflows.
3. Tool do agente para salvar/rodar workflow.
4. Guardrails e recibos.
5. Testes de workflow.

Isso entrega a sensacao Jarvis que o usuario quer: o app observa uma rotina, salva como modo e executa de novo por comando natural.
