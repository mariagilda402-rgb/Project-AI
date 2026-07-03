-- Nexus Phase 14: Sprint 4 mobile schema extensions
-- Run after supabase_migration_phase13.sql

-- Tasks: full customization fields
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS due_date DATE;
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS priority TEXT DEFAULT 'medium';
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'todo';
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS notify_at TIMESTAMPTZ;
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS notify_enabled INTEGER DEFAULT 0;
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS subtasks_json JSONB DEFAULT '[]'::jsonb;

-- Habits: days of week schedule
ALTER TABLE public.habits ADD COLUMN IF NOT EXISTS days_of_week JSONB DEFAULT '[1,2,3,4,5]'::jsonb;

-- Study notebooks: cover image
ALTER TABLE public.study_notebooks ADD COLUMN IF NOT EXISTS cover_image TEXT;

-- Goals: description field
ALTER TABLE public.nexus_goals ADD COLUMN IF NOT EXISTS description TEXT;
