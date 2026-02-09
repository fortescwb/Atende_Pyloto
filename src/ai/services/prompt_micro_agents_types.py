"""Tipos compartilhados dos micro agentes de prompt."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MicroAgentResult:
    context_paths: list[str]
    context_chunks: list[str]
    loaded_contexts: list[str]

    @classmethod
    def empty(cls) -> MicroAgentResult:
        return cls(context_paths=[], context_chunks=[], loaded_contexts=[])


@dataclass(frozen=True, slots=True)
class CaseSelection:
    case_id: str | None
    confidence: float


def merge_results(results: list[MicroAgentResult]) -> MicroAgentResult:
    """Consolida resultados removendo duplicidades."""
    context_paths: list[str] = []
    context_chunks: list[str] = []
    loaded_contexts: list[str] = []

    for result in results:
        for path in result.context_paths:
            if path and path not in context_paths:
                context_paths.append(path)
        for chunk in result.context_chunks:
            if chunk and chunk not in context_chunks:
                context_chunks.append(chunk)
        for path in result.loaded_contexts:
            if path and path not in loaded_contexts:
                loaded_contexts.append(path)

    return MicroAgentResult(
        context_paths=context_paths,
        context_chunks=context_chunks,
        loaded_contexts=loaded_contexts,
    )
