# Nexus Mobile JavaScript modules

`mobile/app.js` remains the single script loaded by the PWA/Android WebView for runtime stability. Do **not** edit it directly.

Edit the ordered modules in this directory, then rebuild the bundle:

```bash
python scripts/bundle_mobile_js.py
```

The load order is controlled by `mobile/js/manifest.txt`. Keep `16_compat_contract.js` last; it exposes legacy inline HTML handlers on `window` and protects optional features with safe fallbacks.
