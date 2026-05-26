from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def _resolve_device(raw_device: str) -> str:
    device = (raw_device or "auto").strip().lower()
    if device != "auto":
        return device
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def _speaker_wav_arg(raw_speaker: str) -> str | list[str]:
    speaker_files = [item for item in raw_speaker.split(";") if item.strip()]
    if len(speaker_files) == 1:
        return speaker_files[0]
    return speaker_files


def _load_xtts(model_name: str, device: str, project_root: Path):
    os.environ.setdefault("COQUI_TOS_AGREED", "1")

    try:
        import transformers.utils.import_utils as import_utils

        if not hasattr(import_utils, "is_torchcodec_available"):
            import_utils.is_torchcodec_available = lambda: False
    except Exception:
        pass

    from TTS.api import TTS as CoquiTTS
    import trainer.io as trainer_io
    import TTS.utils.manage as tts_manage

    def project_data_dir(appname: str) -> Path:
        path = project_root / "data" / "coqui" / appname
        path.mkdir(parents=True, exist_ok=True)
        return path

    trainer_io.get_user_data_dir = project_data_dir
    tts_manage.get_user_data_dir = project_data_dir

    api = CoquiTTS(model_name)
    if hasattr(api, "to"):
        api = api.to(_resolve_device(device))
    return api


def _write_xtts_file(
    api,
    *,
    text: str,
    speaker_wav: str | list[str],
    language: str,
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    api.tts_to_file(
        text=text,
        speaker_wav=speaker_wav,
        language=language,
        file_path=str(out),
    )


def _run_server(api, speaker_wav: str | list[str], default_language: str) -> int:
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
                raise ValueError("Requisicao XTTS precisa de text e out.")
            _write_xtts_file(
                api,
                text=text,
                speaker_wav=speaker_wav,
                language=str(request.get("language") or default_language or "pt"),
                out=Path(out_raw),
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
    os.environ.setdefault("COQUI_TOS_AGREED", "1")

    parser = argparse.ArgumentParser(description="Worker externo para XTTS v2.")
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--model", required=True)
    parser.add_argument("--speaker", required=True)
    parser.add_argument("--language", default="pt")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--out")
    parser.add_argument("--text")
    args = parser.parse_args()

    if not args.server and (not args.out or not args.text):
        parser.error("--out e --text sao obrigatorios fora do modo --server.")

    speaker_wav = _speaker_wav_arg(args.speaker)
    project_root = Path(__file__).resolve().parents[2]
    api = _load_xtts(args.model, args.device, project_root)

    if args.server:
        return _run_server(api, speaker_wav, args.language)

    _write_xtts_file(
        api,
        text=args.text or "",
        speaker_wav=speaker_wav,
        language=args.language,
        out=Path(args.out or ""),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
