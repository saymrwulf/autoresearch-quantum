"""Tests for scoring module — edge cases and registry."""
from __future__ import annotations

import pytest

from autoresearch_quantum.models import EvaluationMetrics, QualityWeights, ScoreConfig
from autoresearch_quantum.scoring.score import (
    SCORE_REGISTRY,
    score_metrics,
    weighted_acceptance_cost,
)


def test_score_all_zero_weights() -> None:
    metrics = EvaluationMetrics(acceptance_rate=0.5, two_qubit_count=10, depth=20)
    config = ScoreConfig(cheap_quality=QualityWeights())  # all zero weights
    score, quality, cost = weighted_acceptance_cost(metrics, "cheap", config)
    assert quality == 0.0
    assert score == 0.0


def test_score_with_none_metrics() -> None:
    metrics = EvaluationMetrics(acceptance_rate=0.8)
    config = ScoreConfig(
        cheap_quality=QualityWeights(
            ideal_fidelity=1.0,
            noisy_fidelity=1.0,
        ),
    )
    # ideal and noisy are None -> skipped
    score, quality, cost = weighted_acceptance_cost(metrics, "cheap", config)
    assert quality == 0.0


def test_score_expensive_tier_uses_expensive_weights() -> None:
    metrics = EvaluationMetrics(
        logical_magic_witness=0.9,
        acceptance_rate=0.8,
    )
    config = ScoreConfig(
        cheap_quality=QualityWeights(logical_witness=0.0),  # zero weight
        expensive_quality=QualityWeights(logical_witness=1.0),  # full weight
    )
    score_cheap, _, _ = weighted_acceptance_cost(metrics, "cheap", config)
    score_exp, _, _ = weighted_acceptance_cost(metrics, "expensive", config)
    assert score_cheap == 0.0
    assert score_exp > 0.0


def test_unknown_score_function_raises() -> None:
    metrics = EvaluationMetrics()
    config = ScoreConfig(name="nonexistent_scorer")
    with pytest.raises(ValueError, match="Unknown score function"):
        score_metrics(metrics, "cheap", config)
