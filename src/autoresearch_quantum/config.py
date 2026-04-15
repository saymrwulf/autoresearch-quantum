from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from .models import (
    CostWeights,
    ExperimentSpec,
    HardwareConfig,
    QualityWeights,
    RungConfig,
    ScoreConfig,
    SearchSpaceConfig,
    TierPolicyConfig,
)


def _quality_weights(data: Mapping[str, Any] | None) -> QualityWeights:
    return QualityWeights(**dict(data or {}))


def _cost_weights(data: Mapping[str, Any] | None) -> CostWeights:
    return CostWeights(**dict(data or {}))


def _score_config(data: Mapping[str, Any] | None) -> ScoreConfig:
    payload = dict(data or {})
    return ScoreConfig(
        name=payload.get("name", "weighted_acceptance_cost"),
        cheap_quality=_quality_weights(payload.get("cheap_quality")),
        expensive_quality=_quality_weights(payload.get("expensive_quality")),
        cost_weights=_cost_weights(payload.get("cost_weights")),
        base_cost=float(payload.get("base_cost", 1.0)),
    )


def _search_space_config(data: Mapping[str, Any] | None) -> SearchSpaceConfig:
    payload = dict(data or {})
    return SearchSpaceConfig(
        dimensions=dict(payload.get("dimensions", {})),
        max_challengers_per_step=int(payload.get("max_challengers_per_step", 8)),
    )


def _tier_policy_config(data: Mapping[str, Any] | None) -> TierPolicyConfig:
    return TierPolicyConfig(**dict(data or {}))


def _hardware_config(data: Mapping[str, Any] | None) -> HardwareConfig:
    return HardwareConfig(**dict(data or {}))


def _experiment_spec(rung: int, data: Mapping[str, Any]) -> ExperimentSpec:
    payload = dict(data)
    payload["rung"] = rung
    if "initial_layout" in payload and payload["initial_layout"] is not None:
        payload["initial_layout"] = tuple(payload["initial_layout"])
    return ExperimentSpec(**payload)


def load_rung_config(path: str | Path) -> RungConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)

    rung = int(payload["rung"])
    return RungConfig(
        rung=rung,
        name=str(payload["name"]),
        description=str(payload["description"]),
        objective=str(payload["objective"]),
        bootstrap_incumbent=_experiment_spec(rung, payload["bootstrap_incumbent"]),
        search_space=_search_space_config(payload.get("search_space")),
        tier_policy=_tier_policy_config(payload.get("tier_policy")),
        score=_score_config(payload.get("score")),
        step_budget=int(payload.get("step_budget", 3)),
        patience=int(payload.get("patience", 2)),
        hardware=_hardware_config(payload.get("hardware")),
        transfer_backends=list(payload.get("transfer_backends", [])),
    )
