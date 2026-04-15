"""Pedagogical structure tests — validates educational quality invariants.

These tests enforce minimum standards for notebook prose, assessment density,
section structure, and learning progression. They catch pedagogical regressions
the same way unit tests catch code regressions.
"""
from __future__ import annotations

import re
from pathlib import Path

import nbformat
import pytest

NOTEBOOK_DIR = Path("notebooks")
CONTENT_NOTEBOOKS = sorted(
    p for p in NOTEBOOK_DIR.rglob("*.ipynb")
    if p.name != "00_START_HERE.ipynb"
)


def _notebook_id(path: Path) -> str:
    return str(path.relative_to(NOTEBOOK_DIR)).replace("/", "__").removesuffix(".ipynb")


def _read_notebook(path: Path) -> nbformat.NotebookNode:
    return nbformat.read(str(path), as_version=4)


def _markdown_cells(nb: nbformat.NotebookNode) -> list[str]:
    return ["".join(c.source) for c in nb.cells if c.cell_type == "markdown"]


def _code_cells(nb: nbformat.NotebookNode) -> list[str]:
    return ["".join(c.source) for c in nb.cells if c.cell_type == "code"]


def _word_count(text: str) -> int:
    """Count words in text, stripping markdown/HTML/LaTeX markup."""
    clean = re.sub(r"<[^>]+>", "", text)       # strip HTML
    clean = re.sub(r"\$[^$]+\$", "MATH", clean)  # replace inline LaTeX
    clean = re.sub(r"\$\$[^$]+\$\$", "MATH", clean)  # block LaTeX
    clean = re.sub(r"[#*_`|>~\-=]", "", clean)  # strip markdown chars
    clean = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", clean)  # links → text
    return len(clean.split())


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(params=CONTENT_NOTEBOOKS, ids=[_notebook_id(p) for p in CONTENT_NOTEBOOKS])
def notebook(request: pytest.FixtureRequest) -> tuple[Path, nbformat.NotebookNode]:
    path = request.param
    return path, _read_notebook(path)


# ── Prose Quality ─────────────────────────────────────────────────────

class TestProseQuality:
    """Every notebook must have sufficient explanatory text."""

    MIN_TOTAL_WORDS = 200  # minimum words across all markdown cells
    MIN_MARKDOWN_RATIO = 0.25  # at least 25% of cells should be markdown

    def test_minimum_word_count(self, notebook: tuple[Path, nbformat.NotebookNode]) -> None:
        """Each notebook has at least MIN_TOTAL_WORDS of prose."""
        path, nb = notebook
        md_cells = _markdown_cells(nb)
        total_words = sum(_word_count(cell) for cell in md_cells)
        assert total_words >= self.MIN_TOTAL_WORDS, (
            f"{path}: only {total_words} words of prose "
            f"(minimum {self.MIN_TOTAL_WORDS})"
        )

    def test_markdown_to_code_ratio(self, notebook: tuple[Path, nbformat.NotebookNode]) -> None:
        """Notebooks are not code-only — sufficient markdown explanation exists."""
        path, nb = notebook
        md_count = len([c for c in nb.cells if c.cell_type == "markdown"])
        total = len(nb.cells)
        if total == 0:
            pytest.skip("empty notebook")
        ratio = md_count / total
        assert ratio >= self.MIN_MARKDOWN_RATIO, (
            f"{path}: markdown ratio {ratio:.0%} "
            f"(minimum {self.MIN_MARKDOWN_RATIO:.0%}, "
            f"{md_count} markdown / {total} total cells)"
        )


# ── Section Structure ─────────────────────────────────────────────────

class TestSectionStructure:
    """Notebooks must have clear sectional organization."""

    def test_has_title_header(self, notebook: tuple[Path, nbformat.NotebookNode]) -> None:
        """First cell is a markdown cell with a level-1 or level-2 heading."""
        path, nb = notebook
        first = nb.cells[0]
        assert first.cell_type == "markdown", (
            f"{path}: first cell is {first.cell_type}, expected markdown header"
        )
        src = "".join(first.source)
        assert re.match(r"^#{1,2}\s", src), (
            f"{path}: first cell doesn't start with # or ## heading"
        )

    def test_has_multiple_sections(self, notebook: tuple[Path, nbformat.NotebookNode]) -> None:
        """Notebook has at least 2 section headers (## or ###)."""
        path, nb = notebook
        md_text = "\n".join(_markdown_cells(nb))
        sections = re.findall(r"^#{2,3}\s", md_text, re.MULTILINE)
        assert len(sections) >= 2, (
            f"{path}: only {len(sections)} section headers found (minimum 2)"
        )


# ── Assessment Density ────────────────────────────────────────────────

ASSESSMENT_PATTERN = re.compile(r"(quiz|predict_choice|reflect|order)\s*\(")


class TestAssessmentDensity:
    """Notebooks must have sufficient interactive assessments."""

    MIN_ASSESSMENTS = 2  # at least 2 assessment calls per notebook

    def test_minimum_assessment_count(self, notebook: tuple[Path, nbformat.NotebookNode]) -> None:
        """Each notebook has at least MIN_ASSESSMENTS interactive assessments."""
        path, nb = notebook
        code = "\n".join(_code_cells(nb))
        # Exclude the LearningTracker import/setup line
        code_no_setup = "\n".join(
            line for line in code.split("\n")
            if "LearningTracker" not in line
        )
        matches = ASSESSMENT_PATTERN.findall(code_no_setup)
        assert len(matches) >= self.MIN_ASSESSMENTS, (
            f"{path}: only {len(matches)} assessments "
            f"(minimum {self.MIN_ASSESSMENTS})"
        )

    def test_assessment_variety(self, notebook: tuple[Path, nbformat.NotebookNode]) -> None:
        """Each notebook uses at least 2 different assessment types."""
        path, nb = notebook
        code = "\n".join(_code_cells(nb))
        code_no_setup = "\n".join(
            line for line in code.split("\n")
            if "LearningTracker" not in line
        )
        types_found = set(ASSESSMENT_PATTERN.findall(code_no_setup))
        assert len(types_found) >= 2, (
            f"{path}: only {len(types_found)} assessment type(s) "
            f"({types_found}), minimum 2 for variety"
        )


# ── Bloom's Taxonomy Coverage ─────────────────────────────────────────

BLOOM_PATTERN = re.compile(r'bloom\s*=\s*["\'](\w+)["\']')


class TestBloomCoverage:
    """Notebooks should exercise multiple Bloom's taxonomy levels."""

    def test_bloom_levels_used(self, notebook: tuple[Path, nbformat.NotebookNode]) -> None:
        """Each notebook exercises at least 2 Bloom's taxonomy levels."""
        path, nb = notebook
        code = "\n".join(_code_cells(nb))
        blooms = set(BLOOM_PATTERN.findall(code))
        if not blooms:
            pytest.skip("no bloom= parameters found")
        assert len(blooms) >= 2, (
            f"{path}: only {len(blooms)} Bloom level(s) ({blooms}), "
            f"minimum 2 for cognitive depth"
        )


# ── Checkpoint Coverage ───────────────────────────────────────────────

class TestCheckpointCoverage:
    """Notebooks with many assessments should include checkpoint summaries."""

    MIN_ASSESSMENTS_FOR_CHECKPOINT = 4

    def test_checkpoint_present_when_needed(
        self, notebook: tuple[Path, nbformat.NotebookNode],
    ) -> None:
        """Notebooks with 4+ assessments should include checkpoint_summary calls."""
        path, nb = notebook
        code = "\n".join(_code_cells(nb))
        assessment_count = len(ASSESSMENT_PATTERN.findall(code))
        if assessment_count < self.MIN_ASSESSMENTS_FOR_CHECKPOINT:
            pytest.skip(f"only {assessment_count} assessments (threshold: {self.MIN_ASSESSMENTS_FOR_CHECKPOINT})")
        has_checkpoint = "checkpoint_summary" in code
        assert has_checkpoint, (
            f"{path}: {assessment_count} assessments but no checkpoint_summary call"
        )


# ── Learning Tracker Integration ──────────────────────────────────────

class TestTrackerIntegration:
    """Every content notebook must integrate the learning tracker."""

    def test_tracker_initialization(self, notebook: tuple[Path, nbformat.NotebookNode]) -> None:
        """Each notebook creates a LearningTracker instance."""
        path, nb = notebook
        code = "\n".join(_code_cells(nb))
        assert "LearningTracker" in code, (
            f"{path}: no LearningTracker initialization found"
        )

    def test_tracker_dashboard_at_end(self, notebook: tuple[Path, nbformat.NotebookNode]) -> None:
        """Each notebook calls tracker.dashboard() near the end."""
        path, nb = notebook
        code_cells = _code_cells(nb)
        if not code_cells:
            pytest.skip("no code cells")
        # Check last 3 code cells for dashboard call
        tail = "\n".join(code_cells[-3:])
        assert "dashboard()" in tail, (
            f"{path}: no tracker.dashboard() call in final code cells"
        )

    def test_tracker_save_at_end(self, notebook: tuple[Path, nbformat.NotebookNode]) -> None:
        """Each notebook saves tracker progress near the end."""
        path, nb = notebook
        code_cells = _code_cells(nb)
        if not code_cells:
            pytest.skip("no code cells")
        tail = "\n".join(code_cells[-3:])
        assert "save()" in tail, (
            f"{path}: no tracker.save() call in final code cells"
        )


# ── Key Insight Pattern ───────────────────────────────────────────────

class TestKeyInsights:
    """Notebooks should have 'Key Insight' callouts for important takeaways."""

    # Interactive dashboards and short notebooks are exempt
    EXEMPT = {"00_dashboard.ipynb"}

    def test_has_key_insights(self, notebook: tuple[Path, nbformat.NotebookNode]) -> None:
        """Notebooks with 5+ sections should have at least one Key Insight callout."""
        path, nb = notebook
        if path.name in self.EXEMPT:
            pytest.skip("interactive dashboard — exempt from insight callouts")
        md_text = "\n".join(_markdown_cells(nb))
        sections = re.findall(r"^#{2,3}\s", md_text, re.MULTILINE)
        if len(sections) < 5:
            pytest.skip(f"only {len(sections)} sections (threshold: 5)")
        has_insight = bool(
            re.search(
                r"key insight|observe:|key fact|result:|proof summary|important|tip:",
                md_text, re.IGNORECASE,
            )
        )
        assert has_insight, (
            f"{path}: {len(sections)} sections but no 'Key Insight' callout"
        )


# ── Cross-Plan Consistency ────────────────────────────────────────────

class TestCrossPlanConsistency:
    """All four plans should cover core concepts."""

    CORE_CONCEPTS = ["stabiliz", "magic", "witness", "ratchet"]

    def test_all_plans_cover_core_concepts(self) -> None:
        """Each plan's notebooks collectively mention all core concepts."""
        plans = {
            "plan_a": sorted(NOTEBOOK_DIR.glob("plan_a/*.ipynb")),
            "plan_b": sorted(NOTEBOOK_DIR.glob("plan_b/*.ipynb")),
            "plan_c": sorted(NOTEBOOK_DIR.glob("plan_c/*.ipynb")),
            "plan_d": sorted(NOTEBOOK_DIR.glob("plan_d/*.ipynb")),
        }
        for plan_name, notebooks in plans.items():
            all_text = ""
            for nb_path in notebooks:
                nb = _read_notebook(nb_path)
                all_text += "\n".join(_markdown_cells(nb) + _code_cells(nb))
            all_text_lower = all_text.lower()
            for concept in self.CORE_CONCEPTS:
                assert concept in all_text_lower, (
                    f"{plan_name}: core concept '{concept}' not found in any notebook"
                )
