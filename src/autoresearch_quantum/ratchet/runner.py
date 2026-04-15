from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any

from ..execution.local import LocalCheapExecutor
from ..lessons.extractor import extract_rung_lesson
from ..models import (
    EvaluationMetrics,
    ExperimentRecord,
    ExperimentSpec,
    LessonFeedback,
    RatchetStepRecord,
    RungConfig,
    RungProgress,
    TierResult,
    generate_experiment_id,
)
from ..persistence.store import ResearchStore
from ..search.challengers import mutation_summary
from ..search.strategies import CompositeGenerator, default_composite

logger = logging.getLogger(__name__)


def _from_dict_spec(payload: dict[str, Any]) -> ExperimentSpec:
    if payload.get("initial_layout") is not None:
        payload = dict(payload)
        payload["initial_layout"] = tuple(payload["initial_layout"])
    return ExperimentSpec(**payload)


def _record_from_json(payload: dict[str, Any]) -> ExperimentRecord:
    cheap = _tier_result_from_dict(payload["cheap_result"])
    expensive = _tier_result_from_dict(payload["expensive_result"]) if payload.get("expensive_result") else None
    return ExperimentRecord(
        experiment_id=payload["experiment_id"],
        rung=int(payload["rung"]),
        role=payload["role"],
        parent_incumbent_id=payload.get("parent_incumbent_id"),
        mutation_note=payload.get("mutation_note", ""),
        spec=_from_dict_spec(payload["spec"]),
        cheap_result=cheap,
        expensive_result=expensive,
        final_score=float(payload.get("final_score", 0.0)),
        promoted_to_expensive=bool(payload.get("promoted_to_expensive", False)),
        became_incumbent=bool(payload.get("became_incumbent", False)),
        created_at=payload.get("created_at", ""),
    )


def _metrics_from_dict(payload: dict[str, Any]) -> EvaluationMetrics:
    return EvaluationMetrics(**payload)


def _tier_result_from_dict(payload: dict[str, Any]) -> TierResult:
    return TierResult(
        tier=payload["tier"],
        score=float(payload["score"]),
        quality_estimate=float(payload["quality_estimate"]),
        metrics=_metrics_from_dict(payload["metrics"]),
        counts_summary=dict(payload.get("counts_summary", {})),
        notes=list(payload.get("notes", [])),
        created_at=payload.get("created_at", ""),
    )


class AutoresearchHarness:
    def __init__(self, store: ResearchStore) -> None:
        self.store = store
        self.local_executor = LocalCheapExecutor()
        self._hardware_executor: Any = None  # Lazy-loaded
        self._experiment_history: set[str] = set()
        self._accumulated_lessons: list[LessonFeedback] = []

    @property
    def hardware_executor(self) -> Any:
        if self._hardware_executor is None:
            from ..execution.hardware import IBMHardwareExecutor
            self._hardware_executor = IBMHardwareExecutor()
        return self._hardware_executor

    def _build_history(self, rung: int) -> set[str]:
        """Collect fingerprints of all experiments already tried in this rung."""
        experiments = self.store.list_experiments(rung)
        return {
            ExperimentSpec(**{  # type: ignore[arg-type]
                k: tuple(v) if k == "initial_layout" and isinstance(v, list) else v
                for k, v in exp["spec"].items()
            }).fingerprint()
            for exp in experiments
        }

    def _get_challenger_generator(self) -> CompositeGenerator:
        return default_composite(has_lessons=bool(self._accumulated_lessons))

    def _evaluate_record(
        self,
        spec: ExperimentSpec,
        rung_config: RungConfig,
        role: str,
        parent_incumbent_id: str | None,
        mutation_note: str,
        promote_to_hardware: bool = False,
    ) -> ExperimentRecord:
        cheap_result = self.local_executor.evaluate(spec, rung_config)
        record = ExperimentRecord(
            experiment_id=generate_experiment_id(spec, role),
            rung=spec.rung,
            role=role,
            parent_incumbent_id=parent_incumbent_id,
            mutation_note=mutation_note,
            spec=spec,
            cheap_result=cheap_result,
            final_score=cheap_result.score,
        )
        if promote_to_hardware and rung_config.tier_policy.enable_hardware:
            expensive_result = self.hardware_executor.evaluate(spec, rung_config)
            record.expensive_result = expensive_result
            record.promoted_to_expensive = True
            record.final_score = expensive_result.score
        self.store.save_experiment(record)
        self._experiment_history.add(spec.fingerprint())
        return record

    def _load_incumbent(self, rung: int) -> ExperimentRecord | None:
        experiment_id = self.store.load_incumbent_id(rung)
        if experiment_id is None:
            return None
        payload = self.store.load_experiment(rung, experiment_id)
        return _record_from_json(payload)

    def ensure_incumbent(self, rung_config: RungConfig) -> ExperimentRecord:
        incumbent = self._load_incumbent(rung_config.rung)
        if incumbent is not None:
            return incumbent
        incumbent = self._evaluate_record(
            rung_config.bootstrap_incumbent,
            rung_config,
            role="incumbent",
            parent_incumbent_id=None,
            mutation_note="bootstrap incumbent",
            promote_to_hardware=False,
        )
        incumbent.became_incumbent = True
        self.store.save_experiment(incumbent)
        self.store.set_incumbent(rung_config.rung, incumbent.experiment_id)
        return incumbent

    def run_single_experiment(
        self,
        spec: ExperimentSpec,
        rung_config: RungConfig,
        role: str = "challenger",
        parent_incumbent_id: str | None = None,
        mutation_note: str = "direct run",
        promote_to_hardware: bool = False,
    ) -> ExperimentRecord:
        return self._evaluate_record(
            spec,
            rung_config,
            role=role,
            parent_incumbent_id=parent_incumbent_id,
            mutation_note=mutation_note,
            promote_to_hardware=promote_to_hardware,
        )

    def run_challenger_set(self, rung_config: RungConfig) -> list[ExperimentRecord]:
        incumbent = self.ensure_incumbent(rung_config)
        history = self._build_history(rung_config.rung) | self._experiment_history
        generator = self._get_challenger_generator()
        challengers = generator.generate(
            incumbent.spec,
            rung_config.search_space,
            history,
            self._accumulated_lessons,
        )
        records: list[ExperimentRecord] = []
        for challenger in challengers:
            records.append(
                self._evaluate_record(
                    challenger.spec,
                    rung_config,
                    role="challenger",
                    parent_incumbent_id=incumbent.experiment_id,
                    mutation_note=challenger.mutation_note,
                    promote_to_hardware=False,
                )
            )
        return records

    def run_ratchet_step(self, rung_config: RungConfig, allow_hardware: bool = False) -> RatchetStepRecord:
        incumbent = self.ensure_incumbent(rung_config)
        history = self._build_history(rung_config.rung) | self._experiment_history
        generator = self._get_challenger_generator()
        challengers = generator.generate(
            incumbent.spec,
            rung_config.search_space,
            history,
            self._accumulated_lessons,
        )

        challenger_records: list[ExperimentRecord] = []
        for challenger in challengers:
            challenger_records.append(
                self._evaluate_record(
                    challenger.spec,
                    rung_config,
                    role="challenger",
                    parent_incumbent_id=incumbent.experiment_id,
                    mutation_note=challenger.mutation_note,
                    promote_to_hardware=False,
                )
            )

        if not challenger_records:
            logger.info("No new challengers generated (search space exhausted for rung %d)", rung_config.rung)

        incumbent_cheap = incumbent.cheap_result.score
        promoted = [
            record
            for record in sorted(
                challenger_records,
                key=lambda item: item.cheap_result.score,
                reverse=True,
            )
            if record.cheap_result.score > (incumbent_cheap + rung_config.tier_policy.cheap_margin)
        ][: rung_config.tier_policy.promote_top_k]

        expensive_tier_result = "Hardware tier disabled."
        if (
            allow_hardware
            and rung_config.tier_policy.enable_hardware
            and promoted
        ):
            if rung_config.tier_policy.confirm_incumbent_on_hardware and not incumbent.promoted_to_expensive:
                incumbent = self._evaluate_record(
                    incumbent.spec,
                    rung_config,
                    role=incumbent.role,
                    parent_incumbent_id=incumbent.parent_incumbent_id,
                    mutation_note=incumbent.mutation_note,
                    promote_to_hardware=True,
                )
                incumbent.became_incumbent = True
                self.store.save_experiment(incumbent)
                self.store.set_incumbent(rung_config.rung, incumbent.experiment_id)

            promoted = [
                self._evaluate_record(
                    record.spec,
                    rung_config,
                    role=record.role,
                    parent_incumbent_id=record.parent_incumbent_id,
                    mutation_note=record.mutation_note,
                    promote_to_hardware=True,
                )
                for record in promoted[: rung_config.tier_policy.hardware_budget or len(promoted)]
            ]
            expensive_tier_result = (
                f"Promoted {len(promoted)} challengers to hardware confirmation on "
                f"{rung_config.hardware.backend_name or rung_config.bootstrap_incumbent.target_backend}."
            )

        candidates = [incumbent, *promoted] if promoted else [incumbent, *challenger_records]
        winner = max(candidates, key=lambda record: record.final_score)
        winning_margin = winner.final_score - incumbent.final_score
        if winner.experiment_id != incumbent.experiment_id and winning_margin > rung_config.tier_policy.confirmation_margin:
            winner = replace(winner, became_incumbent=True)
            self.store.save_experiment(winner)
            self.store.set_incumbent(rung_config.rung, winner.experiment_id)

        cheap_tier_justification = (
            "Promoted challengers beat the incumbent on cheap-tier score by at least "
            f"{rung_config.tier_policy.cheap_margin:.4f}."
            if promoted
            else "No challenger cleared the cheap-tier promotion margin."
        )
        distilled_lesson = self._distill_lesson(incumbent, winner, promoted)

        step = RatchetStepRecord(
            step_index=len(self.store.list_ratchet_steps(rung_config.rung)) + 1,
            rung=rung_config.rung,
            incumbent_before_id=incumbent.experiment_id,
            challengers_tested=[record.experiment_id for record in challenger_records],
            promoted_challengers=[record.experiment_id for record in promoted],
            winner_id=winner.experiment_id,
            winning_margin=winning_margin,
            cheap_tier_justification=cheap_tier_justification,
            expensive_tier_result=expensive_tier_result,
            distilled_lesson=distilled_lesson,
        )
        self.store.save_ratchet_step(step)
        return step

    def run_rung(
        self,
        rung_config: RungConfig,
        allow_hardware: bool = False,
    ) -> tuple[list[RatchetStepRecord], Any, LessonFeedback]:
        # Check for resumable progress
        progress = self.store.load_progress(rung_config.rung)
        if progress and not progress.completed:
            steps_done = progress.steps_completed
            patience_left = progress.patience_remaining
            baseline_incumbent = progress.current_incumbent_id
            logger.info(
                "Resuming rung %d from step %d (patience=%d)",
                rung_config.rung, steps_done, patience_left,
            )
        else:
            steps_done = 0
            patience_left = rung_config.patience
            baseline_incumbent = self.ensure_incumbent(rung_config).experiment_id

        steps: list[RatchetStepRecord] = []

        for step_idx in range(steps_done, rung_config.step_budget):
            step = self.run_ratchet_step(rung_config, allow_hardware=allow_hardware)
            steps.append(step)

            if step.winner_id == baseline_incumbent:
                patience_left -= 1
            else:
                baseline_incumbent = step.winner_id
                patience_left = rung_config.patience

            # Save progress after each step
            self.store.save_progress(RungProgress(
                rung=rung_config.rung,
                steps_completed=step_idx + 1,
                patience_remaining=patience_left,
                current_incumbent_id=baseline_incumbent,
                completed=False,
            ))

            if patience_left <= 0:
                break

        # Mark rung as completed
        self.store.save_progress(RungProgress(
            rung=rung_config.rung,
            steps_completed=steps_done + len(steps),
            patience_remaining=patience_left,
            current_incumbent_id=baseline_incumbent,
            completed=True,
        ))

        lesson, feedback = extract_rung_lesson(
            rung_config,
            self.store.list_experiments(rung_config.rung),
            self.store.list_ratchet_steps(rung_config.rung),
        )
        self.store.save_lesson(lesson)
        self.store.save_lesson_feedback(feedback)
        self._accumulated_lessons.append(feedback)

        return steps, lesson, feedback

    def run_ratchet(
        self,
        rung_configs: list[RungConfig],
        allow_hardware: bool = False,
    ) -> list[tuple[Any, LessonFeedback]]:
        """Run multiple rungs in sequence, propagating winners and lessons."""
        results: list[tuple[Any, LessonFeedback]] = []
        self._accumulated_lessons = []

        for i, rung_config in enumerate(rung_configs):
            # Propagate winner from previous rung as bootstrap
            if i > 0 and results:
                prev_feedback = results[-1][1]
                if prev_feedback.best_spec_fields:
                    propagated_spec = self._propagate_spec(
                        prev_feedback.best_spec_fields,
                        rung_config,
                    )
                    rung_config = replace(
                        rung_config,
                        bootstrap_incumbent=propagated_spec,
                    )
                    logger.info(
                        "Propagated winner from rung %d -> rung %d bootstrap",
                        rung_configs[i - 1].rung,
                        rung_config.rung,
                    )
                    # Save propagated spec for traceability
                    self.store.save_propagated_spec(rung_config.rung, propagated_spec)

                # Narrow search space based on accumulated lessons
                if prev_feedback.narrowed_dimensions:
                    from ..lessons.feedback import narrow_search_space
                    narrowed = narrow_search_space(
                        rung_config.search_space,
                        [r for fb in self._accumulated_lessons for r in fb.rules],
                    )
                    rung_config = replace(rung_config, search_space=narrowed)

            steps, lesson, feedback = self.run_rung(rung_config, allow_hardware=allow_hardware)
            results.append((lesson, feedback))

        return results

    def _propagate_spec(
        self,
        best_fields: dict[str, Any],
        target_config: RungConfig,
    ) -> ExperimentSpec:
        """Build a new ExperimentSpec for the next rung from previous winner fields."""
        target_spec = target_config.bootstrap_incumbent
        # Only override fields that exist in ExperimentSpec and are in the best_fields
        valid_fields = set(ExperimentSpec.__dataclass_fields__.keys())
        updates: dict[str, Any] = {}
        for key, value in best_fields.items():
            if key in valid_fields and key != "rung":
                updates[key] = value
        # Override rung to match the target
        updates["rung"] = target_config.rung
        return target_spec.with_updates(**updates)

    def _distill_lesson(
        self,
        incumbent: ExperimentRecord,
        winner: ExperimentRecord,
        promoted: list[ExperimentRecord],
    ) -> str:
        if winner.experiment_id == incumbent.experiment_id:
            return (
                "No ratchet this step: the incumbent remained best because challengers failed to "
                f"overcome {incumbent.best_result.metrics.dominant_failure_mode}."
            )

        change_note = mutation_summary(incumbent.spec, winner.spec)
        confirmation = "hardware-confirmed" if winner.promoted_to_expensive else "cheap-tier"
        return (
            f"{change_note} became the new incumbent on {confirmation} score. "
            f"It improved final score by {winner.final_score - incumbent.final_score:+.4f}; "
            f"{len(promoted)} challengers were strong enough to justify promotion."
        )
