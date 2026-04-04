from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from statistics import fmean, stdev
from typing import Any

from ..models import LessonFeedback, SearchRule, SearchSpaceConfig


def _record_score(record: dict[str, Any]) -> float:
    return float(record.get("final_score", 0.0))


def extract_search_rules(
    experiment_records: list[dict[str, Any]],
    search_space: SearchSpaceConfig,
    min_samples: int = 2,
    effect_threshold: float = 0.005,
) -> list[SearchRule]:
    """Extract machine-readable search rules from experiment data.

    Analyses per-dimension mean effects, interaction detection, and
    consistency patterns to produce prefer/avoid/fix directives.
    """
    if not experiment_records:
        return []

    overall_mean = fmean(_record_score(r) for r in experiment_records)
    rules: list[SearchRule] = []
    dim_names = list(search_space.dimensions.keys())

    # Per-dimension analysis
    for dim in dim_names:
        grouped: dict[Any, list[float]] = defaultdict(list)
        for record in experiment_records:
            val = record["spec"].get(dim)
            if val is not None:
                grouped[val].append(_record_score(record))

        for value, scores in grouped.items():
            if len(scores) < min_samples:
                continue
            mean_score = fmean(scores)
            delta = mean_score - overall_mean
            confidence = min(1.0, len(scores) / max(len(experiment_records), 1))

            if delta > effect_threshold:
                rules.append(SearchRule(
                    dimension=dim,
                    action="prefer",
                    value=value,
                    confidence=confidence,
                    reason=f"mean score {mean_score:.4f} is {delta:+.4f} above overall mean ({len(scores)} samples)",
                ))
            elif delta < -effect_threshold:
                rules.append(SearchRule(
                    dimension=dim,
                    action="avoid",
                    value=value,
                    confidence=confidence,
                    reason=f"mean score {mean_score:.4f} is {delta:+.4f} below overall mean ({len(scores)} samples)",
                ))

    # Check for "fix" rules: if top-K experiments all share a value
    top_k = min(5, max(3, len(experiment_records) // 3))
    top_records = sorted(experiment_records, key=_record_score, reverse=True)[:top_k]
    if len(top_records) >= 3:
        for dim in dim_names:
            values_in_top = {r["spec"].get(dim) for r in top_records}
            if len(values_in_top) == 1:
                fixed_value = next(iter(values_in_top))
                # Also check it's better than alternatives
                all_with_value = [
                    _record_score(r) for r in experiment_records
                    if r["spec"].get(dim) == fixed_value
                ]
                all_without = [
                    _record_score(r) for r in experiment_records
                    if r["spec"].get(dim) != fixed_value
                ]
                if all_without and fmean(all_with_value) > fmean(all_without):
                    rules.append(SearchRule(
                        dimension=dim,
                        action="fix",
                        value=fixed_value,
                        confidence=min(1.0, len(top_records) / len(experiment_records)),
                        reason=f"all top-{len(top_records)} experiments use {dim}={fixed_value}",
                    ))

    # Interaction detection: for dimension pairs, check if joint effect > sum of marginals
    for dim_a, dim_b in combinations(dim_names, 2):
        marginal_a: dict[Any, float] = {}
        marginal_b: dict[Any, float] = {}
        joint: dict[tuple[Any, Any], list[float]] = defaultdict(list)

        for record in experiment_records:
            va = record["spec"].get(dim_a)
            vb = record["spec"].get(dim_b)
            score = _record_score(record)
            joint[(va, vb)].append(score)

        # Need enough joint observations
        if all(len(v) < min_samples for v in joint.values()):
            continue

        # Compute marginals
        for dim, marginals in [(dim_a, marginal_a), (dim_b, marginal_b)]:
            grouped_m: dict[Any, list[float]] = defaultdict(list)
            for record in experiment_records:
                grouped_m[record["spec"].get(dim)].append(_record_score(record))
            for val, scores in grouped_m.items():
                marginals[val] = fmean(scores) - overall_mean

        # Check for interactions
        for (va, vb), scores in joint.items():
            if len(scores) < min_samples:
                continue
            joint_effect = fmean(scores) - overall_mean
            expected_additive = marginal_a.get(va, 0.0) + marginal_b.get(vb, 0.0)
            interaction = joint_effect - expected_additive
            if abs(interaction) > effect_threshold * 2:
                action = "prefer" if interaction > 0 else "avoid"
                rules.append(SearchRule(
                    dimension=f"{dim_a}+{dim_b}",
                    action=action,
                    value=(va, vb),
                    confidence=min(1.0, len(scores) / len(experiment_records)),
                    reason=(
                        f"interaction effect {interaction:+.4f} "
                        f"(joint={joint_effect:+.4f}, expected_additive={expected_additive:+.4f})"
                    ),
                ))

    return rules


def narrow_search_space(
    search_space: SearchSpaceConfig,
    rules: list[SearchRule],
    min_values_per_dim: int = 2,
) -> SearchSpaceConfig:
    """Prune search space based on lesson rules.

    - Remove "avoid" values (keeping at least min_values_per_dim per dimension)
    - Constrain "fix" dimensions to the fixed value only
    """
    new_dims: dict[str, list[Any]] = {}

    # Collect avoids and fixes per simple dimension
    avoid_map: dict[str, set[Any]] = defaultdict(set)
    fix_map: dict[str, Any] = {}
    for rule in rules:
        if "+" in str(rule.dimension):
            continue  # Skip interaction rules for narrowing
        if rule.action == "avoid" and rule.confidence >= 0.3:
            avoid_map[rule.dimension].add(rule.value)
        elif rule.action == "fix" and rule.confidence >= 0.4:
            fix_map[rule.dimension] = rule.value

    for dim, values in search_space.dimensions.items():
        if dim in fix_map and fix_map[dim] in values:
            new_dims[dim] = [fix_map[dim]]
        elif dim in avoid_map:
            filtered = [v for v in values if v not in avoid_map[dim]]
            if len(filtered) >= min_values_per_dim:
                new_dims[dim] = filtered
            else:
                new_dims[dim] = list(values)  # Keep all if pruning too aggressive
        else:
            new_dims[dim] = list(values)

    return SearchSpaceConfig(
        dimensions=new_dims,
        max_challengers_per_step=search_space.max_challengers_per_step,
    )


def build_lesson_feedback(
    rung: int,
    experiment_records: list[dict[str, Any]],
    search_space: SearchSpaceConfig,
) -> LessonFeedback:
    """Build a complete LessonFeedback from experiment data."""
    rules = extract_search_rules(experiment_records, search_space)
    narrowed = narrow_search_space(search_space, rules)

    # Extract best spec fields from top experiment
    best_spec_fields: dict[str, Any] = {}
    if experiment_records:
        best = max(experiment_records, key=_record_score)
        best_spec_fields = dict(best.get("spec", {}))

    return LessonFeedback(
        rung=rung,
        rules=rules,
        narrowed_dimensions=narrowed.dimensions,
        best_spec_fields=best_spec_fields,
    )
