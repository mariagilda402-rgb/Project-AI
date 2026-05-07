import speech_recognition as sr
import time

def test_mic():
    r = sr.Recognizer()
    print("--- Diagnóstico de Microfone ---")
    
    # 1. Lista microfones
    mics = sr.Microphone.list_microphone_names()
    print(f"\nMicrofones encontrados ({len(mics)}):")
    for i, name in enumerate(mics):
        print(f" [{i}] {name}")
    
    if not mics:
        print("ERRO: Nenhum microfone detectado pelo sistema!")
        return

    # 2. Testa captura
    try:
        with sr.Microphone() as source:
            print("\n1. Calibrando ruído (fique em silêncio por 2 segundos)...")
            r.adjust_for_ambient_noise(source, duration=2)
            print(f"   Threshold de energia: {r.energy_threshold}")
            
            print("\n2. Testando captura: Fale qualquer coisa agora!")
            audio = r.listen(source, timeout=5, phrase_time_limit=5)
            
            print("\n3. Enviando para reconhecimento (Google)...")
            text = r.recognize_google(audio, language="pt-BR")
            print(f"   VOCÊ DISSE: '{text}'")
            print("\nSUCESSO: O microfone e o reconhecimento estão funcionando!")
            
    except sr.WaitTimeoutError:
        print("\nERRO: Tempo esgotado! Você não falou nada ou o microfone não captou som.")
    except sr.UnknownValueError:
        print("\nERRO: Áudio captado, mas não foi possível entender a fala (ruído ou voz muito baixa).")
    except Exception as e:
        print(f"\nERRO CRÍTICO: {e}")

if __name__ == "__main__":
    test_mic()
