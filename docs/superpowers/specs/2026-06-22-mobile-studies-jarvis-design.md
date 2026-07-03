# Nexus Mobile Studies + Jarvis Design

## Objetivo

Transformar a area de Estudos do Nexus Mobile em uma experiencia util de aprendizado diario: notas organizadas por materia, revisao SRS visivel, quiz, captura de material e Jarvis contextual. O mobile deve funcionar sozinho. Desktop e backend Python entram apenas como integracao opcional para sync, processamento mais pesado e recursos avancados.

## Decisoes De Produto

1. O primeiro foco nao e criar um Jarvis global completo. A primeira entrega sera Estudos com Jarvis embutido, porque notas, materias, flashcards e quiz dao ferramentas concretas para a IA agir.
2. A tela Inicio continua existindo como cockpit do dia, mas recebe apenas ajustes direcionais nesta fase: destacar revisoes pendentes, continuar estudo e abrir Jarvis de estudo.
3. Estudos nao deve abrir em graficos vazios. A primeira dobra deve mostrar acoes: revisar agora, continuar nota, capturar material, perguntar ao Jarvis e criar materia/nota.
4. Materia/caderno sera o eixo principal de organizacao. O campo solto de assunto da nota deve ser tratado como metadado secundario ou derivado da materia, para evitar duplicidade mental.
5. Flashcards e memorizacao precisam ser superficies de primeira classe: fila do dia, criacao a partir de nota/materia, revisao com qualidade e proxima revisao.
6. Recursos que exigem IA devem ter dois caminhos: mobile direto quando configurado, desktop opcional quando disponivel. A ausencia do desktop nao pode quebrar a interface nem bloquear estudos locais.

## Escopo Da Primeira Entrega

- Reorganizar a view de Estudos para priorizar fluxo de aprendizado em vez de metricas vazias.
- Adicionar um painel/rail Jarvis contextual em Estudos e no editor de nota.
- Melhorar o fluxo de materias: card de materia com contagem de notas, cards pendentes e acoes rapidas.
- Melhorar o editor mobile sem trocar a tecnologia: manter `contenteditable`, toolbar e slash menu, mas tornar as acoes de estudo mais visiveis.
- Tornar flashcards/SRS acessiveis a partir do topo de Estudos, da materia e da nota.
- Criar fallback local claro para quando IA, rede ou desktop nao estiverem disponiveis.
- Validar no aparelho via ADB e, ao final, enviar o bundle mobile para o celular.

Fora de escopo nesta primeira entrega:

- Refazer todo o app mobile.
- Criar um sistema nativo completo de voz/camera em Android.
- Tornar o desktop obrigatorio para qualquer fluxo.
- Migrar todo o `mobile/app.js` para uma arquitetura nova.

## Arquitetura

### Mobile Local

O estado local continua usando `LocalDB` e as colecoes existentes:

- `study_notebooks` para materias/cadernos.
- `study_notes` para notas.
- `flashcards` para SRS.

A implementacao deve ser incremental e respeitar o app atual. Onde possivel, criar funcoes pequenas para:

- Calcular resumo de estudo do dia.
- Calcular progresso por materia.
- Normalizar a relacao nota/materia.
- Montar a lista de acoes Jarvis disponiveis.

### Jarvis Contextual

Jarvis dentro de Estudos deve operar com contexto explicito:

- Contexto de Estudos: materias, notas recentes, cards pendentes e metas do dia.
- Contexto de Materia: materia selecionada, notas ligadas, cards e progresso.
- Contexto de Nota: conteudo atual, tags, materia, anexos e links.

As primeiras acoes esperadas:

- Explicar esta nota.
- Gerar flashcards.
- Criar resumo.
- Criar quiz rapido.
- Sugerir proximo passo de estudo.
- Capturar material por camera quando disponivel.

Quando uma acao de IA nao puder executar, o app deve mostrar uma resposta util: salvar contexto local, explicar a limitacao e oferecer uma acao manual equivalente quando possivel.

### Desktop Opcional

Se um endpoint desktop estiver disponivel, o mobile pode chamar recursos como `note_teach`, `subject_teach`, `flashcards_generate`, `flashcards_due`, `quiz_random`, `quiz_flashcards_generate` e `study_recommendations`.

Se nao estiver disponivel:

- Notas, materias e revisao continuam funcionando localmente.
- Geracao por IA deve tentar o provedor mobile configurado.
- Se nenhuma IA estiver configurada, o app nao deve fingir resultado. Deve orientar o usuario a configurar IA ou criar manualmente.

## Fluxo De Tela

### Inicio

Mostrar um bloco de estudo mais acionavel:

- Cards SRS para revisar hoje.
- Ultima nota ou materia em andamento.
- Botao para abrir Estudos.
- Botao para falar com Jarvis em modo estudo.

### Estudos

Primeira dobra recomendada:

- Saudacao curta ou titulo "Estudos".
- Estado do dia: revisoes, notas recentes, materias ativas.
- Acoes principais: Revisar agora, Nova nota, Capturar, Jarvis.
- Materias logo abaixo, com cards compactos e informativos.

Graficos e metricas devem ficar abaixo das acoes ou em uma aba secundaria.

### Materia

Ao abrir uma materia:

- Mostrar nome, icone/capa e resumo.
- Acoes: nova nota, revisar cards da materia, gerar cards, perguntar ao Jarvis.
- Lista de notas da materia.
- Indicador de cards pendentes e ultima atividade.

### Editor

Manter o editor rico atual, mas melhorar entrada e descoberta:

- Titulo derivado do primeiro H1 ou primeira linha.
- Materia visivel e facil de trocar.
- Toolbar compacta.
- Slash menu com blocos de nota e acoes IA relevantes.
- Painel Jarvis contextual com acoes de nota.

## Tratamento De Erros

- Erro de sync nao deve dominar a tela principal. Deve aparecer como estado discreto com acao de resolver.
- Falha de IA deve diferenciar: sem internet, sem chave/modelo, desktop indisponivel ou erro do provedor.
- Acoes destrutivas ou que geram muitos cards devem pedir confirmacao via `window.showConfirm()`.
- IDs devem ser comparados como string para seguir o padrao mobile existente.

## Testes E Validacao

Validar antes de concluir:

- `node --check mobile/app.js`.
- Abrir app no aparelho via ADB.
- Capturar screenshots de Inicio, Estudos, Materia, Editor e Revisao.
- Confirmar que Estudos funciona sem desktop aberto.
- Confirmar que criar materia, criar nota, salvar nota e revisar flashcard continuam funcionando.
- Rodar `python scripts/push_mobile_bundle_adb.py` para enviar o bundle final ao celular.
