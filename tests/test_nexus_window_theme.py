from __future__ import annotations

import re
from pathlib import Path

from src.ui.desktop_app import _compose_nexus_module_html


ROOT = Path(__file__).resolve().parents[1]
MODULES = ROOT / "src" / "ui" / "nexus_modules"


RAW_HTML = """<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Nexus Test</title></head>
<body><header><h1>Teste</h1></header><main>ok</main></body>
</html>"""


def test_compose_adds_theme_wrapper_and_toggle():
    html = _compose_nexus_module_html(RAW_HTML, {"theme": "light"})

    assert html is not None
    assert 'id="nx-app-wrapper"' in html
    assert 'data-theme="light"' in html
    assert 'data-nx-theme-toggle' in html
    assert "window.nxToggleTheme" in html


def test_compose_falls_back_to_dark_for_unknown_theme():
    html = _compose_nexus_module_html(RAW_HTML, {"theme": "neon-orange"})

    assert html is not None
    assert 'data-theme="dark"' in html


def test_compose_applies_custom_theme_tokens_and_preset_attribute():
    html = _compose_nexus_module_html(
        RAW_HTML,
        {
            "theme": "dark",
            "theme_preset": "emerald-ledger",
            "theme_name": "Emerald Ledger",
            "theme_tokens": {
                "--accent": "#10b981",
                "--accent-glow": "rgba(16,185,129,0.32)",
            },
        },
    )

    assert html is not None
    assert 'data-theme-preset="emerald-ledger"' in html
    assert "--accent: #10b981" in html
    assert "--accent-glow: rgba(16,185,129,0.32)" in html
    assert '"theme_preset": "emerald-ledger"' in html
    assert '"theme_name": "Emerald Ledger"' in html


def test_boot_js_exposes_persistent_theme_api():
    js = (MODULES / "nexus_boot.js").read_text(encoding="utf-8")

    assert "nexus.theme" in js
    assert "function nxToggleTheme" in js
    assert "localStorage" in js
    assert "data-nx-theme-toggle" in js
    assert "theme_tokens" in js
    assert "nexus.theme." in js


def test_frame_css_declares_light_theme_contract():
    css = (MODULES / "nexus_frame.css").read_text(encoding="utf-8")

    assert '#nx-app-wrapper[data-theme="light"]' in css
    assert "#nx-app-wrapper[data-theme-preset]" in css
    assert ".nx-theme-toggle" in css
    assert "--bg-panel" in css


def test_frame_css_keeps_neon_spin_behind_inner_surface():
    css = (MODULES / "nexus_frame.css").read_text(encoding="utf-8")

    assert re.search(r"#nx-app-wrapper\.neon-enabled::before\s*\{[^}]*inset:\s*0", css, re.S)
    assert re.search(r"#nx-app-wrapper\.neon-enabled::before\s*\{[^}]*z-index:\s*4", css, re.S)
    assert re.search(r"#nx-app-wrapper\.neon-enabled::after\s*\{[^}]*display:\s*none", css, re.S)
    assert re.search(r"\.nx-chrome-inner\s*\{[^}]*z-index:\s*2", css, re.S)


def test_frame_css_does_not_use_oversized_neon_surface():
    css = (MODULES / "nexus_frame.css").read_text(encoding="utf-8")

    assert "width: 200%" not in css
    assert "height: 200%" not in css
    assert "conic-gradient" not in css


def test_overview_declares_command_center_contract():
    html = (MODULES / "overview.html").read_text(encoding="utf-8")

    assert "nexus-cockpit" in html
    assert "command-sidebar" in html
    assert 'id="signalFeed"' in html
    assert 'id="studyQueue"' in html
    assert 'id="goalsPanel"' in html
    assert 'id="rewardsPanel"' in html
    assert "flashcards_due" in html
    assert "goals_list" in html
    assert "rewards_list" in html
    assert "study_stats_list" in html
    assert "jumpModule('memory_graph')" in html
    assert "Grafo Neural" in html


def test_panel_declares_nexus_window_theme_controls_and_api_calls():
    html = (ROOT / "src" / "ui" / "panel.html").read_text(encoding="utf-8")

    assert 'id="nexusThemeModule"' in html
    assert 'id="nexusThemePreset"' in html
    assert 'id="nexusThemePrompt"' in html
    assert 'id="nexusThemeStatus"' in html
    assert "loadNexusThemes" in html
    assert "applyNexusWindowTheme" in html
    assert "generateNexusThemePreset" in html
    assert "nexus_theme_list" in html
    assert "nexus_theme_apply" in html
    assert "nexus_theme_generate" in html


def test_news_module_declares_briefing_studio_contract():
    html = (MODULES / "news.html").read_text(encoding="utf-8")

    assert "Nexus · Noticias" in html
    assert 'id="newsVideoStage"' in html
    assert 'id="newsStoryRail"' in html
    assert 'id="newsTranscriptLane"' in html
    assert 'id="newsNarration"' in html
    assert "refreshNewsBriefing" in html
    assert "selectNewsItem" in html
    assert "news_briefing" in html
    assert "pastLine" in html
    assert "presentLine" in html
    assert "futureLine" in html


def test_news_module_declares_history_and_mindpalace_controls():
    html = (MODULES / "news.html").read_text(encoding="utf-8")

    assert 'id="newsCacheStatus"' in html
    assert 'id="newsBriefingHistory"' in html
    assert "loadNewsHistory" in html
    assert "renderNewsHistory" in html
    assert "saveCurrentNewsToNote" in html
    assert "news_history" in html
    assert "news_save_note" in html
    assert "Salvar no MindPalace" in html


def test_news_module_declares_spotlight_deck_and_followup_task():
    html = (MODULES / "news.html").read_text(encoding="utf-8")

    assert 'id="newsSpotlightPanel"' in html
    assert 'id="newsWhyItMatters"' in html
    assert 'id="newsImpactTags"' in html
    assert 'id="newsTimeline"' in html
    assert "renderSpotlightDeck" in html
    assert "createNewsFollowupTask" in html
    assert "news_followup_task" in html
    assert "createNewsFlashcards" in html
    assert "news_flashcards_generate" in html
    assert "Criar tarefa" in html
    assert "Criar flashcards" in html


def test_news_module_declares_narration_player_and_action_receipt():
    html = (MODULES / "news.html").read_text(encoding="utf-8")

    assert 'id="newsDeckPulse"' in html
    assert 'id="newsDeckMetrics"' in html
    assert 'id="newsNarrationSegments"' in html
    assert 'id="newsActionReceipt"' in html
    assert "playNewsBriefing" in html
    assert "renderNewsDeckMetrics" in html
    assert "renderNewsActionReceipt" in html
    assert "data-news-action" in html
    assert "briefing_script" in html


def test_memory_graph_module_declares_neural_canvas_contract():
    html = (MODULES / "memory_graph.html").read_text(encoding="utf-8")
    service = (ROOT / "src" / "services" / "nexus_service.py").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "desktop_app.py").read_text(encoding="utf-8")

    assert "Grafo neural" in html
    assert 'id="memoryGraphCanvas"' in html
    assert 'id="memoryGraphSpotlight"' in html
    assert 'id="memoryGraphSearch"' in html
    assert 'id="memoryGraphFilters"' in html
    assert 'id="memoryNodeDetails"' in html
    assert 'id="memoryGraphStats"' in html
    assert "loadMemoryGraph" in html
    assert "renderMemoryGraphCanvas" in html
    assert "renderMemoryGraphSpotlight" in html
    assert "ranked_matches" in html
    assert "selectMemoryNode" in html
    assert "memory_graph" in html
    assert "nxBridge('memory_graph'" in html
    assert '"memory_graph": "Grafo neural"' in service
    assert '"grafo neural": "memory_graph"' in service
    assert '"memory_graph"' in desktop


def test_memory_graph_module_declares_obsidian_and_semantic_controls():
    html = (MODULES / "memory_graph.html").read_text(encoding="utf-8")

    assert 'id="memoryGraphSemanticStats"' in html
    assert 'id="memoryGraphObsidianPath"' in html
    assert "exportMemoryGraphObsidian" in html
    assert "importMemoryGraphObsidian" in html
    assert "memory_graph_export_obsidian" in html
    assert "memory_graph_import_obsidian" in html
    assert "semantic_edges" in html
    assert "semantic_topics" in html


def test_ops_module_declares_business_dashboard_contract():
    html_path = MODULES / "ops.html"
    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")
    service = (ROOT / "src" / "services" / "nexus_service.py").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "desktop_app.py").read_text(encoding="utf-8")

    assert 'id="opsDeck"' in html
    assert 'id="opsRecommendations"' in html
    assert 'id="opsNarrative"' in html
    assert 'id="opsSignalReceipt"' in html
    assert "data-ops-action" in html
    assert "nxBridge('ops_dashboard'" in html
    assert "nxBridge('ops_metric_set'" in html
    assert '"ops": "Operacoes"' in service
    assert '"business": "ops"' in service
    assert '"ops"' in desktop


def test_finance_and_habits_render_command_receipts():
    finance = (MODULES / "finance.html").read_text(encoding="utf-8")
    habits = (MODULES / "habits.html").read_text(encoding="utf-8")

    for html in (finance, habits):
        assert "command-receipt" in html
        assert "renderBootReceipt" in html
        assert "boot.receipt" in html

    assert "receiptFinanceAmount" in finance
    assert "receiptHabitName" in habits


def test_finance_and_habits_declare_batch_flow_and_insert_animations():
    finance = (MODULES / "finance.html").read_text(encoding="utf-8")
    habits = (MODULES / "habits.html").read_text(encoding="utf-8")

    for html in (finance, habits):
        assert 'id="nexusFlowBadge"' in html
        assert "renderNexusFlowBadge" in html
        assert "batch_step" in html
        assert "batch_total" in html
        assert "ai-inserted" in html
        assert "aiInsertionPulse" in html

    assert "isFinanceReceiptMatch" in finance
    assert "isHabitInsertionMatch" in habits


def test_finance_declares_visual_charts_and_delete_controls():
    html = (MODULES / "finance.html").read_text(encoding="utf-8")

    assert 'id="financeTrendChart"' in html
    assert 'id="financeCategoryChart"' in html
    assert "renderFinanceCharts" in html
    assert "finance_delete" in html
    assert "btnTxDelete" in html


def test_finance_declares_advanced_monthly_control_panel():
    html = (MODULES / "finance.html").read_text(encoding="utf-8")

    assert 'id="financeInsightPanel"' in html
    assert 'id="financeFilterBar"' in html
    assert 'id="financeFreeCash"' in html
    assert 'id="financeDebtToggle"' in html
    assert 'id="fnote"' in html
    assert "renderFinanceInsights" in html
    assert "applyFinanceFilters" in html
    assert "finance_insights" in html
    assert "cash_after_debt" in html
    assert "non_debt_expense" in html
    assert "debt_ratio_pct" in html
    assert "is_debt" in html
    assert "notes" in html


def test_finance_declares_inline_edit_controls():
    html = (MODULES / "finance.html").read_text(encoding="utf-8")

    assert "editingFinanceId" in html
    assert "startFinanceEdit" in html
    assert "resetFinanceForm" in html
    assert "finance_update" in html
    assert "btnTxEdit" in html
    assert 'id="financeFormMode"' in html
    assert "Salvar alteracao" in html or "Salvar altera" in html


def test_finance_advanced_panel_copy_mentions_debts():
    html = (MODULES / "finance.html").read_text(encoding="utf-8")

    assert "Saldo ap" in html
    assert "d" in html
    assert "Saldo após dívidas" in html


def test_finance_visible_text_has_no_mojibake():
    html = (MODULES / "finance.html").read_text(encoding="utf-8")

    assert "Nexus · Finanças" in html
    assert "Visão geral" in html
    assert "Registro rápido" in html
    assert "Fluxo diário" in html
    assert "Movimentos do mês" in html
    assert "Dívidas" in html
    for marker in ("Ã", "Â", "ðŸ"):
        assert marker not in html


def test_habits_declares_preset_controls_and_bridge_methods():
    html = (MODULES / "habits.html").read_text(encoding="utf-8")

    assert 'id="presetPanel"' in html
    assert 'id="presetName"' in html
    assert 'id="presetSelect"' in html
    assert "presets_list" in html
    assert "preset_save" in html
    assert "preset_apply" in html


def test_habits_declares_goal_based_ai_preset_builder():
    html = (MODULES / "habits.html").read_text(encoding="utf-8")

    assert 'id="presetGoals"' in html
    assert 'id="btnPresetFromGoals"' in html
    assert 'id="presetGoalStatus"' in html
    assert 'id="goalPresetIdeas"' in html
    assert "buildPresetFromGoals" in html
    assert "renderGoalPresetIdeas" in html
    assert "preset_from_goals" in html


def test_habits_preset_receipts_do_not_render_mojibake():
    html = (MODULES / "habits.html").read_text(encoding="utf-8")

    assert "Plano de hábitos sincronizado" in html
    assert "hábitos" in html
    for marker in ("hÃ¡bitos", "hÃƒ", "Ã‚Â·"):
        assert marker not in html


def test_notes_declares_flashcard_generation_controls():
    html = (MODULES / "notes.html").read_text(encoding="utf-8")

    assert 'id="btnFlashcards"' in html
    assert 'id="studyStatus"' in html
    assert "flashcards_generate" in html
    assert "generateFlashcards" in html


def test_notes_declares_summary_controls():
    html = (MODULES / "notes.html").read_text(encoding="utf-8")

    assert 'id="btnSummarize"' in html
    assert "note_summarize" in html
    assert "summarizeNote" in html


def test_notes_declares_teacher_mode_controls():
    html = (MODULES / "notes.html").read_text(encoding="utf-8")

    assert 'id="teacherPanel"' in html
    assert 'id="teacherQuestion"' in html
    assert 'id="btnTeacher"' in html
    assert "note_teach" in html
    assert "askTeacher" in html


def test_notes_declares_media_attachment_preview_controls():
    html = (MODULES / "notes.html").read_text(encoding="utf-8")

    assert 'id="mediaUrl"' in html
    assert 'id="btnAttachMedia"' in html
    assert 'id="notePreview"' in html
    assert 'id="mediaStrip"' in html
    assert "note_attach_media" in html
    assert "renderNotePreview" in html


def test_notes_declares_subject_rail_and_open_tabs():
    html = (MODULES / "notes.html").read_text(encoding="utf-8")

    assert 'id="subjectRail"' in html
    assert 'id="openTabs"' in html
    assert "renderSubjectRail" in html
    assert "renderOpenTabs" in html
    assert "openNoteTabs" in html
    assert "activeSubject" in html


def test_notes_generates_flashcards_for_current_subject():
    html = (MODULES / "notes.html").read_text(encoding="utf-8")

    assert 'id="btnSubjectFlashcards"' in html
    assert "generateSubjectFlashcards" in html
    assert "flashcards_generate" in html
    assert "activeSubject" in html


def test_notes_declares_flashcard_preview_panel():
    html = (MODULES / "notes.html").read_text(encoding="utf-8")

    assert 'id="flashcardPreview"' in html
    assert 'id="flashcardPreviewList"' in html
    assert 'id="btnOpenFlashcards"' in html
    assert "renderFlashcardPreview" in html
    assert "flashcard-card" in html
    assert "pywebview.api.jump('study'" in html


def test_notes_render_ai_command_receipts():
    html = (MODULES / "notes.html").read_text(encoding="utf-8")

    assert 'id="noteReceipt"' in html
    assert "command-receipt" in html
    assert "renderNoteReceipt" in html
    assert "boot.receipt" in html
    assert "receiptNoteTitle" in html
    assert "receiptNoteMeta" in html
    assert "note_summarize" in html
    assert "teacher_mode" in html
    assert "note_media_attach" in html


def test_notes_declares_subject_teacher_controls():
    html = (MODULES / "notes.html").read_text(encoding="utf-8")

    assert 'id="btnSubjectTeacher"' in html
    assert "askSubjectTeacher" in html
    assert "subject_teach" in html
    assert "subject_teacher_mode" in html
    assert "activeSubject" in html


def test_notes_visible_text_has_no_mojibake():
    html = (MODULES / "notes.html").read_text(encoding="utf-8")

    assert "Nexus · MindPalace" in html
    assert "Visão geral" in html
    assert "Anotações" in html
    assert "Explicação guiada pela nota aberta" in html
    for marker in ("Ã", "Â", "ðŸ"):
        assert marker not in html


def test_progress_declares_study_recommendations_panel():
    html = (MODULES / "progress.html").read_text(encoding="utf-8")

    assert 'id="recommendationsPanel"' in html
    assert 'id="recommendationList"' in html
    assert "study_recommendations" in html


def test_progress_declares_visual_study_chart():
    html = (MODULES / "progress.html").read_text(encoding="utf-8")

    assert 'id="studyAccuracyChart"' in html
    assert "renderStudyChart" in html
    assert "chart-bar" in html


def test_progress_declares_study_strategy_cockpit():
    html = (MODULES / "progress.html").read_text(encoding="utf-8")

    assert 'id="studyOverviewPanel"' in html
    assert 'id="overallAccuracy"' in html
    assert 'id="flashcardDueCount"' in html
    assert 'id="weakSubjectsPanel"' in html
    assert 'id="nextActionsPanel"' in html
    assert "renderRecommendationCards" in html
    assert "renderWeakSubjects" in html
    assert "pywebview.api.jump('study'" in html
    assert "pywebview.api.jump('quiz'" in html
    assert "flashcards pendentes" in html


def test_progress_header_keeps_overview_action_aligned():
    html = (MODULES / "progress.html").read_text(encoding="utf-8")

    assert "#nx-app-wrapper .nx-chrome-inner > header" in html
    assert "justify-content: space-between" in html
    assert "header .btn-ghost" in html


def test_progress_visible_text_has_no_mojibake():
    html = (MODULES / "progress.html").read_text(encoding="utf-8")

    assert "Nexus · Progresso" in html
    assert "Visão geral" in html
    assert "Próximas ações" in html
    assert "questões" in html
    for marker in ("Ã", "Â", "ðŸ"):
        assert marker not in html


def test_goals_declares_reward_status_for_one_per_day_rule():
    html = (MODULES / "goals.html").read_text(encoding="utf-8")

    assert 'id="rewardStatus"' in html
    assert "reward_status" in html
    assert "redeemedToday" in html
    assert "btnRedeem" in html


def test_goals_declares_reward_rule_history_and_reset_panel():
    html = (MODULES / "goals.html").read_text(encoding="utf-8")

    assert 'id="rewardRulePanel"' in html
    assert 'id="rewardHistoryList"' in html
    assert 'id="rewardResetHint"' in html
    assert "renderRewardStatus" in html
    assert "renderRewardHistory" in html
    assert "remaining_today" in html
    assert "daily_limit" in html
    assert "next_available_date" in html


def test_study_flashcards_hide_answers_until_revealed():
    html = (MODULES / "study.html").read_text(encoding="utf-8")

    assert "revealAnswer" in html
    assert "answerHidden" in html
    assert "data-answer" in html
    assert "disabled data-review" in html
    assert "aria-expanded" in html


def test_study_renders_flashcard_generation_receipt():
    html = (MODULES / "study.html").read_text(encoding="utf-8")

    assert 'id="studyReceipt"' in html
    assert "renderStudyReceipt" in html
    assert "boot.receipt" in html
    assert "flashcards_generate" in html


def test_study_renders_quiz_flashcard_receipt_and_source_label():
    html = (MODULES / "study.html").read_text(encoding="utf-8")

    assert "quiz_flashcards_generate" in html
    assert "cardSourceLabel" in html
    assert "Quiz ENEM" in html
    assert "Erros do simulado" in html


def test_study_visible_text_has_no_mojibake():
    html = (MODULES / "study.html").read_text(encoding="utf-8")

    assert "Nexus · Flashcards" in html
    assert "Repetição espaçada" in html
    assert "flashcards prontos para revisão" in html
    for marker in ("Ã", "Â", "ðŸ"):
        assert marker not in html


def test_quiz_declares_review_panel_and_explanations():
    html = (MODULES / "quiz.html").read_text(encoding="utf-8")

    assert 'id="reviewPanel"' in html
    assert "quiz_attempt_review" in html
    assert "quiz_flashcards_generate" in html
    assert "btnQuizFlashcards" in html
    assert "reviewStatus" in html
    assert "renderReview" in html
    assert "explanation" in html
    assert "skill" in html


def test_quiz_offers_direct_study_review_after_flashcards_created():
    html = (MODULES / "quiz.html").read_text(encoding="utf-8")

    assert 'id="btnReviewNow"' in html
    assert "openFlashcardReview" in html
    assert "pywebview.api.jump('study'" in html
    assert "quiz_flashcards_generate" in html


def test_quiz_visible_text_has_no_mojibake():
    html = (MODULES / "quiz.html").read_text(encoding="utf-8")

    assert "Revisão guiada" in html
    assert "Configurar Sessão" in html
    for marker in ("Ã", "Â", "ðŸ"):
        assert marker not in html
    assert "📊" not in html


def test_progress_declares_srs_task_integration():
    html = (MODULES / "progress.html").read_text(encoding="utf-8")

    assert 'id="btnCreateSrsTask"' in html
    assert 'id="srsTaskStatus"' in html
    assert "createSrsTask" in html
    assert "task_add" in html
    assert "flashcardsDueForTask" in html


def test_habits_declares_edit_controls():
    html = (MODULES / "habits.html").read_text(encoding="utf-8")

    assert "editHabit" in html
    assert "habit_update" in html
    assert "btnHabitEdit" in html
    assert "editingHabitId" in html


def test_goals_declares_reward_crud_controls():
    html = (MODULES / "goals.html").read_text(encoding="utf-8")

    assert 'id="rewardAddForm"' in html
    assert "reward_add" in html
    assert "reward_delete" in html
    assert "addCustomReward" in html
    assert "deleteReward" in html


def test_notes_declares_capture_controls():
    html = (MODULES / "notes.html").read_text(encoding="utf-8")

    assert 'id="noteCaptureForm"' in html
    assert "note_capture" in html
    assert "captureNote" in html
    assert 'id="captureUrl"' in html


def test_quiz_declares_mode_selector_and_timer():
    html = (MODULES / "quiz.html").read_text(encoding="utf-8")

    assert 'id="quizMode"' in html
    assert 'id="quizTimer"' in html
    assert 'id="quizBreakdown"' in html


def test_phase6_finance_declares_canvas_telemetry():
    html = (MODULES / "finance.html").read_text(encoding="utf-8")

    assert 'id="financeTrendCanvas"' in html
    assert 'id="financeCategoryCanvas"' in html
    assert "drawFinanceTrendCanvas" in html
    assert "drawFinanceCategoryCanvas" in html
    assert "ResizeObserver" in html
    assert '<link rel="stylesheet"' not in html


def test_phase6_habits_declares_momentum_canvas():
    html = (MODULES / "habits.html").read_text(encoding="utf-8")

    assert 'id="habitMomentumCanvas"' in html
    assert 'id="habitMomentumStats"' in html
    assert "drawHabitMomentumCanvas" in html
    assert "renderHabitMomentum" in html
    assert "ResizeObserver" in html
    assert '<link rel="stylesheet"' not in html


def test_phase6_progress_declares_canvas_telemetry():
    html = (MODULES / "progress.html").read_text(encoding="utf-8")

    assert 'id="studyTelemetryCanvas"' in html
    assert 'id="studyTelemetryStats"' in html
    assert "drawStudyTelemetryCanvas" in html
    assert "renderStudyTelemetry" in html
    assert "ResizeObserver" in html
    assert '<link rel="stylesheet"' not in html
