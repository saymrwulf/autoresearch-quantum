from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..models import ExperimentSpec, LessonFeedback, SearchRule, SearchSpaceConfig
from .challengers import GeneratedChallenger


class ChallengerStrategy(ABC):
    @abstractmethod
    def generate(
        self,
        incumbent: ExperimentSpec,
        search_space: SearchSpaceConfig,
        history: set[str],
        lessons: list[LessonFeedback] | None = None,
    ) -> list[GeneratedChallenger]:
        ...


class NeighborWalk(ChallengerStrategy):
    """Single-axis perturbation — the original Codex strategy, kept as baseline."""

    def generate(
        self,
        incumbent: ExperimentSpec,
        search_space: SearchSpaceConfig,
        history: set[str],
        lessons: list[LessonFeedback] | None = None,
    ) -> list[GeneratedChallenger]:
        challengers: list[GeneratedChallenger] = []
        seen = set(history)

        for field_name, values in search_space.dimensions.items():
            current = getattr(incumbent, field_name)
            for value in values:
                normalized = tuple(value) if field_name == "initial_layout" and isinstance(value, list) else value
                if normalized == current:
                    continue
                candidate = incumbent.with_updates(**{field_name: normalized})
                fp = candidate.fingerprint()
                if fp in seen:
                    continue
                seen.add(fp)
                challengers.append(
                    GeneratedChallenger(
                        spec=candidate,
                        mutation_note=f"neighbor: {field_name}: {current} -> {normalized}",
                    )
                )
                if len(challengers) >= search_space.max_challengers_per_step:
                    return challengers
        return challengers


class RandomCombo(ChallengerStrategy):
    """Pick 1–3 random dimensions and mutate them simultaneously."""

    def __init__(self, num_candidates: int = 6, max_mutations: int = 3) -> None:
        self.num_candidates = num_candidates
        self.max_mutations = max_mutations

    def generate(
        self,
        incumbent: ExperimentSpec,
        search_space: SearchSpaceConfig,
        history: set[str],
        lessons: list[LessonFeedback] | None = None,
    ) -> list[GeneratedChallenger]:
        challengers: list[GeneratedChallenger] = []
        seen = set(history)
        dim_names = list(search_space.dimensions.keys())
        if not dim_names:
            return challengers

        attempts = 0
        max_attempts = self.num_candidates * 5

        while len(challengers) < self.num_candidates and attempts < max_attempts:
            attempts += 1
            n_dims = random.randint(1, min(self.max_mutations, len(dim_names)))
            chosen_dims = random.sample(dim_names, n_dims)
            updates: dict[str, Any] = {}
            mutation_parts: list[str] = []

            for dim in chosen_dims:
                values = search_space.dimensions[dim]
                current = getattr(incumbent, dim)
                alternatives = [v for v in values if v != current]
                if not alternatives:
                    continue
                new_val = random.choice(alternatives)
                if dim == "initial_layout" and isinstance(new_val, list):
                    new_val = tuple(new_val)
                updates[dim] = new_val
                mutation_parts.append(f"{dim}: {current} -> {new_val}")

            if not updates:
                continue

            candidate = incumbent.with_updates(**updates)
            fp = candidate.fingerprint()
            if fp in seen:
                continue
            seen.add(fp)
            challengers.append(
                GeneratedChallenger(
                    spec=candidate,
                    mutation_note=f"combo: {', '.join(mutation_parts)}",
                )
            )

        return challengers


class LessonGuided(ChallengerStrategy):
    """Use SearchRules from lessons to bias generation toward promising regions."""

    def __init__(self, num_candidates: int = 4) -> None:
        self.num_candidates = num_candidates

    def generate(
        self,
        incumbent: ExperimentSpec,
        search_space: SearchSpaceConfig,
        history: set[str],
        lessons: list[LessonFeedback] | None = None,
    ) -> list[GeneratedChallenger]:
        if not lessons:
            return []

        # Collect all rules across rungs
        all_rules: list[SearchRule] = []
        for feedback in lessons:
            all_rules.extend(feedback.rules)

        if not all_rules:
            return []

        # Build preference/avoidance maps
        prefer: dict[str, list[tuple[Any, float]]] = {}
        avoid: dict[str, set[Any]] = {}
        fix: dict[str, Any] = {}

        for rule in all_rules:
            if rule.action == "prefer":
                prefer.setdefault(rule.dimension, []).append((rule.value, rule.confidence))
            elif rule.action == "avoid":
                avoid.setdefault(rule.dimension, set()).add(rule.value)
            elif rule.action == "fix":
                fix[rule.dimension] = rule.value

        challengers: list[GeneratedChallenger] = []
        seen = set(history)

        for _ in range(self.num_candidates * 3):
            if len(challengers) >= self.num_candidates:
                break

            updates: dict[str, Any] = {}
            mutation_parts: list[str] = []

            # Apply "fix" rules first
            for dim, value in fix.items():
                if dim in search_space.dimensions:
                    current = getattr(incumbent, dim)
                    if value != current:
                        normalized = tuple(value) if dim == "initial_layout" and isinstance(value, list) else value
                        updates[dim] = normalized
                        mutation_parts.append(f"fix({dim}): {current} -> {normalized}")

            # Then apply "prefer" rules probabilistically
            for dim, preferences in prefer.items():
                if dim in fix or dim not in search_space.dimensions:
                    continue
                current = getattr(incumbent, dim)
                avoided = avoid.get(dim, set())
                # Weighted sampling from preferred values
                candidates = [(v, c) for v, c in preferences if v != current and v not in avoided]
                if not candidates and random.random() < 0.5:
                    # Sometimes also try non-preferred, non-avoided values
                    all_vals = [v for v in search_space.dimensions[dim] if v != current and v not in avoided]
                    if all_vals:
                        val = random.choice(all_vals)
                        normalized = tuple(val) if dim == "initial_layout" and isinstance(val, list) else val
                        updates[dim] = normalized
                        mutation_parts.append(f"explore({dim}): {current} -> {normalized}")
                elif candidates:
                    # Weight by confidence
                    total = sum(c for _, c in candidates)
                    r = random.random() * total
                    cumulative = 0.0
                    chosen = candidates[0][0]
                    for val, conf in candidates:
                        cumulative += conf
                        if r <= cumulative:
                            chosen = val
                            break
                    normalized = tuple(chosen) if dim == "initial_layout" and isinstance(chosen, list) else chosen
                    updates[dim] = normalized
                    mutation_parts.append(f"guided({dim}): {current} -> {normalized}")

            if not updates:
                continue

            candidate = incumbent.with_updates(**updates)
            fp = candidate.fingerprint()
            if fp in seen:
                continue
            seen.add(fp)
            challengers.append(
                GeneratedChallenger(
                    spec=candidate,
                    mutation_note=f"lesson: {', '.join(mutation_parts)}",
                )
            )

        return challengers


@dataclass
class StrategyWeight:
    strategy: ChallengerStrategy
    weight: float


class CompositeGenerator(ChallengerStrategy):
    """Weighted combination of multiple strategies. Allocates budget proportionally."""

    def __init__(self, strategies: list[StrategyWeight]) -> None:
        self.strategies = strategies

    def generate(
        self,
        incumbent: ExperimentSpec,
        search_space: SearchSpaceConfig,
        history: set[str],
        lessons: list[LessonFeedback] | None = None,
    ) -> list[GeneratedChallenger]:
        total_weight = sum(sw.weight for sw in self.strategies)
        budget = search_space.max_challengers_per_step
        all_challengers: list[GeneratedChallenger] = []
        seen = set(history)

        for sw in self.strategies:
            allocation = max(1, int(budget * sw.weight / total_weight))
            sub_space = SearchSpaceConfig(
                dimensions=search_space.dimensions,
                max_challengers_per_step=allocation,
            )
            new_challengers = sw.strategy.generate(incumbent, sub_space, seen, lessons)
            for c in new_challengers:
                fp = c.spec.fingerprint()
                if fp not in seen:
                    seen.add(fp)
                    all_challengers.append(c)
                    if len(all_challengers) >= budget:
                        return all_challengers

        return all_challengers


def default_composite(has_lessons: bool = False) -> CompositeGenerator:
    """Build the default composite generator with sensible weights."""
    strategies: list[StrategyWeight] = [
        StrategyWeight(NeighborWalk(), weight=0.4),
        StrategyWeight(RandomCombo(), weight=0.3),
    ]
    if has_lessons:
        strategies.append(StrategyWeight(LessonGuided(), weight=0.3))
    else:
        # Without lessons, give more budget to exploration
        strategies[1] = StrategyWeight(RandomCombo(num_candidates=8), weight=0.6)
    return CompositeGenerator(strategies)
