from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BenchmarkText:
    label: str
    text: str


def parse_provider_list(value: str) -> list[str]:
    if not value:
        return []
    seen = set()
    providers = []
    for part in value.split(","):
        provider = part.strip().lower()
        if provider and provider not in seen:
            seen.add(provider)
            providers.append(provider)
    return providers


def benchmark_texts() -> list[BenchmarkText]:
    return [
        BenchmarkText(label="neutral", text="Olá, por favor, descreva sua tarefa com detalhes."),
        BenchmarkText(label="urgent", text="Ação urgente: responda imediatamente com foco e prioridade."),
        BenchmarkText(label="friendly", text="Oi! Vamos resolver isso juntos de forma leve e agradável."),
    ]
