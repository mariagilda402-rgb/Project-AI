# Agent instructions for Project-AI

## Mobile app guardrails

- Start by reading this file before editing the repository.
- Do **not** edit `mobile/app.js` directly. It is generated from the ordered modules in `mobile/js/manifest.txt`.
- Make source changes in `mobile/js/*.js`, update `mobile/js/manifest.txt` when adding/removing modules, then run `python scripts/bundle_mobile_js.py`.
- Keep the mobile app offline-first: preserve local storage, local data fallbacks, and graceful degradation when Supabase, network, clipboard, notification, or Android bridge APIs are unavailable.
- Do not add parallel stale copies such as `mobile/app.js.new`, `mobile/app.js.bak`, or similar generated-bundle backups.

## Required checks before commit/PR

Run these checks for mobile changes whenever possible:

```bash
python scripts/check_mobile_integrity.py
python scripts/bundle_mobile_js.py
node --check mobile/app.js
for f in mobile/js/*.js; do node --check "$f" || exit 1; done
pytest -q tests/test_mobile_runtime_contract.py tests/test_mobile_youtube_adb_smoke.py
```

If Android SDK is unavailable, do not claim that an Android build or screenshot was completed. Report the environment limitation explicitly.
