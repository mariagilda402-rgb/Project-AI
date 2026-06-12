import re

path = 'src/services/nexus_cloud_agent.py'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# Add new handler methods
new_handlers = '''
    def handle_discover_iot(self, cmd_id):
        """Mock discovery of local IoT devices since we are the PC on the local network."""
        import json
        devices = [
            {"name": "Luz Quarto", "ip": "192.168.1.100", "status": "LIGADO"},
            {"name": "Ar Condicionado", "ip": "192.168.1.101", "status": "DESLIGADO"},
            {"name": "TV Sala", "ip": "192.168.1.102", "status": "LIGADO"}
        ]
        result_json = json.dumps(devices)
        with self.get_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE nexus_commands SET result=?, status='completed' WHERE id=?", (result_json, cmd_id))
            conn.commit()
        print(f"[NexusCloudAgent] IOT Discovery executado.")

    def handle_toggle_iot(self, cmd_id, command_str):
        """Simulate toggling an IoT device on the local network."""
        parts = command_str.split(":")
        if len(parts) >= 3:
            ip = parts[1]
            state = parts[2]
            print(f"[NexusCloudAgent] Enviando comando {state} para dispositivo IOT {ip}...")
        
        with self.get_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE nexus_commands SET status='completed' WHERE id=?", (cmd_id,))
            conn.commit()
'''

if 'def handle_discover_iot' not in c:
    # Route new commands in process_pending_commands
    old_route = '''                    elif command_str.startswith("GPS_UPDATE:"):
                        self.handle_gps_update(command_str)'''
    new_route = '''                    elif command_str.startswith("GPS_UPDATE:"):
                        self.handle_gps_update(command_str)
                    elif command_str.startswith("DISCOVER_IOT"):
                        self.handle_discover_iot(cmd_id)
                    elif command_str.startswith("TOGGLE_IOT:"):
                        self.handle_toggle_iot(cmd_id, command_str)'''

    c = c.replace(old_route, new_route)

    c = c.replace('    def sync_memory_to_cloud(self):', new_handlers + '\n    def sync_memory_to_cloud(self):')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("NexusCloudAgent updated successfully with IoT handlers!")
else:
    print("IoT handlers already exist.")
