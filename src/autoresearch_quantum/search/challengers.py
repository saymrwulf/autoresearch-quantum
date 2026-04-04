from __future__ import annotations

from dataclasses import dataclass

from ..models import ExperimentSpec, SearchSpaceConfig


@dataclass(frozen=True)
class GeneratedChallenger:
    spec: ExperimentSpec
    mutation_note: str


def generate_neighbor_challengers(
    incumbent: ExperimentSpec,
    search_space: SearchSpaceConfig,
    history: set[str] | None = None,
) -> list[GeneratedChallenger]:
    challengers: list[GeneratedChallenger] = []
    seen: set[str] = set(history or set())

    for field_name, values in search_space.dimensions.items():
        current = getattr(incumbent, field_name)
        for value in values:
            normalized = tuple(value) if field_name == "initial_layout" and isinstance(value, list) else value
            if normalized == current:
                continue
            candidate = incumbent.with_updates(**{field_name: normalized})
            fingerprint = candidate.fingerprint()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            challengers.append(
                GeneratedChallenger(
                    spec=candidate,
                    mutation_note=f"{field_name}: {current} -> {normalized}",
                )
            )
            if len(challengers) >= search_space.max_challengers_per_step:
                return challengers

    return challengers


def mutation_summary(parent: ExperimentSpec, child: ExperimentSpec) -> str:
    changes: list[str] = []
    for field_name in parent.__dataclass_fields__:
        if getattr(parent, field_name) != getattr(child, field_name):
            changes.append(
                f"{field_name}: {getattr(parent, field_name)} -> {getattr(child, field_name)}"
            )
    return ", ".join(changes) if changes else "no mutation"
