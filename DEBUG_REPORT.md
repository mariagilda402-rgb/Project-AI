# 🔍 Nexus Mobile — Relatório de Debug & Otimização

## 🔴 BUGS CRÍTICOS (podem causar crashes ou falha silenciosa)

### BUG 1: `WebAppInterface` nunca é registrada no WebView
**Arquivo:** `MainActivity.java` linha 372  
**Problema:** A classe `WebAppInterface` é declarada como inner class mas **nunca é adicionada ao WebView**.
O código que a vincula (`.addJavascriptInterface`) está em `configureWebView()` mas foi injetado por script que aponta para `NexusAndroid`, não `AndroidNative`:
```java
webView.addJavascriptInterface(new NexusAndroidBridge(), "NexusAndroid");
// FALTANDO:
// webView.addJavascriptInterface(new WebAppInterface(), "AndroidNative");
```
O JS chama `window.AndroidNative.startJarvisCall()` mas o `AndroidNative` **não existe!**
→ **Resultado:** Toda a Fase 10 (Ligação Jarvis), Fase 11 (Câmera OCR) e Fase 13 (Notificações) NÃO funcionam.

---

### BUG 2: `openNativeCamera()` e `stopJarvisCall()` sem `@JavascriptInterface`
**Arquivo:** `MainActivity.java` linhas 409 e 420  
**Problema:** Os métodos `openNativeCamera()` e `stopJarvisCall()` estão na `WebAppInterface` mas SEM a anotação `@JavascriptInterface`. O Android ignora silenciosamente métodos sem essa anotação.

---

### BUG 3: Três `@JavascriptInterface` duplicados consecutivos (linhas 385-389)
**Arquivo:** `MainActivity.java` linhas 385-389  
Três anotações `@JavascriptInterface` vazias seguidas antes de `showNotification()`. Isso é resultante das injeções por script. Embora não cause crash, é código morto e confunde o compilador.

---

### BUG 4: `nav-item` sem `data-target` causa `getElementById(null)` → crash JS
**Arquivo:** `mobile/index.html`  
O item de navegação "Diário" foi adicionado com `onclick` mas **sem** `data-target`:
```html
<a href="#" class="nav-item" onclick="openJournal(); return false;">
```
O código JS da navegação faz `document.getElementById(targetId).classList.add(...)` onde `targetId` será `null` → **TypeError, app congela**.

---

### BUG 5: `loadVideos()` procura `id="videos-list"` mas o HTML tem `id="video-list"`
**Arquivo:** `app.js` linha 165 vs `index.html`  
O container no HTML é `view-videos` sem lista interna nomeada corretamente. A função tenta usar `getElementById('videos-list')` → retorna `null` → erro silencioso.

---

### BUG 6: Polling de GPS enviando para Supabase a cada 5 min cria muitas linhas
**Arquivo:** `app.js` — `initGeoFencing()`  
Cada checagem de GPS insere uma nova linha na tabela `nexus_commands`. Em 24h = ~288 registros/dia só de GPS. Em 1 semana = ~2000 registros. A tabela vai crescer infinitamente sem limpeza.

---

### BUG 7: Base64 de imagem dentro de coluna `TEXT` do Supabase pode exceder limite
**Arquivo:** `app.js` — `receiveCameraImage()`  
Uma foto de câmera com thumbnail (mesmo comprimido) é ~50-200KB em Base64 = ~270KB de texto. Muitos bancos/APIs têm limite de coluna. O Supabase tem limite de row de 1MB mas o PostgREST pode rejeitar se o JSON total exceder 10MB.

---

## 🟡 OTIMIZAÇÕES DE BATERIA

| Problema | Impacto | Solução |
|---|---|---|
| GPS polling rodando no `setInterval` de 5min sem verificar se app está em foreground | Alto | Usar `document.visibilityState` para pausar quando em background |
| Notificações: polling Supabase a cada 20s SEMPRE | Médio | Reduzir para 60s quando em segundo plano, 20s quando ativo |
| `backgroundSync()` função desativada com `return;` no início mas ainda declarada | Baixo | Limpar código morto |
| `injectDeviceContext()` recria JSON e salva no localStorage em cada carregamento | Baixo | Cache por 1h |
| Sem debounce no `sendChatMessage()` — usuário pode spammar inserts | Médio | Adicionar loading state e debounce |

---

## 🟡 PERMISSÕES FALTANDO NO MANIFEST

| Permissão | Por que é necessária | Status |
|---|---|---|
| `ACCESS_FINE_LOCATION` | GPS geofencing (Fase 14) | ❌ FALTANDO |
| `ACCESS_COARSE_LOCATION` | Fallback para GPS | ❌ FALTANDO |
| `READ_MEDIA_IMAGES` (Android 13+) | Ler imagens da galeria para OCR | ❌ FALTANDO |
| `READ_EXTERNAL_STORAGE` (Android < 13) | Compatibilidade de leitura de arquivos | ❌ FALTANDO |
| `WRITE_EXTERNAL_STORAGE` | Download do APK para updates | ❌ FALTANDO |
| `WAKE_LOCK` | Manter CPU ligada durante ligação em background | ❌ FALTANDO |
| `RECEIVE_BOOT_COMPLETED` | Reiniciar serviço se celular reiniciar | ❌ FALTANDO |

**Permissões presentes e corretas:** INTERNET, RECORD_AUDIO, CAMERA, FOREGROUND_SERVICE, POST_NOTIFICATIONS ✅

---

## 🟠 GAPS DE FUNCIONALIDADE (falta no mobile vs PC)

1. **`maybeRequestRuntimePermissions()` não pede LOCATION** → o GPS nunca receberá permissão no Android 6+
2. **`Notification` global não existe no WebView Android** → `sendLocalNotification()` vai crashar (linha 141). Service Workers não rodam em `file://`
3. **`navigator.serviceWorker` retorna `undefined` em WebView** → o bloco de registro do SW sempre falha silenciosamente
4. **`window.supabase.channel()` não existe** → a tentativa de usar Realtime do Supabase (linha 398 na versão anterior) falha
5. **`flashcard-view` tem `display:none` E `display:flex` no mesmo style inline** — o segundo sobrescreve o primeiro, então ele aparece sempre visível ao carregar a página
6. **`journal-view` aberto via JS com `style.display='flex'` não está na div `.view`** → não é controlado pelo roteador de navegação, pode ficar aberto ao trocar de aba

---

## ✅ O QUE FUNCIONA BEM

- Carregamento OTA (Over-The-Air) do bundle JS/HTML via GitHub Pages ✅
- Atualização do APK nativo via FileProvider ✅  
- Sistema Offline-First com LocalDB (localStorage) ✅
- Interface Neon Glassmorphism ✅
- Hábitos com gamificação (XP, ícones) ✅
- `NexusAndroidBridge` (`NexusAndroid`) conectada corretamente ✅
- Foreground Service (`JarvisCallService`) declarado corretamente ✅
- Chat UI e envio para Supabase ✅

---

## 🛠️ PRIORIDADE DE CORREÇÃO

| Prioridade | Item |
|---|---|
| 🔴 P0 | Registrar `WebAppInterface` como `"AndroidNative"` no WebView |
| 🔴 P0 | Adicionar `@JavascriptInterface` em `openNativeCamera()` e `stopJarvisCall()` |
| 🔴 P0 | Adicionar `ACCESS_FINE_LOCATION` ao Manifest + pedir runtime |
| 🔴 P0 | Corrigir nav-item "Diário" sem `data-target` |
| 🔴 P0 | Remover `display:flex` duplicado do `flashcard-view` |
| 🟡 P1 | Limpar GPS — inserir apenas se posição mudou mais de 500m |
| 🟡 P1 | Substituir `sendLocalNotification()` (quebrado) por `window.AndroidNative.showNotification()` |
| 🟡 P1 | Adicionar `WRITE_EXTERNAL_STORAGE` e `WAKE_LOCK` ao Manifest |
| 🟡 P1 | Polling de notificações: pausar quando `document.hidden` |
| 🟢 P2 | Remover código morto (`backgroundSync` com `return;`) |
| 🟢 P2 | Debounce no envio de mensagem do Chat |
