-- =========================================================================
-- MIGRATION: SUPABASE MULTI-USER & RLS (ROW LEVEL SECURITY)
-- Rode esse código no painel SQL Editor do seu Supabase para proteger e
-- separar os dados por usuário (Google Auth).
-- =========================================================================

-- 1. ADICIONAR A COLUNA user_id EM TODAS AS TABELAS SINCRONIZADAS
ALTER TABLE public.nexus_user ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE public.habits ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE public.finance_transactions ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE public.nexus_videos ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE public.nexus_rewards ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE public.study_notes ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE public.nexus_goals ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE public.fitness_workouts ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

-- 2. HABILITAR ROW LEVEL SECURITY (RLS)
ALTER TABLE public.nexus_user ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.habits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.finance_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nexus_videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nexus_rewards ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.study_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nexus_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fitness_workouts ENABLE ROW LEVEL SECURITY;

-- 3. CRIAR POLÍTICAS DE ACESSO (O Usuário só pode VER/MODIFICAR os dados dele mesmo)
-- Função auxiliar para aplicar a mesma política em várias tabelas para evitar repetição manual
DO $$ 
DECLARE 
    tbl_name text;
BEGIN 
    FOR tbl_name IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' AND tablename IN (
            'nexus_user', 'habits', 'tasks', 'finance_transactions', 
            'nexus_videos', 'nexus_rewards', 'study_notes', 
            'nexus_goals', 'fitness_workouts'
        )
    LOOP
        -- Remove política antiga se existir
        EXECUTE format('DROP POLICY IF EXISTS "Isolamento de Usuario" ON public.%I', tbl_name);
        
        -- Cria a nova política atrelando ao ID logado no Supabase Auth
        EXECUTE format('
            CREATE POLICY "Isolamento de Usuario" 
            ON public.%I 
            FOR ALL 
            USING (auth.uid() = user_id) 
            WITH CHECK (auth.uid() = user_id)
        ', tbl_name);
    END LOOP;
END $$;
