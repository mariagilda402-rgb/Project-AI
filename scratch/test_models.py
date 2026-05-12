import time
import outetts

def test_outetts():
    print("\n--- TESTANDO OUTETTS (QWEN 0.5B) ---")
    try:
        print("Carregando modelo OuteTTS na memória da sua placa de vídeo (AMD RX 580)...")
        
        # Gambiarra oficial pra forçar GPU AMD no Windows
        device = "cpu"
        try:
            import torch_directml
            device = torch_directml.device()
            print(f"Sucesso! DirectX 12 ativado. Rodando na GPU: {device}")
        except Exception as e:
            print(f"DirectML não encontrado, caindo para CPU: {e}")

        # A nova versão 0.4.4 usa uma API mais limpa com ModelConfig:
        model_config = outetts.ModelConfig(
            model_path="OuteAI/OuteTTS-0.2-500M",
            device=str(device) # Joga pra AMD
        )
        interface = outetts.Interface(config=model_config)
        
        start = time.time()
        print("Gerando áudio com Qwen...")
        gen_config = outetts.GenerationConfig(
            text="Olá! Eu sou o modelo Qwen e estou falando do seu computador. Testando um, dois, três.",
        )
        output = interface.generate(config=gen_config)
        end = time.time()
        
        output.save("teste_qwen.wav")
        print(f"Qwen finalizado em {end - start:.2f} segundos! Salvo como teste_qwen.wav")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Erro no Qwen: {e}")

if __name__ == "__main__":
    test_outetts()
