import av
import wave

def mp3_to_wav(mp3_path: str, wav_path: str, target_rate: int = 22050) -> bool:
    """Converte um MP3 para WAV (Mono, 16-bit) usando PyAV sem depender do ffmpeg no sistema."""
    try:
        with av.open(mp3_path) as container:
            stream = container.streams.audio[0]
            
            with wave.open(wav_path, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(target_rate)
                
                resampler = av.AudioResampler(format='s16', layout='mono', rate=target_rate)
                
                for frame in container.decode(stream):
                    frame.pts = None
                    for resampled_frame in resampler.resample(frame):
                        wav_file.writeframes(resampled_frame.to_ndarray().tobytes())
        return True
    except Exception as e:
        print(f"[AudioConverter] Erro ao converter mp3 para wav: {e}")
        return False
