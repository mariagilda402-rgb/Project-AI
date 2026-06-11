    -- ==========================================
    -- Nexus Supabase Schema Initialization
    -- ==========================================

    -- 1. nexus_user table
    CREATE TABLE IF NOT EXISTS public.nexus_user (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL DEFAULT 'User',
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        points INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        is_deleted INTEGER DEFAULT 0
    );

    -- Insert default user if not exists
    INSERT INTO public.nexus_user (id, name, xp, level, points)
    VALUES (1, 'User', 0, 1, 0)
    ON CONFLICT (id) DO NOTHING;

    -- 2. habits table
    CREATE TABLE IF NOT EXISTS public.habits (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        active INTEGER DEFAULT 1,
        current_streak INTEGER DEFAULT 0,
        longest_streak INTEGER DEFAULT 0,
        last_done_date TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        is_deleted INTEGER DEFAULT 0
    );

    -- 3. tasks table
    CREATE TABLE IF NOT EXISTS public.tasks (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        completed INTEGER DEFAULT 0,
        points_reward INTEGER DEFAULT 10,
        done_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        is_deleted INTEGER DEFAULT 0
    );

    -- 4. finance_transactions table
    CREATE TABLE IF NOT EXISTS public.finance_transactions (
        id SERIAL PRIMARY KEY,
        type TEXT,
        amount REAL,
        description TEXT,
        category TEXT,
        occurred_at TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        is_deleted INTEGER DEFAULT 0
    );

    -- 5. nexus_videos table (Optional, for offline video cache tracking)
    CREATE TABLE IF NOT EXISTS public.nexus_videos (
        id SERIAL PRIMARY KEY,
        title TEXT,
        url TEXT,
        platform TEXT,
        is_watched INTEGER DEFAULT 0,
        xp_reward INTEGER DEFAULT 25,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        is_deleted INTEGER DEFAULT 0
    );

    -- Enable Realtime for all sync tables
    alter publication supabase_realtime add table public.nexus_user;
    alter publication supabase_realtime add table public.habits;
    alter publication supabase_realtime add table public.tasks;
    alter publication supabase_realtime add table public.finance_transactions;

    -- 6. nexus_rewards table
    CREATE TABLE IF NOT EXISTS public.nexus_rewards (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        cost INTEGER NOT NULL,
        description TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        is_deleted INTEGER DEFAULT 0
    );

    -- 7. study_notes table
    CREATE TABLE IF NOT EXISTS public.study_notes (
        id SERIAL PRIMARY KEY,
        subject TEXT,
        title TEXT NOT NULL,
        content TEXT,
        media_links TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        is_deleted INTEGER DEFAULT 0
    );

    -- 8. nexus_goals table
    CREATE TABLE IF NOT EXISTS public.nexus_goals (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        target_date DATE,
        progress INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        is_deleted INTEGER DEFAULT 0
    );

    -- 9. fitness_workouts table
    CREATE TABLE IF NOT EXISTS public.fitness_workouts (
        id SERIAL PRIMARY KEY,
        date DATE,
        type TEXT NOT NULL,
        duration_minutes INTEGER,
        calories_burned INTEGER,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
        is_deleted INTEGER DEFAULT 0
    );

    alter publication supabase_realtime add table public.nexus_rewards;
    alter publication supabase_realtime add table public.study_notes;
    alter publication supabase_realtime add table public.nexus_goals;
    alter publication supabase_realtime add table public.fitness_workouts;
