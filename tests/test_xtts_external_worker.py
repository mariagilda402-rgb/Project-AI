from __future__ import annotations

import os
import sys
import types
import io
import json
from pathlib import Path


def test_xtts_worker_sets_license_and_uses_project_cache(monkeypatch, tmp_path):
    from src.services import xtts_external_worker

    observed = {}

    class FakeTTS:
        def __init__(self, model_name):
            observed["model_name"] = model_name
            import trainer.io as trainer_io
            import TTS.utils.manage as tts_manage

            observed["trainer_cache"] = trainer_io.get_user_data_dir("tts")
            observed["manager_cache"] = tts_manage.get_user_data_dir("tts")

        def to(self, device):
            observed["device"] = device
            return self

        def tts_to_file(self, *, text, speaker_wav, language, file_path):
            observed["text"] = text
            observed["speaker_wav"] = speaker_wav
            observed["language"] = language
            Path(file_path).write_bytes(b"RIFFworker")

    transformers_import_utils = types.ModuleType("transformers.utils.import_utils")
    transformers_import_utils.is_torchcodec_available = lambda: True
    transformers_utils = types.ModuleType("transformers.utils")
    transformers_utils.import_utils = transformers_import_utils
    transformers = types.ModuleType("transformers")
    transformers.utils = transformers_utils

    tts_pkg = types.ModuleType("TTS")
    tts_pkg.__path__ = []
    tts_api = types.ModuleType("TTS.api")
    tts_api.TTS = FakeTTS
    tts_utils = types.ModuleType("TTS.utils")
    tts_utils.__path__ = []
    tts_manage = types.ModuleType("TTS.utils.manage")
    trainer_pkg = types.ModuleType("trainer")
    trainer_pkg.__path__ = []
    trainer_io = types.ModuleType("trainer.io")

    monkeypatch.setitem(sys.modules, "transformers", transformers)
    monkeypatch.setitem(sys.modules, "transformers.utils", transformers_utils)
    monkeypatch.setitem(sys.modules, "transformers.utils.import_utils", transformers_import_utils)
    monkeypatch.setitem(sys.modules, "TTS", tts_pkg)
    monkeypatch.setitem(sys.modules, "TTS.api", tts_api)
    monkeypatch.setitem(sys.modules, "TTS.utils", tts_utils)
    monkeypatch.setitem(sys.modules, "TTS.utils.manage", tts_manage)
    monkeypatch.setitem(sys.modules, "trainer", trainer_pkg)
    monkeypatch.setitem(sys.modules, "trainer.io", trainer_io)
    monkeypatch.delenv("COQUI_TOS_AGREED", raising=False)

    out = tmp_path / "out.wav"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "xtts_external_worker",
            "--model",
            "tts_models/multilingual/multi-dataset/xtts_v2",
            "--speaker",
            "a.wav;b.wav",
            "--language",
            "pt",
            "--device",
            "cpu",
            "--out",
            str(out),
            "--text",
            "Teste curto.",
        ],
    )

    assert xtts_external_worker.main() == 0

    assert os.environ["COQUI_TOS_AGREED"] == "1"
    assert observed["speaker_wav"] == ["a.wav", "b.wav"]
    assert observed["device"] == "cpu"
    assert observed["trainer_cache"].as_posix().endswith("/data/coqui/tts")
    assert observed["manager_cache"].as_posix().endswith("/data/coqui/tts")
    assert out.read_bytes() == b"RIFFworker"


def test_xtts_worker_does_not_insert_main_venv_site_packages(monkeypatch, tmp_path):
    from src.services import xtts_external_worker

    main_site = str(Path.cwd() / ".venv" / "Lib" / "site-packages")
    sys.path = [path for path in sys.path if path != main_site]

    class FakeTTS:
        def __init__(self, model_name):
            pass

        def to(self, device):
            return self

        def tts_to_file(self, *, text, speaker_wav, language, file_path):
            Path(file_path).write_bytes(b"RIFFworker")

    transformers_import_utils = types.ModuleType("transformers.utils.import_utils")
    transformers_utils = types.ModuleType("transformers.utils")
    transformers_utils.import_utils = transformers_import_utils
    transformers = types.ModuleType("transformers")
    transformers.utils = transformers_utils

    tts_pkg = types.ModuleType("TTS")
    tts_pkg.__path__ = []
    tts_api = types.ModuleType("TTS.api")
    tts_api.TTS = FakeTTS
    tts_utils = types.ModuleType("TTS.utils")
    tts_utils.__path__ = []
    tts_manage = types.ModuleType("TTS.utils.manage")
    trainer_pkg = types.ModuleType("trainer")
    trainer_pkg.__path__ = []
    trainer_io = types.ModuleType("trainer.io")

    for name, module in {
        "transformers": transformers,
        "transformers.utils": transformers_utils,
        "transformers.utils.import_utils": transformers_import_utils,
        "TTS": tts_pkg,
        "TTS.api": tts_api,
        "TTS.utils": tts_utils,
        "TTS.utils.manage": tts_manage,
        "trainer": trainer_pkg,
        "trainer.io": trainer_io,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "xtts_external_worker",
            "--model",
            "model",
            "--speaker",
            "a.wav",
            "--out",
            str(tmp_path / "out.wav"),
            "--text",
            "Teste.",
        ],
    )

    assert xtts_external_worker.main() == 0
    assert main_site not in sys.path


def test_xtts_worker_server_reuses_loaded_model(monkeypatch, tmp_path):
    from src.services import xtts_external_worker

    observed = {"loads": 0, "calls": []}

    class FakeTTS:
        def __init__(self, model_name):
            observed["loads"] += 1
            observed["model_name"] = model_name

        def to(self, device):
            observed["device"] = device
            return self

        def tts_to_file(self, *, text, speaker_wav, language, file_path):
            observed["calls"].append((text, speaker_wav, language))
            Path(file_path).write_bytes(b"RIFFserver")

    transformers_import_utils = types.ModuleType("transformers.utils.import_utils")
    transformers_utils = types.ModuleType("transformers.utils")
    transformers_utils.import_utils = transformers_import_utils
    transformers = types.ModuleType("transformers")
    transformers.utils = transformers_utils

    tts_pkg = types.ModuleType("TTS")
    tts_pkg.__path__ = []
    tts_api = types.ModuleType("TTS.api")
    tts_api.TTS = FakeTTS
    tts_utils = types.ModuleType("TTS.utils")
    tts_utils.__path__ = []
    tts_manage = types.ModuleType("TTS.utils.manage")
    trainer_pkg = types.ModuleType("trainer")
    trainer_pkg.__path__ = []
    trainer_io = types.ModuleType("trainer.io")

    for name, module in {
        "transformers": transformers,
        "transformers.utils": transformers_utils,
        "transformers.utils.import_utils": transformers_import_utils,
        "TTS": tts_pkg,
        "TTS.api": tts_api,
        "TTS.utils": tts_utils,
        "TTS.utils.manage": tts_manage,
        "trainer": trainer_pkg,
        "trainer.io": trainer_io,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    out1 = tmp_path / "out1.wav"
    out2 = tmp_path / "out2.wav"
    stdin = "\n".join(
        [
            json.dumps({"id": "one", "text": "Primeiro.", "out": str(out1)}),
            json.dumps({"id": "two", "text": "Segundo.", "out": str(out2)}),
        ]
    )
    stdout = io.StringIO()

    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin + "\n"))
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "xtts_external_worker",
            "--server",
            "--model",
            "model",
            "--speaker",
            "a.wav;b.wav",
            "--language",
            "pt",
            "--device",
            "cpu",
        ],
    )

    assert xtts_external_worker.main() == 0

    messages = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert messages[0]["type"] == "ready"
    assert messages[1]["id"] == "one"
    assert messages[1]["ok"] is True
    assert messages[2]["id"] == "two"
    assert messages[2]["ok"] is True
    assert observed["loads"] == 1
    assert observed["calls"] == [
        ("Primeiro.", ["a.wav", "b.wav"], "pt"),
        ("Segundo.", ["a.wav", "b.wav"], "pt"),
    ]
    assert out1.read_bytes() == b"RIFFserver"
    assert out2.read_bytes() == b"RIFFserver"
