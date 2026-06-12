with open('src/services/sync_service.py', 'r') as f:
    c = f.read()

if '"nexus_commands"' not in c:
    c = c.replace('"fitness_workouts"', '"fitness_workouts",\n    "nexus_commands",\n    "nexus_memory_sync"')
    with open('src/services/sync_service.py', 'w') as f:
        f.write(c)
