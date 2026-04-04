from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..models import (
    ExperimentRecord,
    ExperimentSpec,
    LessonFeedback,
    RatchetStepRecord,
    RungLesson,
    RungProgress,
    SearchRule,
)


class ResearchStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def rung_dir(self, rung: int) -> Path:
        path = self.root / f"rung_{rung}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def experiment_dir(self, rung: int) -> Path:
        path = self.rung_dir(rung) / "experiments"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def ratchet_dir(self, rung: int) -> Path:
        path = self.rung_dir(rung) / "ratchet_steps"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def save_experiment(self, record: ExperimentRecord) -> Path:
        path = self.experiment_dir(record.rung) / f"{record.experiment_id}.json"
        self._write_json(path, asdict(record))
        return path

    def load_experiment(self, rung: int, experiment_id: str) -> dict[str, Any]:
        path = self.experiment_dir(rung) / f"{experiment_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def list_experiments(self, rung: int) -> list[dict[str, Any]]:
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(self.experiment_dir(rung).glob("*.json"))
        ]

    def save_ratchet_step(self, step: RatchetStepRecord) -> Path:
        path = self.ratchet_dir(step.rung) / f"step_{step.step_index:04d}.json"
        self._write_json(path, asdict(step))
        return path

    def list_ratchet_steps(self, rung: int) -> list[dict[str, Any]]:
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(self.ratchet_dir(rung).glob("*.json"))
        ]

    def set_incumbent(self, rung: int, experiment_id: str) -> Path:
        path = self.rung_dir(rung) / "incumbent.json"
        self._write_json(path, {"experiment_id": experiment_id})
        return path

    def load_incumbent_id(self, rung: int) -> str | None:
        path = self.rung_dir(rung) / "incumbent.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return str(payload["experiment_id"])

    def save_lesson(self, lesson: RungLesson) -> Path:
        json_path = self.rung_dir(lesson.rung) / "lesson.json"
        md_path = self.rung_dir(lesson.rung) / "lesson.md"
        self._write_json(json_path, asdict(lesson))
        md_path.write_text(lesson.narrative, encoding="utf-8")
        return json_path

    def save_lesson_feedback(self, feedback: LessonFeedback) -> Path:
        path = self.rung_dir(feedback.rung) / "lesson_feedback.json"
        payload = {
            "rung": feedback.rung,
            "rules": [asdict(r) for r in feedback.rules],
            "narrowed_dimensions": feedback.narrowed_dimensions,
            "best_spec_fields": feedback.best_spec_fields,
            "transfer_scores": feedback.transfer_scores,
        }
        self._write_json(path, payload)
        return path

    def load_lesson_feedback(self, rung: int) -> LessonFeedback | None:
        path = self.rung_dir(rung) / "lesson_feedback.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        rules = [SearchRule(**r) for r in data.get("rules", [])]
        return LessonFeedback(
            rung=data["rung"],
            rules=rules,
            narrowed_dimensions=data.get("narrowed_dimensions", {}),
            best_spec_fields=data.get("best_spec_fields", {}),
            transfer_scores=data.get("transfer_scores", {}),
        )

    def save_progress(self, progress: RungProgress) -> Path:
        path = self.rung_dir(progress.rung) / "progress.json"
        self._write_json(path, asdict(progress))
        return path

    def load_progress(self, rung: int) -> RungProgress | None:
        path = self.rung_dir(rung) / "progress.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return RungProgress(**data)

    def save_propagated_spec(self, rung: int, spec: ExperimentSpec) -> Path:
        path = self.rung_dir(rung) / "propagated_spec.json"
        self._write_json(path, asdict(spec))
        return path

    def load_propagated_spec(self, rung: int) -> dict[str, Any] | None:
        path = self.rung_dir(rung) / "propagated_spec.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
