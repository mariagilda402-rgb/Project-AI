import os
from huggingface_hub import snapshot_download

def download_qwen_tts():
    print("\n--- INICIANDO DOWNLOAD DO QWEN3-TTS (OuteTTS-0.2-500M) ---")
    print("O modelo tem cerca de 1.5 GB. Dependendo da sua internet, pode levar alguns minutos.")
    print("A barra de progresso abaixo vai mostrar o status real do download:\n")
    
    try:
        # Força o download do modelo via Hugging Face Hub para vermos o progresso real
        model_path = snapshot_download(repo_id="OuteAI/OuteTTS-0.2-500M")
        
        print("\n✅ DOWNLOAD CONCLUÍDO COM SUCESSO!")
        print(f"O modelo foi salvo na sua pasta de cache do HuggingFace.")
        print("Agora você pode rodar o teste de áudio!")
        
    except Exception as e:
        print(f"\n❌ Erro durante o download: {e}")

if __name__ == "__main__":
    download_qwen_tts()
