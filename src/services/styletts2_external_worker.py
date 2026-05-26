from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def _configure_stdio() -> None:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            continue


def _configure_espeak() -> None:
    if os.environ.get("PHONEMIZER_ESPEAK_LIBRARY"):
        return
    candidates = [
        Path(r"C:\Program Files\eSpeak NG\libespeak-ng.dll"),
        Path(r"C:\Program Files (x86)\eSpeak NG\libespeak-ng.dll"),
    ]
    for dll in candidates:
        if dll.is_file():
            os.environ.setdefault("PHONEMIZER_ESPEAK_LIBRARY", str(dll))
            os.environ.setdefault("PHONEMIZER_ESPEAK_PATH", str(dll.with_name("espeak-ng.exe")))
            return


def _configure_nltk() -> None:
    project_root = Path(__file__).resolve().parents[2]
    nltk_dir = project_root / "data" / "nltk_data"
    nltk_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("NLTK_DATA", str(nltk_dir))
    try:
        import nltk

        nltk_path = str(nltk_dir)
        if nltk_path not in nltk.data.path:
            nltk.data.path.insert(0, nltk_path)
    except Exception:
        return


def _load_styletts2(model_checkpoint: str = "", config_path: str = ""):
    _configure_espeak()
    _configure_nltk()
    try:
        from styletts2_fork import tts
    except ImportError:
        from styletts2 import tts  # type: ignore

    kwargs = {}
    if model_checkpoint:
        kwargs["model_checkpoint_path"] = model_checkpoint
    if config_path:
        kwargs["config_path"] = config_path
    return tts.StyleTTS2(**kwargs)


def _write_styletts2_file(
    api,
    *,
    text: str,
    reference: str,
    out: Path,
    alpha: float,
    beta: float,
    diffusion_steps: int,
    embedding_scale: float,
    output_sample_rate: int,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    api.inference(
        text,
        target_voice_path=reference or None,
        output_wav_file=str(out),
        output_sample_rate=output_sample_rate,
        alpha=alpha,
        beta=beta,
        diffusion_steps=diffusion_steps,
        embedding_scale=embedding_scale,
    )


def _run_server(api, args) -> int:
    print(json.dumps({"type": "ready", "ok": True}), flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        started = time.perf_counter()
        request_id = None
        try:
            request = json.loads(line)
            request_id = request.get("id")
            text = str(request.get("text", "")).strip()
            out_raw = str(request.get("out", "")).strip()
            if not text or not out_raw:
                raise ValueError("Requisicao StyleTTS2 precisa de text e out.")
            _write_styletts2_file(
                api,
                text=text,
                reference=args.reference,
                out=Path(out_raw),
                alpha=float(request.get("alpha", args.alpha)),
                beta=float(request.get("beta", args.beta)),
                diffusion_steps=int(request.get("diffusion_steps", args.diffusion_steps)),
                embedding_scale=float(request.get("embedding_scale", args.embedding_scale)),
                output_sample_rate=int(request.get("output_sample_rate", args.output_sample_rate)),
            )
            print(
                json.dumps(
                    {
                        "type": "result",
                        "id": request_id,
                        "ok": True,
                        "seconds": round(time.perf_counter() - started, 3),
                    }
                ),
                flush=True,
            )
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "type": "result",
                        "id": request_id,
                        "ok": False,
                        "error": repr(exc),
                    }
                ),
                flush=True,
            )
    return 0


def main() -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(description="Worker externo para StyleTTS2.")
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--reference", default="")
    parser.add_argument("--model-checkpoint", default="")
    parser.add_argument("--config", default="")
    parser.add_argument("--alpha", type=float, default=0.3)
    parser.add_argument("--beta", type=float, default=0.7)
    parser.add_argument("--diffusion-steps", type=int, default=3)
    parser.add_argument("--embedding-scale", type=float, default=1.0)
    parser.add_argument("--output-sample-rate", type=int, default=24000)
    parser.add_argument("--out")
    parser.add_argument("--text")
    args = parser.parse_args()

    if not args.server and (not args.out or not args.text):
        parser.error("--out e --text sao obrigatorios fora do modo --server.")

    if args.reference and not Path(os.path.expandvars(os.path.expanduser(args.reference))).is_file():
        parser.error("--reference nao encontrado.")

    api = _load_styletts2(args.model_checkpoint, args.config)
    if args.server:
        return _run_server(api, args)

    _write_styletts2_file(
        api,
        text=args.text or "",
        reference=args.reference,
        out=Path(args.out or ""),
        alpha=args.alpha,
        beta=args.beta,
        diffusion_steps=args.diffusion_steps,
        embedding_scale=args.embedding_scale,
        output_sample_rate=args.output_sample_rate,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
