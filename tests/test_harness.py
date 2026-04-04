from __future__ import annotations

from pathlib import Path

from qiskit.quantum_info import Statevector

from autoresearch_quantum.codes.four_two_two import STABILIZERS, encoded_magic_statevector
from autoresearch_quantum.experiments.encoded_magic_state import build_circuit_bundle
from autoresearch_quantum.execution.local import LocalCheapExecutor
from autoresearch_quantum.execution.transfer import TransferEvaluator
from autoresearch_quantum.lessons.feedback import (
    build_lesson_feedback,
    extract_search_rules,
    narrow_search_space,
)
from autoresearch_quantum.models import (
    CostWeights,
    ExperimentSpec,
    FactoryMetrics,
    HardwareConfig,
    LessonFeedback,
    QualityWeights,
    RungConfig,
    RungProgress,
    ScoreConfig,
    SearchRule,
    SearchSpaceConfig,
    TierPolicyConfig,
    TransferReport,
)
from autoresearch_quantum.persistence.store import ResearchStore
from autoresearch_quantum.ratchet.runner import AutoresearchHarness
from autoresearch_quantum.scoring.score import factory_throughput_score, score_metrics
from autoresearch_quantum.search.challengers import generate_neighbor_challengers
from autoresearch_quantum.search.strategies import (
    CompositeGenerator,
    LessonGuided,
    NeighborWalk,
    RandomCombo,
    StrategyWeight,
    default_composite,
)


def _test_rung(search_dimensions: dict[str, list[object]] | None = None) -> RungConfig:
    spec = ExperimentSpec(
        rung=1,
        target_backend="fake_brisbane",
        noise_backend="fake_brisbane",
        shots=64,
        repeats=1,
    )
    return RungConfig(
        rung=1,
        name="test",
        description="test rung",
        objective="test objective",
        bootstrap_incumbent=spec,
        search_space=SearchSpaceConfig(
            dimensions=search_dimensions or {"verification": ["both", "z_only"]},
            max_challengers_per_step=4,
        ),
        tier_policy=TierPolicyConfig(
            cheap_margin=0.0,
            confirmation_margin=0.0,
            cheap_shots=64,
            expensive_shots=128,
            cheap_repeats=1,
            expensive_repeats=1,
            promote_top_k=1,
            enable_hardware=False,
            confirm_incumbent_on_hardware=False,
            hardware_budget=0,
        ),
        score=ScoreConfig(
            cheap_quality=QualityWeights(
                ideal_fidelity=0.2,
                noisy_fidelity=0.3,
                logical_witness=0.3,
                codespace_rate=0.1,
                stability_score=0.05,
                spectator_alignment=0.05,
            ),
            expensive_quality=QualityWeights(
                logical_witness=0.6,
                codespace_rate=0.2,
                stability_score=0.1,
                spectator_alignment=0.1,
            ),
            cost_weights=CostWeights(
                two_qubit_count=0.05,
                depth=0.01,
                shot_count=0.0001,
                runtime_estimate=0.01,
                queue_cost_proxy=0.0,
            ),
        ),
        step_budget=1,
        patience=1,
        hardware=HardwareConfig(),
    )


# ── Original tests ──────────────────────────────────────────────────────────

def test_encoded_target_state_satisfies_stabilizers() -> None:
    state = encoded_magic_statevector()
    assert isinstance(state, Statevector)
    for stabilizer in STABILIZERS.values():
        expectation = state.expectation_value(stabilizer)
        assert abs(expectation - 1.0) < 1e-8


def test_circuit_bundle_contains_expected_contexts() -> None:
    bundle = build_circuit_bundle(ExperimentSpec(rung=1))
    assert set(bundle.witness_circuits) == {"logical_x", "logical_y", "spectator_z"}
    for name, circuit in bundle.witness_circuits.items():
        assert circuit.metadata["context"] == name
        assert "logical_operator" in circuit.metadata
    assert bundle.acceptance.metadata["context"] == "acceptance"


def test_local_executor_produces_score() -> None:
    rung = _test_rung()
    result = LocalCheapExecutor().evaluate(rung.bootstrap_incumbent, rung)
    assert result.score > 0.0
    assert 0.0 <= result.metrics.acceptance_rate <= 1.0
    assert 0.0 <= (result.metrics.logical_magic_witness or 0.0) <= 1.0


def test_neighbor_challengers_mutate_single_dimension() -> None:
    incumbent = ExperimentSpec(rung=1)
    search_space = SearchSpaceConfig(
        dimensions={
            "verification": ["both", "z_only"],
            "seed_style": ["h_p", "ry_rz"],
        },
        max_challengers_per_step=8,
    )
    challengers = generate_neighbor_challengers(incumbent, search_space)
    assert len(challengers) == 2
    for challenger in challengers:
        changed_fields = [
            field_name
            for field_name in incumbent.__dataclass_fields__
            if getattr(incumbent, field_name) != getattr(challenger.spec, field_name)
        ]
        assert len(changed_fields) == 1


def test_ratchet_step_persists_incumbent_and_step(tmp_path: Path) -> None:
    rung = _test_rung({"verification": ["both", "z_only"], "postselection": ["all_measured", "z_only"]})
    harness = AutoresearchHarness(ResearchStore(tmp_path))
    step = harness.run_ratchet_step(rung, allow_hardware=False)
    assert step.step_index == 1
    assert (tmp_path / "rung_1" / "incumbent.json").exists()
    assert list((tmp_path / "rung_1" / "ratchet_steps").glob("*.json"))


# ── New tests: challenger strategies ────────────────────────────────────────

def test_neighbor_walk_respects_history() -> None:
    incumbent = ExperimentSpec(rung=1)
    search_space = SearchSpaceConfig(
        dimensions={"verification": ["both", "z_only"], "seed_style": ["h_p", "ry_rz"]},
        max_challengers_per_step=8,
    )
    # First pass: get all challengers
    all_challengers = generate_neighbor_challengers(incumbent, search_space)
    fps = {c.spec.fingerprint() for c in all_challengers}
    # Second pass with history: should get nothing new
    new_challengers = generate_neighbor_challengers(incumbent, search_space, history=fps)
    assert len(new_challengers) == 0


def test_random_combo_generates_multi_axis_mutations() -> None:
    incumbent = ExperimentSpec(rung=1)
    search_space = SearchSpaceConfig(
        dimensions={
            "verification": ["both", "z_only", "x_only"],
            "seed_style": ["h_p", "ry_rz", "u_magic"],
            "optimization_level": [1, 2, 3],
        },
        max_challengers_per_step=10,
    )
    strategy = RandomCombo(num_candidates=10, max_mutations=3)
    challengers = strategy.generate(incumbent, search_space, set())
    assert len(challengers) > 0
    # At least one challenger should mutate multiple dimensions
    multi_axis = [
        c for c in challengers
        if sum(
            1 for f in incumbent.__dataclass_fields__
            if getattr(incumbent, f) != getattr(c.spec, f)
        ) > 1
    ]
    # Probabilistic, but with 10 candidates and 3 dims it's extremely likely
    assert len(multi_axis) > 0


def test_lesson_guided_uses_rules() -> None:
    incumbent = ExperimentSpec(rung=1)
    search_space = SearchSpaceConfig(
        dimensions={
            "verification": ["both", "z_only", "x_only"],
            "seed_style": ["h_p", "ry_rz", "u_magic"],
        },
        max_challengers_per_step=8,
    )
    feedback = LessonFeedback(
        rung=1,
        rules=[
            SearchRule("verification", "prefer", "z_only", 0.8, "top performer"),
            SearchRule("seed_style", "avoid", "h_p", 0.6, "consistently poor"),
            SearchRule("seed_style", "fix", "ry_rz", 0.9, "all top-K use this"),
        ],
        narrowed_dimensions={},
        best_spec_fields={},
    )
    strategy = LessonGuided(num_candidates=6)
    challengers = strategy.generate(incumbent, search_space, set(), [feedback])
    assert len(challengers) > 0
    # All challengers should have seed_style fixed to ry_rz (from fix rule)
    for c in challengers:
        assert c.spec.seed_style == "ry_rz"


def test_composite_generator_combines_strategies() -> None:
    incumbent = ExperimentSpec(rung=1)
    search_space = SearchSpaceConfig(
        dimensions={
            "verification": ["both", "z_only", "x_only"],
            "seed_style": ["h_p", "ry_rz", "u_magic"],
            "optimization_level": [1, 2, 3],
        },
        max_challengers_per_step=8,
    )
    composite = default_composite(has_lessons=False)
    challengers = composite.generate(incumbent, search_space, set())
    assert len(challengers) > 0
    assert len(challengers) <= 8


# ── New tests: lesson feedback ─────��────────────────────────────────────────

def test_extract_search_rules_prefer_and_avoid() -> None:
    search_space = SearchSpaceConfig(
        dimensions={"verification": ["both", "z_only"]},
        max_challengers_per_step=4,
    )
    records = [
        {"spec": {"verification": "z_only"}, "final_score": 0.8},
        {"spec": {"verification": "z_only"}, "final_score": 0.85},
        {"spec": {"verification": "z_only"}, "final_score": 0.82},
        {"spec": {"verification": "both"}, "final_score": 0.5},
        {"spec": {"verification": "both"}, "final_score": 0.55},
        {"spec": {"verification": "both"}, "final_score": 0.52},
    ]
    rules = extract_search_rules(records, search_space)
    actions = {(r.dimension, r.action, r.value) for r in rules}
    assert ("verification", "prefer", "z_only") in actions
    assert ("verification", "avoid", "both") in actions


def test_narrow_search_space_removes_avoided() -> None:
    search_space = SearchSpaceConfig(
        dimensions={
            "verification": ["both", "z_only", "x_only"],
            "seed_style": ["h_p", "ry_rz", "u_magic"],
        },
        max_challengers_per_step=8,
    )
    rules = [
        SearchRule("verification", "avoid", "x_only", 0.5, "poor"),
        SearchRule("seed_style", "fix", "ry_rz", 0.6, "best"),
    ]
    narrowed = narrow_search_space(search_space, rules)
    assert "x_only" not in narrowed.dimensions["verification"]
    assert narrowed.dimensions["seed_style"] == ["ry_rz"]


def test_build_lesson_feedback_end_to_end() -> None:
    search_space = SearchSpaceConfig(
        dimensions={"verification": ["both", "z_only"]},
        max_challengers_per_step=4,
    )
    records = [
        {"spec": {"verification": "z_only"}, "final_score": 0.8},
        {"spec": {"verification": "z_only"}, "final_score": 0.85},
        {"spec": {"verification": "both"}, "final_score": 0.5},
        {"spec": {"verification": "both"}, "final_score": 0.55},
    ]
    feedback = build_lesson_feedback(1, records, search_space)
    assert feedback.rung == 1
    assert len(feedback.rules) > 0
    assert feedback.best_spec_fields["verification"] == "z_only"


# ── New tests: factory score ────────────────────────────────────────────────

def test_factory_throughput_score_produces_metrics() -> None:
    from autoresearch_quantum.models import EvaluationMetrics
    metrics = EvaluationMetrics(
        ideal_encoded_fidelity=0.95,
        noisy_encoded_fidelity=0.85,
        logical_magic_witness=0.80,
        acceptance_rate=0.70,
        codespace_rate=0.65,
        stability_score=0.90,
        two_qubit_count=30,
        depth=50,
        shot_count=1024,
    )
    config = ScoreConfig(
        name="factory_throughput",
        cheap_quality=QualityWeights(
            noisy_fidelity=0.3,
            logical_witness=0.4,
            codespace_rate=0.2,
            stability_score=0.1,
        ),
    )
    score, quality, cost = factory_throughput_score(metrics, "cheap", config)
    assert score > 0.0
    assert quality > 0.0
    assert cost > 0.0
    assert "factory_metrics" in metrics.extra
    fm = metrics.extra["factory_metrics"]
    assert fm["accepted_states_per_shot"] == 0.70
    assert fm["throughput_proxy"] > 0.0


def test_score_registry_has_factory() -> None:
    from autoresearch_quantum.scoring.score import SCORE_REGISTRY
    assert "factory_throughput" in SCORE_REGISTRY


# ── New tests: transfer evaluation ──────────────���───────────────────────────

def test_transfer_evaluator_runs_across_backends() -> None:
    rung = _test_rung()
    evaluator = TransferEvaluator()
    report = evaluator.evaluate_across_backends(
        rung.bootstrap_incumbent,
        ["fake_brisbane"],  # Use single backend for speed
        rung,
    )
    assert isinstance(report, TransferReport)
    assert report.transfer_score > 0.0
    assert "fake_brisbane" in report.per_backend_scores


# ── New tests: persistence (progress, feedback) ───��────────────────────────

def test_save_and_load_progress(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path)
    progress = RungProgress(
        rung=1,
        steps_completed=2,
        patience_remaining=1,
        current_incumbent_id="r1-incumbent-abc123",
        completed=False,
    )
    store.save_progress(progress)
    loaded = store.load_progress(1)
    assert loaded is not None
    assert loaded.steps_completed == 2
    assert loaded.current_incumbent_id == "r1-incumbent-abc123"
    assert not loaded.completed


def test_save_and_load_lesson_feedback(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path)
    feedback = LessonFeedback(
        rung=1,
        rules=[SearchRule("verification", "prefer", "z_only", 0.8, "good")],
        narrowed_dimensions={"verification": ["z_only"]},
        best_spec_fields={"verification": "z_only"},
    )
    store.save_lesson_feedback(feedback)
    loaded = store.load_lesson_feedback(1)
    assert loaded is not None
    assert len(loaded.rules) == 1
    assert loaded.rules[0].dimension == "verification"
    assert loaded.rules[0].action == "prefer"


# ── New tests: resumability in harness ──────────────────────────────────────

def test_run_rung_saves_progress(tmp_path: Path) -> None:
    rung = _test_rung({"verification": ["both", "z_only"]})
    store = ResearchStore(tmp_path)
    harness = AutoresearchHarness(store)
    steps, lesson, feedback = harness.run_rung(rung, allow_hardware=False)
    assert len(steps) >= 1
    progress = store.load_progress(1)
    assert progress is not None
    assert progress.completed


def test_run_rung_returns_lesson_and_feedback(tmp_path: Path) -> None:
    rung = _test_rung({"verification": ["both", "z_only"]})
    harness = AutoresearchHarness(ResearchStore(tmp_path))
    steps, lesson, feedback = harness.run_rung(rung, allow_hardware=False)
    assert lesson.rung == 1
    assert isinstance(feedback, LessonFeedback)
    assert feedback.rung == 1


# ── New tests: cross-rung propagation ──────��────────────────────────────────

def test_run_ratchet_propagates_winner(tmp_path: Path) -> None:
    rung1 = _test_rung({"verification": ["both", "z_only"]})
    rung2_spec = ExperimentSpec(
        rung=2,
        target_backend="fake_brisbane",
        noise_backend="fake_brisbane",
        shots=64,
        repeats=1,
    )
    rung2 = RungConfig(
        rung=2,
        name="test rung 2",
        description="test rung 2",
        objective="test objective 2",
        bootstrap_incumbent=rung2_spec,
        search_space=SearchSpaceConfig(
            dimensions={"verification": ["both", "z_only"]},
            max_challengers_per_step=2,
        ),
        tier_policy=rung1.tier_policy,
        score=rung1.score,
        step_budget=1,
        patience=1,
        hardware=HardwareConfig(),
    )

    store = ResearchStore(tmp_path)
    harness = AutoresearchHarness(store)
    results = harness.run_ratchet([rung1, rung2], allow_hardware=False)
    assert len(results) == 2
    # Both should have lesson + feedback
    for lesson, feedback in results:
        assert lesson is not None
        assert isinstance(feedback, LessonFeedback)
    # Accumulated lessons should have entries from both rungs
    assert len(harness._accumulated_lessons) == 2


# ── New tests: seed determinism fix ─────────────────────────────────────────

def test_different_specs_get_different_seeds() -> None:
    """Two specs with different fingerprints should produce different seeds."""
    import hashlib
    spec_a = ExperimentSpec(rung=1, verification="both")
    spec_b = ExperimentSpec(rung=1, verification="z_only")
    seed_a = int(hashlib.sha256(f"{spec_a.fingerprint()}-0".encode()).hexdigest()[:8], 16)
    seed_b = int(hashlib.sha256(f"{spec_b.fingerprint()}-0".encode()).hexdigest()[:8], 16)
    assert seed_a != seed_b
