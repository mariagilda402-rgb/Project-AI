# TTS Benchmarking

Objetivo: comparar providers para um assistente responsivo estilo Jarvis no hardware local.

## Ordem padrao

O provider principal vem de `TTS_PROVIDER`. O padrao do projeto agora e:

```env
TTS_PROVIDER=xtts
TTS_PROVIDER_ORDER=edge,kokoro,piper,rvc,openai,elevenlabs,murf,fish,local
```

Isso cria a cadeia: XTTS v2 -> Edge TTS -> Kokoro -> outros fallbacks -> voz local.

## XTTS v2

Instalacao opcional:

```powershell
.\.venv\Scripts\python.exe -m pip install coqui-tts
```

Configure o audio limpo da voz alvo:

```env
XTTS_SPEAKER_WAV=C:\caminho\voz_limpa_01.wav;C:\caminho\voz_limpa_02.wav
XTTS_LANGUAGE=pt
XTTS_DEVICE=auto
```

O XTTS so e carregado quando o provider for realmente usado. Se `XTTS_SPEAKER_WAV`
nao apontar para um arquivo existente, ele falha limpo e entra no fallback.

## Benchmark

Teste cada provider isoladamente, sem fallback:

```powershell
.\.venv\Scripts\python.exe -m src.services.tts_benchmark --providers xtts,edge,kokoro,piper,rvc,xtts_rvc --no-playback
```

Teste ouvindo e dando notas humanas:

```powershell
.\.venv\Scripts\python.exe -m src.services.tts_benchmark --providers xtts,edge,kokoro,piper,rvc,xtts_rvc --rate
```

## StyleTTS2

StyleTTS2 entra por adaptador de comando externo para evitar acoplar o projeto a
um script de pesquisa especifico. Configure uma lista JSON com placeholders:

```env
STYLETTS2_COMMAND=["python","C:\\StyleTTS2\\inference.py","--text","{text}","--out","{out}","--ref","{ref}"]
STYLETTS2_REFERENCE_WAV=C:\caminho\voz_limpa.wav
```

Depois inclua `styletts2` no benchmark:

```powershell
.\.venv\Scripts\python.exe -m src.services.tts_benchmark --providers xtts,styletts2,edge,kokoro --rate
```

Teste a cadeia real de fallback:

```powershell
.\.venv\Scripts\python.exe -m src.services.tts_benchmark --providers xtts --with-fallbacks --rate
```

O relatorio padrao sai em `data/tts_benchmarks/latest.json` e inclui latencia,
RAM do processo antes/depois, arquivos gerados quando `--no-playback` e notas de
qualidade/clonagem/emocao quando `--rate` estiver ativo.
