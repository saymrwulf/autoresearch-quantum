"""Tests for lessons.feedback — interaction detection, narrowing edge cases."""
from __future__ import annotations

from autoresearch_quantum.lessons.feedback import (
    build_lesson_feedback,
    extract_search_rules,
    narrow_search_space,
)
from autoresearch_quantum.models import SearchRule, SearchSpaceConfig


def test_interaction_detection() -> None:
    """Two dimensions that interact should produce an interaction rule."""
    search_space = SearchSpaceConfig(
        dimensions={
            "seed_style": ["h_p", "ry_rz"],
            "verification": ["both", "z_only"],
        },
        max_challengers_per_step=4,
    )
    # Construct data where (h_p, both) is much better than expected from marginals
    records = [
        {"spec": {"seed_style": "h_p", "verification": "both"}, "final_score": 0.95},
        {"spec": {"seed_style": "h_p", "verification": "both"}, "final_score": 0.92},
        {"spec": {"seed_style": "h_p", "verification": "z_only"}, "final_score": 0.50},
        {"spec": {"seed_style": "h_p", "verification": "z_only"}, "final_score": 0.48},
        {"spec": {"seed_style": "ry_rz", "verification": "both"}, "final_score": 0.55},
        {"spec": {"seed_style": "ry_rz", "verification": "both"}, "final_score": 0.52},
        {"spec": {"seed_style": "ry_rz", "verification": "z_only"}, "final_score": 0.70},
        {"spec": {"seed_style": "ry_rz", "verification": "z_only"}, "final_score": 0.68},
    ]
    rules = extract_search_rules(records, search_space)
    interaction_rules = [r for r in rules if "+" in str(r.dimension)]
    assert len(interaction_rules) > 0


def test_fix_rule_generated_when_top_k_agree() -> None:
    search_space = SearchSpaceConfig(
        dimensions={"verification": ["both", "z_only", "x_only"]},
        max_challengers_per_step=4,
    )
    records = [
        {"spec": {"verification": "z_only"}, "final_score": 0.90},
        {"spec": {"verification": "z_only"}, "final_score": 0.88},
        {"spec": {"verification": "z_only"}, "final_score": 0.85},
        {"spec": {"verification": "z_only"}, "final_score": 0.83},
        {"spec": {"verification": "both"}, "final_score": 0.40},
        {"spec": {"verification": "both"}, "final_score": 0.42},
        {"spec": {"verification": "x_only"}, "final_score": 0.30},
        {"spec": {"verification": "x_only"}, "final_score": 0.32},
    ]
    rules = extract_search_rules(records, search_space)
    fix_rules = [r for r in rules if r.action == "fix"]
    assert any(r.value == "z_only" for r in fix_rules)


def test_narrow_preserves_min_values() -> None:
    """Narrowing should not reduce a dimension below min_values_per_dim."""
    search_space = SearchSpaceConfig(
        dimensions={"verification": ["both", "z_only"]},
        max_challengers_per_step=4,
    )
    rules = [SearchRule("verification", "avoid", "z_only", 0.5, "test")]
    narrowed = narrow_search_space(search_space, rules, min_values_per_dim=2)
    assert len(narrowed.dimensions["verification"]) == 2  # kept both since pruning would go below 2


def test_narrow_ignores_low_confidence_rules() -> None:
    search_space = SearchSpaceConfig(
        dimensions={"verification": ["both", "z_only", "x_only"]},
        max_challengers_per_step=4,
    )
    rules = [SearchRule("verification", "avoid", "x_only", 0.1, "low confidence")]  # confidence < 0.3
    narrowed = narrow_search_space(search_space, rules)
    assert "x_only" in narrowed.dimensions["verification"]


def test_extract_rules_empty_records() -> None:
    search_space = SearchSpaceConfig(
        dimensions={"verification": ["both", "z_only"]},
        max_challengers_per_step=4,
    )
    rules = extract_search_rules([], search_space)
    assert rules == []


def test_extract_rules_below_min_samples() -> None:
    search_space = SearchSpaceConfig(
        dimensions={"verification": ["both", "z_only"]},
        max_challengers_per_step=4,
    )
    records = [
        {"spec": {"verification": "z_only"}, "final_score": 0.90},
        # Only 1 sample for z_only, below min_samples=2
    ]
    rules = extract_search_rules(records, search_space, min_samples=2)
    single_dim_rules = [r for r in rules if "+" not in str(r.dimension)]
    assert len(single_dim_rules) == 0
