import re

with open('mobile-apk/app/src/main/java/com/nexus/mobile/MainActivity.java', 'r', encoding='utf-8') as f:
    c = f.read()

interface_class = '''
    private class WebAppInterface {
        @JavascriptInterface
        public void startJarvisCall() {
            runOnUiThread(() -> {
                Intent serviceIntent = new Intent(MainActivity.this, JarvisCallService.class);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    startForegroundService(serviceIntent);
                } else {
                    startService(serviceIntent);
                }
            });
        }

        @JavascriptInterface
        public void stopJarvisCall() {
            runOnUiThread(() -> {
                Intent serviceIntent = new Intent(MainActivity.this, JarvisCallService.class);
                serviceIntent.setAction("STOP_SERVICE");
                startService(serviceIntent);
            });
        }

        @JavascriptInterface
        public void captureScreenAndClipboard() {
            runOnUiThread(() -> {
                // Clipboard reading
                android.content.ClipboardManager clipboard = (android.content.ClipboardManager) getSystemService(android.content.Context.CLIPBOARD_SERVICE);
                String clipText = "";
                if (clipboard != null && clipboard.hasPrimaryClip() && clipboard.getPrimaryClip().getItemCount() > 0) {
                    CharSequence text = clipboard.getPrimaryClip().getItemAt(0).getText();
                    if(text != null) clipText = text.toString();
                }
                
                // Screen Capture (Simplified mock for now to avoid MediaProjection complexities in background)
                // In a real app, MediaProjection requires user consent Intent onActivityResult.
                String finalClip = clipText;
                
                // Send back to JS
                String jsCode = "javascript:if(window.receiveNativeVision) window.receiveNativeVision('Clipboard: " + finalClip.replace("'", "\\\\'") + "');";
                webView.evaluateJavascript(jsCode, null);
            });
        }
    }
'''

if 'WebAppInterface' not in c:
    # Insert class before the final brace
    c = c[:c.rfind('}')] + interface_class + '\n}\n'
    
    # Add interface binding in onCreate
    # Find webView setup
    setup_str = 'webView.getSettings().setJavaScriptEnabled(true);'
    if setup_str in c:
        c = c.replace(setup_str, setup_str + '\n        webView.addJavascriptInterface(new WebAppInterface(), "AndroidNative");')
        
    with open('mobile-apk/app/src/main/java/com/nexus/mobile/MainActivity.java', 'w', encoding='utf-8') as f:
        f.write(c)
