"""Informacoes do sistema (CPU, RAM, disco, bateria, processos)."""
from __future__ import annotations

import platform

from .base import ToolResult


class SystemInfoTool:
    name = "system_info"
    description = "Retorna informacoes do sistema (CPU, RAM, disco, bateria)."
    critical = False

    def get_info(self) -> ToolResult:
        try:
            import psutil
        except ImportError:
            return ToolResult(False, "psutil nao instalado. Rode: pip install psutil")

        cpu_percent = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")

        lines = [
            f"SO: {platform.system()} {platform.release()} ({platform.machine()})",
            f"CPU: {cpu_percent}% ({psutil.cpu_count()} cores)",
            f"RAM: {mem.used / (1024**3):.1f}/{mem.total / (1024**3):.1f} GB ({mem.percent}%)",
            f"Disco C: {disk.used / (1024**3):.0f}/{disk.total / (1024**3):.0f} GB "
            f"({disk.percent}% usado, {disk.free / (1024**3):.0f} GB livre)",
        ]

        battery = psutil.sensors_battery()
        if battery:
            status = "carregando" if battery.power_plugged else "bateria"
            lines.append(f"Bateria: {battery.percent}% ({status})")

        procs: list[tuple[str, float]] = []
        for p in psutil.process_iter(["name", "memory_percent"]):
            try:
                info = p.info
                pct = info.get("memory_percent") or 0.0
                if pct > 0.5:
                    procs.append((info["name"], pct))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(key=lambda x: x[1], reverse=True)
        if procs:
            top = procs[:5]
            lines.append("Top processos (RAM): " + ", ".join(f"{n} ({p:.1f}%)" for n, p in top))

        return ToolResult(True, "\n".join(lines))

    def run(self, command: str) -> ToolResult:
        return self.get_info()
