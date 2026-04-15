"""Learning progress tracker — records every student interaction and measures mastery."""
from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from IPython.display import HTML, display

# Bloom's taxonomy levels, ordered by cognitive demand
BLOOM_LEVELS = ["remember", "understand", "apply", "analyze", "evaluate", "create"]

# Mapping from Bloom level to colour for visual feedback
_BLOOM_COLOURS = {
    "remember": "#6baed6",
    "understand": "#74c476",
    "apply": "#fdae6b",
    "analyze": "#fc9272",
    "evaluate": "#9e9ac8",
    "create": "#e377c2",
}


@dataclass
class Attempt:
    """One student interaction with an assessment item."""
    question_id: str
    bloom_level: str
    section: str
    correct: bool | None  # None for free-response / code challenges
    student_answer: Any
    expected_answer: Any | None
    timestamp: float = field(default_factory=time.time)
    attempt_number: int = 1
    feedback: str = ""


class LearningTracker:
    """Singleton-per-notebook tracker that accumulates attempts and reports mastery.

    Usage in a notebook::

        from autoresearch_quantum.teaching import LearningTracker
        tracker = LearningTracker("plan_a_01")

    Then pass ``tracker`` to every assessment call.
    At the end, call ``tracker.dashboard()`` or ``tracker.save()``.
    """

    def __init__(self, notebook_id: str, save_dir: str | Path | None = None) -> None:
        self.notebook_id = notebook_id
        self.attempts: list[Attempt] = []
        self._save_dir = Path(save_dir) if save_dir else None
        self._section_stack: str = "intro"

    # ── section management ──────────────────────────────────────────────
    def set_section(self, name: str) -> None:
        self._section_stack = name

    @property
    def current_section(self) -> str:
        return self._section_stack

    # ── recording ───────────────────────────────────────────────────────
    def record(
        self,
        question_id: str,
        bloom_level: str,
        correct: bool | None,
        student_answer: Any,
        expected_answer: Any | None = None,
        feedback: str = "",
    ) -> None:
        prior = [a for a in self.attempts if a.question_id == question_id]
        attempt = Attempt(
            question_id=question_id,
            bloom_level=bloom_level,
            section=self.current_section,
            correct=correct,
            student_answer=student_answer,
            expected_answer=expected_answer,
            attempt_number=len(prior) + 1,
            feedback=feedback,
        )
        self.attempts.append(attempt)

    # ── queries ─────────────────────────────────────────────────────────
    def score_by_section(self) -> dict[str, dict[str, Any]]:
        """Returns {section: {correct: n, incorrect: n, total: n, pct: float}}.

        Only the latest attempt per question is counted.
        """
        latest: dict[str, Attempt] = {}
        for a in self.attempts:
            if a.correct is not None:
                latest[a.question_id] = a
        sections: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"correct": 0, "incorrect": 0, "total": 0},
        )
        for a in latest.values():
            s = sections[a.section]
            s["total"] += 1
            if a.correct:
                s["correct"] += 1
            else:
                s["incorrect"] += 1
        for s in sections.values():
            s["pct"] = round(100 * s["correct"] / s["total"], 1) if s["total"] else 0.0
        return dict(sections)

    def score_by_bloom(self) -> dict[str, dict[str, Any]]:
        """Returns {bloom_level: {correct: n, total: n, pct: float}}."""
        latest: dict[str, Attempt] = {}
        for a in self.attempts:
            if a.correct is not None:
                latest[a.question_id] = a
        out: dict[str, dict[str, Any]] = defaultdict(lambda: {"correct": 0, "total": 0})
        for a in latest.values():
            b = out[a.bloom_level]
            b["total"] += 1
            if a.correct:
                b["correct"] += 1
        for b in out.values():
            b["pct"] = round(100 * b["correct"] / b["total"], 1) if b["total"] else 0.0
        return dict(out)

    def struggled_questions(self) -> list[str]:
        """Questions where the student needed >1 attempt or got it wrong."""
        counts: dict[str, int] = defaultdict(int)
        final_correct: dict[str, bool] = {}
        for a in self.attempts:
            if a.correct is not None:
                counts[a.question_id] += 1
                final_correct[a.question_id] = a.correct
        return [qid for qid, n in counts.items() if n > 1 or not final_correct.get(qid, True)]

    def mastery_score(self) -> float:
        """Overall percentage of questions answered correctly (latest attempt)."""
        latest: dict[str, Attempt] = {}
        for a in self.attempts:
            if a.correct is not None:
                latest[a.question_id] = a
        if not latest:
            return 0.0
        correct = sum(1 for a in latest.values() if a.correct)
        return round(100 * correct / len(latest), 1)

    # ── display ─────────────────────────────────────────────────────────
    def dashboard(self) -> None:
        """Render an HTML dashboard summarising progress so far."""
        by_section = self.score_by_section()
        by_bloom = self.score_by_bloom()
        struggled = self.struggled_questions()
        mastery = self.mastery_score()

        html_parts = [
            '<div style="font-family: system-ui, sans-serif; max-width: 700px; '
            'margin: 20px auto; padding: 20px; border: 2px solid #333; border-radius: 12px; '
            'background: #fafafa;">',
            f'<h2 style="margin-top:0;">Learning Dashboard — {self.notebook_id}</h2>',
        ]

        # overall mastery bar
        colour = "#4caf50" if mastery >= 70 else "#ff9800" if mastery >= 40 else "#f44336"
        html_parts.append(
            f'<div style="margin-bottom:16px;">'
            f'<strong>Overall mastery: {mastery}%</strong>'
            f'<div style="background:#ddd; border-radius:8px; height:24px; margin-top:4px;">'
            f'<div style="background:{colour}; width:{mastery}%; height:100%; border-radius:8px; '
            f'transition: width 0.3s;"></div></div></div>'
        )

        # per-section table
        if by_section:
            html_parts.append("<h3>By Section</h3>")
            html_parts.append(
                '<table style="border-collapse:collapse; width:100%;">'
                "<tr><th style='text-align:left; padding:4px 8px; border-bottom:1px solid #ccc;'>Section</th>"
                "<th style='padding:4px 8px; border-bottom:1px solid #ccc;'>Correct</th>"
                "<th style='padding:4px 8px; border-bottom:1px solid #ccc;'>Total</th>"
                "<th style='padding:4px 8px; border-bottom:1px solid #ccc;'>Score</th></tr>"
            )
            for sec, data in by_section.items():
                pct = data["pct"]
                c = "#4caf50" if pct >= 70 else "#ff9800" if pct >= 40 else "#f44336"
                html_parts.append(
                    f"<tr><td style='padding:4px 8px;'>{sec}</td>"
                    f"<td style='padding:4px 8px; text-align:center;'>{data['correct']}</td>"
                    f"<td style='padding:4px 8px; text-align:center;'>{data['total']}</td>"
                    f"<td style='padding:4px 8px; text-align:center; color:{c}; font-weight:bold;'>{pct}%</td></tr>"
                )
            html_parts.append("</table>")

        # per-bloom table
        if by_bloom:
            html_parts.append("<h3>By Cognitive Level (Bloom's Taxonomy)</h3>")
            html_parts.append(
                '<table style="border-collapse:collapse; width:100%;">'
                "<tr><th style='text-align:left; padding:4px 8px; border-bottom:1px solid #ccc;'>Level</th>"
                "<th style='padding:4px 8px; border-bottom:1px solid #ccc;'>Correct</th>"
                "<th style='padding:4px 8px; border-bottom:1px solid #ccc;'>Total</th>"
                "<th style='padding:4px 8px; border-bottom:1px solid #ccc;'>Score</th></tr>"
            )
            for level in BLOOM_LEVELS:
                if level in by_bloom:
                    data = by_bloom[level]
                    pct = data["pct"]
                    bc = _BLOOM_COLOURS.get(level, "#999")
                    html_parts.append(
                        f"<tr><td style='padding:4px 8px;'>"
                        f"<span style='display:inline-block;width:12px;height:12px;background:{bc};"
                        f"border-radius:50%;margin-right:6px;'></span>{level.title()}</td>"
                        f"<td style='padding:4px 8px; text-align:center;'>{data['correct']}</td>"
                        f"<td style='padding:4px 8px; text-align:center;'>{data['total']}</td>"
                        f"<td style='padding:4px 8px; text-align:center; font-weight:bold;'>{pct}%</td></tr>"
                    )
            html_parts.append("</table>")

        # struggled questions
        if struggled:
            html_parts.append("<h3>Needs Review</h3><ul>")
            for qid in struggled:
                html_parts.append(f"<li><code>{qid}</code></li>")
            html_parts.append("</ul>")

        html_parts.append("</div>")
        display(HTML("\n".join(html_parts)))

    # ── persistence ─────────────────────────────────────────────────────
    def save(self, path: str | Path | None = None) -> Path:
        """Save all attempts to a JSON file for later analysis."""
        if path is None:
            if self._save_dir:
                self._save_dir.mkdir(parents=True, exist_ok=True)
                path = self._save_dir / f"{self.notebook_id}_progress.json"
            else:
                path = Path(f"{self.notebook_id}_progress.json")
        else:
            path = Path(path)

        data = {
            "notebook_id": self.notebook_id,
            "mastery_score": self.mastery_score(),
            "total_questions": len({a.question_id for a in self.attempts if a.correct is not None}),
            "total_attempts": len(self.attempts),
            "by_section": self.score_by_section(),
            "by_bloom": self.score_by_bloom(),
            "struggled": self.struggled_questions(),
            "attempts": [
                {
                    "question_id": a.question_id,
                    "bloom_level": a.bloom_level,
                    "section": a.section,
                    "correct": a.correct,
                    "student_answer": str(a.student_answer),
                    "expected_answer": str(a.expected_answer),
                    "attempt_number": a.attempt_number,
                    "timestamp": a.timestamp,
                }
                for a in self.attempts
            ],
        }
        path.write_text(json.dumps(data, indent=2))
        return path
