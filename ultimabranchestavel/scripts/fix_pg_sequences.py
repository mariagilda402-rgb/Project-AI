import sys
sys.path.append(r'd:\Documentos\Projeto AI')
from src.database.pg_wrapper import get_connection

def fix_sequences():
    tables = [
        'study_notes', 'flashcards', 'habits', 'nexus_videos', 
        'nexus_rewards', 'reward_redemptions', 'nexus_user', 
        'tasks', 'finance_transactions', 'health_metrics',
        'voice_profiles', 'news_briefings', 'news_items',
        'goals', 'goal_milestones', 'study_sessions'
    ]
    with get_connection(r'd:\Documentos\Projeto AI\data\nexus.db') as conn:
        cur = conn.cursor()
        for t in tables:
            try:
                # setval requires the max ID. If table is empty, this returns None, which setval handles if provided a default, 
                # or we can use COALESCE
                cur.execute(f"SELECT setval('{t}_id_seq', COALESCE((SELECT MAX(id) FROM {t}), 1) + 1, false)")
                print(f"Sequence fixed for {t}")
                conn.commit()
            except Exception as e:
                # Might not have a sequence named exactly this, ignore and rollback
                conn.rollback()

if __name__ == '__main__':
    fix_sequences()
