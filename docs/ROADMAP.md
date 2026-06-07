# Nexus Life OS - Roadmap Futuro

Este documento armazena ideias e recursos planejados para implementação futura, garantindo que o escopo principal (Estabilidade e Nuvem) seja priorizado sem perdermos inovações no radar.

## Biometria de Voz e Controle de Acesso (Voice Diarization)
**Status:** Planejado (Pós-Mobile)
**Conceito:** O sistema Jarvis conseguirá escutar o ambiente e distinguir "quem" está falando.

**Como vai funcionar:**
1. **Cadastro (Voice Print):** A IA vai extrair um vetor matemático (embedding) do tom de voz do dono (ex: Jean) e associá-lo como `Level: Admin`. 
2. **Adição de Familiares:** O dono pode "apresentar" novos usuários por voz. Ex: *"Jarvis, essa é a Laura"*. O sistema recorta o áudio de saudação dela, extrai o vetor da voz e salva no banco de dados como `Level: 2`.
3. **Diarização em Tempo Real:** Quando houverem múltiplos locutores na sala, a IA separará o áudio (Diarização) e identificará a voz (Identificação de Locutor) cruzando os embeddings. O log passará ao LLM a indicação de quem falou o quê:
   - `[Jean]: Jarvis, apague minha última anotação.` (Permitido)
   - `[Laura]: Jarvis, abra a conta bancária do Jean.` (Bloqueado via Role-Based Access Control)

**Por que não fazer agora?**
- É um recurso avançado que depende de modelos de áudio rodando de forma otimizada (como ECAPA-TDNN) para não travar o PC local.
- O foco atual absoluto é remover o banco de dados do HD local e jogá-lo na nuvem para viabilizar o App Mobile.
