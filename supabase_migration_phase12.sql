-- Nexus Phase 12: cross-device sync tables + schema fixes
-- Run in Supabase SQL editor after base schema

-- Fix / create remote commands (mobile chat queue)
CREATE TABLE IF NOT EXISTS public.nexus_commands (
    id SERIAL PRIMARY KEY,
    command TEXT NOT NULL,
    source TEXT DEFAULT 'mobile',
    status TEXT DEFAULT 'pending',
    result TEXT,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.nexus_memory_sync (
    id SERIAL PRIMARY KEY,
    key_name TEXT UNIQUE NOT NULL,
    data_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    is_deleted INTEGER DEFAULT 0
);

-- Habit completion logs (critical for streaks)
CREATE TABLE IF NOT EXISTS public.habit_logs (
    id SERIAL PRIMARY KEY,
    habit_id INTEGER NOT NULL,
    completed_date DATE NOT NULL,
    date TEXT,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    is_deleted INTEGER DEFAULT 0,
    UNIQUE(habit_id, completed_date)
);

-- Extend habits
ALTER TABLE public.habits ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE public.habits ADD COLUMN IF NOT EXISTS period TEXT;
ALTER TABLE public.habits ADD COLUMN IF NOT EXISTS alarm_time TEXT;
ALTER TABLE public.habits ADD COLUMN IF NOT EXISTS xp_reward INTEGER DEFAULT 50;
ALTER TABLE public.habits ADD COLUMN IF NOT EXISTS target_time TEXT;

-- Study notebooks + flashcards
CREATE TABLE IF NOT EXISTS public.study_notebooks (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT,
    color TEXT,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    is_deleted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS public.flashcards (
    id SERIAL PRIMARY KEY,
    note_id INTEGER,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    ease_factor REAL DEFAULT 2.5,
    interval INTEGER DEFAULT 0,
    repetitions INTEGER DEFAULT 0,
    next_review TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    is_deleted INTEGER DEFAULT 0
);

ALTER TABLE public.study_notes ADD COLUMN IF NOT EXISTS notebook_id INTEGER;
ALTER TABLE public.study_notes ADD COLUMN IF NOT EXISTS tags TEXT;
ALTER TABLE public.study_notes ADD COLUMN IF NOT EXISTS pinned INTEGER DEFAULT 0;

-- Routines
CREATE TABLE IF NOT EXISTS public.routines (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    time_of_day TEXT,
    steps_json JSONB,
    active INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    is_deleted INTEGER DEFAULT 0
);

-- Journal
CREATE TABLE IF NOT EXISTS public.journal_entries (
    id SERIAL PRIMARY KEY,
    date DATE DEFAULT CURRENT_DATE,
    content TEXT,
    mood INTEGER,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    is_deleted INTEGER DEFAULT 0
);

-- Pomodoro sessions
CREATE TABLE IF NOT EXISTS public.pomo_sessions (
    id SERIAL PRIMARY KEY,
    type TEXT DEFAULT 'focus',
    duration_minutes INTEGER DEFAULT 25,
    session_date DATE,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    is_deleted INTEGER DEFAULT 0
);

-- Reading tracker
CREATE TABLE IF NOT EXISTS public.reading_books (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    total_pages INTEGER,
    current_page INTEGER DEFAULT 0,
    status TEXT DEFAULT 'reading',
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    is_deleted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS public.reading_sessions (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES public.reading_books(id),
    pages_read INTEGER DEFAULT 0,
    duration_minutes INTEGER,
    session_date DATE,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    is_deleted INTEGER DEFAULT 0
);

-- Fitness mobile fields
ALTER TABLE public.fitness_workouts ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE public.fitness_workouts ADD COLUMN IF NOT EXISTS muscle_group TEXT;
ALTER TABLE public.fitness_workouts ADD COLUMN IF NOT EXISTS exercises_json JSONB;

-- Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE public.nexus_videos;
ALTER PUBLICATION supabase_realtime ADD TABLE public.habit_logs;
ALTER PUBLICATION supabase_realtime ADD TABLE public.flashcards;
ALTER PUBLICATION supabase_realtime ADD TABLE public.routines;
ALTER PUBLICATION supabase_realtime ADD TABLE public.journal_entries;
ALTER PUBLICATION supabase_realtime ADD TABLE public.pomo_sessions;
ALTER PUBLICATION supabase_realtime ADD TABLE public.reading_books;
ALTER PUBLICATION supabase_realtime ADD TABLE public.reading_sessions;
