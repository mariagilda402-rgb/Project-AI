from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from src.config import load_settings
from src.services.tts import TTSService, parse_tts_provider_order, resolve_tts_provider_order


@dataclass(frozen=True)
class BenchmarkText:
    label: str
    text: str


@dataclass
class BenchmarkResult:
    provider: str
    label: str
    success: bool
    latency_sec: float
    ram_before_mb: float | None
    ram_after_mb: float | None
    audio_files: list[str]
    error: str
    perceived_quality: int | None = None
    cloning_quality: int | None = None
    emotion_quality: int | None = None
    notes: str = ""


def parse_provider_list(raw: str | Iterable[str]) -> list[str]:
    return parse_tts_provider_order(raw)


def benchmark_texts() -> list[BenchmarkText]:
    return [
        BenchmarkText("neutral", "Tudo esta funcionando normalmente, senhor."),
        BenchmarkText("urgent", "[urgente] Atencao! Detectei atividade incomum."),
        BenchmarkText("friendly", "[feliz] Claro, senhor. Vou cuidar disso agora."),
    ]


def _process_ram_mb() -> float | None:
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:
        return None


def _build_service(provider: str, provider_order: list[str]) -> TTSService:
    settings = load_settings()
    return TTSService(
        api_key=settings.openai_api_key,
        model=settings.tts_model,
        voice=settings.tts_voice,
        provider=provider,
        provider_order=provider_order,
        murf_api_key=settings.murf_api_key,
        murf_voice_id=settings.murf_voice_id,
        murf_api_url=settings.murf_api_url,
        allow_system_player_on_failure=settings.tts_allow_system_player,
        max_chunk_chars=settings.tts_max_chunk_chars,
        pause_between_chunks_sec=settings.tts_pause_between_chunks_sec,
        edge_tts_rate=settings.edge_tts_rate,
        edge_tts_volume=settings.edge_tts_volume,
        kokoro_voice=settings.kokoro_voice,
        kokoro_speed=settings.kokoro_speed,
        xtts_model_name=settings.xtts_model_name,
        xtts_speaker_wav=settings.xtts_speaker_wav,
        xtts_language=settings.xtts_language,
        xtts_device=settings.xtts_device,
        xtts_rvc_voice=settings.xtts_rvc_voice,
        xtts_python=settings.xtts_python,
        xtts_persistent=settings.xtts_persistent,
        styletts2_command=settings.styletts2_command,
        styletts2_reference_wav=settings.styletts2_reference_wav,
        styletts2_python=settings.styletts2_python,
        styletts2_model_checkpoint=settings.styletts2_model_checkpoint,
        styletts2_config=settings.styletts2_config,
        styletts2_alpha=settings.styletts2_alpha,
        styletts2_beta=settings.styletts2_beta,
        styletts2_diffusion_steps=settings.styletts2_diffusion_steps,
        styletts2_embedding_scale=settings.styletts2_embedding_scale,
        styletts2_persistent=settings.styletts2_persistent,
        styletts2_preload=settings.styletts2_preload,
        tts_prefetch_chunks=settings.tts_prefetch_chunks,
        elevenlabs_api_keys=settings.elevenlabs_api_keys,
        piper_repo_id=settings.piper_repo_id,
        piper_jarvis_quality=settings.piper_jarvis_quality,
        piper_model_file=settings.piper_model_file,
        piper_config_file=settings.piper_config_file,
        piper_use_cuda=settings.piper_use_cuda,
        piper_fx_preset=settings.piper_fx_preset,
        fish_audio_api_key=os.environ.get("FISH_AUDIO_API_KEY", ""),
    )


def run_provider_sample(
    provider: str,
    sample: BenchmarkText,
    *,
    playback: bool,
    with_fallbacks: bool,
) -> BenchmarkResult:
    provider_order = (
        resolve_tts_provider_order(provider)
        if with_fallbacks
        else parse_tts_provider_order([provider])
    )
    service = _build_service(provider, provider_order)
    if not with_fallbacks:
        service.provider_order = provider_order
    audio_files: list[str] = []

    if not playback:
        def capture_audio(path):
            audio_files.append(str(Path(path).resolve()))

        service._play_audio_file = capture_audio  # type: ignore[method-assign]
        service._play_wav = capture_audio  # type: ignore[method-assign]
        service._play_mp3 = capture_audio  # type: ignore[method-assign]
        service._play_file = capture_audio  # type: ignore[method-assign]

    before = _process_ram_mb()
    started = time.perf_counter()
    try:
        service._speak_one_chunk(sample.text)
        success = not bool(service.last_error)
        error = service.last_error
    except Exception as exc:
        success = False
        error = repr(exc)
    latency = time.perf_counter() - started
    after = _process_ram_mb()
    return BenchmarkResult(
        provider=provider,
        label=sample.label,
        success=success,
        latency_sec=round(latency, 3),
        ram_before_mb=round(before, 1) if before is not None else None,
        ram_after_mb=round(after, 1) if after is not None else None,
        audio_files=audio_files,
        error=error,
    )


def prompt_ratings(result: BenchmarkResult) -> None:
    print(f"\n{result.provider} / {result.label} / {result.latency_sec}s")
    if result.error:
        print(f"Erro: {result.error}")
        return
    for field, label in [
        ("perceived_quality", "qualidade geral"),
        ("cloning_quality", "clonagem/timbre"),
        ("emotion_quality", "emocao/prosodia"),
    ]:
        raw = input(f"Nota de {label} (1-5, Enter para pular): ").strip()
        if raw:
            try:
                setattr(result, field, max(1, min(5, int(raw))))
            except ValueError:
                pass
    result.notes = input("Notas curtas (Enter para pular): ").strip()


def run_benchmark(
    providers: list[str],
    *,
    playback: bool = True,
    with_fallbacks: bool = False,
    ask_ratings: bool = False,
) -> list[BenchmarkResult]:
    results: list[BenchmarkResult] = []
    for provider in providers:
        for sample in benchmark_texts():
            result = run_provider_sample(
                provider,
                sample,
                playback=playback,
                with_fallbacks=with_fallbacks,
            )
            if ask_ratings:
                prompt_ratings(result)
            results.append(result)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark local de providers TTS.")
    parser.add_argument(
        "--providers",
        default="xtts,edge,kokoro,piper,rvc,xtts_rvc,styletts2",
        help="Lista separada por virgulas. Ex.: xtts,edge,kokoro,piper,rvc",
    )
    parser.add_argument(
        "--out",
        default="data/tts_benchmarks/latest.json",
        help="Arquivo JSON de saida.",
    )
    parser.add_argument("--no-playback", action="store_true", help="Nao tocar o audio.")
    parser.add_argument(
        "--with-fallbacks",
        action="store_true",
        help="Testa cada provider com a cadeia de fallback ativa.",
    )
    parser.add_argument("--rate", action="store_true", help="Pedir notas humanas 1-5.")
    args = parser.parse_args()

    providers = parse_provider_list(args.providers)
    results = run_benchmark(
        providers,
        playback=not args.no_playback,
        with_fallbacks=args.with_fallbacks,
        ask_ratings=args.rate,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Relatorio salvo em {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
