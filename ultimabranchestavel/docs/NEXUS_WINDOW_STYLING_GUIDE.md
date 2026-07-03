# Guia de Estilização das Janelas Nexus

> [!CAUTION]
> **LEIA ISTO ANTES DE EDITAR QUALQUER CSS DO NEXUS LIFE OS.**
> Este documento existe porque já perdemos tempo significativo tentando estilizar módulos pelo arquivo errado.

## Arquitetura de CSS das Janelas Nexus

Quando o Python abre uma janela de módulo Nexus (ex: Hábitos, Finanças), o seguinte acontece:

1. O HTML do módulo é lido do disco (`src/ui/nexus_modules/<modulo>.html`)
2. A função `_compose_nexus_module_html()` em `desktop_app.py` **injeta** código adicional:
   - Um `<base href="file:///...nexus_modules/">` — mas é injetado **DEPOIS** dos `<link>` do `<head>` original
   - O arquivo `nexus_frame.css` — que controla o chrome/frame da janela
   - O wrapper `#nx-app-wrapper` envolvendo todo o `<body>`
3. O HTML final é passado como string via `html=` para o `webview.create_window()`

## ⚠️ REGRAS CRÍTICAS

### 1. `nexus.css` externo NÃO FUNCIONA para estilizar módulos
O `<link rel="stylesheet" href="nexus.css">` no `<head>` do módulo **não carrega** porque:
- O `<base>` tag é injetado DEPOIS do `<link>`, então o path relativo não resolve
- Mesmo que resolvesse, `nexus_frame.css` tem seletores de maior especificidade (`#nx-app-wrapper .card`, etc.) que sobrescrevem tudo

### 2. ONDE colocar estilos de módulo
**Use `<style>` inline dentro do próprio `<head>` do HTML do módulo.**

```html
<head>
  <meta charset="utf-8" />
  <title>Nexus · Meu Módulo</title>
  <!-- NÃO USE: <link rel="stylesheet" href="nexus.css" /> -->
  <style>
    /* Seus estilos aqui, com seletores de alta especificidade */
    #nx-app-wrapper .minha-classe { ... }
  </style>
</head>
```

### 3. Use seletores de ALTA ESPECIFICIDADE
O `nexus_frame.css` usa `#nx-app-wrapper .card`, `#nx-app-wrapper input`, etc.
Para sobrescrever, use:

```css
/* ✅ Correto — especificidade alta */
#nx-app-wrapper .nx-chrome-inner > header { ... }
#nx-app-wrapper .nx-chrome-inner > main { ... }
#nx-app-wrapper .meu-card-custom { ... }

/* ❌ Errado — será sobrescrito pelo nexus_frame.css */
.card { ... }
input { ... }
header { ... }
```

### 4. Variáveis CSS disponíveis (definidas pelo nexus_frame.css)
Dentro de `#nx-app-wrapper`, as seguintes variáveis estão disponíveis:

| Variável | Valor | Uso |
|---|---|---|
| `--bg` | `#0a0a0a` | Fundo principal |
| `--bg-panel` | `#111111` | Fundo dos cards |
| `--surface` | `rgba(255,255,255,0.04)` | Superfícies sutis |
| `--border` | `rgba(255,255,255,0.08)` | Bordas padrão |
| `--border-accent` | `rgba(139,92,246,0.35)` | Bordas neon |
| `--text` | `#e4e4e7` | Texto principal |
| `--text-dim` | `#71717a` | Texto secundário |
| `--muted` | `#71717a` | Texto apagado |
| `--accent` | `#8b5cf6` | Cor de destaque (roxo) |
| `--accent-glow` | `rgba(139,92,246,0.3)` | Brilho neon |
| `--danger` | `#ef4444` | Vermelho |
| `--success` | `#22c55e` | Verde |
| `--warning` | `#f59e0b` | Amarelo |

### 5. O `nexus_frame.css` JÁ aplica tema escuro
Não precisa redefinir cores de fundo, cards básicos, inputs, e botões. O frame já cuida disso.
Foque apenas nos **estilos específicos do seu módulo**.

## Fluxo de Renderização

```
habits.html  →  _compose_nexus_module_html()  →  HTML final
    │                      │
    │                      ├── Injeta <base href>
    │                      ├── Injeta <script>boot</script>
    │                      ├── Injeta nexus_frame.css
    │                      └── Envolve body em #nx-app-wrapper > .nx-chrome-bar + .nx-chrome-inner
    │
    └── <style> inline é preservado e funciona ✅
```

## Referência: `nexus_frame.css` já estiliza:
- `body` (transparent, flex, animation)
- `#nx-app-wrapper` (dark bg, rounded, neon border spin)
- `.nx-chrome-bar` (barra de título)
- `.nx-chrome-inner` (área de conteúdo)
- `#nx-app-wrapper .card` (cards escuros)
- `#nx-app-wrapper input/textarea/select` (inputs escuros)
- `#nx-app-wrapper .btn-primary/.btn-ghost` (botões)
- `#nx-app-wrapper .toast-banner`
