# Unified Jarvis PC + Mobile Implementation Plan

> Atualizado em 2026-06-22 para registrar a decisao de produto: o objetivo e "um Jarvis, varios dispositivos", com memoria compartilhada, voz transferivel entre PC/celular, acoes remotas, exibidor universal e interrupcao por voz/toque. Este arquivo e o plano permanente para continuar mesmo se o historico do chat for perdido.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one Jarvis consciousness shared by PC and mobile, with shared memory, one active voice endpoint, device handoff, remote actions, interruptible tasks, and a universal visual renderer that works on both devices.

**Architecture:** Keep the desktop as the strongest runtime at first, but do not make the mobile app useless without it. Add a small `src/jarvis_unified/` layer for session state, device registry, events, memory gateway, command routing, and renderer contracts; connect the mobile WebView through a local WebSocket first, then add cloud relay later.

**Tech Stack:** Python dataclasses, existing desktop services, Flask + `flask-sock` pattern already used by `src/services/visualizer_app.py`, Android WebView + Java bridge, plain mobile JavaScript, pytest, ADB, later Supabase Realtime/Presence and Firebase Cloud Messaging.

---

## Product Decision

The right mental model is:

```text
One Jarvis mind, many bodies.
```

The PC, phone, and future Android TV are surfaces/devices. They should not become separate Jarvis personalities.

Portuguese product summary:

- O Jarvis deve ter uma consciencia unica, nao um Jarvis separado no PC e outro no celular.
- O endpoint de fala pode ser o celular enquanto o endpoint de acao e o PC.
- O usuario pode dizer no celular: "Jarvis, vai para o PC e pesquisa X"; ele continua ouvindo/respondendo pelo celular, mas age no PC.
- O usuario pode dizer no PC: "vamos continuar pelo celular"; o sistema deve abrir/ativar o app mobile e mover o canal de voz para ele.
- O celular nao deve virar um app morto quando o PC estiver fechado. Ele continua com estudos, notas, tarefas, financas, OCR e acoes locais.
- A memoria importante deve ser compartilhada, mas sem injetar o banco inteiro em todo prompt. O Jarvis consulta indices/resumos conforme precisa.
- O exibidor universal deve renderizar blocos consistentes nos dois dispositivos: texto, markdown, imagens, videos, tabelas, metricas, graficos, progresso e transcricao em tempo real.

Important rules:

- Only one active voice channel should speak at a time.
- The device receiving speech does not need to be the device executing the action.
- The mobile app must keep local features working when the PC is offline.
- The PC can be the primary brain when it is online.
- All long actions, speech, generated UI, and remote commands need interruption support.
- Do not do a broad desktop refactor before proving the integration path.

Example:

```text
User speaks on phone:
"Jarvis, go to the PC and research square roots."

Session:
voice_endpoint = mobile:moto-e20
action_target = desktop:main-pc
display_endpoint = mobile:moto-e20
```

Jarvis keeps listening and speaking through the phone while the desktop performs the browser/research/file actions.

## Current Code Map

Desktop strengths:

- `src/agent/orchestrator.py` coordinates LLM turns, tools, memory, streaming, and runtime mode.
- `src/services/llm.py` already supports Gemini, Groq, OpenRouter, NVIDIA, and Ollama.
- `src/services/tts.py` already supports several desktop TTS providers.
- `src/services/stt.py` already has speech recognition and Groq Whisper support.
- `src/memory/store.py`, `src/memory/vector_db.py`, and `src/memory/structured_memory.py` already store memory.
- `src/tools/*` already performs PC actions.
- `src/services/nexus_service.py` already exposes notes, flashcards, tasks, finance, habits, and Nexus actions.
- `src/services/visualizer_app.py` already uses Flask + WebSocket and should be the model for the first local bridge.

Mobile strengths:

- `mobile/` is the WebView app bundle.
- `mobile/app.js` contains LocalDB, studies, notes, tasks, finance, habits, Jarvis note agent, OCR, and call mode UI.
- `mobile-apk/app/src/main/java/com/nexus/mobile/MainActivity.java` exposes native Android bridge methods to JavaScript.
- `mobile-apk/app/src/main/java/com/nexus/mobile/JarvisCallService.java` already supports a foreground call service.

Known mobile call issue:

- `AndroidNative.startJarvisCall()` currently blocks call mode when not on Wi-Fi.
- The call service notification exists, but reliable mobile TTS for the conversation still needs a provider path.

## External API Notes

Verified references on 2026-06-22:

- Groq TTS: https://console.groq.com/docs/text-to-speech
- Groq STT: https://console.groq.com/docs/speech-to-text
- Supabase Realtime Broadcast: https://supabase.com/docs/guides/realtime/broadcast
- Supabase Realtime Presence: https://supabase.com/docs/guides/realtime/presence
- Firebase Cloud Messaging: https://firebase.google.com/docs/cloud-messaging

Practical reading:

- Groq TTS exists through an OpenAI-compatible `audio/speech` endpoint, but the official TTS docs currently list English and Arabic voices. Do not assume pt-BR quality until tested on the device.
- Groq STT is a good fit for mobile speech-to-text because the project already uses Groq.
- Groq Vision/OCR exists and is a good fit for "foto do caderno para texto". The mobile app already has a Groq Vision OCR path with Gemini fallback.
- Groq should not be treated as the default image generator. For notes with images, prefer: trusted web/Wikipedia image insertion first; later add a dedicated image model/provider if real image generation is required.
- Groq Compound can be useful for research because it can use built-in web/code tools, but the note agent must still validate/sanitize output before inserting into notes.
- Supabase Realtime is a good candidate for the later cloud relay and presence.
- FCM is useful for waking/notifying Android when the app is closed; it should not carry full sensitive conversation payloads.

Provider recommendation:

- LLM/research: Groq first for speed, with Gemini fallback when Groq fails or when Gemini is better for a specific multimodal task.
- STT: Groq Whisper first.
- OCR/vision: Groq Vision first, Gemini fallback.
- TTS mobile pt-BR: test Groq first only as an experiment; if pronunciation/voice is poor, prefer ElevenLabs/OpenAI/Edge-style backend audio.
- Image generation: not Groq by default; use web assets first, then a separate image-generation provider later.

## What Will Be Implemented First

The first implementation should be Phase 1, not the whole dream at once. It creates the "spine" that all later features need.

Package 1: Unified session spine

- Add `src/jarvis_unified/` with models, session state, device registry, event bus, memory gateway skeleton and renderer schema.
- Add feature flags in `.env`/`src/config.py`: `UNIFIED_JARVIS_ENABLED`, host, port and optional token.
- Start a local LAN bridge from desktop only when the flag is enabled.
- Let mobile register itself as a device and send/receive events through WebSocket.
- Add interrupt events (`speech`, `display`, `task`, `all`) even before every subsystem can fully cancel.
- Add minimal renderer host on mobile for assistant transcript/render updates.
- Remove the hard Wi-Fi-only restriction from Android `startJarvisCall()`.
- Add native `getUnifiedDeviceInfo()` in Android so the mobile device is not hardcoded as "Moto E20".

What this first package will prove:

- PC and celular can see the same active session.
- The phone can say "I am the voice/display endpoint".
- The PC can remain the action target.
- The phone can send "interrupt all".
- The mobile UI can receive live render/transcript events from desktop.

What it will not solve yet:

- Full cloud relay outside LAN.
- Android Accessibility control.
- Perfect TTS on mobile.
- Full note-writing agent over the desktop orchestrator.
- Complete universal renderer blocks.
- True cancellation of every long-running desktop tool.

Package 2: Shared memory bridge

- Expand `MemoryGateway` to query desktop short-term memory, structured memory, semantic memory and Nexus notes/tasks/habits/finance summaries.
- Add mobile event merge types: `note_saved`, `note_agent_change`, `task_completed`, `habit_completed`, `finance_transaction_added`, `mobile_voice_turn`.
- Store compact memory facts, not full mobile database dumps.
- Ensure saved note summaries/keywords from mobile are visible to the desktop Jarvis when it searches context.

Package 3: Reliable mobile voice loop

- Move call-mode speech through a backend/provider path with `speech_id`.
- Add stop/cancel for currently playing speech.
- Test TTS providers on real phone:
  - Groq first as experiment.
  - Edge/backend audio if stable and free.
  - OpenAI/ElevenLabs if quality is worth API use.
- Keep Groq STT for transcription because it is already a good fit.

Package 4: Universal renderer v1

- Implement renderer blocks on mobile first: markdown, image, YouTube, table, metric grid, line/bar charts, progress, tool status and transcript.
- Reuse the same JSON schema for desktop HUD later.
- Make Jarvis able to create dashboards like finance market view, research board, study explanation and task execution progress.

Package 5: Remote command routing

- Add `CommandRouter`.
- Start with safe commands:
  - `desktop.search_web`
  - `desktop.open_app`
  - `desktop.open_nexus_tab`
  - `mobile.open_nexus_view`
  - `mobile.open_call_mode`
  - `mobile.render_surface`
- Add confirmation for risky operations.
- Add audit log for cross-device actions.

Package 6: Cloud and wake

- Add Supabase Realtime/Presence after LAN path works.
- Use FCM only to wake/notify Android, not to send private conversation payloads.
- Add signed/authenticated events before any remote action outside LAN.

Package 7: Android Accessibility

- Add only after session/cloud/security is stable.
- Build explicit consent UI, persistent status indicator and emergency stop.
- Implement primitives: read screen, tap, type, back, open app.
- Keep confirmation required for purchases, banking, account changes, deletion and messaging.

Recommended execution order now:

1. Implement Package 1 completely and deploy to phone.
2. Verify phone connects to desktop bridge and can send interrupt.
3. Implement Package 2 memory bridge so Jarvis really feels like one consciousness.
4. Fix mobile TTS/call mode.
5. Build the universal renderer.

This order is deliberate: without session/events, TTS, renderer, memory and remote control become isolated hacks.

## File Structure

Create:

- `src/jarvis_unified/__init__.py`
  - Public package marker.
- `src/jarvis_unified/models.py`
  - Dataclasses for `DeviceInfo`, `JarvisSession`, `JarvisEvent`, `RenderDocument`, and command payloads.
- `src/jarvis_unified/session_state.py`
  - Thread-safe current session state, voice endpoint, display endpoint, active tasks, and interruption token.
- `src/jarvis_unified/device_registry.py`
  - Online devices, capabilities, last seen timestamps, and heartbeat expiration.
- `src/jarvis_unified/event_bus.py`
  - In-process publish/subscribe event bus used by tests and the local server.
- `src/jarvis_unified/local_server.py`
  - Flask + `flask-sock` local bridge for mobile/desktop events.
- `src/jarvis_unified/memory_gateway.py`
  - Unified interface over memory store, vector memory, structured memory, and Nexus data.
- `src/jarvis_unified/renderer_schema.py`
  - Universal renderer validation and helper constructors.
- `tests/test_unified_jarvis_models.py`
- `tests/test_unified_jarvis_session.py`
- `tests/test_unified_jarvis_event_bus.py`
- `tests/test_unified_jarvis_memory_gateway.py`
- `tests/test_unified_jarvis_renderer_schema.py`

Modify:

- `src/config.py`
  - Add feature flags and local bridge settings.
- `src/main.py`
  - Start the local bridge when enabled.
- `src/agent/orchestrator.py`
  - Later: accept a device/session context and send deltas/events.
- `src/services/tts.py`
  - Later: expose cancellable speech IDs and optional mobile/cloud output.
- `src/services/nexus_service.py`
  - Later: expose compact memory snapshots and mobile note/task/habit event merge.
- `mobile/index.html`
  - Add connection/status surface and universal renderer host.
- `mobile/app.js`
  - Add `UnifiedJarvisClient`, event handling, interrupt, handoff, and renderer client.
- `mobile/style.css`
  - Add compact status and renderer styles.
- `mobile-apk/app/src/main/java/com/nexus/mobile/MainActivity.java`
  - Add native bridge helpers for device info, call handoff, and app wake behavior.
- `mobile-apk/app/src/main/java/com/nexus/mobile/JarvisCallService.java`
  - Keep foreground service stable for call mode.
- `tests/test_mobile_runtime_contract.py`
  - Add contract checks for new mobile handlers and UI anchors.

## Core Contracts

### DeviceInfo

```json
{
  "device_id": "mobile:moto-e20",
  "kind": "mobile",
  "name": "Moto E20",
  "capabilities": {
    "voice_input": true,
    "voice_output": true,
    "display": true,
    "camera": true,
    "local_actions": true,
    "desktop_control": false,
    "accessibility_control": false
  },
  "status": "online",
  "last_seen": "2026-06-22T12:00:00Z"
}
```

### JarvisSession

```json
{
  "session_id": "uuid",
  "active_user": "maria",
  "voice_endpoint": "mobile:moto-e20",
  "display_endpoint": "mobile:moto-e20",
  "action_target": "desktop:main-pc",
  "active_tasks": [],
  "interruption_token": "uuid",
  "last_turn_at": "2026-06-22T12:00:00Z"
}
```

### JarvisEvent

```json
{
  "event_id": "uuid",
  "session_id": "uuid",
  "source_device": "mobile:moto-e20",
  "target_device": "desktop:main-pc",
  "type": "user_utterance",
  "payload": {
    "text": "Jarvis, go to the PC and research square roots."
  },
  "created_at": "2026-06-22T12:00:00Z",
  "expires_at": "2026-06-22T12:01:00Z"
}
```

Event types for phase 1:

- `device_register`
- `device_heartbeat`
- `user_utterance`
- `assistant_delta`
- `assistant_final`
- `handoff_voice`
- `set_action_target`
- `render_update`
- `tool_status`
- `interrupt`

### Interrupt Event

```json
{
  "type": "interrupt",
  "payload": {
    "scope": "speech|display|task|all",
    "reason": "user_voice",
    "task_id": "optional-task-id"
  }
}
```

Each runtime maps this to:

- Stop current TTS.
- Stop or pause STT if needed.
- Cancel pending LLM request when possible.
- Cancel a tool/task if it has `task_id`.
- Clear/freeze generated UI when requested.

### Universal Renderer

Start with a JSON document:

```json
{
  "surface_id": "market-dashboard",
  "type": "dashboard",
  "title": "Market overview",
  "blocks": [
    {
      "id": "m1",
      "type": "metric_grid",
      "items": [
        {"label": "Ibovespa", "value": "123400", "delta": "-0.8%"}
      ]
    },
    {
      "id": "table1",
      "type": "table",
      "columns": ["Asset", "Price", "Day"],
      "rows": [["PETR4", "R$ 38.20", "+1.2%"]]
    }
  ]
}
```

Incremental update:

```json
{
  "type": "render_update",
  "payload": {
    "surface_id": "market-dashboard",
    "op": "append|replace|patch|clear",
    "block": {
      "id": "speech1",
      "type": "assistant_transcript",
      "text": "I found the strongest movements..."
    }
  }
}
```

Initial block types:

- `text`
- `markdown`
- `image`
- `video_youtube`
- `table`
- `metric_grid`
- `chart_line`
- `chart_bar`
- `progress`
- `timeline`
- `tool_status`
- `assistant_transcript`

## Implementation Phases

### Phase 0 - This document

Status: complete when this file exists and is reviewed.

Decision:

- Start LAN/local first.
- Keep cloud relay for phase 6.
- Keep Android accessibility for phase 7.
- Fix mobile TTS after the session/event spine exists, unless call mode becomes a blocker.

### Phase 1 - Local session spine PC <-> mobile

Goal:

Mobile and desktop share one session, register devices, send events, hand off voice/action targets, and interrupt running surfaces.

### Phase 2 - Unified memory

Goal:

Both devices query the same memory through `MemoryGateway`. Mobile still keeps local data, but important mobile events can be merged into desktop memory when connected.

### Phase 3 - Reliable mobile call TTS

Goal:

Make call mode speak reliably on the phone, with cancellation.

Provider order to test:

1. Groq TTS as a device experiment, because it already fits the Groq account flow. Current official docs list English/Arabic, so this may fail the pt-BR quality bar.
2. Edge/free backend TTS if it can produce stable audio files streamed to mobile.
3. OpenAI TTS if the existing key is available and latency is acceptable.
4. ElevenLabs if natural Portuguese matters more than free/cheap use.
5. Android/Web Speech fallback only as emergency.

### Phase 4 - Universal Renderer v1

Goal:

Jarvis can show consistent dashboards, text, images, videos, charts, task progress, and transcript on mobile and desktop.

Important note/media behavior:

- When creating study notes, Jarvis may use web research plus the local note index to decide between creating a new note or updating an existing note.
- It should inspect note titles, subjects, summaries, keywords and only open full content for likely matches.
- It should prepare a draft/change set before applying when risk is non-trivial.
- It should support undo for generated note edits.
- Images in notes should initially come from trusted URLs/assets with captions/sources. Generated images require a separate provider later.
- YouTube embeds can use the existing mobile editor integration when the source is relevant.

### Phase 5 - Secure remote actions

Goal:

Phone can ask Jarvis to act on PC; PC can ask Jarvis to open/navigate Nexus mobile. Sensitive actions require confirmation and audit logs.

### Phase 6 - Cloud relay

Goal:

Work outside the local network with Supabase Realtime/Presence or equivalent. Use FCM only for Android wake/notification.

### Phase 7 - Android accessibility and multi-device

Goal:

With explicit consent, Jarvis can control other Android apps. Later add Android TV as a display/action target.

---

## Phase 1 Detailed Tasks

### Task 1: Baseline Checks

**Files:**

- Read: `src/config.py`
- Read: `src/main.py`
- Read: `src/services/visualizer_app.py`
- Read: `mobile/app.js`
- Read: `mobile-apk/app/src/main/java/com/nexus/mobile/MainActivity.java`

- [ ] **Step 1: Run current desktop tests related to config/mobile**

Run:

```powershell
pytest tests/test_config_defaults.py tests/test_mobile_runtime_contract.py -q
```

Expected:

```text
passed
```

- [ ] **Step 2: Run mobile JavaScript parser check**

Run:

```powershell
node --check mobile/app.js
```

Expected: exit code `0`.

- [ ] **Step 3: Confirm Android device/package if doing device QA**

Run:

```powershell
adb devices
adb shell cmd package resolve-activity --brief com.nexus.mobile
```

Expected output includes:

```text
com.nexus.mobile/.MainActivity
```

### Task 2: Add Unified Jarvis Settings

**Files:**

- Modify: `src/config.py`
- Modify: `tests/test_config_defaults.py`

- [ ] **Step 1: Write failing config test**

Append to `tests/test_config_defaults.py`:

```python
def test_unified_jarvis_settings_from_env(monkeypatch):
    monkeypatch.setenv("UNIFIED_JARVIS_ENABLED", "true")
    monkeypatch.setenv("UNIFIED_JARVIS_HOST", "127.0.0.1")
    monkeypatch.setenv("UNIFIED_JARVIS_PORT", "5124")
    monkeypatch.setenv("UNIFIED_JARVIS_TOKEN", "dev-token")

    settings = load_settings()

    assert settings.unified_jarvis_enabled is True
    assert settings.unified_jarvis_host == "127.0.0.1"
    assert settings.unified_jarvis_port == 5124
    assert settings.unified_jarvis_token == "dev-token"
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
pytest tests/test_config_defaults.py::test_unified_jarvis_settings_from_env -q
```

Expected: fail because `Settings` does not yet expose these fields.

- [ ] **Step 3: Add fields to `Settings`**

Add near the end of `Settings` in `src/config.py`:

```python
    unified_jarvis_enabled: bool = False
    unified_jarvis_host: str = "0.0.0.0"
    unified_jarvis_port: int = 5124
    unified_jarvis_token: str = ""
```

- [ ] **Step 4: Populate fields in `load_settings()`**

Add to the `Settings(...)` return:

```python
        unified_jarvis_enabled=_as_bool(
            os.getenv("UNIFIED_JARVIS_ENABLED"), default=False
        ),
        unified_jarvis_host=(
            os.getenv("UNIFIED_JARVIS_HOST", "0.0.0.0") or "0.0.0.0"
        ).strip(),
        unified_jarvis_port=_as_int(
            os.getenv("UNIFIED_JARVIS_PORT"), 5124, minimum=1024, maximum=65535
        ),
        unified_jarvis_token=(os.getenv("UNIFIED_JARVIS_TOKEN", "") or "").strip(),
```

- [ ] **Step 5: Run config tests**

Run:

```powershell
pytest tests/test_config_defaults.py -q
```

Expected: all tests pass.

### Task 3: Add Shared Models

**Files:**

- Create: `src/jarvis_unified/__init__.py`
- Create: `src/jarvis_unified/models.py`
- Create: `tests/test_unified_jarvis_models.py`

- [ ] **Step 1: Write model tests**

Create `tests/test_unified_jarvis_models.py`:

```python
from src.jarvis_unified.models import DeviceInfo, JarvisEvent, JarvisSession


def test_device_info_defaults_to_online():
    device = DeviceInfo(
        device_id="mobile:moto-e20",
        kind="mobile",
        name="Moto E20",
        capabilities={"voice_input": True, "display": True},
    )

    assert device.status == "online"
    assert device.capabilities["voice_input"] is True


def test_session_tracks_voice_display_and_action_target():
    session = JarvisSession.create(active_user="maria")

    session.voice_endpoint = "mobile:moto-e20"
    session.display_endpoint = "mobile:moto-e20"
    session.action_target = "desktop:main-pc"

    assert session.voice_endpoint == "mobile:moto-e20"
    assert session.display_endpoint == "mobile:moto-e20"
    assert session.action_target == "desktop:main-pc"
    assert session.interruption_token


def test_event_roundtrip_dict():
    event = JarvisEvent.create(
        session_id="s1",
        source_device="mobile:moto-e20",
        target_device="desktop:main-pc",
        event_type="user_utterance",
        payload={"text": "pesquise raiz quadrada"},
    )

    data = event.to_dict()
    restored = JarvisEvent.from_dict(data)

    assert restored.event_id == event.event_id
    assert restored.type == "user_utterance"
    assert restored.payload["text"] == "pesquise raiz quadrada"
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
pytest tests/test_unified_jarvis_models.py -q
```

Expected: fail because package does not exist.

- [ ] **Step 3: Create package marker**

Create `src/jarvis_unified/__init__.py`:

```python
"""Unified Jarvis PC/mobile runtime contracts."""
```

- [ ] **Step 4: Implement models**

Create `src/jarvis_unified/models.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class DeviceInfo:
    device_id: str
    kind: str
    name: str
    capabilities: dict[str, Any]
    status: str = "online"
    last_seen: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeviceInfo":
        return cls(
            device_id=str(data["device_id"]),
            kind=str(data["kind"]),
            name=str(data.get("name") or data["device_id"]),
            capabilities=dict(data.get("capabilities") or {}),
            status=str(data.get("status") or "online"),
            last_seen=str(data.get("last_seen") or utc_now_iso()),
        )


@dataclass(slots=True)
class JarvisSession:
    session_id: str
    active_user: str
    voice_endpoint: str = ""
    display_endpoint: str = ""
    action_target: str = ""
    active_tasks: list[dict[str, Any]] = field(default_factory=list)
    interruption_token: str = field(default_factory=lambda: str(uuid4()))
    last_turn_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def create(cls, active_user: str) -> "JarvisSession":
        return cls(session_id=str(uuid4()), active_user=active_user)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class JarvisEvent:
    event_id: str
    session_id: str
    source_device: str
    target_device: str
    type: str
    payload: dict[str, Any]
    created_at: str
    expires_at: str

    @classmethod
    def create(
        cls,
        session_id: str,
        source_device: str,
        target_device: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        ttl_seconds: int = 60,
    ) -> "JarvisEvent":
        now = datetime.now(timezone.utc)
        return cls(
            event_id=str(uuid4()),
            session_id=session_id,
            source_device=source_device,
            target_device=target_device,
            type=event_type,
            payload=dict(payload or {}),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=max(1, ttl_seconds))).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JarvisEvent":
        return cls(
            event_id=str(data["event_id"]),
            session_id=str(data["session_id"]),
            source_device=str(data["source_device"]),
            target_device=str(data.get("target_device") or ""),
            type=str(data["type"]),
            payload=dict(data.get("payload") or {}),
            created_at=str(data.get("created_at") or utc_now_iso()),
            expires_at=str(data.get("expires_at") or utc_now_iso()),
        )
```

- [ ] **Step 5: Run model tests**

Run:

```powershell
pytest tests/test_unified_jarvis_models.py -q
```

Expected: all tests pass.

### Task 4: Add Session State And Device Registry

**Files:**

- Create: `src/jarvis_unified/session_state.py`
- Create: `src/jarvis_unified/device_registry.py`
- Create: `tests/test_unified_jarvis_session.py`

- [ ] **Step 1: Write session/registry tests**

Create `tests/test_unified_jarvis_session.py`:

```python
from src.jarvis_unified.device_registry import DeviceRegistry
from src.jarvis_unified.models import DeviceInfo
from src.jarvis_unified.session_state import JarvisSessionState


def test_session_handoff_and_action_target():
    state = JarvisSessionState(active_user="maria")
    session = state.current()

    state.set_voice_endpoint("mobile:moto-e20")
    state.set_display_endpoint("mobile:moto-e20")
    state.set_action_target("desktop:main-pc")

    updated = state.current()
    assert updated.session_id == session.session_id
    assert updated.voice_endpoint == "mobile:moto-e20"
    assert updated.display_endpoint == "mobile:moto-e20"
    assert updated.action_target == "desktop:main-pc"


def test_interrupt_rotates_token_and_clears_tasks_for_all_scope():
    state = JarvisSessionState(active_user="maria")
    state.add_task({"task_id": "t1", "kind": "research"})
    before = state.current().interruption_token

    event = state.interrupt(scope="all", reason="user_voice")

    after = state.current().interruption_token
    assert after != before
    assert state.current().active_tasks == []
    assert event.payload["scope"] == "all"


def test_device_registry_upserts_and_lists_online_devices():
    registry = DeviceRegistry()
    registry.upsert(
        DeviceInfo(
            device_id="desktop:main-pc",
            kind="desktop",
            name="Main PC",
            capabilities={"desktop_control": True},
        )
    )

    devices = registry.list_devices()

    assert len(devices) == 1
    assert devices[0].device_id == "desktop:main-pc"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
pytest tests/test_unified_jarvis_session.py -q
```

Expected: fail because implementation files do not exist.

- [ ] **Step 3: Implement session state**

Create `src/jarvis_unified/session_state.py`:

```python
from __future__ import annotations

import threading
from uuid import uuid4

from .models import JarvisEvent, JarvisSession, utc_now_iso


class JarvisSessionState:
    def __init__(self, active_user: str = "maria") -> None:
        self._lock = threading.RLock()
        self._session = JarvisSession.create(active_user=active_user)

    def current(self) -> JarvisSession:
        with self._lock:
            return JarvisSession(**self._session.to_dict())

    def set_voice_endpoint(self, device_id: str) -> JarvisSession:
        with self._lock:
            self._session.voice_endpoint = device_id
            self._session.last_turn_at = utc_now_iso()
            return self.current()

    def set_display_endpoint(self, device_id: str) -> JarvisSession:
        with self._lock:
            self._session.display_endpoint = device_id
            self._session.last_turn_at = utc_now_iso()
            return self.current()

    def set_action_target(self, device_id: str) -> JarvisSession:
        with self._lock:
            self._session.action_target = device_id
            self._session.last_turn_at = utc_now_iso()
            return self.current()

    def add_task(self, task: dict) -> JarvisSession:
        with self._lock:
            self._session.active_tasks.append(dict(task))
            self._session.last_turn_at = utc_now_iso()
            return self.current()

    def interrupt(self, scope: str = "all", reason: str = "user") -> JarvisEvent:
        with self._lock:
            self._session.interruption_token = str(uuid4())
            if scope in {"all", "task"}:
                self._session.active_tasks.clear()
            self._session.last_turn_at = utc_now_iso()
            return JarvisEvent.create(
                session_id=self._session.session_id,
                source_device="system",
                target_device="*",
                event_type="interrupt",
                payload={"scope": scope, "reason": reason},
                ttl_seconds=10,
            )
```

- [ ] **Step 4: Implement device registry**

Create `src/jarvis_unified/device_registry.py`:

```python
from __future__ import annotations

import threading
from datetime import datetime, timezone

from .models import DeviceInfo, utc_now_iso


class DeviceRegistry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._devices: dict[str, DeviceInfo] = {}

    def upsert(self, device: DeviceInfo) -> DeviceInfo:
        with self._lock:
            device.status = "online"
            device.last_seen = utc_now_iso()
            self._devices[device.device_id] = device
            return DeviceInfo.from_dict(device.to_dict())

    def get(self, device_id: str) -> DeviceInfo | None:
        with self._lock:
            device = self._devices.get(device_id)
            return DeviceInfo.from_dict(device.to_dict()) if device else None

    def list_devices(self) -> list[DeviceInfo]:
        with self._lock:
            return [DeviceInfo.from_dict(d.to_dict()) for d in self._devices.values()]

    def mark_offline_if_stale(self, max_age_seconds: int = 30) -> list[DeviceInfo]:
        now = datetime.now(timezone.utc)
        changed: list[DeviceInfo] = []
        with self._lock:
            for device in self._devices.values():
                try:
                    last_seen = datetime.fromisoformat(device.last_seen)
                except ValueError:
                    last_seen = now
                if (now - last_seen).total_seconds() > max_age_seconds and device.status != "offline":
                    device.status = "offline"
                    changed.append(DeviceInfo.from_dict(device.to_dict()))
        return changed
```

- [ ] **Step 5: Run tests**

Run:

```powershell
pytest tests/test_unified_jarvis_session.py -q
```

Expected: all tests pass.

### Task 5: Add Event Bus

**Files:**

- Create: `src/jarvis_unified/event_bus.py`
- Create: `tests/test_unified_jarvis_event_bus.py`

- [ ] **Step 1: Write event bus test**

Create `tests/test_unified_jarvis_event_bus.py`:

```python
from src.jarvis_unified.event_bus import JarvisEventBus
from src.jarvis_unified.models import JarvisEvent


def test_event_bus_publishes_to_matching_subscribers():
    bus = JarvisEventBus()
    received = []

    bus.subscribe("assistant_delta", received.append)
    event = JarvisEvent.create(
        session_id="s1",
        source_device="desktop:main-pc",
        target_device="mobile:moto-e20",
        event_type="assistant_delta",
        payload={"text": "Oi"},
    )

    bus.publish(event)

    assert received == [event]


def test_event_bus_keeps_recent_history():
    bus = JarvisEventBus(max_history=2)
    for idx in range(3):
        bus.publish(
            JarvisEvent.create(
                session_id="s1",
                source_device="a",
                target_device="b",
                event_type="tool_status",
                payload={"idx": idx},
            )
        )

    assert [e.payload["idx"] for e in bus.history()] == [1, 2]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
pytest tests/test_unified_jarvis_event_bus.py -q
```

Expected: fail because implementation does not exist.

- [ ] **Step 3: Implement event bus**

Create `src/jarvis_unified/event_bus.py`:

```python
from __future__ import annotations

import threading
from collections import defaultdict, deque
from collections.abc import Callable

from .models import JarvisEvent


EventHandler = Callable[[JarvisEvent], None]


class JarvisEventBus:
    def __init__(self, max_history: int = 100) -> None:
        self._lock = threading.RLock()
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: deque[JarvisEvent] = deque(maxlen=max(1, max_history))

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        with self._lock:
            self._subscribers[event_type].append(handler)

    def publish(self, event: JarvisEvent) -> None:
        with self._lock:
            self._history.append(event)
            handlers = list(self._subscribers.get(event.type, []))
            handlers.extend(self._subscribers.get("*", []))
        for handler in handlers:
            handler(event)

    def history(self) -> list[JarvisEvent]:
        with self._lock:
            return list(self._history)
```

- [ ] **Step 4: Run event bus tests**

Run:

```powershell
pytest tests/test_unified_jarvis_event_bus.py -q
```

Expected: all tests pass.

### Task 6: Add Local Flask/WebSocket Bridge

**Files:**

- Create: `src/jarvis_unified/local_server.py`
- Modify: `src/main.py`
- Test: `tests/test_unified_jarvis_event_bus.py`

- [ ] **Step 1: Implement app factory**

Create `src/jarvis_unified/local_server.py` with an app factory, not a global server:

```python
from __future__ import annotations

import json
import threading
from typing import Any

from .device_registry import DeviceRegistry
from .event_bus import JarvisEventBus
from .models import DeviceInfo, JarvisEvent
from .session_state import JarvisSessionState


def create_app(
    session_state: JarvisSessionState,
    registry: DeviceRegistry,
    bus: JarvisEventBus,
    token: str = "",
):
    from flask import Flask, jsonify, request
    from flask_sock import Sock

    app = Flask(__name__)
    sock = Sock(app)
    clients: list[Any] = []
    clients_lock = threading.RLock()

    def authorized() -> bool:
        if not token:
            return True
        return request.headers.get("X-Jarvis-Token") == token

    def broadcast(event: JarvisEvent) -> None:
        message = json.dumps(event.to_dict(), ensure_ascii=False)
        with clients_lock:
            dead = []
            for ws in clients:
                try:
                    ws.send(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                clients.remove(ws)

    bus.subscribe("*", broadcast)

    @app.route("/api/jarvis/session")
    def api_session():
        if not authorized():
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        return jsonify({"ok": True, "session": session_state.current().to_dict()})

    @app.route("/api/jarvis/devices", methods=["GET", "POST"])
    def api_devices():
        if not authorized():
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            device = registry.upsert(DeviceInfo.from_dict(data))
            event = JarvisEvent.create(
                session_id=session_state.current().session_id,
                source_device=device.device_id,
                target_device="*",
                event_type="device_register",
                payload=device.to_dict(),
            )
            bus.publish(event)
            return jsonify({"ok": True, "device": device.to_dict()})
        return jsonify({"ok": True, "devices": [d.to_dict() for d in registry.list_devices()]})

    @app.route("/api/jarvis/events", methods=["POST"])
    def api_events():
        if not authorized():
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        event = JarvisEvent.from_dict(request.get_json(silent=True) or {})
        bus.publish(event)
        return jsonify({"ok": True})

    @sock.route("/jarvis/ws")
    def ws_handler(ws):
        with clients_lock:
            clients.append(ws)
        try:
            ws.send(json.dumps({"type": "session", "session": session_state.current().to_dict()}))
            while True:
                raw = ws.receive(timeout=30)
                if raw is None:
                    ws.send(json.dumps({"type": "ping"}))
                    continue
                event = JarvisEvent.from_dict(json.loads(raw))
                bus.publish(event)
        except Exception:
            pass
        finally:
            with clients_lock:
                if ws in clients:
                    clients.remove(ws)

    return app
```

- [ ] **Step 2: Add server starter**

In the same file, add:

```python
def start_background_server(host: str, port: int, token: str = ""):
    session_state = JarvisSessionState(active_user="maria")
    registry = DeviceRegistry()
    bus = JarvisEventBus()
    app = create_app(session_state, registry, bus, token=token)

    thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True,
        name="UnifiedJarvisLocalServer",
    )
    thread.start()
    return thread
```

- [ ] **Step 3: Wire into `src/main.py`**

After settings are loaded and startup services begin, add guarded startup:

```python
    if getattr(settings, "unified_jarvis_enabled", False):
        try:
            from src.jarvis_unified.local_server import start_background_server

            start_background_server(
                settings.unified_jarvis_host,
                settings.unified_jarvis_port,
                token=settings.unified_jarvis_token,
            )
            print(
                f"[UnifiedJarvis] Local bridge on "
                f"http://{settings.unified_jarvis_host}:{settings.unified_jarvis_port}"
            )
        except Exception as exc:
            print(f"[UnifiedJarvis] Failed to start local bridge: {exc}")
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
pytest tests/test_unified_jarvis_models.py tests/test_unified_jarvis_session.py tests/test_unified_jarvis_event_bus.py tests/test_config_defaults.py -q
```

Expected: all tests pass.

### Task 7: Add Mobile Unified Client

**Files:**

- Modify: `mobile/index.html`
- Modify: `mobile/app.js`
- Modify: `mobile/style.css`
- Modify: `tests/test_mobile_runtime_contract.py`

- [ ] **Step 1: Add mobile contract test**

Append to `tests/test_mobile_runtime_contract.py`:

```python
def test_mobile_has_unified_jarvis_client_contract():
    app_js = read_app_js()
    html = read_index_html()

    assert "window.UnifiedJarvisClient" in app_js
    assert "window.connectUnifiedJarvis" in app_js
    assert "window.sendUnifiedJarvisInterrupt" in app_js
    assert 'id="unified-jarvis-status"' in html
    assert 'id="unified-renderer-surface"' in html
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
pytest tests/test_mobile_runtime_contract.py::test_mobile_has_unified_jarvis_client_contract -q
```

Expected: fail because handlers and anchors do not exist yet.

- [ ] **Step 3: Add status/renderer anchors**

Add near the existing Jarvis/call mode UI in `mobile/index.html`:

```html
<div id="unified-jarvis-status" class="unified-jarvis-status" data-state="offline">
    <span></span>
</div>
<section id="unified-renderer-surface" class="unified-renderer-surface" hidden></section>
```

- [ ] **Step 4: Add mobile JavaScript client**

Add near other Jarvis/mobile bridge functions in `mobile/app.js`:

```javascript
window.UnifiedJarvisClient = {
    socket: null,
    state: 'offline',
    deviceId: 'mobile:moto-e20',
    sessionId: '',
    url: localStorage.getItem('unified_jarvis_ws') || 'ws://127.0.0.1:5124/jarvis/ws',

    setState(state) {
        this.state = state;
        const node = document.getElementById('unified-jarvis-status');
        if (node) {
            node.dataset.state = state;
            const label = node.querySelector('span') || node;
            label.textContent = state === 'online' ? 'Jarvis PC conectado' : 'Jarvis PC offline';
        }
    },

    connect() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) return;
        try {
            this.socket = new WebSocket(this.url);
        } catch (error) {
            this.setState('offline');
            return;
        }
        this.socket.onopen = () => {
            this.setState('online');
            this.sendEvent('device_register', '*', {
                device_id: this.deviceId,
                kind: 'mobile',
                name: 'Moto E20',
                capabilities: {
                    voice_input: true,
                    voice_output: true,
                    display: true,
                    camera: true,
                    local_actions: true
                }
            });
        };
        this.socket.onmessage = (message) => this.handleMessage(message.data);
        this.socket.onclose = () => this.setState('offline');
        this.socket.onerror = () => this.setState('offline');
    },

    sendEvent(type, targetDevice, payload) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return false;
        const event = {
            event_id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
            session_id: this.sessionId || 'mobile-session',
            source_device: this.deviceId,
            target_device: targetDevice || '*',
            type,
            payload: payload || {},
            created_at: new Date().toISOString(),
            expires_at: new Date(Date.now() + 60000).toISOString()
        };
        this.socket.send(JSON.stringify(event));
        return true;
    },

    handleMessage(raw) {
        let event;
        try {
            event = JSON.parse(raw);
        } catch (_) {
            return;
        }
        if (event.type === 'session' && event.session) {
            this.sessionId = event.session.session_id || this.sessionId;
            return;
        }
        if (event.type === 'render_update') {
            renderUnifiedJarvisUpdate(event.payload || {});
        }
        if (event.type === 'assistant_delta' && event.payload && event.payload.text) {
            renderUnifiedJarvisUpdate({
                surface_id: 'assistant-live',
                op: 'append',
                block: { type: 'assistant_transcript', text: event.payload.text }
            });
        }
    }
};

window.connectUnifiedJarvis = function() {
    window.UnifiedJarvisClient.connect();
};

window.sendUnifiedJarvisInterrupt = function(scope) {
    return window.UnifiedJarvisClient.sendEvent('interrupt', '*', {
        scope: scope || 'all',
        reason: 'user_tap'
    });
};

function renderUnifiedJarvisUpdate(update) {
    const surface = document.getElementById('unified-renderer-surface');
    if (!surface) return;
    surface.hidden = false;
    if (update.op === 'clear') {
        surface.innerHTML = '';
        return;
    }
    const block = update.block || {};
    if (block.type === 'assistant_transcript') {
        const line = document.createElement('p');
        line.className = 'unified-renderer-transcript';
        line.textContent = block.text || '';
        surface.appendChild(line);
    }
}
```

- [ ] **Step 5: Add minimal CSS**

Add to `mobile/style.css`:

```css
.unified-jarvis-status {
    position: fixed;
    left: 12px;
    bottom: 82px;
    z-index: 1200;
    border: 1px solid rgba(255,255,255,0.1);
    background: rgba(8,10,16,0.88);
    color: var(--text-secondary);
    border-radius: 999px;
    padding: 7px 10px;
    font-size: 0.72rem;
    pointer-events: none;
}

.unified-jarvis-status[data-state="online"] {
    color: #8ff0c1;
    border-color: rgba(34,197,94,0.35);
}

.unified-renderer-surface {
    margin: 12px;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(9,12,20,0.92);
    border-radius: 14px;
    padding: 12px;
}

.unified-renderer-transcript {
    margin: 0 0 8px;
    color: var(--text-primary);
    line-height: 1.45;
}
```

- [ ] **Step 6: Run tests and parser**

Run:

```powershell
node --check mobile/app.js
pytest tests/test_mobile_runtime_contract.py::test_mobile_has_unified_jarvis_client_contract -q
```

Expected: parser succeeds and contract test passes.

### Task 8: Fix Call Mode Wi-Fi Dependency And Add Native Device Info

**Files:**

- Modify: `mobile-apk/app/src/main/java/com/nexus/mobile/MainActivity.java`
- Modify: `mobile-apk/app/src/main/java/com/nexus/mobile/JarvisCallService.java`
- Modify: `tests/test_mobile_runtime_contract.py`

- [ ] **Step 1: Add contract test for native bridge**

Append to `tests/test_mobile_runtime_contract.py`:

```python
def test_mobile_native_bridge_exposes_unified_device_helpers():
    main = (ROOT / "mobile-apk" / "app" / "src" / "main" / "java" / "com" / "nexus" / "mobile" / "MainActivity.java").read_text(encoding="utf-8")

    assert "getUnifiedDeviceInfo" in main
    assert "startJarvisCall" in main
    assert "Conecte-se ao Wi-Fi para ligar ao Jarvis" not in main
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
pytest tests/test_mobile_runtime_contract.py::test_mobile_native_bridge_exposes_unified_device_helpers -q
```

Expected: fail until native code is changed.

- [ ] **Step 3: Remove hard Wi-Fi block from `startJarvisCall()`**

Replace:

```java
if (!isWifiConnected()) {
    runOnUiThread(() -> Toast.makeText(MainActivity.this,
        "Conecte-se ao Wi-Fi para ligar ao Jarvis.", Toast.LENGTH_LONG).show());
    return;
}
```

with no hard return. The call can warn later in JS, but the service should start on mobile data too.

- [ ] **Step 4: Add native device info**

Inside `WebAppInterface`, add:

```java
@JavascriptInterface
public String getUnifiedDeviceInfo() {
    try {
        JSONObject json = new JSONObject();
        json.put("device_id", "mobile:" + Build.MANUFACTURER.toLowerCase() + "-" + Build.MODEL.toLowerCase().replace(" ", "-"));
        json.put("kind", "mobile");
        json.put("name", Build.MANUFACTURER + " " + Build.MODEL);
        JSONObject capabilities = new JSONObject();
        capabilities.put("voice_input", true);
        capabilities.put("voice_output", true);
        capabilities.put("display", true);
        capabilities.put("camera", true);
        capabilities.put("local_actions", true);
        capabilities.put("accessibility_control", false);
        json.put("capabilities", capabilities);
        return json.toString();
    } catch (Exception e) {
        return "{\"device_id\":\"mobile:android\",\"kind\":\"mobile\",\"name\":\"Android\",\"capabilities\":{}}";
    }
}
```

- [ ] **Step 5: Use native device info in mobile JS later**

In `mobile/app.js`, update `UnifiedJarvisClient.connect()` later to call:

```javascript
if (window.AndroidNative && typeof AndroidNative.getUnifiedDeviceInfo === 'function') {
    try {
        const nativeDevice = JSON.parse(AndroidNative.getUnifiedDeviceInfo());
        this.deviceId = nativeDevice.device_id || this.deviceId;
    } catch (_) {}
}
```

- [ ] **Step 6: Run tests and APK build**

Run:

```powershell
pytest tests/test_mobile_runtime_contract.py::test_mobile_native_bridge_exposes_unified_device_helpers -q
cd mobile-apk
.\gradlew.bat :app:assembleDebug
cd ..
```

Expected: test passes and APK build succeeds.

### Task 9: Add Memory Gateway Skeleton

**Files:**

- Create: `src/jarvis_unified/memory_gateway.py`
- Create: `tests/test_unified_jarvis_memory_gateway.py`

- [ ] **Step 1: Write skeleton tests**

Create `tests/test_unified_jarvis_memory_gateway.py`:

```python
from src.jarvis_unified.memory_gateway import MemoryGateway


class FakeNexusService:
    def __init__(self):
        self.saved_events = []

    def get_study_recommendations(self, limit):
        return [{"title": "Matematica"}]


def test_memory_gateway_returns_compact_context():
    gateway = MemoryGateway(nexus_service=FakeNexusService())

    result = gateway.query("matematica", limit=3)

    assert result["query"] == "matematica"
    assert "sources" in result


def test_memory_gateway_accepts_mobile_event():
    fake = FakeNexusService()
    gateway = MemoryGateway(nexus_service=fake)

    merged = gateway.merge_mobile_event({
        "kind": "note_saved",
        "title": "Raiz quadrada",
        "summary": "Resumo curto"
    })

    assert merged["ok"] is True
    assert merged["kind"] == "note_saved"
```

- [ ] **Step 2: Implement skeleton gateway**

Create `src/jarvis_unified/memory_gateway.py`:

```python
from __future__ import annotations

from typing import Any


class MemoryGateway:
    def __init__(self, memory_store: Any = None, vector_memory: Any = None, structured_memory: Any = None, nexus_service: Any = None) -> None:
        self.memory_store = memory_store
        self.vector_memory = vector_memory
        self.structured_memory = structured_memory
        self.nexus_service = nexus_service

    def query(self, query: str, limit: int = 8) -> dict[str, Any]:
        sources: list[dict[str, Any]] = []
        if self.nexus_service and hasattr(self.nexus_service, "get_study_recommendations"):
            try:
                sources.append({
                    "source": "nexus_study",
                    "items": self.nexus_service.get_study_recommendations(limit),
                })
            except Exception:
                pass
        return {
            "ok": True,
            "query": query,
            "sources": sources,
        }

    def merge_mobile_event(self, event: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "kind": str(event.get("kind") or "unknown"),
            "stored": False,
        }
```

- [ ] **Step 3: Run gateway tests**

Run:

```powershell
pytest tests/test_unified_jarvis_memory_gateway.py -q
```

Expected: all tests pass.

### Task 10: Add Renderer Schema Skeleton

**Files:**

- Create: `src/jarvis_unified/renderer_schema.py`
- Create: `tests/test_unified_jarvis_renderer_schema.py`

- [ ] **Step 1: Write renderer tests**

Create `tests/test_unified_jarvis_renderer_schema.py`:

```python
from src.jarvis_unified.renderer_schema import make_dashboard, make_render_update, validate_block


def test_validate_supported_blocks():
    assert validate_block({"type": "text", "text": "Oi"})["ok"] is True
    assert validate_block({"type": "chart_pie"})["ok"] is False


def test_make_dashboard_and_update():
    doc = make_dashboard("market", "Mercado", [{"type": "text", "text": "Resumo"}])
    update = make_render_update("market", "append", {"type": "assistant_transcript", "text": "Falando..."})

    assert doc["surface_id"] == "market"
    assert update["type"] == "render_update"
    assert update["payload"]["op"] == "append"
```

- [ ] **Step 2: Implement renderer schema**

Create `src/jarvis_unified/renderer_schema.py`:

```python
from __future__ import annotations

from typing import Any


SUPPORTED_BLOCKS = {
    "text",
    "markdown",
    "image",
    "video_youtube",
    "table",
    "metric_grid",
    "chart_line",
    "chart_bar",
    "progress",
    "timeline",
    "tool_status",
    "assistant_transcript",
}


def validate_block(block: dict[str, Any]) -> dict[str, Any]:
    block_type = str(block.get("type") or "")
    if block_type not in SUPPORTED_BLOCKS:
        return {"ok": False, "error": f"Unsupported block type: {block_type}"}
    return {"ok": True}


def make_dashboard(surface_id: str, title: str, blocks: list[dict[str, Any]]) -> dict[str, Any]:
    valid_blocks = [block for block in blocks if validate_block(block)["ok"]]
    return {
        "surface_id": surface_id,
        "type": "dashboard",
        "title": title,
        "blocks": valid_blocks,
    }


def make_render_update(surface_id: str, op: str, block: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "type": "render_update",
        "payload": {
            "surface_id": surface_id,
            "op": op,
            "block": block or {},
        },
    }
```

- [ ] **Step 3: Run renderer tests**

Run:

```powershell
pytest tests/test_unified_jarvis_renderer_schema.py -q
```

Expected: all tests pass.

### Task 11: Device QA For Phase 1

**Files:**

- Use: `scripts/push_mobile_bundle_adb.py`
- Verify: connected Android device

- [ ] **Step 1: Run all new unit/contract tests**

Run:

```powershell
pytest tests/test_unified_jarvis_models.py tests/test_unified_jarvis_session.py tests/test_unified_jarvis_event_bus.py tests/test_unified_jarvis_memory_gateway.py tests/test_unified_jarvis_renderer_schema.py tests/test_mobile_runtime_contract.py tests/test_config_defaults.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Parse mobile JS**

Run:

```powershell
node --check mobile/app.js
```

Expected: exit code `0`.

- [ ] **Step 3: Deploy mobile bundle**

Run:

```powershell
python scripts/push_mobile_bundle_adb.py
```

Expected: bundle is pushed and `com.nexus.mobile` restarts.

- [ ] **Step 4: Start desktop bridge for manual QA**

Run the desktop app with:

```powershell
$env:UNIFIED_JARVIS_ENABLED='true'
$env:UNIFIED_JARVIS_HOST='0.0.0.0'
$env:UNIFIED_JARVIS_PORT='5124'
python -m src.main
```

Expected: log includes:

```text
[UnifiedJarvis] Local bridge
```

- [ ] **Step 5: Verify phone connects**

On the phone:

```text
Open Nexus.
Tap or trigger the unified Jarvis connection.
Status chip changes to "Jarvis PC conectado".
```

If testing through ADB/WebView console, verify:

```javascript
window.connectUnifiedJarvis()
window.UnifiedJarvisClient.state
```

Expected:

```text
online
```

- [ ] **Step 6: Verify interrupt event**

Run in WebView console:

```javascript
window.sendUnifiedJarvisInterrupt('all')
```

Expected:

```text
Desktop bridge receives an interrupt event.
No JavaScript error in WebView console.
```

## Later Phase Task Summaries

### Phase 2: Memory

- Expand `MemoryGateway.query()` to call `MemoryStore`, vector DB, structured memory, and Nexus summaries.
- Add mobile event types: `note_saved`, `task_completed`, `habit_completed`, `finance_transaction_added`, `jarvis_mobile_turn`.
- Store only compact memory facts by default; do not dump entire mobile database into every LLM turn.
- Add tests that a mobile note summary can be queried from desktop and vice versa.

### Phase 3: TTS

- Add `speech_id` to TTS calls.
- Add `TTSGateway.speak(text, target_device)` and `TTSGateway.stop(speech_id)`.
- Test Groq TTS pt-BR first; if voice quality is bad, test ElevenLabs.
- Mobile should be able to play remote audio and stop it on interrupt.

### Phase 4: Renderer

- Implement all initial block types in mobile.
- Reuse the same schema for desktop visualizer/HUD.
- Add progressive transcript updates while Jarvis speaks.
- Add chart blocks using the chart library already used by mobile when possible.

### Phase 5: Remote Actions

- Add `CommandRouter`.
- Start with safe commands:
  - `desktop.search_web`
  - `desktop.open_nexus`
  - `mobile.open_nexus_view`
  - `mobile.open_call_mode`
- Require confirmation for file deletion, purchases, bank actions, app installs, and Accessibility actions.

### Phase 6: Cloud

- Add Supabase Realtime Broadcast for event relay.
- Add Supabase Presence for device online/offline status.
- Add FCM only for Android wake/notification.
- Add device auth tokens and signed events before allowing remote actions outside LAN.

### Phase 7: Android Accessibility

- Build only after phase 1-6 are stable.
- Add explicit consent and persistent status UI.
- Add read-screen/tap/type/back primitives.
- Require confirmation for risky operations.

## Recommendation On Desktop Modularization

Do not modularize the whole desktop first.

Do this surgical split only:

- `src/jarvis_unified/session_state.py`
- `src/jarvis_unified/device_registry.py`
- `src/jarvis_unified/event_bus.py`
- `src/jarvis_unified/memory_gateway.py`
- `src/jarvis_unified/renderer_schema.py`

Reason:

The desktop already works and already has a lot of behavior. A broad refactor before the integration would delay the real goal and risk breaking tools, memory, TTS, STT, and Nexus. The session/event layer gives us a stable spine without rewriting the body.

## Open Questions

1. Should phase 1 be LAN-only first, or should cloud/Supabase be added from the beginning?

   Recommendation: LAN-only first, but keep the event envelope cloud-ready.

2. Which TTS should be tested first for Portuguese call mode?

   Recommendation: test Groq TTS first because the project already uses Groq. If quality is not good enough, test ElevenLabs next.

3. Should the PC always be the primary brain when online?

   Recommendation: yes for phase 1-3. Mobile keeps standalone local/cloud behavior for notes, tasks, finance, OCR, and simple Jarvis actions when PC is offline.

4. What should the universal renderer feel like?

   Recommendation: mixed style. Use compact dashboard mode for finance/tasks/research data, and more animated/cinematic mode for voice explanations and presentations.

## Self-Review

- Spec coverage: Covers shared memory, one consciousness, voice/action separation, PC actions from mobile, universal renderer, interruption, TTS call mode, future Android control, cloud relay, multi-device path, and desktop modularization.
- Scope control: Phase 1 avoids Accessibility, cloud relay, and deep desktop refactor. Those are later phases.
- Test coverage: Phase 1 has pytest coverage for settings, models, session, registry, event bus, memory skeleton, renderer skeleton, and mobile contract. Device QA uses ADB after bundle deploy.
- Risk: The local server is a new long-running service. Keep it feature-flagged with `UNIFIED_JARVIS_ENABLED=false` by default until stable.
- Security: LAN bridge should use `UNIFIED_JARVIS_TOKEN` before exposing beyond local testing. Cloud phase must add signed/authenticated events before remote actions.
