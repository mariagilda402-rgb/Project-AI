-- =========================================================================
-- Nexus Phase 15: Jarvis chat/calls, alarmes standalone, preferências de UI
-- Rode no Supabase SQL Editor APÓS phase12–14 e multiuser (se usar Google Auth).
--
-- Deploy Edge Functions (CLI):
--   supabase secrets set GEMINI_API_KEY=sua_chave
--   supabase secrets set GEMINI_MODEL=gemini-2.0-flash
--   supabase functions deploy jarvis-chat
--   supabase functions deploy jarvis-note-action
--   supabase functions deploy jarvis-tts
-- =========================================================================

-- 1) Chat texto persistente
CREATE TABLE IF NOT EXISTS public.jarvis_chat_messages (
    id BIGINT PRIMARY KEY,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    source TEXT DEFAULT 'mobile',
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    is_deleted INTEGER DEFAULT 0,
    user_id UUID REFERENCES auth.users(id)
);

CREATE INDEX IF NOT EXISTS idx_jarvis_chat_messages_user ON public.jarvis_chat_messages (user_id, updated_at DESC);

-- 2) Sessões de ligação Jarvis (histórico separado do chat)
CREATE TABLE IF NOT EXISTS public.jarvis_call_sessions (
    id BIGINT PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    duration_sec INTEGER,
    source TEXT DEFAULT 'mobile',
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    is_deleted INTEGER DEFAULT 0,
    user_id UUID REFERENCES auth.users(id)
);

CREATE TABLE IF NOT EXISTS public.jarvis_call_turns (
    id BIGINT PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES public.jarvis_call_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    is_deleted INTEGER DEFAULT 0,
    user_id UUID REFERENCES auth.users(id)
);

CREATE INDEX IF NOT EXISTS idx_jarvis_call_sessions_user ON public.jarvis_call_sessions (user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_jarvis_call_turns_session ON public.jarvis_call_turns (session_id, created_at);

-- 3) Alarmes standalone (e metadados de vínculo)
CREATE TABLE IF NOT EXISTS public.nexus_alarms (
    id BIGINT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT,
    alarm_time TEXT NOT NULL,
    days_of_week JSONB DEFAULT '[0,1,2,3,4,5,6]'::jsonb,
    enabled INTEGER DEFAULT 1,
    source_type TEXT DEFAULT 'standalone',
    source_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    is_deleted INTEGER DEFAULT 0,
    user_id UUID REFERENCES auth.users(id)
);

CREATE INDEX IF NOT EXISTS idx_nexus_alarms_user ON public.nexus_alarms (user_id, alarm_time);

-- 4) Preferências de UI (ordem módulos, TTS, etc.)
CREATE TABLE IF NOT EXISTS public.nexus_user_settings (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    settings_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

-- Triggers updated_at
CREATE OR REPLACE FUNCTION public.nexus_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE t text;
BEGIN
    FOR t IN SELECT unnest(ARRAY[
        'jarvis_chat_messages', 'jarvis_call_sessions', 'nexus_alarms', 'nexus_user_settings'
    ]) LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_updated ON public.%I', t, t);
        EXECUTE format(
            'CREATE TRIGGER trg_%s_updated BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.nexus_set_updated_at()',
            t, t
        );
    END LOOP;
END $$;

-- RLS (multi-user)
ALTER TABLE public.jarvis_chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jarvis_call_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jarvis_call_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nexus_alarms ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nexus_user_settings ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE tbl_name text;
BEGIN
    FOR tbl_name IN SELECT unnest(ARRAY[
        'jarvis_chat_messages', 'jarvis_call_sessions', 'jarvis_call_turns', 'nexus_alarms', 'nexus_user_settings'
    ]) LOOP
        EXECUTE format('DROP POLICY IF EXISTS "Isolamento de Usuario" ON public.%I', tbl_name);
        EXECUTE format(
            'CREATE POLICY "Isolamento de Usuario" ON public.%I FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id)',
            tbl_name
        );
    END LOOP;
END $$;
