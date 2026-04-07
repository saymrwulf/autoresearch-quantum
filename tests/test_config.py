"""Tests for YAML config loading."""
from __future__ import annotations

from pathlib import Path

from autoresearch_quantum.config import load_rung_config
from autoresearch_quantum.models import ExperimentSpec, RungConfig


def test_load_rung1_config() -> None:
    config = load_rung_config(Path("configs/rungs/rung1.yaml"))
    assert isinstance(config, RungConfig)
    assert config.rung == 1
    assert config.name == "[[4,2,2]] Encoded Magic-State Preparation"
    assert config.step_budget == 3
    assert config.patience == 2


def test_rung1_bootstrap_spec() -> None:
    config = load_rung_config(Path("configs/rungs/rung1.yaml"))
    spec = config.bootstrap_incumbent
    assert isinstance(spec, ExperimentSpec)
    assert spec.rung == 1
    assert spec.seed_style == "h_p"
    assert spec.encoder_style == "cx_chain"
    assert spec.target_backend == "fake_brisbane"


def test_rung1_search_space() -> None:
    config = load_rung_config(Path("configs/rungs/rung1.yaml"))
    dims = config.search_space.dimensions
    assert "seed_style" in dims
    assert "encoder_style" in dims
    assert config.search_space.max_challengers_per_step == 8


def test_rung1_score_config() -> None:
    config = load_rung_config(Path("configs/rungs/rung1.yaml"))
    assert config.score.name == "weighted_acceptance_cost"
    assert config.score.cheap_quality.noisy_fidelity == 0.40
    assert config.score.cost_weights.two_qubit_count == 0.08


def test_rung1_tier_policy() -> None:
    config = load_rung_config(Path("configs/rungs/rung1.yaml"))
    assert config.tier_policy.cheap_shots == 512
    assert config.tier_policy.enable_hardware is False
    assert config.tier_policy.promote_top_k == 2


def test_load_all_rungs() -> None:
    """All rung configs should load without error."""
    for i in range(1, 6):
        config_path = Path(f"configs/rungs/rung{i}.yaml")
        if config_path.exists():
            config = load_rung_config(config_path)
            assert config.rung == i
