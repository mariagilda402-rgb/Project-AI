-- Nexus Phase 13: Quiz attempts sync (mobile ENEM progress)
-- Run after supabase_migration_phase12.sql

CREATE TABLE IF NOT EXISTS public.quiz_attempts (
    id SERIAL PRIMARY KEY,
    area TEXT,
    score_pct REAL,
    correct_count INTEGER,
    total_count INTEGER,
    duration_sec INTEGER,
    finished_at TIMESTAMPTZ,
    answers_json JSONB,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    is_deleted INTEGER DEFAULT 0,
    client_id TEXT
);

ALTER PUBLICATION supabase_realtime ADD TABLE public.quiz_attempts;
