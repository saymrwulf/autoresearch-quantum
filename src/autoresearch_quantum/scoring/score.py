from __future__ import annotations

from typing import Callable

from ..models import EvaluationMetrics, FactoryMetrics, QualityWeights, ScoreConfig


def _clamp(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, value))


def _quality_components(metrics: EvaluationMetrics, weights: QualityWeights) -> dict[str, float | None]:
    spectator_alignment = None
    if metrics.spectator_logical_z is not None:
        spectator_alignment = (1.0 + metrics.spectator_logical_z) / 2.0
    return {
        "ideal_fidelity": _clamp(metrics.ideal_encoded_fidelity),
        "noisy_fidelity": _clamp(metrics.noisy_encoded_fidelity),
        "logical_witness": _clamp(metrics.logical_magic_witness),
        "codespace_rate": _clamp(metrics.codespace_rate),
        "stability_score": _clamp(metrics.stability_score),
        "spectator_alignment": _clamp(spectator_alignment),
    }


def weighted_acceptance_cost(
    metrics: EvaluationMetrics,
    tier: str,
    config: ScoreConfig,
) -> tuple[float, float, float]:
    weights = config.cheap_quality if tier == "cheap" else config.expensive_quality
    values = _quality_components(metrics, weights)
    weight_map = {
        "ideal_fidelity": weights.ideal_fidelity,
        "noisy_fidelity": weights.noisy_fidelity,
        "logical_witness": weights.logical_witness,
        "codespace_rate": weights.codespace_rate,
        "stability_score": weights.stability_score,
        "spectator_alignment": weights.spectator_alignment,
    }
    weighted_sum = 0.0
    total_weight = 0.0
    for key, weight in weight_map.items():
        value = values[key]
        if weight <= 0 or value is None:
            continue
        weighted_sum += weight * value
        total_weight += weight

    quality = weighted_sum / total_weight if total_weight else 0.0
    cost = (
        config.base_cost
        + (config.cost_weights.two_qubit_count * metrics.two_qubit_count)
        + (config.cost_weights.depth * metrics.depth)
        + (config.cost_weights.shot_count * metrics.shot_count)
        + (config.cost_weights.runtime_estimate * metrics.runtime_estimate)
        + (config.cost_weights.queue_cost_proxy * metrics.queue_cost_proxy)
    )
    metrics.total_cost = cost
    score = (quality * metrics.acceptance_rate) / max(cost, 1e-9)
    return score, quality, cost


def factory_throughput_score(
    metrics: EvaluationMetrics,
    tier: str,
    config: ScoreConfig,
) -> tuple[float, float, float]:
    """Score optimised for accepted magic states per unit cost.

    Computes FactoryMetrics as a side-effect attached to metrics.extra.
    """
    weights = config.cheap_quality if tier == "cheap" else config.expensive_quality
    values = _quality_components(metrics, weights)
    weight_map = {
        "ideal_fidelity": weights.ideal_fidelity,
        "noisy_fidelity": weights.noisy_fidelity,
        "logical_witness": weights.logical_witness,
        "codespace_rate": weights.codespace_rate,
        "stability_score": weights.stability_score,
        "spectator_alignment": weights.spectator_alignment,
    }
    weighted_sum = 0.0
    total_weight = 0.0
    for key, weight in weight_map.items():
        value = values[key]
        if weight <= 0 or value is None:
            continue
        weighted_sum += weight * value
        total_weight += weight

    quality = weighted_sum / total_weight if total_weight else 0.0

    # Cost with heavier penalty
    cost = (
        config.base_cost
        + (config.cost_weights.two_qubit_count * metrics.two_qubit_count * 1.5)
        + (config.cost_weights.depth * metrics.depth * 1.5)
        + (config.cost_weights.shot_count * metrics.shot_count)
        + (config.cost_weights.runtime_estimate * metrics.runtime_estimate)
        + (config.cost_weights.queue_cost_proxy * metrics.queue_cost_proxy)
    )
    metrics.total_cost = cost

    # Factory-specific metrics
    acceptance = metrics.acceptance_rate
    witness = metrics.logical_magic_witness or 0.0
    logical_error = max(0.0, 1.0 - witness)
    accepted_per_shot = acceptance
    accepted_per_cost = acceptance / max(cost, 1e-9)
    cost_per_accepted = cost / max(acceptance, 1e-9)
    quality_yield = quality * acceptance
    throughput_proxy = acceptance * witness / max(cost, 1e-9)

    factory = FactoryMetrics(
        accepted_states_per_shot=accepted_per_shot,
        logical_error_per_accepted=logical_error,
        accepted_per_unit_cost=accepted_per_cost,
        quality_yield=quality_yield,
        cost_per_accepted=cost_per_accepted,
        throughput_proxy=throughput_proxy,
    )
    metrics.extra["factory_metrics"] = {
        "accepted_states_per_shot": factory.accepted_states_per_shot,
        "logical_error_per_accepted": factory.logical_error_per_accepted,
        "accepted_per_unit_cost": factory.accepted_per_unit_cost,
        "quality_yield": factory.quality_yield,
        "cost_per_accepted": factory.cost_per_accepted,
        "throughput_proxy": factory.throughput_proxy,
    }

    # Score = throughput proxy (acceptance * witness / cost)
    score = throughput_proxy
    return score, quality, cost


SCORE_REGISTRY: dict[str, Callable[[EvaluationMetrics, str, ScoreConfig], tuple[float, float, float]]] = {
    "weighted_acceptance_cost": weighted_acceptance_cost,
    "factory_throughput": factory_throughput_score,
}


def score_metrics(metrics: EvaluationMetrics, tier: str, config: ScoreConfig) -> tuple[float, float, float]:
    try:
        score_fn = SCORE_REGISTRY[config.name]
    except KeyError as exc:
        raise ValueError(f"Unknown score function: {config.name}") from exc
    return score_fn(metrics, tier, config)
