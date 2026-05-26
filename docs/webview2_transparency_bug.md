# 🪟 Bug da Transparência WebView2 — Documentação Técnica

> **Status:** ✅ RESOLVIDO
> **Data:** 2025-05-19
> **Tempo de investigação:** ~5 horas
> **Arquivos afetados:** `desktop_app.py`, `nexus_window_api.py`, `nexus_boot.js`, `panel.html`

---

## 🐛 O Problema

Quando a janela do painel (unificado ou principal) era **maximizada e depois restaurada ao tamanho normal**, um **quadrado branco** aparecia ao redor do conteúdo da interface. A transparência do fundo, que funcionava perfeitamente na abertura inicial, era **permanentemente quebrada** após qualquer operação de resize/maximize/restore.

Além disso, ao maximizar usando `toggle_fullscreen()`, o navegador Opera (e possivelmente outros apps) **congelava** enquanto a janela transparente estivesse em foco.

---

## 🔬 Causa Raiz

O PyWebView usa o **Microsoft Edge WebView2** como motor de renderização no Windows. O WebView2 roda em um **processo separado** do aplicativo Python. A transparência funciona assim:

1. O PyWebView cria uma janela Win32 com `transparent=True` → configura `WS_EX_LAYERED`
2. O WebView2 Controller recebe `DefaultBackgroundColor = Color.Transparent`
3. O CSS do HTML usa `background-color: transparent` no `<html>` e `<body>`

**O bug:** Quando o WebView2 precisa re-renderizar após um resize, existe um pequeno delay entre o redimensionamento da janela host e a re-renderização do conteúdo web. Durante esse delay, o WebView2 pinta seu **fundo padrão interno (branco)**, e em certas operações de resize no Windows, o motor **nunca restaura a transparência** — ela fica permanentemente quebrada até a janela ser destruída e recriada.

### Por que isso acontece especificamente:
- O WebView2 é um processo separado (Edge browser engine)
- O redimensionamento causa um "gap" de renderização onde o compositor do WebView2 perde a referência do canal Alpha
- O Windows DWM (Desktop Window Manager) interpreta o resize como uma mudança de estado da janela e pode desativar otimizações de transparência
- Uma vez que o compositor do WebView2 "perde" a transparência, **nenhuma API externa consegue restaurá-la** — nem `SetWindowLongW`, nem `SetLayeredWindowAttributes`, nem variáveis de ambiente

---

## ❌ O que NÃO funcionou (e por quê)

### 1. `background_color='#0a0a0a'` no `webview.create_window()`
**Por que falhou:** Este parâmetro define a cor do fundo da janela Win32, mas o WebView2 tem seu próprio compositor interno que ignora essa configuração quando a transparência é habilitada. O CSS `background: transparent` no HTML tem prioridade sobre essa cor.

### 2. `WEBVIEW2_DEFAULT_BACKGROUND_COLOR = "00000000"` (env var)
**Por que falhou:** Esta variável de ambiente é aplicada **apenas na inicialização** do ambiente WebView2. Após o motor estar rodando e ocorrer um resize, ele não re-lê essa variável. Além disso, o pywebview pode não repassar essa variável para o processo filho do Edge.

### 3. Re-aplicar `WS_EX_LAYERED` via ctypes (Win32 API)
**Por que falhou:** A flag `WS_EX_LAYERED` geralmente **já está presente** na janela — o Windows não a remove durante o resize. O problema não é a flag em si, mas sim o **compositor interno do WebView2** que perdeu a referência de transparência. Forçar a flag não tem efeito porque ela já existia.

### 4. `SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA)`
**Por que falhou:** Esta API controla a **opacidade global** da janela (0-255), não a transparência per-pixel que o WebView2 usa. Definir alpha=255 apenas confirma que a janela está 100% opaca como um todo, mas não restaura a transparência do **conteúdo CSS** dentro do WebView2.

### 5. `.maximize()` nativo do PyWebView
**Por que falhou:** Envia o comando `SW_MAXIMIZE` do Windows, que muda o **estado da janela** no gerenciador de janelas. Isso ativa a "Otimização de Tela Cheia" do DWM, que congela a renderização GPU de apps em background (Opera). Além disso, o `.restore()` após o maximize quebra a transparência definitivamente.

### 6. `.toggle_fullscreen()` do PyWebView
**Por que falhou:** Pior que `.maximize()` — coloca a janela em modo exclusivo de tela cheia, sobrepondo a barra de tarefas. Congela todos os apps atrás e quebra a transparência na volta.

### 7. "Fake Maximize" (resize manual via ctypes) sem hide/show
**Por que falhou parcialmente:** O fake maximize funcionou para **não congelar o Opera** (grande vitória!), mas o resize em si ainda causava o flash branco do WebView2 e a perda permanente de transparência ao restaurar.

---

## ✅ A Solução que Funcionou

### Técnica: **Hide → Resize → Show**

```python
# Ao desmaximizar:
w.hide()                          # 1. Esconde a janela
w.move(prev_x, prev_y)           # 2. Reposiciona (invisível)
w.resize(prev_w, prev_h)         # 3. Redimensiona (invisível)
time.sleep(0.15)                  # 4. Aguarda WebView2 processar
w.show()                          # 5. Mostra de volta
```

### Por que funciona:
- Quando o PyWebView faz `w.hide()`, o processo do WebView2 **desativa seu compositor**
- Quando `w.show()` é chamado, o WebView2 **re-inicializa completamente** seu pipeline de renderização
- Nessa re-inicialização, ele **re-lê** a configuração de transparência e a aplica corretamente
- O resize acontece **enquanto a janela está oculta**, então não há "gap" de renderização visível
- Do ponto de vista do usuário, é um piscar imperceptível de ~150ms

### Para o maximize (Fake Maximize):
Em vez de usar `.maximize()` nativo (que causa problemas com o DWM), calculamos manualmente o tamanho da área útil da tela via `ctypes.SystemParametersInfoW(SPI_GETWORKAREA)` e fazemos `w.move() + w.resize()`. O Windows nunca sabe que a janela foi "maximizada", evitando otimizações destrutivas do DWM.

---

## 📋 Resumo para Correção Rápida (Instruções Futuras)

Se este bug voltar a acontecer em qualquer janela do projeto:

1. **NUNCA use** `.maximize()`, `.restore()`, ou `.toggle_fullscreen()` em janelas transparentes
2. **SEMPRE use** "Fake Maximize": `move() + resize()` com coordenadas calculadas via `SystemParametersInfoW`
3. **SEMPRE faça** `hide() → resize() → sleep(0.15) → show()` ao restaurar o tamanho
4. O `ResizeObserver` no JavaScript (`nexus_boot.js` e `panel.html`) cuida de remover bordas/padding/sombras CSS quando a janela atinge o tamanho máximo da tela

---

## 📁 Arquivos Modificados

| Arquivo | O que foi alterado |
|---|---|
| `src/ui/desktop_app.py` | Env var `WEBVIEW2_DEFAULT_BACKGROUND_COLOR`, Fake Maximize, Hide→Show cycle |
| `src/ui/nexus_window_api.py` | Fake Maximize, Hide→Show cycle (para janelas Nexus) |
| `src/ui/nexus_modules/nexus_boot.js` | `ResizeObserver` para CSS adaptativo em tela cheia |
| `src/ui/panel.html` | `ResizeObserver` para CSS adaptativo em tela cheia |
