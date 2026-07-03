# Mobile App Deployment & Architecture

## Problema Frequente
Muitas vezes, ao atualizar arquivos como `app.js` ou `index.html` na pasta `/mobile` local, e enviar via ADB para o celular, as alterações parecem não surtir efeito. Isso ocorre devido ao sistema de `WebViewAssetLoader` configurado no `MainActivity.java`.

## Como Funciona o WebViewAssetLoader
O Android App (Nexus Mobile) intercepta requisições de rede feitas pela WebView e serve arquivos locais. A lógica de URLs funciona da seguinte forma:

1. **LOCAL_APP_URL (`https://appassets.androidplatform.net/assets/index.html`)**: 
   Acessa a pasta nativa `assets` embutida e empacotada **dentro do APK** original. Quando o app não tem atualizações "Over-The-Air" (OTA), ele usa essa versão base imutável.
   
2. **DOWNLOADED_APP_URL (`https://appassets.androidplatform.net/bundle/index.html`)**:
   Acessa arquivos instalados na memória interna do celular, mais especificamente em: `/data/data/com.nexus.mobile/files/mobile_bundle/`. 
   O aplicativo dá prioridade para ler dessa pasta caso ela exista. Se a pasta `mobile_bundle` existir, a WebView vai direcionar requisições de assets para ela, efetivamente permitindo Hot Reloading e OTA Updates sem precisar recompilar o APK.

## O Erro de Deployment
Enviar arquivos para `files/www` ou para o cache (`app_webview`) não resolve, pois a WebView do Nexus Mobile está programada (via `InternalBundlePathHandler`) para sempre buscar as atualizações da pasta `mobile_bundle`.

### Solução e Script Padrão
Para garantir que as atualizações sejam aplicadas no app mobile instantaneamente via ADB, deve-se SEMPRE utilizar o script python padronizado de deploy:

```bash
python scripts/push_mobile_bundle_adb.py
```

O que este script faz:
1. Cria a pasta `files/mobile_bundle` usando o namespace do pacote (`com.nexus.mobile`).
2. Puxa todos os arquivos (HTML, CSS, JS, manifest) para o armazenamento tmp do Android.
3. Move os arquivos para `files/mobile_bundle`.
4. Força a parada do aplicativo e reabre.
5. Isso anula a necessidade de lidar manualmente com Service Workers (`sw.js`) e cache, pois os arquivos físicos em disco serão sobrescritos no diretório de bundles do Android.
