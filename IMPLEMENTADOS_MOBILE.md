# Funcionalidades do Nexus Mobile (Implementadas)

Este documento centraliza tudo o que já foi implementado na transição do "Cérebro Jarvis" do Desktop para o Celular.

## 📱 Funcionalidades Concluídas

**Fase 1 a 3:**
- Interface Dark Neon Glassmorphism (Visual Hacker).
- Sistema Gamificado de Hábitos (com XP, ícones customizados e frequência).
- Botão flutuante "Call Jarvis" (Início).

**Fase 5: Sessão de Estudos Inteligente**
- Editor de Anotações Completo (Title, Subject, Content).
- Diff Editor (Painel de sugestões da Inteligência Artificial idêntico a revisões de código).
- Sistema de Auto-sumarização (O PC gera um Assunto Geral quando a nota é salva no celular).

**Fase 6: Módulo de Vídeos e Insights**
- Captura de link do YouTube.
- Extração de Transcrição e Inserção inteligente nas Notas via PC/Gemini.

**Fase 7 a 10: O Core Nativo & Jarvis Background**
- **Memória:** Sincronização Local e Nuvem (`nexus_memory_sync`). O celular herda as memórias do PC.
- **Background Call Service:** Um Serviço de Plano de Fundo nativo Android (Java) que mantém a ligação com o Jarvis ativa mesmo com o app minimizado ou tela desligada (Foreground Notification).
- **Olhos do Jarvis:** O celular envia o que está na Área de Transferência (Clipboard) para o Jarvis silenciosamente sob demanda.
- **Chat Textual:** UI de Histórico do Chat na aba de Início para interação silenciosa.
- **Abas Restantes:** UI Mock para Loja, Metas, Treino e Casa Inteligente (IoT).

---

## ⏸ Funcionalidades Congeladas / Adiadas
Por decisão do usuário (12/06/2026), as seguintes funcionalidades do PC **não serão** implementadas no Mobile neste momento:

1. **Visão Contínua (Vision Tracker):** Tirar fotos contínuas e analisar via YOLO na tela gasta muita bateria no ambiente móvel. Adiado.
2. **Avatar 3D / Visualizador de Áudio Contínuo:** Renderização pesada de interface gráfica para IA. Adiado.

*(Documento atualizado automaticamente pelo Jarvis).*
