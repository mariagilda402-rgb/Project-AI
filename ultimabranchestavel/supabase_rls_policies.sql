-- ==========================================
-- Nexus App - Políticas de Acesso (RLS)
-- Cole este SQL inteiro no SQL Editor do Supabase e clique em RUN
-- ==========================================

-- TABELA: nexus_user
ALTER TABLE public.nexus_user ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for anon" ON public.nexus_user;
CREATE POLICY "Allow all for anon" ON public.nexus_user
    FOR ALL TO anon USING (true) WITH CHECK (true);

-- TABELA: habits
ALTER TABLE public.habits ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for anon" ON public.habits;
CREATE POLICY "Allow all for anon" ON public.habits
    FOR ALL TO anon USING (true) WITH CHECK (true);

-- TABELA: tasks
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for anon" ON public.tasks;
CREATE POLICY "Allow all for anon" ON public.tasks
    FOR ALL TO anon USING (true) WITH CHECK (true);

-- TABELA: finance_transactions
ALTER TABLE public.finance_transactions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for anon" ON public.finance_transactions;
CREATE POLICY "Allow all for anon" ON public.finance_transactions
    FOR ALL TO anon USING (true) WITH CHECK (true);

-- TABELA: nexus_videos
ALTER TABLE public.nexus_videos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for anon" ON public.nexus_videos;
CREATE POLICY "Allow all for anon" ON public.nexus_videos
    FOR ALL TO anon USING (true) WITH CHECK (true);

-- TABELA: nexus_rewards
ALTER TABLE public.nexus_rewards ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for anon" ON public.nexus_rewards;
CREATE POLICY "Allow all for anon" ON public.nexus_rewards
    FOR ALL TO anon USING (true) WITH CHECK (true);

-- TABELA: study_notes
ALTER TABLE public.study_notes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for anon" ON public.study_notes;
CREATE POLICY "Allow all for anon" ON public.study_notes
    FOR ALL TO anon USING (true) WITH CHECK (true);

-- TABELA: nexus_goals
ALTER TABLE public.nexus_goals ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for anon" ON public.nexus_goals;
CREATE POLICY "Allow all for anon" ON public.nexus_goals
    FOR ALL TO anon USING (true) WITH CHECK (true);

-- TABELA: fitness_workouts
ALTER TABLE public.fitness_workouts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for anon" ON public.fitness_workouts;
CREATE POLICY "Allow all for anon" ON public.fitness_workouts
    FOR ALL TO anon USING (true) WITH CHECK (true);

-- Inserir usuário padrão (caso não exista ainda)
INSERT INTO public.nexus_user (id, name, xp, level, points)
VALUES (1, 'User', 0, 1, 0)
ON CONFLICT (id) DO NOTHING;
