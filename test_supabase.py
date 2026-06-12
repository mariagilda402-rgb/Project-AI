import os
import urllib.request
import json
from dotenv import load_dotenv

def test_supabase_connection():
    load_dotenv()
    
    key = os.environ.get("SUPABASE_KEY")
    
    # URL corrigida com o ID certo do projeto
    base_url = "https://oxwpwfhjyiiwdhcggtlt.supabase.co"
    
    print(f"Testando conexao com: {base_url}")
    
    try:
        req = urllib.request.Request(
            f"{base_url}/rest/v1/nexus_user?select=id,name&limit=1",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            print("\n Conexao BEM-SUCEDIDA com o Supabase!")
            print(f"Tabela 'nexus_user' respondeu. Dados: {data}")
            
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"\n Erro HTTP {e.code}: {body}")
        if e.code == 400 or e.code == 401:
            print("A chave SUPABASE_KEY pode estar errada.")
        elif "does not exist" in body:
            print("Tabela nao existe. Rode o supabase_schema.sql no SQL Editor.")
    except Exception as e:
        print(f"\n Erro: {e}")

if __name__ == "__main__":
    test_supabase_connection()
