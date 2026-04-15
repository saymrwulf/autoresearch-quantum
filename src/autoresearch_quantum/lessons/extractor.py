from __future__ import annotations

from collections import defaultdict
from statistics import fmean
from typing import Any

from ..models import LessonFeedback, RungConfig, RungLesson
from .feedback import build_lesson_feedback


def _record_score(record: dict[str, Any]) -> float:
    return float(record.get("final_score", 0.0))


def extract_rung_lesson(
    rung_config: RungConfig,
    experiment_records: list[dict[str, Any]],
    ratchet_steps: list[dict[str, Any]],
) -> tuple[RungLesson, LessonFeedback]:
    if not experiment_records:
        empty = "No experiments were recorded for this rung."
        empty_lesson = RungLesson(
            rung=rung_config.rung,
            name=rung_config.name,
            objective=rung_config.objective,
            what_helped=[empty],
            what_hurt=[empty],
            what_seems_invariant=[empty],
            what_seems_hardware_specific=[empty],
            what_should_be_tested_next=[empty],
            what_should_be_promoted_to_next_rung=[empty],
            what_should_be_discarded=[empty],
            narrative=empty,
        )
        empty_feedback = LessonFeedback(
            rung=rung_config.rung,
            rules=[],
            narrowed_dimensions={},
            best_spec_fields={},
        )
        return empty_lesson, empty_feedback

    overall_mean = fmean(_record_score(record) for record in experiment_records)
    top_records = sorted(experiment_records, key=_record_score, reverse=True)[: min(3, len(experiment_records))]

    value_effects: list[tuple[float, str, Any, int]] = []
    hardware_deltas: list[tuple[float, str, Any]] = []
    for dimension in rung_config.search_space.dimensions:
        grouped: dict[Any, list[dict[str, Any]]] = defaultdict(list)
        for record in experiment_records:
            grouped[record["spec"][dimension]].append(record)
        for value, records in grouped.items():
            mean_score = fmean(_record_score(record) for record in records)
            value_effects.append((mean_score - overall_mean, dimension, value, len(records)))

            hardware_scores = [
                float(record["expensive_result"]["score"]) - float(record["cheap_result"]["score"])
                for record in records
                if record.get("expensive_result")
            ]
            if hardware_scores:
                hardware_deltas.append((fmean(hardware_scores), dimension, value))

    helped = [
        f"{dimension}={value} improved mean score by {delta:+.4f} over {samples} runs."
        for delta, dimension, value, samples in sorted(value_effects, reverse=True)[:3]
    ]
    hurt = [
        f"{dimension}={value} hurt mean score by {delta:+.4f} over {samples} runs."
        for delta, dimension, value, samples in sorted(value_effects)[:3]
    ]

    invariants: list[str] = []
    for dimension in rung_config.search_space.dimensions:
        top_values = {record["spec"][dimension] for record in top_records}
        if len(top_values) == 1:
            value = next(iter(top_values))
            invariants.append(f"Top-ranked experiments consistently kept {dimension}={value}.")

    hardware_specific = [
        f"{dimension}={value} shifted hardware score by {delta:+.4f} relative to cheap-tier screening."
        for delta, dimension, value in sorted(hardware_deltas, key=lambda item: abs(item[0]), reverse=True)[:3]
    ] or ["No hardware-specific divergence was observed in this rung."]

    explored_values = {
        dimension: {record["spec"][dimension] for record in experiment_records}
        for dimension in rung_config.search_space.dimensions
    }
    should_test_next = []
    for dimension, values in rung_config.search_space.dimensions.items():
        remaining = [value for value in values if value not in explored_values[dimension]]
        if remaining:
            should_test_next.append(f"Probe remaining {dimension} values: {remaining}.")
    if not should_test_next:
        should_test_next.append(
            "Lift the best settings into a new experiment family or backend target for transfer testing."
        )

    step_lessons = [step["distilled_lesson"] for step in ratchet_steps[-3:] if step.get("distilled_lesson")]
    promoted = step_lessons or ["Carry forward the best incumbent settings as priors for the next rung."]
    discarded = [
        entry
        for entry in hurt
        if "over 1 runs" not in entry
    ] or ["No setting is discarded yet; collect more evidence before pruning."]

    narrative_lines = [
        f"# Rung {rung_config.rung}: {rung_config.name}",
        "",
        f"Objective: {rung_config.objective}",
        "",
        "## What Helped",
        *[f"- {item}" for item in helped],
        "",
        "## What Hurt",
        *[f"- {item}" for item in hurt],
        "",
        "## Invariants",
        *[f"- {item}" for item in invariants or ['No invariant emerged strongly enough yet.']],
        "",
        "## Hardware-Specific Effects",
        *[f"- {item}" for item in hardware_specific],
        "",
        "## Next Tests",
        *[f"- {item}" for item in should_test_next],
        "",
        "## Promote Forward",
        *[f"- {item}" for item in promoted],
        "",
        "## Discard",
        *[f"- {item}" for item in discarded],
    ]

    lesson = RungLesson(
        rung=rung_config.rung,
        name=rung_config.name,
        objective=rung_config.objective,
        what_helped=helped,
        what_hurt=hurt,
        what_seems_invariant=invariants or ["No invariant emerged strongly enough yet."],
        what_seems_hardware_specific=hardware_specific,
        what_should_be_tested_next=should_test_next,
        what_should_be_promoted_to_next_rung=promoted,
        what_should_be_discarded=discarded,
        narrative="\n".join(narrative_lines),
    )
    feedback = build_lesson_feedback(
        rung_config.rung,
        experiment_records,
        rung_config.search_space,
    )
    return lesson, feedback
