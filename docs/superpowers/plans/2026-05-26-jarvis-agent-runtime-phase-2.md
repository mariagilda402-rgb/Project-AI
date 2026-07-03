# Jarvis Agent Runtime Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `nexus_command` mode-aware so News and Psych/Coach requests do not advertise unrelated Nexus actions.

**Architecture:** Keep the broad Nexus schema as the default. Add lightweight mode profiles inside `src/agent/gemini_tools.py` that replace the `nexus_command` description and parameter map only when `active_mode` is provided. Pass the active mode from `AgentOrchestrator` into Gemini/OpenAI schema builders.

**Tech Stack:** Python 3.10-compatible typing, pytest, existing Gemini/OpenAI-compatible tool schema builders.

---

### Task 1: Add Mode Profiles For Nexus Command

**Files:**
- Modify: `src/agent/gemini_tools.py`
- Modify: `tests/test_agent_runtime_tool_schemas.py`

- [ ] Write tests proving `active_mode="news"` includes news actions and excludes finance/reward/ops actions.
- [ ] Write tests proving `active_mode="psych_coach"` includes habit/task/goal/note actions and excludes news/finance/reward/ops actions.
- [ ] Implement mode profiles and apply them to Gemini/OpenAI `nexus_command`.
- [ ] Verify default schemas still expose the full Nexus command set.

### Task 2: Pass Active Mode From Orchestrator

**Files:**
- Modify: `src/agent/orchestrator.py`
- Modify: `tests/test_agent_orchestrator_runtime.py`

- [ ] Extend the orchestrator runtime test to assert the News-mode `nexus_command` description is narrowed.
- [ ] Pass `active_mode=runtime_resolution.mode.value` to both schema builders.
- [ ] Run runtime/orchestrator/schema tests.

### Task 3: Verify

**Files:**
- No new files required.

- [ ] Run runtime-focused tests.
- [ ] Run existing agent schema/provider tests.
- [ ] Run `tests/test_nexus_life.py` with a long timeout because it currently takes more than 3 minutes.
