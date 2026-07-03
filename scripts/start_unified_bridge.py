from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.jarvis_unified.local_server import UnifiedJarvisLocalBridge


def _local_ipv4s() -> list[str]:
    ips: set[str] = set()
    try:
        hostname = socket.gethostname()
        for result in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = result[4][0]
            if not ip.startswith("127."):
                ips.add(ip)
    except Exception:
        pass
    return sorted(ips)


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the local Unified Jarvis bridge.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5124)
    parser.add_argument("--token", default="")
    parser.add_argument("--event-log", default="data/unified_bridge_events.jsonl")
    args = parser.parse_args()

    log_path = Path(args.event_log)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def on_event(event):
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    print("[UnifiedJarvis] Bridge starting.")
    print(f"[UnifiedJarvis] USB/ADB reverse URL: ws://127.0.0.1:{args.port}/jarvis/ws")
    for ip in _local_ipv4s():
        print(f"[UnifiedJarvis] LAN URL: ws://{ip}:{args.port}/jarvis/ws")
    print(f"[UnifiedJarvis] Events: {log_path}")

    bridge = UnifiedJarvisLocalBridge(
        host=args.host,
        port=args.port,
        token=args.token,
        on_event=on_event,
    )
    bridge.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
