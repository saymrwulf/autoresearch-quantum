"""Tests for persistence.store — edge cases and round-trip serialization."""
from __future__ import annotations

from pathlib import Path

from autoresearch_quantum.models import (
    EvaluationMetrics,
    ExperimentRecord,
    ExperimentSpec,
    RatchetStepRecord,
    RungLesson,
    TierResult,
)
from autoresearch_quantum.persistence.store import ResearchStore


def _make_record(experiment_id: str = "r1-test-abc", score: float = 0.5) -> ExperimentRecord:
    return ExperimentRecord(
        experiment_id=experiment_id,
        rung=1,
        role="challenger",
        parent_incumbent_id=None,
        mutation_note="test",
        spec=ExperimentSpec(rung=1),
        cheap_result=TierResult(
            tier="cheap",
            score=score,
            quality_estimate=0.5,
            metrics=EvaluationMetrics(),
        ),
        final_score=score,
    )


def test_save_and_load_experiment(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path)
    record = _make_record()
    store.save_experiment(record)
    loaded = store.load_experiment(1, "r1-test-abc")
    assert loaded["experiment_id"] == "r1-test-abc"
    assert loaded["final_score"] == 0.5


def test_list_experiments_sorted(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path)
    store.save_experiment(_make_record("r1-a-111", 0.3))
    store.save_experiment(_make_record("r1-b-222", 0.7))
    experiments = store.list_experiments(1)
    assert len(experiments) == 2


def test_save_and_load_ratchet_step(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path)
    step = RatchetStepRecord(
        step_index=1,
        rung=1,
        incumbent_before_id="r1-inc",
        challengers_tested=["r1-c1", "r1-c2"],
        promoted_challengers=[],
        winner_id="r1-inc",
        winning_margin=0.0,
        cheap_tier_justification="none promoted",
        expensive_tier_result="disabled",
        distilled_lesson="no change",
    )
    store.save_ratchet_step(step)
    steps = store.list_ratchet_steps(1)
    assert len(steps) == 1
    assert steps[0]["step_index"] == 1


def test_set_and_load_incumbent(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path)
    assert store.load_incumbent_id(1) is None
    store.set_incumbent(1, "r1-inc-xyz")
    assert store.load_incumbent_id(1) == "r1-inc-xyz"


def test_save_lesson_writes_markdown(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path)
    lesson = RungLesson(
        rung=1,
        name="test",
        objective="test obj",
        what_helped=["a"],
        what_hurt=["b"],
        what_seems_invariant=["c"],
        what_seems_hardware_specific=["d"],
        what_should_be_tested_next=["e"],
        what_should_be_promoted_to_next_rung=["f"],
        what_should_be_discarded=["g"],
        narrative="# Test narrative",
    )
    store.save_lesson(lesson)
    md_path = store.rung_dir(1) / "lesson.md"
    assert md_path.exists()
    assert md_path.read_text() == "# Test narrative"


def test_load_propagated_spec_missing(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path)
    assert store.load_propagated_spec(99) is None


def test_save_and_load_propagated_spec(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path)
    spec = ExperimentSpec(rung=2, seed_style="ry_rz")
    store.save_propagated_spec(2, spec)
    loaded = store.load_propagated_spec(2)
    assert loaded is not None
    assert loaded["seed_style"] == "ry_rz"
